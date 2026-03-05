from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from schemas.domain import CommentaryContext, CompletedGame, HintContext, OpeningInfo


class LLMProvider(ABC):
    @abstractmethod
    async def get_commentary(self, context: CommentaryContext) -> AsyncIterator[str]:
        raise NotImplementedError

    @abstractmethod
    async def get_hint(self, context: HintContext) -> str:
        raise NotImplementedError

    @abstractmethod
    async def get_opening_commentary(self, opening: OpeningInfo, side: str) -> AsyncIterator[str]:
        raise NotImplementedError

    @abstractmethod
    async def get_game_summary(self, game: CompletedGame) -> str:
        raise NotImplementedError

    @abstractmethod
    async def health(self) -> tuple[str, str | None]:
        raise NotImplementedError
