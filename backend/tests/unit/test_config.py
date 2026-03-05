import pytest
from pydantic import ValidationError

from config import ConfigStore


def test_config_load_llm_local(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
engine:
  provider: local
  local:
    path: C:/stockfish.exe
    skill_level: 10
    depth: 12
    think_time_ms: 1000
    artificial_delay:
      enabled: true
      min_ms: 50
      max_ms: 100
      scale_with_complexity: true
  api:
    url: https://lichess.org/api/cloud-eval
llm:
  local:
    base_url: http://localhost:11434
    model: llama3.1
commentary:
  on_every_move: false
  min_eval_swing_to_trigger: 0.3
  always_comment_on_blunders: true
  always_comment_on_engine_moves: true
  persona: coach
""".strip(),
        encoding="utf-8",
    )

    store = ConfigStore(config_path)
    config = store.load()
    assert config.llm.local.model == "llama3.1"


def test_config_update_validation_error(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
engine:
  provider: local
  local:
    path: C:/stockfish.exe
    skill_level: 10
    depth: 12
    think_time_ms: 1000
    artificial_delay:
      enabled: true
      min_ms: 50
      max_ms: 100
      scale_with_complexity: true
  api:
    url: https://lichess.org/api/cloud-eval
llm:
  local:
    base_url: http://localhost:11434
    model: llama3.1
commentary:
  on_every_move: false
  min_eval_swing_to_trigger: 0.3
  always_comment_on_blunders: true
  always_comment_on_engine_moves: true
  persona: coach
""".strip(),
        encoding="utf-8",
    )

    store = ConfigStore(config_path)
    store.load()

    with pytest.raises(ValidationError):
        store.update({"engine": {"local": {"skill_level": 40}}})


def test_config_loads_from_example_when_config_missing(tmp_path):
    example_path = tmp_path / "config.example.yaml"
    example_path.write_text(
        """
engine:
  provider: local
  local:
    path: C:/stockfish.exe
    skill_level: 10
    depth: 12
    think_time_ms: 1000
    artificial_delay:
      enabled: true
      min_ms: 50
      max_ms: 100
      scale_with_complexity: true
  api:
    url: https://lichess.org/api/cloud-eval
llm:
  local:
    base_url: http://localhost:11434
    model: llama3.1
commentary:
  on_every_move: false
  min_eval_swing_to_trigger: 0.3
  always_comment_on_blunders: true
  always_comment_on_engine_moves: true
  persona: coach
runtime:
  max_active_sessions: 100
  session_ttl_hours: 6
  cleanup_interval_seconds: 300
""".strip(),
        encoding="utf-8",
    )

    store = ConfigStore(tmp_path / "config.yaml")
    config = store.load()

    assert config.engine.local.path == "C:/stockfish.exe"
