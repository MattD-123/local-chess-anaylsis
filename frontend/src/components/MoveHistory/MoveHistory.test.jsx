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

  render(<MoveHistory state={state} setViewFen={() => {}} />);

  expect(screen.getByText(/1\. e4/i)).toBeInTheDocument();
  expect(screen.getByText(/Best/i)).toBeInTheDocument();
});

it("supports analyze navigation controls", () => {
  const setViewFen = vi.fn();
  const state = {
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

  render(<MoveHistory state={state} setViewFen={setViewFen} showAnalyzeControls />);

  fireEvent.click(screen.getByRole("button", { name: /Previous Move/i }));
  expect(setViewFen).toHaveBeenCalledWith("start-fen");

  fireEvent.click(screen.getByRole("button", { name: /Next Move/i }));
  expect(setViewFen).toHaveBeenCalledWith("fen2");

  fireEvent.click(screen.getByRole("button", { name: /Current Position/i }));
  expect(setViewFen).toHaveBeenCalledWith(null);
});
