from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any


class CommentaryBus:
    def __init__(self):
        self._queues: dict[str, asyncio.Queue[tuple[str, dict[str, Any]]]] = defaultdict(asyncio.Queue)

    def ensure_game(self, game_id: str) -> None:
        _ = self._queues[game_id]

    async def publish(self, game_id: str, event: str, data: dict[str, Any]) -> None:
        await self._queues[game_id].put((event, data))

    async def stream(self, game_id: str) -> AsyncIterator[str]:
        queue = self._queues[game_id]
        while True:
            try:
                event, payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield self._format(event, payload)
            except asyncio.TimeoutError:
                yield self._format("heartbeat", {"game_id": game_id})

    @staticmethod
    def _format(event: str, payload: dict[str, Any]) -> str:
        return f"event: {event}\ndata: {json.dumps(payload)}\n\n"

    def close_game(self, game_id: str) -> None:
        self._queues.pop(game_id, None)
