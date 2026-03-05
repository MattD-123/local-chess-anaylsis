from providers.llm.prompt_builder import PromptBuilder
from schemas.domain import CommentaryContext, Evaluation, MoveCandidate, MoveRecord, OpeningInfo


def test_player_move_prompt_contains_required_context():
    builder = PromptBuilder()
    context = CommentaryContext(
        kind="player_move",
        persona="coach",
        opening=OpeningInfo(eco="C20", name="King's Pawn Game", fen="fen", moves_remaining=3),
        move=MoveRecord(
            move_number=1,
            color="white",
            san="e4",
            uci="e2e4",
            fen_before="start",
            fen_after="after",
            eval_before=Evaluation(cp=20, normalized_pawns=0.2),
            eval_after=Evaluation(cp=5, normalized_pawns=0.05),
            eval_delta=-0.15,
            classification="Inaccuracy",
            commentary=None,
            best_move="d2d4",
            in_opening=True,
        ),
        best_move=MoveCandidate(uci="d2d4", san="d4", evaluation=Evaluation(cp=30, normalized_pawns=0.3)),
        legal_move_count=20,
        who_was_winning="white",
    )

    prompt = builder.build_commentary_prompt(context)
    assert "Opening: King's Pawn Game (C20)" in prompt
    assert "Move played: e4 by white" in prompt
    assert "Stockfish best move was: d4" in prompt
