import { render, screen } from "@testing-library/react";

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
