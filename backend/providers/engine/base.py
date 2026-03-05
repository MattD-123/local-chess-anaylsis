from __future__ import annotations

from abc import ABC, abstractmethod

from schemas.domain import Evaluation, MoveCandidate


class ChessEngine(ABC):
    @abstractmethod
    async def get_best_move(self, fen: str, skill_level: int, depth: int) -> MoveCandidate:
        raise NotImplementedError

    @abstractmethod
    async def evaluate_position(self, fen: str, depth: int) -> Evaluation:
        raise NotImplementedError

    @abstractmethod
    async def get_top_moves(self, fen: str, n: int, depth: int) -> list[MoveCandidate]:
        raise NotImplementedError

    @abstractmethod
    async def set_skill_level(self, level: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def health(self) -> tuple[str, str | None]:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError
