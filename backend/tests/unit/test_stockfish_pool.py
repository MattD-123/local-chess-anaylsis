import asyncio

import pytest

from providers.engine.stockfish_pool import StockfishPoolProvider
from schemas.domain import Evaluation, MoveCandidate


class FakeWorker:
    delay_seconds = 0.0

    def __init__(self, path: str, think_time_ms: int, default_depth: int):
        self.path = path
        self.think_time_ms = think_time_ms
        self.default_depth = default_depth

    async def set_skill_level(self, level: int) -> None:
        return None

    async def get_best_move(self, fen: str, skill_level: int, depth: int, think_time_ms: int | None = None):
        await asyncio.sleep(self.delay_seconds)
        return MoveCandidate(uci="e2e4", san="e4", evaluation=Evaluation(normalized_pawns=0.1))

    async def evaluate_position(self, fen: str, depth: int):
        await asyncio.sleep(self.delay_seconds)
        return Evaluation(cp=10, normalized_pawns=0.1)

    async def get_top_moves(self, fen: str, n: int, depth: int):
        await asyncio.sleep(self.delay_seconds)
        return [MoveCandidate(uci="e2e4", san="e4", evaluation=Evaluation(normalized_pawns=0.1))]

    async def compute_artificial_delay_ms(
        self,
        fen: str,
        *,
        min_ms: int,
        max_ms: int,
        scale_with_complexity: bool,
        depth: int | None = None,
    ) -> int:
        return 0

    async def health(self):
        return "ok", None

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_pool_reports_metrics(monkeypatch):
    monkeypatch.setattr("providers.engine.stockfish_pool.StockfishLocalProvider", FakeWorker)
    FakeWorker.delay_seconds = 0.02

    pool = StockfishPoolProvider(
        path="ignored",
        think_time_ms=100,
        default_depth=8,
        pool_size=2,
        max_queue_size=4,
        queue_timeout_ms=500,
    )
    try:
        await asyncio.gather(
            pool.evaluate_position("startpos", 8),
            pool.evaluate_position("startpos", 8),
        )
        metrics = pool.metrics()
        assert metrics["workers_total"] == 2
        assert "avg_wait_ms" in metrics
    finally:
        await pool.close()


@pytest.mark.asyncio
async def test_pool_queue_timeout(monkeypatch):
    monkeypatch.setattr("providers.engine.stockfish_pool.StockfishLocalProvider", FakeWorker)
    FakeWorker.delay_seconds = 0.2

    pool = StockfishPoolProvider(
        path="ignored",
        think_time_ms=100,
        default_depth=8,
        pool_size=1,
        max_queue_size=1,
        queue_timeout_ms=20,
    )
    try:
        first = asyncio.create_task(pool.evaluate_position("startpos", 8))
        await asyncio.sleep(0.01)
        with pytest.raises(TimeoutError):
            await pool.evaluate_position("startpos", 8)
        await first
        assert pool.metrics()["queue_timeout_count"] >= 1
    finally:
        await pool.close()
