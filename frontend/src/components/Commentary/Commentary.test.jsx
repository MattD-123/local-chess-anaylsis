import { render, screen } from "@testing-library/react";

import Commentary from "./index";

it("renders commentary history entries", () => {
  const state = {
    commentaryHistory: [{ key: "1-white", moveNumber: 1, color: "white", text: "Strong central push." }],
    commentaryDrafts: {},
    typing: false,
  };

  render(<Commentary state={state} />);

  expect(screen.getByText(/Strong central push/i)).toBeInTheDocument();
});
