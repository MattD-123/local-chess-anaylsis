from __future__ import annotations

import asyncio
import logging
import os
import random
from typing import Any

import chess
import chess.engine

from providers.engine.base import ChessEngine
from schemas.domain import Evaluation, MoveCandidate

logger = logging.getLogger(__name__)


def _score_to_evaluation(score: chess.engine.PovScore | None) -> Evaluation:
    if score is None:
        return Evaluation(cp=0, mate=None, normalized_pawns=0.0)

    white_score = score.white()
    mate = white_score.mate()
    cp = white_score.score()
    if cp is not None:
        return Evaluation(cp=cp, mate=mate, normalized_pawns=cp / 100.0)

    if mate is None:
        return Evaluation(cp=0, mate=None, normalized_pawns=0.0)

    normalized = 100.0 if mate > 0 else -100.0
    return Evaluation(cp=None, mate=mate, normalized_pawns=normalized)


class StockfishLocalProvider(ChessEngine):
    def __init__(
        self,
        path: str,
        think_time_ms: int = 2000,
        default_depth: int = 15,
    ):
        self._path = path
        self._think_time_ms = think_time_ms
        self._default_depth = default_depth
        self._skill_level = 10
        self._engine: chess.engine.SimpleEngine | None = None
        self._lock = asyncio.Lock()
        self._analysis_lock = asyncio.Lock()

    @staticmethod
    def _skill_to_elo(skill_level: int) -> int:
        bounded = max(0, min(20, skill_level))
        # Map 0..20 to ~200..3200.
        return 200 + round((bounded / 20.0) * 3000)

    async def _ensure_engine(self) -> chess.engine.SimpleEngine:
        async with self._lock:
            if self._engine is not None:
                return self._engine

            if not self._path:
                raise RuntimeError("Stockfish path is not configured")
            if not os.path.exists(self._path):
                raise RuntimeError(f"Stockfish binary not found at {self._path}")

            logger.info("Starting Stockfish engine at %s", self._path)
            self._engine = await asyncio.to_thread(chess.engine.SimpleEngine.popen_uci, self._path)
            try:
                await asyncio.to_thread(
                    self._engine.configure,
                    {"Skill Level": max(0, min(20, self._skill_level))},
                )
            except Exception:
                logger.debug("Stockfish does not support Skill Level UCI option", exc_info=True)
            return self._engine

    async def _with_restart(self, fn, *args, **kwargs):
        async with self._analysis_lock:
            try:
                engine = await self._ensure_engine()
                return await asyncio.to_thread(fn, engine, *args, **kwargs)
            except (chess.engine.EngineTerminatedError, BrokenPipeError, RuntimeError) as exc:
                logger.warning("Stockfish operation failed, attempting restart: %s", exc)
                await self._restart_engine()
                engine = await self._ensure_engine()
                return await asyncio.to_thread(fn, engine, *args, **kwargs)

    async def _restart_engine(self) -> None:
        async with self._lock:
            if self._engine is not None:
                try:
                    await asyncio.to_thread(self._engine.quit)
                except Exception:
                    logger.debug("Error while quitting Stockfish", exc_info=True)
                self._engine = None

    async def set_skill_level(self, level: int) -> None:
        self._skill_level = max(0, min(20, level))
        async with self._analysis_lock:
            engine = await self._ensure_engine()
            try:
                await asyncio.to_thread(engine.configure, {"Skill Level": self._skill_level})
            except Exception:
                logger.debug("Stockfish Skill Level option unavailable", exc_info=True)
            # Strength calibration for engines supporting Elo mode.
            # Keep deterministic mapping so slider changes feel consistent game to game.
            try:
                elo = self._skill_to_elo(self._skill_level)
                await asyncio.to_thread(
                    engine.configure,
                    {"UCI_LimitStrength": True, "UCI_Elo": elo},
                )
            except Exception:
                logger.debug("Stockfish UCI strength options unavailable", exc_info=True)

    def _build_limit(
        self,
        depth: int | None = None,
        *,
        use_time: bool = False,
        think_time_ms: int | None = None,
    ) -> chess.engine.Limit:
        if use_time:
            effective_think = think_time_ms if think_time_ms is not None else self._think_time_ms
            return chess.engine.Limit(depth=depth or self._default_depth, time=effective_think / 1000.0)
        return chess.engine.Limit(depth=depth or self._default_depth)

    @staticmethod
    def _parse_candidate(board: chess.Board, info: dict[str, Any]) -> MoveCandidate | None:
        pv = info.get("pv")
        if not pv:
            return None
        move = pv[0]
        san = board.san(move)
        eval_obj = _score_to_evaluation(info.get("score"))
        return MoveCandidate(uci=move.uci(), san=san, evaluation=eval_obj)

    async def evaluate_position(self, fen: str, depth: int) -> Evaluation:
        board = chess.Board(fen)
        limit = self._build_limit(depth, use_time=False)

        def _analyse(engine: chess.engine.SimpleEngine, _board: chess.Board, _limit: chess.engine.Limit):
            return engine.analyse(_board, _limit)

        info = await self._with_restart(_analyse, board, limit)
        return _score_to_evaluation(info.get("score"))

    async def get_top_moves(
        self,
        fen: str,
        n: int,
        depth: int,
        *,
        use_time: bool = False,
        think_time_ms: int | None = None,
    ) -> list[MoveCandidate]:
        board = chess.Board(fen)
        limit = self._build_limit(depth, use_time=use_time, think_time_ms=think_time_ms)

        def _analyse_multi(
            engine: chess.engine.SimpleEngine,
            _board: chess.Board,
            _limit: chess.engine.Limit,
            _n: int,
        ):
            return engine.analyse(_board, _limit, multipv=max(1, _n))

        infos = await self._with_restart(_analyse_multi, board, limit, n)

        if isinstance(infos, dict):
            infos = [infos]

        moves: list[MoveCandidate] = []
        for info in infos:
            candidate = self._parse_candidate(board, info)
            if candidate is not None:
                moves.append(candidate)
        return moves[:n]

    @staticmethod
    def _select_with_skill(top_moves: list[MoveCandidate], skill_level: int) -> MoveCandidate:
        if not top_moves:
            raise RuntimeError("No move candidates available")
        if len(top_moves) == 1:
            return top_moves[0]

        skill = max(0, min(20, skill_level))
        if skill >= 19:
            return top_moves[0]

        # Lower skill explores deeper into candidate list, higher skill focuses on top lines.
        max_candidates = 3 + round((20 - skill) / 4)
        capped = top_moves[: max(2, min(len(top_moves), max_candidates))]

        # Temperature-like rank weighting. High skill strongly favors rank #1.
        alpha = 0.55 + (skill / 12.0)
        rank_weights = [1.0 / ((idx + 1) ** alpha) for idx in range(len(capped))]
        return random.choices(capped, weights=rank_weights, k=1)[0]

    async def get_best_move(
        self,
        fen: str,
        skill_level: int,
        depth: int,
        think_time_ms: int | None = None,
    ) -> MoveCandidate:
        # Make lower skills meaningfully weaker by reducing effective search depth.
        bounded_skill = max(0, min(20, skill_level))
        effective_depth = max(4, round(depth * (0.35 + (0.65 * bounded_skill / 20.0))))
        candidate_count = 3 + round((20 - bounded_skill) / 4)
        top_moves = await self.get_top_moves(
            fen,
            n=max(3, min(8, candidate_count)),
            depth=effective_depth,
            use_time=True,
            think_time_ms=think_time_ms,
        )
        return self._select_with_skill(top_moves, skill_level)

    async def compute_artificial_delay_ms(
        self,
        fen: str,
        *,
        min_ms: int,
        max_ms: int,
        scale_with_complexity: bool,
        depth: int | None = None,
    ) -> int:
        if max_ms <= min_ms:
            return max(0, min_ms)

        if not scale_with_complexity:
            return random.randint(min_ms, max_ms)

        board = chess.Board(fen)
        legal_count = board.legal_moves.count()
        top2 = await self.get_top_moves(fen, n=2, depth=depth or self._default_depth)

        if len(top2) >= 2:
            gap = abs(top2[0].evaluation.normalized_pawns - top2[1].evaluation.normalized_pawns)
        else:
            gap = 1.5

        mobility = min(1.0, legal_count / 40.0)
        closeness = max(0.0, 1.0 - min(gap / 2.0, 1.0))
        complexity = (0.6 * mobility) + (0.4 * closeness)

        midpoint = min_ms + int((max_ms - min_ms) * complexity)
        jitter = int((max_ms - min_ms) * 0.15)
        lower = max(min_ms, midpoint - jitter)
        upper = min(max_ms, midpoint + jitter)
        return random.randint(lower, upper)

    async def health(self) -> tuple[str, str | None]:
        try:
            await self._ensure_engine()
            return "ok", None
        except Exception as exc:
            detail = str(exc).strip()
            if not detail:
                detail = f"{type(exc).__name__}: {exc!r}"
            return "down", detail

    async def close(self) -> None:
        await self._restart_engine()
