from __future__ import annotations

from schemas.domain import CommentaryContext, CompletedGame, HintContext, OpeningInfo


class PromptBuilder:
    def build_commentary_prompt(self, context: CommentaryContext) -> str:
        if context.kind == "player_move":
            return self._build_player_move_prompt(context)
        if context.kind == "engine_move":
            return self._build_engine_move_prompt(context)
        return self._build_opening_entry_prompt(context)

    def _build_player_move_prompt(self, context: CommentaryContext) -> str:
        move = context.move
        opening = context.opening
        best = context.best_move

        if move is None:
            raise ValueError("Player move prompt requires move context")

        opening_name = opening.name if opening else "Unknown opening"
        eco_code = opening.eco if opening else "N/A"
        moves_remaining = opening.moves_remaining if opening else 0
        best_move = best.san or best.uci if best else "Unavailable"
        best_eval = best.evaluation.normalized_pawns if best else 0.0

        blunder_clause = ""
        excellent_clause = ""
        if move.classification.lower() == "blunder":
            blunder_clause = "This was a significant mistake - explain what went wrong and what the correct idea was."
        if move.classification.lower() in {"best", "excellent"}:
            excellent_clause = "Acknowledge this was a strong move and briefly explain why."

        return (
            f"You are a {context.persona} providing live chess commentary.\n\n"
            "Position context:\n"
            f"- Opening: {opening_name} ({eco_code}) - {moves_remaining} moves of theory remaining\n"
            f"- Move played: {move.san} by {move.color}\n"
            f"- Evaluation before: {move.eval_before.normalized_pawns:.2f} ({context.who_was_winning or 'no side'} was better)\n"
            f"- Evaluation after: {move.eval_after.normalized_pawns:.2f}\n"
            f"- Classification: {move.classification}\n"
            f"- Stockfish best move was: {best_move} (eval: {best_eval:.2f})\n"
            f"- Legal moves available: {context.legal_move_count or 0}\n\n"
            f"{blunder_clause}\n"
            f"{excellent_clause}\n\n"
            "Give 1-2 sentences of commentary. Be specific about what the move does - threats created, "
            "pieces activated, weaknesses exploited. Do not be generic. Do not repeat the move notation "
            "back verbatim. Speak naturally as the requested persona."
        )

    def _build_engine_move_prompt(self, context: CommentaryContext) -> str:
        move = context.move
        opening = context.opening
        if move is None:
            raise ValueError("Engine move prompt requires move context")

        return (
            f"You are a {context.persona}. The engine just played {move.san}.\n\n"
            f"- Evaluation swing: {move.eval_delta:.2f} in engine's favor\n"
            f"- This move: {context.tactical_description or 'No tactical motif provided'}\n"
            f"- Opening context: {opening.name if opening else 'Out of book'}\n"
            f"- Threats created: {context.threats or 'Not specified'}\n\n"
            "Explain in 2 sentences what the engine is doing and what the human player should watch out for."
        )

    def _build_opening_entry_prompt(self, context: CommentaryContext) -> str:
        opening = context.opening
        if opening is None:
            raise ValueError("Opening prompt requires opening context")

        return (
            f"The game has entered the {opening.name} ({opening.eco}).\n\n"
            "Briefly explain (3 sentences max) what each side is trying to achieve in this opening "
            f"and what the key strategic ideas are. Speak as a {context.persona}."
        )

    def build_hint_prompt(self, context: HintContext) -> str:
        moves = "\n".join(
            f"- {candidate.san or candidate.uci}: eval {candidate.evaluation.normalized_pawns:.2f}"
            for candidate in context.top_moves
        )
        opening_line = (
            f"Current opening: {context.opening.name} ({context.opening.eco}).\n"
            if context.opening
            else "Current opening: unknown or out of book.\n"
        )
        return (
            "You are a chess coach. Give one practical hint in 2 short sentences.\n"
            f"{opening_line}"
            f"Side to move: {context.side_to_move}.\n"
            "Top candidate moves:\n"
            f"{moves or '- No engine line available'}"
        )

    def build_game_summary_prompt(self, game: CompletedGame) -> str:
        opening = f"{game.opening.name} ({game.opening.eco})" if game.opening else "Unknown opening"
        key_moments = "\n".join(
            f"- Move {m.move_number} {m.color}: {m.san} ({m.classification}, delta {m.eval_delta:.2f})"
            for m in game.moves[-12:]
        )
        return (
            "Summarize this chess game in a concise coaching style.\n"
            f"Result: {game.result}, termination: {game.termination_reason}\n"
            f"Opening: {opening}\n"
            "Recent key moments:\n"
            f"{key_moments or '- No moves recorded'}"
        )

    def build_opening_commentary_prompt(self, opening: OpeningInfo, side: str, persona: str) -> str:
        return (
            f"The game has entered the {opening.name} ({opening.eco}).\n"
            f"Comment from the perspective of {persona}.\n"
            f"The human is playing {side}.\n"
            "In up to 3 sentences, explain strategic plans, typical piece placement, and common tactical ideas."
        )
