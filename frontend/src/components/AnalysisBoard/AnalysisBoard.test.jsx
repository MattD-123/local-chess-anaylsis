import { fireEvent, render, screen } from "@testing-library/react";

import AnalysisBoard from "./index";

const baseState = {
  playerColor: "white",
  viewFen: null,
  moveHistory: [
    {
      move_number: 1,
      color: "white",
      san: "e4",
      classification: "Good",
      fen_after: "fen-1",
      best_move: "e2e4",
      eval_before: { normalized_pawns: 0.0 },
      eval_after: { normalized_pawns: 0.2 },
    },
    {
      move_number: 1,
      color: "black",
      san: "e5",
      classification: "Blunder",
      fen_after: "fen-2",
      best_move: "c7c5",
      eval_before: { normalized_pawns: 0.2 },
      eval_after: { normalized_pawns: 1.1 },
    },
  ],
};

it("filters to review moves and selects a move for board jump", () => {
  const setViewFen = vi.fn();
  render(<AnalysisBoard state={baseState} setViewFen={setViewFen} />);

  fireEvent.click(screen.getByLabelText(/Blunder Review Mode/i));
  expect(screen.queryByRole("button", { name: /1\.\s*e4/i })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /1\.\s*e5/i })).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /1\.\s*e5/i }));
  expect(setViewFen).toHaveBeenCalledWith("fen-2");
  expect(screen.getByText(/Best move suggestion:/i)).toBeInTheDocument();
});

it("refreshes analysis view when state changes between sessions", () => {
  const setViewFen = vi.fn();
  const { rerender } = render(<AnalysisBoard state={baseState} setViewFen={setViewFen} />);
  expect(screen.getByRole("button", { name: /1\.\s*e4/i })).toBeInTheDocument();

  rerender(
    <AnalysisBoard
      state={{
        playerColor: "black",
        viewFen: null,
        moveHistory: [
          {
            move_number: 1,
            color: "white",
            san: "d4",
            classification: "Best",
            fen_after: "fen-x",
            best_move: "d2d4",
            eval_before: { normalized_pawns: 0.0 },
            eval_after: { normalized_pawns: 0.1 },
          },
        ],
      }}
      setViewFen={setViewFen}
    />
  );

  expect(screen.queryByRole("button", { name: /1\.\s*e4/i })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /1\.\s*d4/i })).toBeInTheDocument();
});

it("shows analysis at the currently viewed move", () => {
  const setViewFen = vi.fn();
  render(
    <AnalysisBoard
      state={{
        ...baseState,
        viewFen: "fen-1",
      }}
      setViewFen={setViewFen}
    />
  );

  expect(screen.getByText(/Showing analysis through move 1/i)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /1\.\s*e5/i })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /1\.\s*e4/i })).toBeInTheDocument();
});
