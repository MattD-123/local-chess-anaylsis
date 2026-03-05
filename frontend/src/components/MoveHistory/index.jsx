import React from "react";

import { moveClassToColor, selectMoveFen, selectViewedMoveIndex } from "../../providers/GameProvider";

export default function MoveHistory({ state, setViewFen, setViewMoveIndex, showAnalyzeControls = false }) {
  const moves = state.moveHistory || [];
  const viewedIndex = selectViewedMoveIndex(state);
  const startFen = moves[0]?.fen_before || null;
  const atCurrentPosition = state.viewFen == null && state.viewMoveIndex == null;

  const movePositionLabel = atCurrentPosition
    ? "Viewing current position"
    : viewedIndex < 0
      ? "Viewing beginning position"
      : `Viewing move ${viewedIndex + 1} of ${moves.length}`;

  const onGoToBeginning = () => {
    setViewMoveIndex?.(-1);
  };

  const onPreviousMove = () => {
    if (viewedIndex < 0) {
      return;
    }
    if (viewedIndex === 0) {
      setViewMoveIndex?.(-1);
      return;
    }
    setViewMoveIndex?.(viewedIndex - 1);
  };

  const onNextMove = () => {
    if (moves.length === 0) {
      return;
    }
    if (viewedIndex < 0) {
      setViewMoveIndex?.(0);
      return;
    }
    if (viewedIndex >= moves.length - 1) {
      return;
    }
    setViewMoveIndex?.(viewedIndex + 1);
  };

  return (
    <section className="panel rounded-2xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-heading text-base font-bold text-ink">Move History</h3>
        {showAnalyzeControls ? null : (
          <button
            type="button"
            className="rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-600 hover:bg-white/70"
            onClick={() => setViewFen(null)}
          >
            Live Position
          </button>
        )}
      </div>

      {showAnalyzeControls ? (
        <div className="mb-3 space-y-2">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-45"
              onClick={onGoToBeginning}
              disabled={!startFen}
              title="Skip to beginning"
              aria-label="Skip to beginning"
            >
              ⏮
            </button>
            <button
              type="button"
              className="rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-45"
              onClick={onPreviousMove}
              disabled={moves.length === 0 || viewedIndex < 0}
              title="Previous move"
              aria-label="Previous move"
            >
              ◀
            </button>
            <button
              type="button"
              className="rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-45"
              onClick={onNextMove}
              disabled={moves.length === 0 || viewedIndex >= moves.length - 1}
              title="Next move"
              aria-label="Next move"
            >
              ▶
            </button>
            <button
              type="button"
              className="rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-45"
              onClick={() => setViewMoveIndex?.(null)}
              disabled={atCurrentPosition}
              title="Current position"
              aria-label="Current position"
            >
              ⏭
            </button>
          </div>
          <p className="text-xs font-semibold text-slate-500">{movePositionLabel}</p>
        </div>
      ) : null}

      <div className="max-h-60 space-y-1 overflow-y-auto pr-1 text-sm">
        {moves.length === 0 ? (
          <p className="text-slate-500">No moves yet.</p>
        ) : null}

        {moves.map((move, index) => (
          <button
            key={`${move.move_number}-${move.color}-${index}`}
            type="button"
            className="flex w-full items-center justify-between rounded-md px-2 py-1 text-left hover:bg-white/70"
            onClick={() => (setViewMoveIndex ? setViewMoveIndex(index) : setViewFen(selectMoveFen(state, index)))}
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
