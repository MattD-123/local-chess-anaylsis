from __future__ import annotations

import asyncio
import io
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import chess
import chess.pgn

from config import ConfigStore
from database.repo import ChessRepository
from providers.engine.router import EngineRouter
from providers.llm.router import LLMRouter
from schemas.api import (
    GameOptions,
    GameOptionsPatch,
    GameSettingsResponse,
    HistoryItem,
    HistoryResponse,
    HintResponse,
    MoveResponse,
    NewGameResponse,
    OpeningStatsResponse,
    PgnImportResponse,
    ResignResponse,
)
from schemas.domain import CommentaryContext, Evaluation, HintContext, MoveCandidate, MoveRecord, OpeningInfo
from services.commentary import CommentaryBus
from services.openings import OpeningService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GameSession:
    game_id: str
    player_color: str
    options: GameOptions
    board: chess.Board = field(default_factory=chess.Board)
    move_history: list[MoveRecord] = field(default_factory=list)
    opening: OpeningInfo | None = None
    in_opening: bool = True
    game_over: bool = False
    result: str | None = None
    termination_reason: str | None = None
    engine_thinking: bool = False
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def player_turn(self) -> bool:
        return (self.board.turn and self.player_color == "white") or (
            (not self.board.turn) and self.player_color == "black"
        )

    @property
    def uci_history(self) -> list[str]:
        return [record.uci for record in self.move_history]


class GameService:
    def __init__(
        self,
        config_store: ConfigStore,
        repo: ChessRepository,
        engine_router: EngineRouter,
        llm_router: LLMRouter,
        opening_service: OpeningService,
        commentary_bus: CommentaryBus,
    ):
        self._config_store = config_store
        self._repo = repo
        self._engine_router = engine_router
        self._llm_router = llm_router
        self._opening_service = opening_service
        self._commentary_bus = commentary_bus
        self._sessions: dict[str, GameSession] = {}
        self._cleanup_task: asyncio.Task | None = None

    def _default_game_options(self) -> GameOptions:
        config = self._config_store.get()
        return GameOptions(
            skill_level=config.engine.local.skill_level,
            depth=config.engine.local.depth,
            think_time_ms=config.engine.local.think_time_ms,
            artificial_delay_enabled=config.engine.local.artificial_delay.enabled,
            persona=config.commentary.persona,
        )

    def _merge_game_options(self, base: GameOptions, patch: GameOptionsPatch | None) -> GameOptions:
        if patch is None:
            return base.model_copy(deep=True)
        payload = patch.model_dump(exclude_none=True)
        return base.model_copy(update=payload)

    @staticmethod
    def _touch(session: GameSession) -> None:
        session.last_activity = datetime.now(timezone.utc)

    def _max_sessions(self) -> int:
        return self._config_store.get().runtime.max_active_sessions

    def _session_ttl(self) -> timedelta:
        return timedelta(hours=self._config_store.get().runtime.session_ttl_hours)

    def _cleanup_interval_seconds(self) -> int:
        return self._config_store.get().runtime.cleanup_interval_seconds

    def _check_capacity_or_raise(self) -> None:
        if len(self._sessions) >= self._max_sessions():
            raise ValueError("Maximum active sessions reached. Please try again later.")

    async def start(self) -> None:
        if self._cleanup_task and not self._cleanup_task.done():
            return
        self._cleanup_task = asyncio.create_task(self._session_cleanup_loop())

    async def stop(self) -> None:
        if self._cleanup_task is None:
            return
        self._cleanup_task.cancel()
        try:
            await self._cleanup_task
        except asyncio.CancelledError:
            pass
        self._cleanup_task = None

    async def _session_cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(self._cleanup_interval_seconds())
            try:
                self._cleanup_stale_sessions()
            except Exception:
                logger.exception("Session cleanup loop failed")

    def _cleanup_stale_sessions(self) -> None:
        now = datetime.now(timezone.utc)
        ttl = self._session_ttl()
        stale_ids = [
            game_id
            for game_id, session in self._sessions.items()
            if now - session.last_activity > ttl
        ]
        for game_id in stale_ids:
            self._sessions.pop(game_id, None)
            self._commentary_bus.close_game(game_id)

    def _classify_eval_loss(self, eval_loss: float, legal_move_count: int) -> str:
        if legal_move_count <= 1:
            return "Forced"
        if eval_loss <= 0.10:
            return "Best"
        if eval_loss <= 0.25:
            return "Good"
        if eval_loss <= 0.50:
            return "Inaccuracy"
        if eval_loss <= 1.50:
            return "Mistake"
        return "Blunder"

    @staticmethod
    def _compute_player_eval_loss(player_color: str, before: Evaluation, after: Evaluation) -> float:
        if player_color == "white":
            loss = before.normalized_pawns - after.normalized_pawns
        else:
            loss = after.normalized_pawns - before.normalized_pawns
        return max(0.0, loss)

    @staticmethod
    def _compute_side_eval_loss(side: str, before: Evaluation, after: Evaluation) -> float:
        if side == "white":
            loss = before.normalized_pawns - after.normalized_pawns
        else:
            loss = after.normalized_pawns - before.normalized_pawns
        return max(0.0, loss)

    @staticmethod
    def _leader_from_eval(evaluation: Evaluation) -> str:
        if evaluation.normalized_pawns > 0.2:
            return "white"
        if evaluation.normalized_pawns < -0.2:
            return "black"
        return "neither side"

    @staticmethod
    def _result_for_resign(player_color: str) -> str:
        return "0-1" if player_color == "white" else "1-0"

    @staticmethod
    def _terminal_eval_for_result(result: str) -> Evaluation:
        if result == "1-0":
            return Evaluation(cp=None, mate=1, normalized_pawns=100.0)
        if result == "0-1":
            return Evaluation(cp=None, mate=-1, normalized_pawns=-100.0)
        return Evaluation(cp=0, mate=0, normalized_pawns=0.0)

    def _game_result_from_board(self, board: chess.Board) -> tuple[str, str]:
        outcome = board.outcome(claim_draw=True)
        if outcome is None:
            return "*", "ongoing"
        winner = outcome.winner
        result = "1/2-1/2"
        if winner is True:
            result = "1-0"
        elif winner is False:
            result = "0-1"
        return result, outcome.termination.name.lower()

    @staticmethod
    def _parse_move(board: chess.Board, move_text: str) -> chess.Move:
        try:
            move = chess.Move.from_uci(move_text)
            if move in board.legal_moves:
                return move
        except ValueError:
            pass
        return board.parse_san(move_text)

    def _build_move_response(self, session: GameSession, current_eval: Evaluation) -> MoveResponse:
        return MoveResponse(
            game_id=session.game_id,
            fen=session.board.fen(),
            move_history=session.move_history,
            opening=session.opening,
            current_eval=current_eval,
            game_over=session.game_over,
            result=session.result,
            termination_reason=session.termination_reason,
            engine_thinking=session.engine_thinking,
        )

    async def new_game(
        self,
        player_color: str,
        config_overrides: dict | None = None,
        options_patch: GameOptionsPatch | None = None,
    ) -> NewGameResponse:
        if config_overrides:
            self._config_store.update(config_overrides)

        self._check_capacity_or_raise()
        options = self._merge_game_options(self._default_game_options(), options_patch)
        game_id = str(uuid.uuid4())
        session = GameSession(game_id=game_id, player_color=player_color, options=options)
        self._touch(session)
        self._sessions[game_id] = session

        self._repo.create_game(game_id, player_color, options.skill_level)
        self._commentary_bus.ensure_game(game_id)

        if not session.player_turn():
            session.engine_thinking = True
            asyncio.create_task(self._run_engine_turn(session))

        return NewGameResponse(
            game_id=game_id,
            fen=session.board.fen(),
            player_color=player_color,
            engine_to_move=not session.player_turn(),
            options=session.options,
        )

    async def import_pgn(self, pgn_text: str, player_color: str) -> PgnImportResponse:
        text = (pgn_text or "").strip()
        if not text:
            raise ValueError("PGN content is required")

        parsed = chess.pgn.read_game(io.StringIO(text))
        if parsed is None:
            raise ValueError("Unable to parse PGN")

        self._check_capacity_or_raise()
        options = self._default_game_options()
        game_id = str(uuid.uuid4())
        session = GameSession(game_id=game_id, player_color=player_color, options=options)
        self._touch(session)
        self._sessions[game_id] = session
        self._repo.create_game(game_id, player_color, options.skill_level)
        self._commentary_bus.ensure_game(game_id)

        engine = await self._engine_router.get_active_engine()
        depth = session.options.depth

        for move in parsed.mainline_moves():
            fen_before = session.board.fen()
            color = "white" if session.board.turn else "black"
            move_number = session.board.fullmove_number
            legal_move_count = session.board.legal_moves.count()

            if move not in session.board.legal_moves:
                raise ValueError(f"Invalid PGN move at ply {len(session.move_history) + 1}: {move.uci()}")

            eval_before_task = asyncio.create_task(engine.evaluate_position(fen_before, depth))
            top_moves_task = asyncio.create_task(engine.get_top_moves(fen_before, n=3, depth=depth))

            san = session.board.san(move)
            session.board.push(move)
            fen_after = session.board.fen()

            eval_after_task = asyncio.create_task(engine.evaluate_position(fen_after, depth))
            eval_before, top_moves, eval_after = await asyncio.gather(
                eval_before_task,
                top_moves_task,
                eval_after_task,
            )

            best_move = top_moves[0] if top_moves else None
            eval_loss = self._compute_side_eval_loss(color, eval_before, eval_after)
            classification = self._classify_eval_loss(eval_loss, legal_move_count)
            eval_delta = eval_after.normalized_pawns - eval_before.normalized_pawns

            opening = self._opening_service.detect_opening(fen_after, session.uci_history + [move.uci()])
            if opening:
                session.opening = opening
                session.in_opening = True
            else:
                session.in_opening = False

            move_record = MoveRecord(
                move_number=move_number,
                color=color,
                san=san,
                uci=move.uci(),
                fen_before=fen_before,
                fen_after=fen_after,
                eval_before=eval_before,
                eval_after=eval_after,
                eval_delta=eval_delta,
                classification=classification,
                commentary=None,
                best_move=best_move.uci if best_move else None,
                in_opening=session.in_opening,
            )
            session.move_history.append(move_record)
            self._repo.add_move(session.game_id, move_record)

        result, termination = self._game_result_from_board(session.board)
        header_result = (parsed.headers.get("Result") or "").strip()
        if result == "*" and header_result in {"1-0", "0-1", "1/2-1/2"}:
            result = header_result
        if termination == "ongoing":
            termination = "imported_pgn"

        session.game_over = True
        session.result = result
        session.termination_reason = termination

        pgn_for_storage = str(parsed).strip() or str(chess.pgn.Game.from_board(session.board)).strip()
        self._repo.finalize_game(
            session.game_id,
            result=result,
            termination_reason=termination,
            opening_eco=session.opening.eco if session.opening else None,
            opening_name=session.opening.name if session.opening else None,
            pgn=pgn_for_storage,
            move_count=len(session.move_history),
        )
        self._repo.refresh_opening_stats()

        current_eval = session.move_history[-1].eval_after if session.move_history else Evaluation(normalized_pawns=0.0)
        return PgnImportResponse(
            game_id=session.game_id,
            player_color=session.player_color,
            fen=session.board.fen(),
            move_history=session.move_history,
            opening=session.opening,
            current_eval=current_eval,
            game_over=session.game_over,
            result=session.result,
            termination_reason=session.termination_reason,
            imported_move_count=len(session.move_history),
        )

    def _get_session(self, game_id: str) -> GameSession:
        session = self._sessions.get(game_id)
        if session is None:
            raise ValueError("Game not found")
        self._touch(session)
        return session

    async def update_game_settings(self, game_id: str, patch: GameOptionsPatch) -> GameSettingsResponse:
        session = self._get_session(game_id)
        session.options = self._merge_game_options(session.options, patch)
        self._touch(session)
        return GameSettingsResponse(game_id=game_id, options=session.options)

    @staticmethod
    def _build_pgn_from_move_records(move_history: list[MoveRecord], result: str | None = None) -> str:
        game = chess.pgn.Game()
        node = game
        board = chess.Board()
        for record in move_history:
            move = chess.Move.from_uci(record.uci)
            if move not in board.legal_moves:
                break
            node = node.add_variation(move)
            board.push(move)

        game.headers["Event"] = "Interactive Chess Coach"
        game.headers["Site"] = "Local"
        game.headers["Result"] = result or "*"
        return str(game)

    def export_pgn(self, game_id: str) -> str:
        session = self._sessions.get(game_id)
        if session is not None:
            return self._build_pgn_from_move_records(session.move_history, result=session.result)

        game_row = self._repo.get_game(game_id)
        if not game_row:
            raise ValueError("Game not found")

        pgn = (game_row.get("pgn") or "").strip()
        if pgn:
            return pgn

        move_history = self._repo.get_moves(game_id)
        return self._build_pgn_from_move_records(move_history, result=game_row.get("result"))

    async def submit_player_move(self, game_id: str, move_text: str) -> MoveResponse:
        session = self._get_session(game_id)

        async with session.lock:
            if session.game_over:
                raise ValueError("Game is already complete")
            if not session.player_turn():
                raise ValueError("It is not the player's turn")

            engine = await self._engine_router.get_active_engine()
            app_config = self._config_store.get()
            depth = session.options.depth

            fen_before = session.board.fen()
            color = "white" if session.board.turn else "black"
            move_number = session.board.fullmove_number
            legal_move_count = session.board.legal_moves.count()

            try:
                move = self._parse_move(session.board, move_text)
            except ValueError as exc:
                raise ValueError("Illegal move") from exc

            eval_before_task = asyncio.create_task(engine.evaluate_position(fen_before, depth))
            top_moves_task = asyncio.create_task(engine.get_top_moves(fen_before, n=3, depth=depth))

            san = session.board.san(move)
            session.board.push(move)
            fen_after = session.board.fen()

            eval_after_task = asyncio.create_task(engine.evaluate_position(fen_after, depth))
            try:
                eval_before, top_moves, eval_after = await asyncio.gather(
                    eval_before_task,
                    top_moves_task,
                    eval_after_task,
                )
            except TimeoutError as exc:
                for task in (eval_before_task, top_moves_task, eval_after_task):
                    task.cancel()
                if session.board.move_stack and session.board.peek() == move:
                    session.board.pop()
                await self._commentary_bus.publish(
                    session.game_id,
                    "error",
                    {"message": "Engine queue is busy. Please retry your move."},
                )
                raise ValueError("Engine queue is busy. Please retry your move.") from exc

            best_move = top_moves[0] if top_moves else None
            eval_loss = self._compute_player_eval_loss(session.player_color, eval_before, eval_after)
            classification = self._classify_eval_loss(eval_loss, legal_move_count)
            eval_delta = eval_after.normalized_pawns - eval_before.normalized_pawns

            opening = self._opening_service.detect_opening(fen_after, session.uci_history + [move.uci()])
            if opening:
                session.opening = opening
                session.in_opening = True
                await self._commentary_bus.publish(
                    session.game_id,
                    "opening_update",
                    {"opening": opening.model_dump(mode="json")},
                )
            else:
                session.in_opening = False
                if session.opening is not None:
                    session.opening = OpeningInfo(
                        eco=session.opening.eco,
                        name=session.opening.name,
                        pgn=session.opening.pgn,
                        uci=session.opening.uci,
                        fen=fen_after,
                        variation=session.opening.variation,
                        in_opening=False,
                        moves_remaining=0,
                    )
                    await self._commentary_bus.publish(
                        session.game_id,
                        "opening_update",
                        {"opening": session.opening.model_dump(mode="json")},
                    )

            move_record = MoveRecord(
                move_number=move_number,
                color=color,
                san=san,
                uci=move.uci(),
                fen_before=fen_before,
                fen_after=fen_after,
                eval_before=eval_before,
                eval_after=eval_after,
                eval_delta=eval_delta,
                classification=classification,
                commentary=None,
                best_move=best_move.uci if best_move else None,
                in_opening=session.in_opening,
            )
            session.move_history.append(move_record)
            self._repo.add_move(session.game_id, move_record)

            should_comment = (
                app_config.commentary.on_every_move
                or abs(eval_delta) >= app_config.commentary.min_eval_swing_to_trigger
                or (app_config.commentary.always_comment_on_blunders and classification == "Blunder")
            )
            if should_comment:
                context = CommentaryContext(
                    kind="player_move",
                    persona=session.options.persona,
                    opening=session.opening,
                    move=move_record,
                    best_move=best_move,
                    legal_move_count=legal_move_count,
                    who_was_winning=self._leader_from_eval(eval_before),
                )
                asyncio.create_task(self._stream_commentary(session, context, move_record))

            if session.board.is_game_over(claim_draw=True):
                result, termination = self._game_result_from_board(session.board)
                terminal_eval = self._terminal_eval_for_result(result)
                move_record.eval_after = terminal_eval
                await self._finalize_game(session, result=result, termination_reason=termination)
                return self._build_move_response(session, terminal_eval)

            if not session.player_turn():
                session.engine_thinking = True
                asyncio.create_task(self._run_engine_turn(session))

            self._touch(session)
            return self._build_move_response(session, eval_after)

    async def _run_engine_turn(self, session: GameSession) -> None:
        try:
            async with session.lock:
                if session.game_over or session.player_turn():
                    session.engine_thinking = False
                    return

                config = self._config_store.get()
                engine = await self._engine_router.get_active_engine()
                local_engine = await self._engine_router.get_local_engine()
                depth = session.options.depth
                skill = session.options.skill_level

                fen_before = session.board.fen()
                color = "white" if session.board.turn else "black"
                move_number = session.board.fullmove_number

                eval_before_task = asyncio.create_task(engine.evaluate_position(fen_before, depth))
                best_move_task = asyncio.create_task(
                    engine.get_best_move(
                        fen_before,
                        skill,
                        depth,
                        think_time_ms=session.options.think_time_ms,
                    )
                )

                delay_ms = 0
                if config.engine.provider == "local" and session.options.artificial_delay_enabled:
                    delay_ms = await local_engine.compute_artificial_delay_ms(
                        fen_before,
                        min_ms=config.engine.local.artificial_delay.min_ms,
                        max_ms=config.engine.local.artificial_delay.max_ms,
                        scale_with_complexity=config.engine.local.artificial_delay.scale_with_complexity,
                        depth=depth,
                    )

                eval_before, best_move = await asyncio.gather(eval_before_task, best_move_task)
                if delay_ms > 0:
                    await asyncio.sleep(delay_ms / 1000.0)

                move = chess.Move.from_uci(best_move.uci)
                san = session.board.san(move)
                session.board.push(move)
                fen_after = session.board.fen()

                eval_after = await engine.evaluate_position(fen_after, depth)
                if session.board.is_game_over(claim_draw=True):
                    result, _ = self._game_result_from_board(session.board)
                    eval_after = self._terminal_eval_for_result(result)
                if color == "white":
                    eval_gain = eval_after.normalized_pawns - eval_before.normalized_pawns
                else:
                    eval_gain = eval_before.normalized_pawns - eval_after.normalized_pawns

                opening = self._opening_service.detect_opening(fen_after, session.uci_history + [move.uci()])
                if opening:
                    session.opening = opening
                    session.in_opening = True
                    await self._commentary_bus.publish(
                        session.game_id,
                        "opening_update",
                        {"opening": opening.model_dump(mode="json")},
                    )
                else:
                    session.in_opening = False

                move_record = MoveRecord(
                    move_number=move_number,
                    color=color,
                    san=san,
                    uci=move.uci(),
                    fen_before=fen_before,
                    fen_after=fen_after,
                    eval_before=eval_before,
                    eval_after=eval_after,
                    eval_delta=eval_gain,
                    classification="Engine",
                    commentary=None,
                    best_move=best_move.uci,
                    in_opening=session.in_opening,
                )
                session.move_history.append(move_record)
                self._repo.add_move(session.game_id, move_record)

                await self._commentary_bus.publish(
                    session.game_id,
                    "engine_move",
                    {
                        "move": move_record.model_dump(mode="json"),
                        "fen": session.board.fen(),
                        "eval": eval_after.model_dump(mode="json"),
                    },
                )

                if config.commentary.always_comment_on_engine_moves:
                    context = CommentaryContext(
                        kind="engine_move",
                        persona=session.options.persona,
                        opening=session.opening,
                        move=move_record,
                        tactical_description="Improve coordination and pressure key weaknesses.",
                        threats="Tactical pressure around king safety and central control.",
                    )
                    asyncio.create_task(self._stream_commentary(session, context, move_record))

                if session.board.is_game_over(claim_draw=True):
                    result, termination = self._game_result_from_board(session.board)
                    await self._finalize_game(session, result=result, termination_reason=termination)

                self._touch(session)

        except TimeoutError:
            await self._commentary_bus.publish(
                session.game_id,
                "error",
                {"message": "Engine queue timeout while computing bot move."},
            )
        except Exception as exc:
            logger.exception("Engine turn failed for game %s", session.game_id)
            await self._commentary_bus.publish(
                session.game_id,
                "error",
                {"message": f"Engine turn failed: {exc}"},
            )
        finally:
            session.engine_thinking = False

    async def _stream_commentary(
        self,
        session: GameSession,
        context: CommentaryContext,
        move_record: MoveRecord,
    ) -> None:
        provider = await self._llm_router.get_active_provider()
        text_parts: list[str] = []
        try:
            stream = await provider.get_commentary(context)
            await self._commentary_bus.publish(session.game_id, "status", {"typing": True})
            async for chunk in stream:
                text_parts.append(chunk)
                await self._commentary_bus.publish(
                    session.game_id,
                    "commentary_chunk",
                    {
                        "move_number": move_record.move_number,
                        "color": move_record.color,
                        "chunk": chunk,
                    },
                )
        except Exception as exc:
            logger.warning("Skipping commentary for move due to provider failure: %s", exc)
            await self._commentary_bus.publish(
                session.game_id,
                "error",
                {"message": f"Commentary unavailable: {exc}"},
            )
        finally:
            text = "".join(text_parts).strip()
            if text:
                self._repo.update_move_commentary(
                    session.game_id,
                    move_record.move_number,
                    move_record.color,
                    text,
                )
                for record in session.move_history:
                    if record.move_number == move_record.move_number and record.color == move_record.color:
                        record.commentary = text
                        break

            await self._commentary_bus.publish(
                session.game_id,
                "commentary_done",
                {
                    "move_number": move_record.move_number,
                    "color": move_record.color,
                    "text": text,
                },
            )
            await self._commentary_bus.publish(session.game_id, "status", {"typing": False})

    async def get_hint(self, game_id: str) -> HintResponse:
        session = self._get_session(game_id)
        provider = await self._llm_router.get_active_provider()
        engine = await self._engine_router.get_active_engine()

        top_moves = await engine.get_top_moves(session.board.fen(), n=3, depth=session.options.depth)
        context = HintContext(
            fen=session.board.fen(),
            side_to_move="white" if session.board.turn else "black",
            opening=session.opening,
            top_moves=top_moves,
        )
        hint = await provider.get_hint(context)
        return HintResponse(game_id=game_id, hint=hint)

    async def resign(self, game_id: str) -> ResignResponse:
        session = self._get_session(game_id)
        if session.game_over:
            return ResignResponse(
                game_id=game_id,
                result=session.result or "*",
                termination_reason=session.termination_reason or "unknown",
            )

        result = self._result_for_resign(session.player_color)
        await self._finalize_game(session, result=result, termination_reason="resigned")
        return ResignResponse(game_id=game_id, result=result, termination_reason="resigned")

    async def _finalize_game(self, session: GameSession, *, result: str, termination_reason: str) -> None:
        session.game_over = True
        session.result = result
        session.termination_reason = termination_reason
        self._touch(session)

        game = chess.pgn.Game.from_board(session.board)
        pgn = str(game)

        opening_eco = session.opening.eco if session.opening else None
        opening_name = session.opening.name if session.opening else None

        self._repo.finalize_game(
            session.game_id,
            result=result,
            termination_reason=termination_reason,
            opening_eco=opening_eco,
            opening_name=opening_name,
            pgn=pgn,
            move_count=len(session.move_history),
        )
        self._repo.refresh_opening_stats()

        await self._commentary_bus.publish(
            session.game_id,
            "status",
            {
                "game_over": True,
                "result": result,
                "termination_reason": termination_reason,
            },
        )

    async def get_game_state(self, game_id: str) -> MoveResponse:
        session = self._get_session(game_id)
        engine = await self._engine_router.get_active_engine()
        eval_now = await engine.evaluate_position(session.board.fen(), self._config_store.get().engine.local.depth)
        return self._build_move_response(session, eval_now)

    def get_history(self) -> HistoryResponse:
        rows = self._repo.list_games(limit=100)
        items = [
            HistoryItem(
                game_id=row["id"],
                date=datetime.fromisoformat(row["date"]),
                player_color=row["player_color"],
                result=row.get("result") or "*",
                opening_eco=row.get("opening_eco"),
                opening_name=row.get("opening_name"),
                move_count=row.get("move_count") or 0,
            )
            for row in rows
        ]
        return HistoryResponse(items=items)

    def get_opening_stats(self) -> OpeningStatsResponse:
        self._repo.refresh_opening_stats()
        rows = self._repo.get_opening_stats()
        return OpeningStatsResponse(items=rows)

    async def get_analysis_game_payload(self, game_id: str) -> tuple[GameSession | None, dict | None]:
        session = self._sessions.get(game_id)
        return session, self._repo.get_game(game_id)

    def get_bus(self) -> CommentaryBus:
        return self._commentary_bus
