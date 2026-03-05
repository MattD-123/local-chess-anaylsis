from __future__ import annotations

import logging
import random

import chess
import httpx

from providers.engine.base import ChessEngine
from schemas.domain import Evaluation, MoveCandidate

logger = logging.getLogger(__name__)


class StockfishAPIProvider(ChessEngine):
    def __init__(self, base_url: str, timeout_seconds: float = 10.0):
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._skill_level = 20

    async def set_skill_level(self, level: int) -> None:
        self._skill_level = max(0, min(20, level))

    @staticmethod
    def _parse_eval_from_pv(pv: dict) -> Evaluation:
        cp = pv.get("cp")
        mate = pv.get("mate")
        if cp is not None:
            return Evaluation(cp=int(cp), mate=mate, normalized_pawns=float(cp) / 100.0)
        if mate is not None:
            normalized = 100.0 if mate > 0 else -100.0
            return Evaluation(cp=None, mate=int(mate), normalized_pawns=normalized)
        return Evaluation(cp=0, mate=None, normalized_pawns=0.0)

    async def _fetch(self, fen: str, depth: int, multipv: int) -> dict:
        params = {
            "fen": fen,
            "multiPv": max(1, multipv),
            "depth": depth,
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.get(self._base_url, params=params)
            response.raise_for_status()
            return response.json()

    async def evaluate_position(self, fen: str, depth: int) -> Evaluation:
        payload = await self._fetch(fen, depth=depth, multipv=1)
        pvs = payload.get("pvs") or []
        if not pvs:
            return Evaluation(cp=0, mate=None, normalized_pawns=0.0)
        return self._parse_eval_from_pv(pvs[0])

    async def get_top_moves(self, fen: str, n: int, depth: int) -> list[MoveCandidate]:
        payload = await self._fetch(fen, depth=depth, multipv=n)
        pvs = payload.get("pvs") or []
        board = chess.Board(fen)
        candidates: list[MoveCandidate] = []
        for pv in pvs[:n]:
            move_line = (pv.get("moves") or "").split()
            if not move_line:
                continue
            first = move_line[0]
            try:
                move = chess.Move.from_uci(first)
                san = board.san(move) if move in board.legal_moves else first
            except Exception:
                san = first
            candidates.append(
                MoveCandidate(
                    uci=first,
                    san=san,
                    evaluation=self._parse_eval_from_pv(pv),
                )
            )
        return candidates

    async def get_best_move(
        self,
        fen: str,
        skill_level: int,
        depth: int,
        think_time_ms: int | None = None,
    ) -> MoveCandidate:
        top = await self.get_top_moves(fen, n=3, depth=depth)
        if not top:
            raise RuntimeError("No best move returned from cloud engine")

        if len(top) == 1:
            return top[0]

        # Approximate lower skill by occasionally selecting the second move.
        if skill_level < 12 and len(top) > 1:
            threshold = (12 - skill_level) / 20.0
            if threshold > 0 and random.random() < threshold:
                return top[1]
        return top[0]

    async def health(self) -> tuple[str, str | None]:
        try:
            await self._fetch(chess.STARTING_FEN, depth=8, multipv=1)
            return "ok", None
        except Exception as exc:
            logger.warning("Engine API health degraded: %s", exc)
            return "degraded", str(exc)

    async def close(self) -> None:
        return None
