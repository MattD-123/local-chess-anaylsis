import { render, screen } from "@testing-library/react";

import MaterialPanel from "./MaterialPanel";

it("renders captured material as chess icons", () => {
  render(
    <MaterialPanel
      fen="rnbqkbnr/ppp1pppp/8/3P4/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2"
      playerColor="white"
    />
  );

  expect(screen.getByText(/\+1/i)).toBeInTheDocument();
  expect(screen.getByText("♟")).toBeInTheDocument();
});
