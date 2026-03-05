import importlib

import chess
import pytest
from fastapi.testclient import TestClient


class FakeEngine:
    async def get_best_move(self, fen, skill_level, depth):
        board = chess.Board(fen)
        move = next(iter(board.legal_moves))
        return self._candidate(board, move)

    async def evaluate_position(self, fen, depth):
        from schemas.domain import Evaluation

        board = chess.Board(fen)
        # Slight signal based on side to move to keep values deterministic.
        return Evaluation(cp=10 if board.turn else -10, normalized_pawns=0.1 if board.turn else -0.1)

    async def get_top_moves(self, fen, n, depth):
        board = chess.Board(fen)
        moves = list(board.legal_moves)[:n]
        return [self._candidate(board, move) for move in moves]

    async def set_skill_level(self, level):
        return None

    async def health(self):
        return "ok", None

    async def close(self):
        return None

    async def compute_artificial_delay_ms(self, fen, *, min_ms, max_ms, scale_with_complexity, depth=None):
        return 0

    @staticmethod
    def _candidate(board, move):
        from schemas.domain import Evaluation, MoveCandidate

        return MoveCandidate(uci=move.uci(), san=board.san(move), evaluation=Evaluation(cp=5, normalized_pawns=0.05))


class FakeLLM:
    async def get_commentary(self, context):
        async def _gen():
            yield "Test commentary."

        return _gen()

    async def get_hint(self, context):
        return "Play toward central control."

    async def get_opening_commentary(self, opening, side):
        async def _gen():
            yield "Opening note"

        return _gen()

    async def get_game_summary(self, game):
        return "Summary"


@pytest.fixture
def client(tmp_path, monkeypatch):
    async def _noop_bootstrap(self):
        return None

    monkeypatch.setattr("services.openings.OpeningService.bootstrap_if_needed", _noop_bootstrap)
    monkeypatch.setattr("database.session.get_default_db_path", lambda: tmp_path / "test.db")

    import main

    importlib.reload(main)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
engine:
  provider: local
  local:
    path: C:/stockfish.exe
    skill_level: 10
    depth: 10
    think_time_ms: 300
    artificial_delay:
      enabled: true
      min_ms: 10
      max_ms: 30
      scale_with_complexity: true
  api:
    url: https://lichess.org/api/cloud-eval
llm:
  local:
    base_url: http://localhost:11434
    model: llama3.1
commentary:
  on_every_move: true
  min_eval_swing_to_trigger: 0.1
  always_comment_on_blunders: true
  always_comment_on_engine_moves: true
  persona: coach
""".strip(),
        encoding="utf-8",
    )

    from config import ConfigStore as BaseConfigStore

    class TestConfigStore(BaseConfigStore):
        def __init__(self):
            super().__init__(config_path)

    monkeypatch.setattr(main, "ConfigStore", TestConfigStore)

    with TestClient(main.app) as test_client:
        fake_engine = FakeEngine()
        fake_llm = FakeLLM()

        async def _active_engine():
            return fake_engine

        async def _local_engine():
            return fake_engine

        async def _llm_provider():
            return fake_llm

        test_client.app.state.engine_router.get_active_engine = _active_engine
        test_client.app.state.engine_router.get_local_engine = _local_engine
        test_client.app.state.llm_router.get_active_provider = _llm_provider

        yield test_client


def test_config_and_new_game(client: TestClient):
    config_response = client.get("/config")
    assert config_response.status_code == 200
    assert "engine" in config_response.json()["config"]

    update_response = client.post("/config", json={"patch": {"commentary": {"persona": "rival"}}})
    assert update_response.status_code == 200
    assert update_response.json()["config"]["commentary"]["persona"] == "rival"

    game_response = client.post("/game/new", json={"player_color": "white"})
    assert game_response.status_code == 200
    assert game_response.json()["game_id"]


def test_move_hint_and_health(client: TestClient):
    game = client.post("/game/new", json={"player_color": "white"}).json()
    game_id = game["game_id"]

    move_response = client.post("/game/move", json={"game_id": game_id, "move": "e2e4"})
    assert move_response.status_code == 200

    hint_response = client.get("/game/hint", params={"game_id": game_id})
    assert hint_response.status_code == 200
    assert "central" in hint_response.json()["hint"].lower()

    health_response = client.get("/health")
    assert health_response.status_code == 200
    payload = health_response.json()
    assert "engine" in payload and "llm" in payload and "openings" in payload


def test_import_and_export_pgn(client: TestClient):
    pgn = """
[Event "Example"]
[Site "Local"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
""".strip()

    import_response = client.post("/game/import-pgn", json={"pgn": pgn, "player_color": "white"})
    assert import_response.status_code == 200
    payload = import_response.json()
    assert payload["game_id"]
    assert payload["imported_move_count"] == 6
    assert payload["game_over"] is True

    export_response = client.get("/game/export-pgn", params={"game_id": payload["game_id"]})
    assert export_response.status_code == 200
    exported = export_response.text
    assert "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6" in exported


def test_commentary_sse_smoke(client: TestClient):
    async def fake_stream(game_id):
        yield "event: status\\ndata: {\"typing\": false}\\n\\n"

    bus = client.app.state.game_service.get_bus()
    bus.stream = fake_stream

    with client.stream("GET", "/game/commentary", params={"game_id": "demo"}) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        first_chunk = next(response.iter_lines())
        assert "event: status" in first_chunk
