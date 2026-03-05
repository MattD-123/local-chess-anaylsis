import React, { useEffect, useMemo, useState } from "react";

import { getGameHistory } from "../../api/client";

function formatDate(isoDate) {
  if (!isoDate) {
    return "Unknown";
  }
  const parsed = new Date(isoDate);
  if (Number.isNaN(parsed.getTime())) {
    return "Unknown";
  }
  return parsed.toLocaleString();
}

function resultLabel(item) {
  if (!item.result || item.result === "*") {
    return "In Progress";
  }
  return item.result;
}

export default function GameLibrary({ activeGameId, onLoadGame }) {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const refreshHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await getGameHistory();
      setGames(payload.items || []);
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Failed to load game history");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshHistory();
  }, [activeGameId]);

  const visibleGames = useMemo(() => games.slice(0, 20), [games]);

  return (
    <section className="panel rounded-2xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-heading text-base font-bold text-ink">Saved Games</h3>
        <button
          type="button"
          className="rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-white/70"
          onClick={refreshHistory}
          disabled={loading}
        >
          Refresh
        </button>
      </div>

      {error ? <p className="mb-2 text-xs font-semibold text-red-700">{error}</p> : null}
      {loading ? <p className="text-sm text-slate-500">Loading games...</p> : null}
      {!loading && visibleGames.length === 0 ? <p className="text-sm text-slate-500">No saved games yet.</p> : null}

      <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
        {visibleGames.map((item) => (
          <article key={item.game_id} className="rounded-lg border border-slate-200 bg-white/75 p-2">
            <p className="text-xs font-semibold text-slate-600">{formatDate(item.date)}</p>
            <p className="text-sm font-semibold text-slate-800">
              {item.player_color} | {resultLabel(item)} | {item.move_count} moves
            </p>
            <p className="text-xs text-slate-600">{item.opening_name || "No opening recorded"}</p>
            <button
              type="button"
              className="mt-2 rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-white"
              onClick={() => onLoadGame(item.game_id)}
              disabled={item.game_id === activeGameId}
            >
              {item.game_id === activeGameId ? "Loaded" : "Load"}
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
