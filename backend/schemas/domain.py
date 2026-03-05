from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Evaluation(BaseModel):
    cp: int | None = None
    mate: int | None = None
    normalized_pawns: float = 0.0

    model_config = ConfigDict(extra="forbid")


class MoveCandidate(BaseModel):
    uci: str
    san: str | None = None
    evaluation: Evaluation = Field(default_factory=Evaluation)

    model_config = ConfigDict(extra="forbid")


class OpeningInfo(BaseModel):
    eco: str
    name: str
    pgn: str | None = None
    uci: str | None = None
    fen: str
    variation: str | None = None
    in_opening: bool = True
    moves_remaining: int = 0

    model_config = ConfigDict(extra="forbid")


class MoveRecord(BaseModel):
    move_number: int
    color: Literal["white", "black"]
    san: str
    uci: str
    fen_before: str
    fen_after: str
    eval_before: Evaluation
    eval_after: Evaluation
    eval_delta: float
    classification: str
    commentary: str | None = None
    best_move: str | None = None
    in_opening: bool = False

    model_config = ConfigDict(extra="forbid")


class CommentaryContext(BaseModel):
    kind: Literal["player_move", "engine_move", "opening_entry"]
    persona: Literal["coach", "grandmaster", "commentator", "rival"]
    opening: OpeningInfo | None = None
    move: MoveRecord | None = None
    best_move: MoveCandidate | None = None
    legal_move_count: int | None = None
    who_was_winning: str | None = None
    threats: str | None = None
    tactical_description: str | None = None

    model_config = ConfigDict(extra="forbid")


class HintContext(BaseModel):
    fen: str
    side_to_move: Literal["white", "black"]
    opening: OpeningInfo | None = None
    top_moves: list[MoveCandidate] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class CompletedGame(BaseModel):
    game_id: str
    player_color: Literal["white", "black"]
    result: str
    termination_reason: str
    opening: OpeningInfo | None = None
    pgn: str
    move_count: int
    moves: list[MoveRecord] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(extra="forbid")
