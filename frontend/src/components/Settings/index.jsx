import React, { useEffect, useMemo, useState } from "react";

const SKILL_LABELS = [
  "Beginner",
  "Casual",
  "Learning",
  "Developing",
  "Club",
  "Advanced",
  "Expert",
  "Master",
  "Elite",
  "Near Perfect",
];

function skillLabel(level) {
  const bucket = Math.min(9, Math.max(0, Math.floor((level - 1) / 2)));
  return SKILL_LABELS[bucket];
}

export default function Settings({
  config,
  saveSettings,
  requestHint,
  resign,
  hint,
  gameId,
  playerColor,
  importGamePgn,
  exportGamePgn,
}) {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [pgnText, setPgnText] = useState("");
  const [pgnLoading, setPgnLoading] = useState(false);
  const [pgnStatus, setPgnStatus] = useState("");
  const [pgnError, setPgnError] = useState("");

  useEffect(() => {
    if (!config) {
      return;
    }
    setForm({
      engineProvider: config.engine.provider,
      skillLevel: config.engine.local.skill_level,
      persona: config.commentary.persona,
      artificialDelayEnabled: config.engine.local.artificial_delay.enabled,
    });
  }, [config]);

  const skillText = useMemo(() => {
    if (!form) {
      return "";
    }
    return `${form.skillLevel} - ${skillLabel(form.skillLevel)}`;
  }, [form]);

  if (!form) {
    return <section className="panel rounded-2xl p-4 text-sm text-slate-500">Loading settings...</section>;
  }

  const updateField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const onSave = async () => {
    setSaving(true);
    try {
      const skill = Number(form.skillLevel);
      const depth = Math.max(4, Math.round(6 + (skill * 0.6)));
      const thinkTimeMs = Math.round(300 + (skill * 90));
      await saveSettings({
        engine: {
          provider: form.engineProvider,
          local: {
            skill_level: skill,
            depth,
            think_time_ms: thinkTimeMs,
            artificial_delay: {
              enabled: Boolean(form.artificialDelayEnabled),
            },
          },
        },
        commentary: {
          persona: form.persona,
        },
      });
    } finally {
      setSaving(false);
    }
  };

  const onImportPgn = async () => {
    if (!pgnText.trim()) {
      setPgnError("Paste PGN content first.");
      return;
    }

    setPgnLoading(true);
    setPgnError("");
    setPgnStatus("");
    try {
      const imported = await importGamePgn(pgnText, playerColor || "white");
      setPgnStatus(`Imported ${imported.imported_move_count} moves into game ${imported.game_id.slice(0, 8)}...`);
      setPgnText("");
    } catch (error) {
      setPgnError(error instanceof Error ? error.message : "PGN import failed");
    } finally {
      setPgnLoading(false);
    }
  };

  const onExportPgn = async () => {
    setPgnLoading(true);
    setPgnError("");
    setPgnStatus("");
    try {
      const pgn = await exportGamePgn();
      const blob = new Blob([pgn], { type: "application/x-chess-pgn" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${gameId || "game"}.pgn`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setPgnStatus("PGN exported.");
    } catch (error) {
      setPgnError(error instanceof Error ? error.message : "PGN export failed");
    } finally {
      setPgnLoading(false);
    }
  };

  return (
    <section className="panel rounded-2xl p-4">
      <h3 className="font-heading text-base font-bold text-ink">Settings</h3>

      <div className="mt-3 grid gap-3 text-sm text-slate-700">
        <label className="flex flex-col gap-1">
          Engine Provider
          <select
            className="rounded-lg border border-slate-300 bg-white px-2 py-1"
            value={form.engineProvider}
            onChange={(event) => updateField("engineProvider", event.target.value)}
          >
            <option value="local">local</option>
            <option value="api">api</option>
          </select>
        </label>

        <label className="flex flex-col gap-1">
          Difficulty: <span className="font-semibold">{skillText}</span>
          <input
            type="range"
            min="1"
            max="20"
            value={form.skillLevel}
            onChange={(event) => updateField("skillLevel", Number(event.target.value))}
          />
        </label>

        <label className="flex flex-col gap-1">
          Persona
          <select
            className="rounded-lg border border-slate-300 bg-white px-2 py-1"
            value={form.persona}
            onChange={(event) => updateField("persona", event.target.value)}
          >
            <option value="coach">coach</option>
            <option value="grandmaster">grandmaster</option>
            <option value="commentator">commentator</option>
            <option value="rival">rival</option>
          </select>
        </label>

        <label className="inline-flex items-center gap-2">
          <input
            type="checkbox"
            checked={Boolean(form.artificialDelayEnabled)}
            onChange={(event) => updateField("artificialDelayEnabled", event.target.checked)}
          />
          Artificial delay
        </label>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onSave}
          disabled={saving}
          className="rounded-lg bg-ink px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
        >
          {saving ? "Saving..." : "Save Settings"}
        </button>
        <button
          type="button"
          onClick={requestHint}
          className="rounded-lg border border-slate-400 px-3 py-1.5 text-sm font-semibold text-slate-700"
        >
          Get Hint
        </button>
        <button
          type="button"
          onClick={resign}
          className="rounded-lg border border-red-400 px-3 py-1.5 text-sm font-semibold text-red-700"
        >
          Resign
        </button>
      </div>

      {hint ? <p className="mt-3 rounded-lg bg-white/70 p-2 text-sm text-slate-700">Hint: {hint}</p> : null}

      <div className="mt-4 rounded-xl border border-slate-300 bg-white/65 p-3">
        <h4 className="font-heading text-sm font-bold text-ink">PGN Tools</h4>
        <textarea
          className="mt-2 h-24 w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700"
          placeholder='Paste PGN to import, e.g. [Event "Game"] ...'
          value={pgnText}
          onChange={(event) => setPgnText(event.target.value)}
        />
        <div className="mt-2 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={pgnLoading}
            className="rounded-lg bg-ink px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
            onClick={onImportPgn}
          >
            Import PGN
          </button>
          <button
            type="button"
            disabled={pgnLoading || !gameId}
            className="rounded-lg border border-slate-400 px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-60"
            onClick={onExportPgn}
          >
            Export Current PGN
          </button>
        </div>
        {pgnStatus ? <p className="mt-2 text-xs font-semibold text-green-700">{pgnStatus}</p> : null}
        {pgnError ? <p className="mt-2 text-xs font-semibold text-red-700">{pgnError}</p> : null}
      </div>
    </section>
  );
}
