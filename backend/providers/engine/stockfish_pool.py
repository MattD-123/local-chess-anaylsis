from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Any, Awaitable, Callable

from providers.engine.base import ChessEngine
from providers.engine.stockfish_local import StockfishLocalProvider
from schemas.domain import Evaluation, MoveCandidate


class StockfishPoolProvider(ChessEngine):
    def __init__(
        self,
        *,
        path: str,
        think_time_ms: int,
        default_depth: int,
        pool_size: int,
        max_queue_size: int,
        queue_timeout_ms: int,
    ):
        self._pool_size = max(1, pool_size)
        self._workers: list[StockfishLocalProvider] = [
            StockfishLocalProvider(path=path, think_time_ms=think_time_ms, default_depth=default_depth)
            for _ in range(self._pool_size)
        ]
        self._in_flight: list[int] = [0] * self._pool_size
        self._select_lock = asyncio.Lock()
        self._max_queue_size = max(1, max_queue_size)
        self._slots = asyncio.Semaphore(self._max_queue_size)
        self._queue_timeout_seconds = max(0.1, queue_timeout_ms / 1000.0)
        self._wait_samples_ms: deque[float] = deque(maxlen=200)
        self._skill_level = 10
        self._timeouts = 0
        self._last_healthy = self._pool_size

    async def _acquire_slot(self) -> float:
        start = time.monotonic()
        try:
            await asyncio.wait_for(self._slots.acquire(), timeout=self._queue_timeout_seconds)
        except TimeoutError as exc:
            self._timeouts += 1
            raise TimeoutError("Engine queue timeout") from exc
        wait_ms = (time.monotonic() - start) * 1000.0
        self._wait_samples_ms.append(wait_ms)
        return wait_ms

    async def _acquire_worker_index(self) -> int:
        async with self._select_lock:
            index = min(range(len(self._workers)), key=lambda idx: self._in_flight[idx])
            self._in_flight[index] += 1
            return index

    async def _release_worker_index(self, index: int) -> None:
        async with self._select_lock:
            self._in_flight[index] = max(0, self._in_flight[index] - 1)

    async def _run_with_worker(self, action: Callable[[StockfishLocalProvider], Awaitable[Any]]) -> Any:
        await self._acquire_slot()
        worker_index = await self._acquire_worker_index()
        worker = self._workers[worker_index]
        try:
            return await action(worker)
        finally:
            await self._release_worker_index(worker_index)
            self._slots.release()

    async def set_skill_level(self, level: int) -> None:
        self._skill_level = max(0, min(20, level))
        await asyncio.gather(*(worker.set_skill_level(self._skill_level) for worker in self._workers))

    async def get_best_move(
        self,
        fen: str,
        skill_level: int,
        depth: int,
        think_time_ms: int | None = None,
    ) -> MoveCandidate:
        return await self._run_with_worker(
            lambda worker: worker.get_best_move(
                fen,
                skill_level,
                depth,
                think_time_ms=think_time_ms,
            )
        )

    async def evaluate_position(self, fen: str, depth: int) -> Evaluation:
        return await self._run_with_worker(lambda worker: worker.evaluate_position(fen, depth))

    async def get_top_moves(self, fen: str, n: int, depth: int) -> list[MoveCandidate]:
        return await self._run_with_worker(lambda worker: worker.get_top_moves(fen, n, depth))

    async def compute_artificial_delay_ms(
        self,
        fen: str,
        *,
        min_ms: int,
        max_ms: int,
        scale_with_complexity: bool,
        depth: int | None = None,
    ) -> int:
        return await self._run_with_worker(
            lambda worker: worker.compute_artificial_delay_ms(
                fen,
                min_ms=min_ms,
                max_ms=max_ms,
                scale_with_complexity=scale_with_complexity,
                depth=depth,
            )
        )

    async def health(self) -> tuple[str, str | None]:
        statuses = await asyncio.gather(*(worker.health() for worker in self._workers))
        healthy = sum(1 for status, _ in statuses if status == "ok")
        self._last_healthy = healthy
        if healthy == len(self._workers):
            return "ok", None
        details = [detail for status, detail in statuses if status != "ok" and detail]
        return "degraded", "; ".join(details) if details else f"{healthy}/{len(self._workers)} workers healthy"

    def metrics(self) -> dict[str, Any]:
        current_running = sum(self._in_flight)
        available = getattr(self._slots, "_value", 0)
        queue_depth = max(0, self._max_queue_size - available - current_running)
        avg_wait = sum(self._wait_samples_ms) / len(self._wait_samples_ms) if self._wait_samples_ms else 0.0
        return {
            "workers_total": len(self._workers),
            "workers_healthy": self._last_healthy,
            "in_flight_requests": current_running,
            "queue_depth": int(max(0, queue_depth)),
            "avg_wait_ms": round(avg_wait, 2),
            "queue_timeout_count": self._timeouts,
        }

    async def close(self) -> None:
        await asyncio.gather(*(worker.close() for worker in self._workers))
