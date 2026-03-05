from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from schemas.api import GameOptions
from schemas.domain import Evaluation
from services.game import GameService, GameSession


def _service() -> GameService:
    return GameService(  # type: ignore[arg-type]
        config_store=None,
        repo=None,
        engine_router=None,
        llm_router=None,
        opening_service=None,
        commentary_bus=None,
    )


def test_classification_thresholds():
    service = _service()
    assert service._classify_eval_loss(0.05, 10) == "Best"
    assert service._classify_eval_loss(0.20, 10) == "Good"
    assert service._classify_eval_loss(0.40, 10) == "Inaccuracy"
    assert service._classify_eval_loss(1.00, 10) == "Mistake"
    assert service._classify_eval_loss(2.00, 10) == "Blunder"
    assert service._classify_eval_loss(1.00, 1) == "Forced"


def test_player_eval_loss_by_color():
    before = Evaluation(cp=50, normalized_pawns=0.5)
    after = Evaluation(cp=10, normalized_pawns=0.1)

    white_loss = GameService._compute_player_eval_loss("white", before, after)
    black_loss = GameService._compute_player_eval_loss("black", before, after)

    assert white_loss == 0.4
    assert black_loss == 0.0


@pytest.mark.asyncio
async def test_checkmate_result_forces_terminal_eval_sign_for_winner():
    config = SimpleNamespace(
        commentary=SimpleNamespace(
            on_every_move=False,
            min_eval_swing_to_trigger=99.0,
            always_comment_on_blunders=False,
            always_comment_on_engine_moves=False,
        )
    )
    config_store = Mock()
    config_store.get.return_value = config

    engine = Mock()
    engine.evaluate_position = AsyncMock(
        side_effect=[
            Evaluation(cp=250, normalized_pawns=2.5),
            # Simulate a sign error from engine score conversion on terminal nodes.
            Evaluation(cp=None, mate=-1, normalized_pawns=-100.0),
        ]
    )
    engine.get_top_moves = AsyncMock(return_value=[])

    engine_router = Mock()
    engine_router.get_active_engine = AsyncMock(return_value=engine)

    repo = Mock()
    repo.add_move = Mock()
    repo.finalize_game = Mock()
    repo.refresh_opening_stats = Mock()

    opening_service = Mock()
    opening_service.detect_opening = Mock(return_value=None)

    commentary_bus = Mock()
    commentary_bus.publish = AsyncMock()

    service = GameService(
        config_store=config_store,
        repo=repo,
        engine_router=engine_router,
        llm_router=Mock(),
        opening_service=opening_service,
        commentary_bus=commentary_bus,
    )

    session = GameSession(
        game_id="game-1",
        player_color="white",
        options=GameOptions(
            skill_level=10,
            depth=10,
            think_time_ms=250,
            artificial_delay_enabled=False,
            persona="coach",
        ),
    )
    service._sessions["game-1"] = session
    for san in ["e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6"]:
        session.board.push_san(san)

    response = await service.submit_player_move("game-1", "h5f7")

    assert response.game_over is True
    assert response.result == "1-0"
    assert response.current_eval.normalized_pawns == 100.0
    assert session.move_history[-1].eval_after.normalized_pawns == 100.0
