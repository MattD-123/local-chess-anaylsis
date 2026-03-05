import { fireEvent, render, screen } from "@testing-library/react";

import MoveHistory from "./index";

it("renders move list and classification colors", () => {
  const state = {
    moveHistory: [
      {
        move_number: 1,
        color: "white",
        san: "e4",
        classification: "Best",
        fen_after: "fen1",
      },
    ],
  };

  render(<MoveHistory state={state} setViewFen={() => {}} setViewMoveIndex={() => {}} />);

  expect(screen.getByText(/1\. e4/i)).toBeInTheDocument();
  expect(screen.getByText(/Best/i)).toBeInTheDocument();
});

it("supports analyze navigation controls", () => {
  const setViewFen = vi.fn();
  const setViewMoveIndex = vi.fn();
  const state = {
    viewMoveIndex: 0,
    viewFen: "fen1",
    moveHistory: [
      {
        move_number: 1,
        color: "white",
        san: "e4",
        classification: "Best",
        fen_before: "start-fen",
        fen_after: "fen1",
      },
      {
        move_number: 1,
        color: "black",
        san: "e5",
        classification: "Good",
        fen_before: "fen1",
        fen_after: "fen2",
      },
    ],
  };

  render(
    <MoveHistory
      state={state}
      setViewFen={setViewFen}
      setViewMoveIndex={setViewMoveIndex}
      showAnalyzeControls
    />
  );

  fireEvent.click(screen.getByRole("button", { name: /Previous move/i }));
  expect(setViewMoveIndex).toHaveBeenCalledWith(-1);

  fireEvent.click(screen.getByRole("button", { name: /Next move/i }));
  expect(setViewMoveIndex).toHaveBeenCalledWith(1);

  fireEvent.click(screen.getByRole("button", { name: /Current position/i }));
  expect(setViewMoveIndex).toHaveBeenCalledWith(null);
});
