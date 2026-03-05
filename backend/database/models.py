from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS games (
  id TEXT PRIMARY KEY,
  date TEXT NOT NULL,
  player_color TEXT NOT NULL,
  result TEXT,
  termination_reason TEXT,
  opening_eco TEXT,
  opening_name TEXT,
  pgn TEXT,
  move_count INTEGER DEFAULT 0,
  engine_skill INTEGER,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS moves (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  game_id TEXT NOT NULL,
  move_number INTEGER NOT NULL,
  color TEXT NOT NULL,
  san TEXT NOT NULL,
  uci TEXT NOT NULL,
  fen_before TEXT NOT NULL,
  fen_after TEXT NOT NULL,
  eval_before REAL,
  eval_after REAL,
  eval_delta REAL,
  classification TEXT,
  commentary TEXT,
  best_move TEXT,
  in_opening INTEGER DEFAULT 0,
  FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS openings (
  eco TEXT,
  name TEXT,
  pgn TEXT,
  uci TEXT,
  fen TEXT
);

CREATE TABLE IF NOT EXISTS opening_stats (
  eco TEXT PRIMARY KEY,
  wins INTEGER NOT NULL DEFAULT 0,
  losses INTEGER NOT NULL DEFAULT 0,
  draws INTEGER NOT NULL DEFAULT 0,
  total_games INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_openings_fen ON openings(fen);
CREATE INDEX IF NOT EXISTS idx_openings_uci ON openings(uci);
CREATE INDEX IF NOT EXISTS idx_moves_game_id ON moves(game_id);
"""


@dataclass(slots=True)
class GameRow:
    id: str
    date: datetime
    player_color: str
    result: str | None
    opening_eco: str | None
    opening_name: str | None
    pgn: str | None
    move_count: int
    engine_skill: int | None
    created_at: datetime


@dataclass(slots=True)
class MoveRow:
    game_id: str
    move_number: int
    color: str
    san: str
    uci: str
    fen_before: str
    fen_after: str
    eval_before: float | None
    eval_after: float | None
    eval_delta: float | None
    classification: str | None
    commentary: str | None
    best_move: str | None
    in_opening: bool


def initialize_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_SQL)
    connection.commit()
