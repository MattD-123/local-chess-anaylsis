import React, { useMemo, useState } from "react";
import { Chess } from "chess.js";

import { selectViewedMoveIndex } from "../../providers/GameProvider";

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

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function moveAccuracy(move) {
  const cpl = moveCentipawnLoss(move);
  // Exponential approximation used by many chess analysis tools.
  return clamp(103.1668 * Math.exp(-0.04354 * cpl) - 3.1669, 0, 100);
}

function normalizedClass(move) {
  return (move?.classification || "").toLowerCase();
}

function classColor(move) {
  const cls = normalizedClass(move);
  if (cls === "best" || cls === "excellent" || cls === "good") {
    return "#16a34a";
  }
  if (cls === "inaccuracy") {
    return "#ca8a04";
  }
  if (cls === "mistake") {
    return "#ea580c";
  }
  if (cls === "blunder") {
    return "#dc2626";
  }
  if (cls === "forced") {
    return "#1d4ed8";
  }
  return "#334155";
}

function sideMetrics(moves, side) {
  const sideMoves = moves.filter((move) => move.color === side);
  const counts = {
    best: 0,
    good: 0,
    inaccuracy: 0,
    mistake: 0,
    blunder: 0,
    forced: 0,
  };

  for (const move of sideMoves) {
    const cls = normalizedClass(move);
    if (cls === "best" || cls === "excellent") {
      counts.best += 1;
    } else if (cls === "good") {
      counts.good += 1;
    } else if (cls === "inaccuracy") {
      counts.inaccuracy += 1;
    } else if (cls === "mistake") {
      counts.mistake += 1;
    } else if (cls === "blunder") {
      counts.blunder += 1;
    } else if (cls === "forced") {
      counts.forced += 1;
    }
  }

  if (sideMoves.length === 0) {
    return {
      side,
      moves: 0,
      avgCpl: 0,
      accuracy: 0,
      ratingEstimate: 200,
      counts,
    };
  }

  const totalCpl = sideMoves.reduce((sum, move) => sum + moveCentipawnLoss(move), 0);
  const avgCpl = totalCpl / sideMoves.length;
  const accuracy = sideMoves.reduce((sum, move) => sum + moveAccuracy(move), 0) / sideMoves.length;

  const estimateRaw =
    200 +
    accuracy * 30 -
    counts.blunder * 120 -
    counts.mistake * 45 -
    counts.inaccuracy * 18 -
    Math.max(0, avgCpl - 20) * 1.7;

  return {
    side,
    moves: sideMoves.length,
    avgCpl: Math.round(avgCpl),
    accuracy: Math.round(accuracy * 10) / 10,
    ratingEstimate: Math.round(clamp(estimateRaw, 200, 3200)),
    counts,
  };
}

function isLegalUciForFen(fen, uci) {
  if (!fen || !uci || uci.length < 4) {
    return false;
  }
  const game = new Chess();
  try {
    game.load(fen);
    const result = game.move({
      from: uci.slice(0, 2),
      to: uci.slice(2, 4),
      promotion: uci.length > 4 ? uci.slice(4, 5) : "q",
    });
    return Boolean(result);
  } catch {
    return false;
  }
}

export default function AnalysisBoard({ state, setViewFen, setViewMoveIndex }) {
  const [showOnlyBlunders, setShowOnlyBlunders] = useState(false);
  const moves = state.moveHistory || [];
  const viewedIndex = selectViewedMoveIndex(state);
  const isCurrentPosition = state.viewFen == null;
  const displayedFen = useMemo(() => {
    if (moves.length === 0) {
      return null;
    }
    if (viewedIndex < 0) {
      return moves[0].fen_before;
    }
    return moves[Math.min(viewedIndex, moves.length - 1)].fen_after;
  }, [moves, viewedIndex]);

  const movesAtViewedMoment = useMemo(() => {
    if (moves.length === 0) {
      return [];
    }
    if (isCurrentPosition) {
      return moves;
    }
    if (viewedIndex < 0) {
      return [];
    }
    return moves.slice(0, viewedIndex + 1);
  }, [isCurrentPosition, moves, viewedIndex]);

  const points = useMemo(() => {
    if (movesAtViewedMoment.length === 0) {
      return [];
    }
    const innerWidth = GRAPH_WIDTH - GRAPH_PADDING * 2;
    const innerHeight = GRAPH_HEIGHT - GRAPH_PADDING * 2;
    return movesAtViewedMoment.map((move, index) => {
      const x =
        movesAtViewedMoment.length <= 1
          ? GRAPH_WIDTH / 2
          : GRAPH_PADDING + (innerWidth * index) / (movesAtViewedMoment.length - 1);
      const evalValue = clampEval(move?.eval_after?.normalized_pawns ?? 0);
      const y = GRAPH_PADDING + ((MAX_EVAL - evalValue) / (MAX_EVAL * 2)) * innerHeight;
      return { x, y, evalValue };
    });
  }, [movesAtViewedMoment]);

  const linePoints = points.map((point) => `${point.x},${point.y}`).join(" ");
  const selectedMove = viewedIndex >= 0 ? moves[viewedIndex] : null;
  const selectedPointIndex = points.length - 1;
  const positionAdvice = useMemo(() => {
    if (!displayedFen) {
      return null;
    }
    const startIndex = Math.max(0, viewedIndex + 1);
    for (let index = startIndex; index < moves.length; index += 1) {
      if (moves[index].fen_before === displayedFen) {
        const best = moves[index].best_move || null;
        if (best && isLegalUciForFen(displayedFen, best)) {
          return best;
        }
        return null;
      }
    }
    return null;
  }, [displayedFen, moves, viewedIndex]);
  const whiteMetrics = useMemo(() => sideMetrics(movesAtViewedMoment, "white"), [movesAtViewedMoment]);
  const blackMetrics = useMemo(() => sideMetrics(movesAtViewedMoment, "black"), [movesAtViewedMoment]);
  const userMetrics = state.playerColor === "black" ? blackMetrics : whiteMetrics;

  const reviewMoves = useMemo(() => {
    const isReviewMove = (move) => {
      const label = (move.classification || "").toLowerCase();
      return label === "inaccuracy" || label === "mistake" || label === "blunder";
    };
    if (!showOnlyBlunders) {
      return movesAtViewedMoment;
    }
    return movesAtViewedMoment.filter(isReviewMove);
  }, [movesAtViewedMoment, showOnlyBlunders]);

  const onSelectMove = (move) => {
    const index = moves.indexOf(move);
    if (index >= 0 && setViewMoveIndex) {
      setViewMoveIndex(index);
      return;
    }
    setViewFen(move.fen_after);
  };

  return (
    <section className="panel min-w-0 rounded-2xl p-4 md:p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-heading text-base font-bold text-ink md:text-lg">Game Review</h3>
        <span className="rounded-md border border-slate-300 bg-white/75 px-2 py-1 text-xs font-semibold text-slate-700">
          Player Accuracy: {userMetrics.accuracy.toFixed(1)}%
        </span>
      </div>
      <p className="mb-3 text-xs font-semibold text-slate-500">
        {isCurrentPosition
          ? `Showing analysis at current position (move ${moves.length})`
          : viewedIndex < 0
            ? "Showing analysis at game start"
            : `Showing analysis through move ${viewedIndex + 1}`}
      </p>

      <div className="mb-3 grid gap-2 md:grid-cols-2">
        <article className="rounded-xl border border-slate-300 bg-white/85 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">White</p>
          <p className="mt-1 text-xl font-black text-slate-900">{whiteMetrics.accuracy.toFixed(1)}%</p>
          <p className="text-xs text-slate-600">Est. Rating: {whiteMetrics.ratingEstimate}</p>
          <p className="mt-1 text-xs text-slate-600">Avg CPL: {whiteMetrics.avgCpl}</p>
        </article>
        <article className="rounded-xl border border-slate-300 bg-white/85 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Black</p>
          <p className="mt-1 text-xl font-black text-slate-900">{blackMetrics.accuracy.toFixed(1)}%</p>
          <p className="text-xs text-slate-600">Est. Rating: {blackMetrics.ratingEstimate}</p>
          <p className="mt-1 text-xs text-slate-600">Avg CPL: {blackMetrics.avgCpl}</p>
        </article>
      </div>

      <div className="mb-3 grid gap-2 md:grid-cols-4">
        <MetricPill label="Best" value={userMetrics.counts.best + userMetrics.counts.good} tone="good" />
        <MetricPill label="Inaccuracies" value={userMetrics.counts.inaccuracy} tone="inaccuracy" />
        <MetricPill label="Mistakes" value={userMetrics.counts.mistake} tone="mistake" />
        <MetricPill label="Blunders" value={userMetrics.counts.blunder} tone="blunder" />
      </div>

      {movesAtViewedMoment.length === 0 ? (
        <p className="text-sm text-slate-500">Play or import a game to see evaluation trends.</p>
      ) : (
        <div className="min-w-0 rounded-xl border border-slate-300 bg-white/80 p-2">
          <svg
            viewBox={`0 0 ${GRAPH_WIDTH} ${GRAPH_HEIGHT}`}
            className="h-44 w-full max-w-full"
            preserveAspectRatio="xMidYMid meet"
          >
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
                r={selectedPointIndex === index ? 5 : 3.5}
                fill={selectedPointIndex === index ? "#0f172a" : classColor(movesAtViewedMoment[index])}
                className="cursor-pointer"
                onClick={() => onSelectMove(movesAtViewedMoment[index])}
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

      <div className="mt-3 max-h-56 space-y-1 overflow-y-auto pr-1 text-sm">
        {reviewMoves.length === 0 ? (
          <p className="text-slate-500">No inaccuracies, mistakes, or blunders yet.</p>
        ) : (
          reviewMoves.map((move) => {
            return (
              <button
                key={`${move.move_number}-${move.color}-${move.fen_after}`}
                type="button"
                className="flex w-full items-center justify-between rounded-md border border-slate-200 bg-white/70 px-2 py-1 text-left hover:bg-white"
                onClick={() => onSelectMove(move)}
              >
                <span className="font-semibold text-slate-700">
                  {move.move_number}. {move.san} ({move.color})
                </span>
                <span className="text-xs font-semibold text-slate-600">
                  {move.classification} - CPL {Math.round(moveCentipawnLoss(move))} - Acc {moveAccuracy(move).toFixed(1)}%
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
          <p>Best move suggestion (current position): <strong>{positionAdvice || "N/A"}</strong></p>
          <p>
            Eval shift: {selectedMove.eval_before.normalized_pawns.toFixed(2)} to{" "}
            {selectedMove.eval_after.normalized_pawns.toFixed(2)}
          </p>
          <p>Move accuracy estimate: <strong>{moveAccuracy(selectedMove).toFixed(1)}%</strong></p>
        </div>
      ) : null}

      <p className="mt-3 text-[11px] text-slate-500">
        Rating and accuracy are estimated from centipawn loss and move quality labels; this is not an official rating.
      </p>
    </section>
  );
}

function MetricPill({ label, value, tone }) {
  const toneClass =
    tone === "good"
      ? "border-green-300 bg-green-50 text-green-900"
      : tone === "inaccuracy"
        ? "border-yellow-300 bg-yellow-50 text-yellow-900"
        : tone === "mistake"
          ? "border-orange-300 bg-orange-50 text-orange-900"
          : "border-red-300 bg-red-50 text-red-900";

  return (
    <article className={`rounded-lg border px-3 py-2 ${toneClass}`}>
      <p className="text-[11px] font-semibold uppercase tracking-wide">{label}</p>
      <p className="text-lg font-black">{value}</p>
    </article>
  );
}
