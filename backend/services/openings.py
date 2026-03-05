from __future__ import annotations

import asyncio
import csv
import io
import logging
import re
from dataclasses import dataclass

import chess
import httpx

from database.repo import ChessRepository
from schemas.domain import OpeningInfo

logger = logging.getLogger(__name__)

OPENING_FILES = ["a", "b", "c", "d", "e"]
OPENING_URL_TEMPLATE = "https://raw.githubusercontent.com/lichess-org/chess-openings/master/{name}.tsv"
MOVE_NUMBER_RE = re.compile(r"^\d+\.(\.\.)?$")
RESULT_TOKENS = {"1-0", "0-1", "1/2-1/2", "*"}


@dataclass(slots=True)
class OpeningServiceHealth:
    status: str
    detail: str | None = None


class OpeningService:
    def __init__(self, repo: ChessRepository):
        self._repo = repo
        self._degraded = False
        self._detail: str | None = None
        self._lock = asyncio.Lock()

    async def bootstrap_if_needed(self) -> None:
        if self._repo.openings_count() > 0:
            logger.info("Openings DB already populated")
            return

        async with self._lock:
            if self._repo.openings_count() > 0:
                return

            logger.info("Bootstrapping openings database from Lichess TSV files")
            try:
                rows = await self._download_rows()
                self._repo.insert_openings_bulk(rows)
                logger.info("Inserted %s opening rows", len(rows))
                self._degraded = False
                self._detail = None
            except Exception as exc:
                self._degraded = True
                self._detail = str(exc)
                logger.warning("Openings bootstrap failed; continuing without opening detection: %s", exc)

    async def _download_rows(self) -> list[tuple[str, str, str, str, str]]:
        rows: list[tuple[str, str, str, str, str]] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for name in OPENING_FILES:
                url = OPENING_URL_TEMPLATE.format(name=name)
                response = await client.get(url)
                response.raise_for_status()
                parsed = self.parse_openings_tsv(response.text)
                rows.extend(parsed)
        return rows

    @staticmethod
    def parse_openings_tsv(content: str) -> list[tuple[str, str, str, str, str]]:
        reader = csv.DictReader(io.StringIO(content), delimiter="\t")
        records: list[tuple[str, str, str, str, str]] = []
        for row in reader:
            eco = (row.get("eco") or "").strip()
            name = (row.get("name") or "").strip()
            pgn = (row.get("pgn") or "").strip()
            uci = (row.get("uci") or "").strip()
            fen = (row.get("fen") or "").strip()
            if (not uci or not fen) and pgn:
                derived = OpeningService._derive_uci_and_fen_from_pgn(pgn)
                if derived:
                    uci, fen = derived
            if not fen:
                continue
            records.append((eco, name, pgn, uci, fen))
        return records

    @staticmethod
    def _derive_uci_and_fen_from_pgn(pgn: str) -> tuple[str, str] | None:
        board = chess.Board()
        ucis: list[str] = []
        for token in pgn.split():
            token = token.strip()
            if not token or token in RESULT_TOKENS or MOVE_NUMBER_RE.match(token) or token.startswith("$"):
                continue
            try:
                move = board.parse_san(token)
            except ValueError:
                return None
            board.push(move)
            ucis.append(move.uci())
        if not ucis:
            return None
        return " ".join(ucis), board.fen()

    def detect_opening(self, fen: str, uci_history: list[str]) -> OpeningInfo | None:
        row = self._repo.get_opening_by_fen(fen)
        if not row:
            return None

        uci_prefix = " ".join(uci_history)
        moves_remaining = self._repo.get_max_opening_plies_for_prefix(uci_prefix)
        full_name = row.get("name") or "Unknown Opening"
        variation = None
        if ":" in full_name:
            _, variation = full_name.split(":", 1)
            variation = variation.strip()

        return OpeningInfo(
            eco=row.get("eco") or "",
            name=full_name,
            pgn=row.get("pgn"),
            uci=row.get("uci"),
            fen=row.get("fen") or fen,
            variation=variation,
            in_opening=True,
            moves_remaining=moves_remaining,
        )

    def health(self) -> OpeningServiceHealth:
        if self._degraded:
            return OpeningServiceHealth(status="degraded", detail=self._detail)
        return OpeningServiceHealth(status="ok", detail=None)
