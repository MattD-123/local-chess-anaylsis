import React, { useMemo, useState } from "react";

const GRAPH_WIDTH = 560;
const GRAPH_HEIGHT = 180;
const GRAPH_PADDING = 18;
const MAX_EVAL = 10;

function clampEval(value) {
  return Math.max(-MAX_EVAL, Math.min(MAX_EVAL, value));
}

function moveCentipawnLoss(move) {
  const before = move?.eval_before?.normalized_pawns ?? 0;
  const after = move?.eval_after?.normalized_pawns ?? 0;
  if (move.color === "white") {
    return Math.max(0, (before - after) * 100);
  }
  return Math.max(0, (after - before) * 100);
}

export default function AnalysisBoard({ state, setViewFen }) {
  const [showOnlyBlunders, setShowOnlyBlunders] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(null);
  const moves = state.moveHistory || [];

  const points = useMemo(() => {
    if (moves.length === 0) {
      return [];
    }
    const innerWidth = GRAPH_WIDTH - GRAPH_PADDING * 2;
    const innerHeight = GRAPH_HEIGHT - GRAPH_PADDING * 2;
    return moves.map((move, index) => {
      const x =
        moves.length <= 1
          ? GRAPH_WIDTH / 2
          : GRAPH_PADDING + (innerWidth * index) / (moves.length - 1);
      const evalValue = clampEval(move?.eval_after?.normalized_pawns ?? 0);
      const y = GRAPH_PADDING + ((MAX_EVAL - evalValue) / (MAX_EVAL * 2)) * innerHeight;
      return { x, y, evalValue };
    });
  }, [moves]);

  const linePoints = points.map((point) => `${point.x},${point.y}`).join(" ");
  const selectedMove = selectedIndex != null ? moves[selectedIndex] : null;

  const playerMoves = useMemo(
    () => moves.filter((move) => move.color === state.playerColor),
    [moves, state.playerColor]
  );

  const averageCpl = useMemo(() => {
    if (playerMoves.length === 0) {
      return 0;
    }
    const total = playerMoves.reduce((sum, move) => sum + moveCentipawnLoss(move), 0);
    return Math.round(total / playerMoves.length);
  }, [playerMoves]);

  const reviewMoves = useMemo(() => {
    const isReviewMove = (move) => {
      const label = (move.classification || "").toLowerCase();
      return label === "inaccuracy" || label === "mistake" || label === "blunder";
    };
    if (!showOnlyBlunders) {
      return moves;
    }
    return moves.filter(isReviewMove);
  }, [moves, showOnlyBlunders]);

  const onSelectMove = (move, index) => {
    setSelectedIndex(index);
    setViewFen(move.fen_after);
  };

  return (
    <section className="panel rounded-2xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-heading text-base font-bold text-ink">Analysis Board</h3>
        <span className="text-xs font-semibold text-slate-600">Avg CPL ({state.playerColor}): {averageCpl}</span>
      </div>

      {moves.length === 0 ? (
        <p className="text-sm text-slate-500">Play or import a game to see evaluation trends.</p>
      ) : (
        <div className="rounded-xl border border-slate-300 bg-white/75 p-2">
          <svg viewBox={`0 0 ${GRAPH_WIDTH} ${GRAPH_HEIGHT}`} className="h-44 w-full">
            <line
              x1={GRAPH_PADDING}
              y1={GRAPH_HEIGHT / 2}
              x2={GRAPH_WIDTH - GRAPH_PADDING}
              y2={GRAPH_HEIGHT / 2}
              stroke="rgba(51, 65, 85, 0.4)"
              strokeWidth="1"
              strokeDasharray="6 4"
            />
            <polyline fill="none" stroke="#0f766e" strokeWidth="2.5" points={linePoints} />
            {points.map((point, index) => (
              <circle
                key={`pt-${index}`}
                cx={point.x}
                cy={point.y}
                r={selectedIndex === index ? 5 : 3.5}
                fill={selectedIndex === index ? "#b91c1c" : "#1d4ed8"}
                className="cursor-pointer"
                onClick={() => onSelectMove(moves[index], index)}
              />
            ))}
          </svg>
        </div>
      )}

      <div className="mt-3 flex items-center gap-2">
        <label className="inline-flex items-center gap-2 text-xs font-semibold text-slate-700">
          <input
            type="checkbox"
            checked={showOnlyBlunders}
            onChange={(event) => setShowOnlyBlunders(event.target.checked)}
          />
          Blunder Review Mode
        </label>
      </div>

      <div className="mt-3 max-h-52 space-y-1 overflow-y-auto pr-1 text-sm">
        {reviewMoves.length === 0 ? (
          <p className="text-slate-500">No inaccuracies, mistakes, or blunders yet.</p>
        ) : (
          reviewMoves.map((move) => {
            const index = moves.indexOf(move);
            return (
              <button
                key={`${move.move_number}-${move.color}-${index}`}
                type="button"
                className="flex w-full items-center justify-between rounded-md border border-slate-200 bg-white/70 px-2 py-1 text-left hover:bg-white"
                onClick={() => onSelectMove(move, index)}
              >
                <span className="font-semibold text-slate-700">
                  {move.move_number}. {move.san}
                </span>
                <span className="text-xs font-semibold text-slate-600">
                  {move.classification} • CPL {Math.round(moveCentipawnLoss(move))}
                </span>
              </button>
            );
          })
        )}
      </div>

      {selectedMove ? (
        <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50/70 p-2 text-xs text-blue-900">
          <p>
            Selected: <strong>{selectedMove.move_number}. {selectedMove.san}</strong> ({selectedMove.classification})
          </p>
          <p>Best move suggestion: <strong>{selectedMove.best_move || "N/A"}</strong></p>
          <p>
            Eval shift: {selectedMove.eval_before.normalized_pawns.toFixed(2)} to{" "}
            {selectedMove.eval_after.normalized_pawns.toFixed(2)}
          </p>
        </div>
      ) : null}
    </section>
  );
}
