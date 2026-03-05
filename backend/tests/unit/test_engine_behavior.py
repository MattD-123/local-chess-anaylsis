import asyncio

from providers.engine.stockfish_local import StockfishLocalProvider
from schemas.domain import Evaluation, MoveCandidate


def test_skill_selection_allows_weaker_choices():
    top = [
        MoveCandidate(uci="e2e4", san="e4", evaluation=Evaluation(normalized_pawns=0.5)),
        MoveCandidate(uci="d2d4", san="d4", evaluation=Evaluation(normalized_pawns=0.4)),
        MoveCandidate(uci="g1f3", san="Nf3", evaluation=Evaluation(normalized_pawns=0.3)),
    ]

    picks = {candidate.uci: 0 for candidate in top}
    for _ in range(200):
        chosen = StockfishLocalProvider._select_with_skill(top, skill_level=2)
        picks[chosen.uci] += 1

    assert picks["e2e4"] < 200
    assert picks["d2d4"] > 0 or picks["g1f3"] > 0


def test_artificial_delay_within_bounds(monkeypatch):
    provider = StockfishLocalProvider(path="/tmp/stockfish")

    async def fake_top_moves(*args, **kwargs):
        return [
            MoveCandidate(uci="e2e4", san="e4", evaluation=Evaluation(normalized_pawns=0.3)),
            MoveCandidate(uci="d2d4", san="d4", evaluation=Evaluation(normalized_pawns=0.25)),
        ]

    monkeypatch.setattr(provider, "get_top_moves", fake_top_moves)

    delay = asyncio.run(
        provider.compute_artificial_delay_ms(
            "8/8/8/8/8/8/8/K6k w - - 0 1",
            min_ms=100,
            max_ms=300,
            scale_with_complexity=True,
            depth=8,
        )
    )
    assert 100 <= delay <= 300
