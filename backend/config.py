from __future__ import annotations

import copy
import os
import re
from pathlib import Path
from threading import RLock
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


class ArtificialDelayConfig(BaseModel):
    enabled: bool = True
    min_ms: int = 500
    max_ms: int = 4000
    scale_with_complexity: bool = True

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_bounds(self) -> "ArtificialDelayConfig":
        if self.min_ms < 0 or self.max_ms < 0:
            raise ValueError("artificial delay bounds must be non-negative")
        if self.min_ms > self.max_ms:
            raise ValueError("artificial delay min_ms must be <= max_ms")
        return self


class EngineLocalConfig(BaseModel):
    path: str
    skill_level: int = 10
    depth: int = 15
    think_time_ms: int = 2000
    artificial_delay: ArtificialDelayConfig = Field(default_factory=ArtificialDelayConfig)

    model_config = ConfigDict(extra="forbid")

    @field_validator("skill_level")
    @classmethod
    def validate_skill_level(cls, value: int) -> int:
        if not 0 <= value <= 20:
            raise ValueError("engine.local.skill_level must be between 0 and 20")
        return value

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("engine.local.depth must be > 0")
        return value

    @field_validator("think_time_ms")
    @classmethod
    def validate_think_time(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("engine.local.think_time_ms must be > 0")
        return value


class EngineApiConfig(BaseModel):
    url: str = "https://lichess.org/api/cloud-eval"

    model_config = ConfigDict(extra="forbid")


class EngineConfig(BaseModel):
    provider: Literal["local", "api"] = "local"
    local: EngineLocalConfig
    api: EngineApiConfig = Field(default_factory=EngineApiConfig)

    model_config = ConfigDict(extra="forbid")


class LLMLocalConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1"

    model_config = ConfigDict(extra="forbid")


class LLMConfig(BaseModel):
    local: LLMLocalConfig = Field(default_factory=LLMLocalConfig)

    model_config = ConfigDict(extra="forbid")


class CommentaryConfig(BaseModel):
    on_every_move: bool = False
    min_eval_swing_to_trigger: float = 0.3
    always_comment_on_blunders: bool = True
    always_comment_on_engine_moves: bool = True
    persona: Literal["coach", "grandmaster", "commentator", "rival"] = "coach"

    model_config = ConfigDict(extra="forbid")

    @field_validator("min_eval_swing_to_trigger")
    @classmethod
    def validate_eval_swing(cls, value: float) -> float:
        if value < 0:
            raise ValueError("commentary.min_eval_swing_to_trigger must be >= 0")
        return value


class AppConfig(BaseModel):
    engine: EngineConfig
    llm: LLMConfig
    commentary: CommentaryConfig = Field(default_factory=CommentaryConfig)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_provider_requirements(self) -> "AppConfig":
        if self.engine.provider == "local" and not self.engine.local.path:
            raise ValueError("engine.local.path is required when engine.provider is local")
        return self


def _interpolate_env(value: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        env_key = match.group(1)
        return os.getenv(env_key, "")

    return ENV_PATTERN.sub(_replace, value)


def resolve_env_placeholders(data: Any) -> Any:
    if isinstance(data, dict):
        return {key: resolve_env_placeholders(val) for key, val in data.items()}
    if isinstance(data, list):
        return [resolve_env_placeholders(item) for item in data]
    if isinstance(data, str):
        return _interpolate_env(data)
    return data


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in patch.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def get_default_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config.yaml"


class ConfigStore:
    def __init__(self, config_path: Path | None = None):
        self._config_path = config_path or get_default_config_path()
        self._lock = RLock()
        self._raw_data: dict[str, Any] = {}
        self._config: AppConfig | None = None
        self._last_mtime_ns: int | None = None

    @property
    def path(self) -> Path:
        return self._config_path

    def load(self) -> AppConfig:
        with self._lock:
            if not self._config_path.exists():
                raise FileNotFoundError(f"Config not found at {self._config_path}")
            raw = yaml.safe_load(self._config_path.read_text(encoding="utf-8")) or {}
            interpolated = resolve_env_placeholders(raw)
            config = AppConfig.model_validate(interpolated)
            self._raw_data = raw
            self._config = config
            self._last_mtime_ns = self._config_path.stat().st_mtime_ns
            return config

    def _config_file_changed(self) -> bool:
        if self._last_mtime_ns is None:
            return True
        if not self._config_path.exists():
            return False
        return self._config_path.stat().st_mtime_ns > self._last_mtime_ns

    def get(self) -> AppConfig:
        with self._lock:
            if self._config is None or self._config_file_changed():
                return self.load()
            return self._config.model_copy(deep=True)

    def get_dict(self, *, resolved: bool = True) -> dict[str, Any]:
        with self._lock:
            if self._config is None or self._config_file_changed():
                self.load()
            if resolved:
                return self._config.model_dump(mode="json") if self._config else {}
            return copy.deepcopy(self._raw_data)

    def update(self, patch: dict[str, Any]) -> AppConfig:
        with self._lock:
            if self._config is None:
                self.load()
            current_raw = copy.deepcopy(self._raw_data)
            merged_raw = deep_merge(current_raw, patch)
            interpolated = resolve_env_placeholders(merged_raw)

            try:
                validated = AppConfig.model_validate(interpolated)
            except ValidationError:
                raise

            self._raw_data = merged_raw
            self._config = validated
            serialized = yaml.safe_dump(merged_raw, sort_keys=False)
            self._config_path.write_text(serialized, encoding="utf-8")
            self._last_mtime_ns = self._config_path.stat().st_mtime_ns
            return validated.model_copy(deep=True)
