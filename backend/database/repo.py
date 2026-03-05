from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable

from database import models
from database.session import SQLiteSessionManager
from schemas.domain import Evaluation, MoveRecord


class ChessRepository:
    def __init__(self, session_manager: SQLiteSessionManager):
        self._session_manager = session_manager

    def initialize(self) -> None:
        with self._session_manager.connect() as conn:
            models.initialize_schema(conn)

    def create_game(self, game_id: str, player_color: str, engine_skill: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._session_manager.connect() as conn:
            conn.execute(
                """
                INSERT INTO games
                (id, date, player_color, result, termination_reason, opening_eco, opening_name, pgn, move_count, engine_skill, created_at)
                VALUES (?, ?, ?, NULL, NULL, NULL, NULL, NULL, 0, ?, ?)
                """,
                (game_id, now, player_color, engine_skill, now),
            )
            conn.commit()

    def finalize_game(
        self,
        game_id: str,
        *,
        result: str,
        termination_reason: str,
        opening_eco: str | None,
        opening_name: str | None,
        pgn: str,
        move_count: int,
    ) -> None:
        with self._session_manager.connect() as conn:
            conn.execute(
                """
                UPDATE games
                SET result = ?, termination_reason = ?, opening_eco = ?, opening_name = ?, pgn = ?, move_count = ?
                WHERE id = ?
                """,
                (result, termination_reason, opening_eco, opening_name, pgn, move_count, game_id),
            )
            conn.commit()

    def add_move(self, game_id: str, move: MoveRecord) -> None:
        with self._session_manager.connect() as conn:
            conn.execute(
                """
                INSERT INTO moves
                (game_id, move_number, color, san, uci, fen_before, fen_after,
                 eval_before, eval_after, eval_delta, classification, commentary, best_move, in_opening)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id,
                    move.move_number,
                    move.color,
                    move.san,
                    move.uci,
                    move.fen_before,
                    move.fen_after,
                    move.eval_before.normalized_pawns,
                    move.eval_after.normalized_pawns,
                    move.eval_delta,
                    move.classification,
                    move.commentary,
                    move.best_move,
                    1 if move.in_opening else 0,
                ),
            )
            conn.commit()

    def update_move_commentary(self, game_id: str, move_number: int, color: str, commentary: str) -> None:
        with self._session_manager.connect() as conn:
            conn.execute(
                """
                UPDATE moves
                SET commentary = ?
                WHERE game_id = ? AND move_number = ? AND color = ?
                """,
                (commentary, game_id, move_number, color),
            )
            conn.commit()

    def get_game(self, game_id: str):
        with self._session_manager.connect() as conn:
            row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
            return dict(row) if row else None

    def get_moves(self, game_id: str) -> list[MoveRecord]:
        with self._session_manager.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM moves
                WHERE game_id = ?
                ORDER BY id ASC
                """,
                (game_id,),
            ).fetchall()

        moves: list[MoveRecord] = []
        for row in rows:
            moves.append(
                MoveRecord(
                    move_number=row["move_number"],
                    color=row["color"],
                    san=row["san"],
                    uci=row["uci"],
                    fen_before=row["fen_before"],
                    fen_after=row["fen_after"],
                    eval_before=Evaluation(cp=None, mate=None, normalized_pawns=row["eval_before"] or 0.0),
                    eval_after=Evaluation(cp=None, mate=None, normalized_pawns=row["eval_after"] or 0.0),
                    eval_delta=row["eval_delta"] or 0.0,
                    classification=row["classification"] or "unknown",
                    commentary=row["commentary"],
                    best_move=row["best_move"],
                    in_opening=bool(row["in_opening"]),
                )
            )
        return moves

    def list_games(self, limit: int = 50) -> list[dict]:
        with self._session_manager.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, date, player_color, result, opening_eco, opening_name, move_count
                FROM games
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def openings_count(self) -> int:
        with self._session_manager.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM openings").fetchone()
            return int(row["c"] if row else 0)

    def insert_openings_bulk(self, rows: Iterable[tuple[str, str, str, str, str]]) -> None:
        with self._session_manager.connect() as conn:
            conn.executemany(
                "INSERT INTO openings (eco, name, pgn, uci, fen) VALUES (?, ?, ?, ?, ?)",
                list(rows),
            )
            conn.commit()

    def get_opening_by_fen(self, fen: str) -> dict | None:
        with self._session_manager.connect() as conn:
            row = conn.execute(
                "SELECT eco, name, pgn, uci, fen FROM openings WHERE fen = ? LIMIT 1",
                (fen,),
            ).fetchone()
        return dict(row) if row else None

    def count_openings_with_prefix(self, uci_prefix: str) -> int:
        if not uci_prefix:
            return 0
        with self._session_manager.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM openings WHERE uci LIKE ?",
                (f"{uci_prefix}%",),
            ).fetchone()
        return int(row["c"] if row else 0)

    def get_max_opening_plies_for_prefix(self, uci_prefix: str) -> int:
        if not uci_prefix:
            return 0
        with self._session_manager.connect() as conn:
            rows = conn.execute(
                "SELECT uci FROM openings WHERE uci LIKE ?",
                (f"{uci_prefix}%",),
            ).fetchall()
        if not rows:
            return 0
        current_plies = len([part for part in uci_prefix.split(" ") if part])
        max_plies = max(len((row["uci"] or "").split(" ")) for row in rows if row["uci"])
        return max(0, max_plies - current_plies)

    def get_opening_stats(self) -> list[dict]:
        with self._session_manager.connect() as conn:
            rows = conn.execute(
                "SELECT eco, wins, losses, draws, total_games FROM opening_stats ORDER BY total_games DESC, eco ASC"
            ).fetchall()
        return [dict(row) for row in rows]

    def refresh_opening_stats(self) -> None:
        with self._session_manager.connect() as conn:
            game_rows = conn.execute(
                """
                SELECT opening_eco, player_color, result
                FROM games
                WHERE opening_eco IS NOT NULL AND result IS NOT NULL
                """
            ).fetchall()

            stats: dict[str, dict[str, int]] = defaultdict(
                lambda: {"wins": 0, "losses": 0, "draws": 0, "total_games": 0}
            )
            for row in game_rows:
                eco = row["opening_eco"]
                player_color = row["player_color"]
                result = row["result"]
                entry = stats[eco]
                entry["total_games"] += 1

                if result == "1/2-1/2":
                    entry["draws"] += 1
                elif (player_color == "white" and result == "1-0") or (
                    player_color == "black" and result == "0-1"
                ):
                    entry["wins"] += 1
                else:
                    entry["losses"] += 1

            conn.execute("DELETE FROM opening_stats")
            conn.executemany(
                """
                INSERT INTO opening_stats (eco, wins, losses, draws, total_games)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (eco, values["wins"], values["losses"], values["draws"], values["total_games"])
                    for eco, values in stats.items()
                ],
            )
            conn.commit()
