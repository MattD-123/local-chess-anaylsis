from __future__ import annotations

from datetime import datetime, timezone

from database.repo import ChessRepository
from providers.llm.router import LLMRouter
from schemas.api import AnalysisResponse
from schemas.domain import CompletedGame, OpeningInfo


class AnalysisService:
    def __init__(self, repo: ChessRepository, llm_router: LLMRouter):
        self._repo = repo
        self._llm_router = llm_router

    async def get_analysis(self, game_id: str) -> AnalysisResponse:
        game_row = self._repo.get_game(game_id)
        if not game_row:
            raise ValueError("Game not found")

        moves = self._repo.get_moves(game_id)
        opening = None
        if game_row.get("opening_eco") and game_row.get("opening_name"):
            opening = OpeningInfo(
                eco=game_row["opening_eco"],
                name=game_row["opening_name"],
                fen=moves[0].fen_before if moves else "",
                in_opening=True,
                moves_remaining=0,
            )

        created_raw = game_row.get("created_at") or datetime.now(timezone.utc).isoformat()
        created_at = datetime.fromisoformat(created_raw)

        completed = CompletedGame(
            game_id=game_id,
            player_color=game_row["player_color"],
            result=game_row.get("result") or "*",
            termination_reason=game_row.get("termination_reason") or "unknown",
            opening=opening,
            pgn=game_row.get("pgn") or "",
            move_count=game_row.get("move_count") or len(moves),
            moves=moves,
            created_at=created_at,
        )

        provider = await self._llm_router.get_active_provider()
        summary = await provider.get_game_summary(completed)
        return AnalysisResponse(game=completed, summary=summary)
