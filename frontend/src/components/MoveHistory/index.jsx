import React from "react";

import { moveClassToColor, selectMoveFen } from "../../providers/GameProvider";

export default function MoveHistory({ state, setViewFen }) {
  return (
    <section className="panel rounded-2xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-heading text-base font-bold text-ink">Move History</h3>
        <button
          type="button"
          className="rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-600 hover:bg-white/70"
          onClick={() => setViewFen(null)}
        >
          Live Position
        </button>
      </div>
      <div className="max-h-60 space-y-1 overflow-y-auto pr-1 text-sm">
        {state.moveHistory.length === 0 ? (
          <p className="text-slate-500">No moves yet.</p>
        ) : null}

        {state.moveHistory.map((move, index) => (
          <button
            key={`${move.move_number}-${move.color}-${index}`}
            type="button"
            className="flex w-full items-center justify-between rounded-md px-2 py-1 text-left hover:bg-white/70"
            onClick={() => setViewFen(selectMoveFen(state, index))}
          >
            <span className="font-semibold text-slate-700">
              {move.move_number}. {move.san}
            </span>
            <span style={{ color: moveClassToColor(move.classification) }}>{move.classification}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
