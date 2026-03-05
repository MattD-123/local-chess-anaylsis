from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from schemas.domain import CompletedGame, Evaluation, MoveRecord, OpeningInfo


class GameOptions(BaseModel):
    skill_level: int = Field(ge=0, le=20)
    depth: int = Field(gt=0)
    think_time_ms: int = Field(gt=0)
    artificial_delay_enabled: bool = True
    persona: Literal["coach", "grandmaster", "commentator", "rival"] = "coach"

    model_config = ConfigDict(extra="forbid")


class GameOptionsPatch(BaseModel):
    skill_level: int | None = Field(default=None, ge=0, le=20)
    depth: int | None = Field(default=None, gt=0)
    think_time_ms: int | None = Field(default=None, gt=0)
    artificial_delay_enabled: bool | None = None
    persona: Literal["coach", "grandmaster", "commentator", "rival"] | None = None

    model_config = ConfigDict(extra="forbid")


class NewGameRequest(BaseModel):
    player_color: Literal["white", "black"] = "white"
    config_overrides: dict[str, Any] | None = None
    options: GameOptionsPatch | None = None

    model_config = ConfigDict(extra="forbid")


class NewGameResponse(BaseModel):
    game_id: str
    fen: str
    player_color: Literal["white", "black"]
    engine_to_move: bool
    options: GameOptions


class MoveRequest(BaseModel):
    game_id: str
    move: str

    model_config = ConfigDict(extra="forbid")


class MoveResponse(BaseModel):
    game_id: str
    fen: str
    move_history: list[MoveRecord]
    opening: OpeningInfo | None = None
    current_eval: Evaluation
    game_over: bool
    result: str | None = None
    termination_reason: str | None = None
    engine_thinking: bool = False


class GameSettingsRequest(BaseModel):
    game_id: str
    options: GameOptionsPatch

    model_config = ConfigDict(extra="forbid")


class GameSettingsResponse(BaseModel):
    game_id: str
    options: GameOptions


class PgnImportRequest(BaseModel):
    pgn: str
    player_color: Literal["white", "black"] = "white"

    model_config = ConfigDict(extra="forbid")


class PgnImportResponse(BaseModel):
    game_id: str
    player_color: Literal["white", "black"]
    fen: str
    move_history: list[MoveRecord]
    opening: OpeningInfo | None = None
    current_eval: Evaluation
    game_over: bool
    result: str | None = None
    termination_reason: str | None = None
    imported_move_count: int


class HintRequest(BaseModel):
    game_id: str

    model_config = ConfigDict(extra="forbid")


class HintResponse(BaseModel):
    game_id: str
    hint: str


class ResignRequest(BaseModel):
    game_id: str

    model_config = ConfigDict(extra="forbid")


class ResignResponse(BaseModel):
    game_id: str
    result: str
    termination_reason: str


class AnalysisResponse(BaseModel):
    game: CompletedGame
    summary: str | None = None


class HistoryItem(BaseModel):
    game_id: str
    date: datetime
    player_color: str
    result: str
    opening_eco: str | None = None
    opening_name: str | None = None
    move_count: int


class HistoryResponse(BaseModel):
    items: list[HistoryItem]


class OpeningStatsItem(BaseModel):
    eco: str
    wins: int
    losses: int
    draws: int
    total_games: int


class OpeningStatsResponse(BaseModel):
    items: list[OpeningStatsItem]


class ConfigResponse(BaseModel):
    config: dict[str, Any]


class ConfigUpdateRequest(BaseModel):
    patch: dict[str, Any]


class ProviderHealth(BaseModel):
    status: Literal["ok", "degraded", "down"]
    detail: str | None = None
    metrics: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    engine: ProviderHealth
    llm: ProviderHealth
    openings: ProviderHealth
    timestamp: datetime


class SSEEvent(BaseModel):
    event: str
    data: dict[str, Any] = Field(default_factory=dict)
