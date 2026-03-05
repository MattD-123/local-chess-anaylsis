import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import Settings from "./index";

it("sends per-game options when saving settings", async () => {
  const saveSettings = vi.fn().mockResolvedValue({});
  const requestHint = vi.fn();
  const resign = vi.fn();

  render(
    <Settings
      config={{
        engine: { provider: "local", local: { skill_level: 10, depth: 12, think_time_ms: 1000, artificial_delay: { enabled: true } } },
        commentary: { persona: "coach" },
      }}
      gameOptions={{
        skill_level: 10,
        depth: 12,
        think_time_ms: 1000,
        artificial_delay_enabled: true,
        persona: "coach",
      }}
      saveSettings={saveSettings}
      requestHint={requestHint}
      resign={resign}
      hint={null}
      gameId="g-1"
      playerColor="white"
      importGamePgn={vi.fn()}
      exportGamePgn={vi.fn()}
    />
  );

  fireEvent.change(screen.getByLabelText(/Depth/i), { target: { value: "9" } });
  fireEvent.change(screen.getByLabelText(/Think Time \(ms\)/i), { target: { value: "600" } });
  fireEvent.click(screen.getByRole("button", { name: /Save Settings/i }));

  await waitFor(() =>
    expect(saveSettings).toHaveBeenCalledWith({
      skill_level: 10,
      depth: 9,
      think_time_ms: 600,
      artificial_delay_enabled: true,
      persona: "coach",
    })
  );
});
