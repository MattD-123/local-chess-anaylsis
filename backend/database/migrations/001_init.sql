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
