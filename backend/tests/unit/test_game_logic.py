from schemas.domain import Evaluation
from services.game import GameService


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
    assert service._classify_eval_loss(0.05) == "Best"
    assert service._classify_eval_loss(0.20) == "Good"
    assert service._classify_eval_loss(0.40) == "Inaccuracy"
    assert service._classify_eval_loss(1.00) == "Mistake"
    assert service._classify_eval_loss(2.00) == "Blunder"


def test_player_eval_loss_by_color():
    before = Evaluation(cp=50, normalized_pawns=0.5)
    after = Evaluation(cp=10, normalized_pawns=0.1)

    white_loss = GameService._compute_player_eval_loss("white", before, after)
    black_loss = GameService._compute_player_eval_loss("black", before, after)

    assert white_loss == 0.4
    assert black_loss == 0.0
