import { moveClassToColor } from "./GameProvider";

it("maps move classes to configured colors", () => {
  expect(moveClassToColor("Best")).toBe("var(--good)");
  expect(moveClassToColor("Inaccuracy")).toBe("var(--inaccuracy)");
  expect(moveClassToColor("Mistake")).toBe("var(--mistake)");
  expect(moveClassToColor("Blunder")).toBe("var(--blunder)");
});
