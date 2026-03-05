import React, { useMemo } from "react";
import { Chess } from "chess.js";

const BASE_COUNTS = {
  p: 8,
  n: 2,
  b: 2,
  r: 2,
  q: 1,
};

const PIECE_ICONS = {
  w: {
    p: "♙",
    n: "♘",
    b: "♗",
    r: "♖",
    q: "♕",
  },
  b: {
    p: "♟",
    n: "♞",
    b: "♝",
    r: "♜",
    q: "♛",
  },
};

const PIECE_VALUES = {
  p: 1,
  n: 3,
  b: 3,
  r: 5,
  q: 9,
};

function countPiecesFromFen(fen) {
  const game = new Chess();
  if (fen) {
    game.load(fen);
  }
  const counts = {
    w: { p: 0, n: 0, b: 0, r: 0, q: 0 },
    b: { p: 0, n: 0, b: 0, r: 0, q: 0 },
  };

  for (const row of game.board()) {
    for (const square of row) {
      if (!square || square.type === "k") {
        continue;
      }
      counts[square.color][square.type] += 1;
    }
  }
  return counts;
}

function formatCaptured(missing) {
  return Object.entries(missing)
    .filter(([, count]) => count > 0)
    .map(([piece, count]) => ({ piece, count }));
}

function scoreCaptured(captured) {
  return captured.reduce((sum, item) => sum + PIECE_VALUES[item.piece] * item.count, 0);
}

export default function MaterialPanel({ fen, playerColor }) {
  const material = useMemo(() => {
    const counts = countPiecesFromFen(fen);

    const missingWhite = {
      p: BASE_COUNTS.p - counts.w.p,
      n: BASE_COUNTS.n - counts.w.n,
      b: BASE_COUNTS.b - counts.w.b,
      r: BASE_COUNTS.r - counts.w.r,
      q: BASE_COUNTS.q - counts.w.q,
    };

    const missingBlack = {
      p: BASE_COUNTS.p - counts.b.p,
      n: BASE_COUNTS.n - counts.b.n,
      b: BASE_COUNTS.b - counts.b.b,
      r: BASE_COUNTS.r - counts.b.r,
      q: BASE_COUNTS.q - counts.b.q,
    };

    const capturedByWhite = formatCaptured(missingBlack);
    const capturedByBlack = formatCaptured(missingWhite);

    const whiteGain = scoreCaptured(capturedByWhite);
    const blackGain = scoreCaptured(capturedByBlack);
    const imbalance = whiteGain - blackGain;

    return { capturedByWhite, capturedByBlack, imbalance };
  }, [fen]);

  const perspectiveImbalance = playerColor === "black" ? -material.imbalance : material.imbalance;
  const imbalanceText =
    perspectiveImbalance > 0
      ? `You are up +${perspectiveImbalance}`
      : perspectiveImbalance < 0
        ? `You are down ${perspectiveImbalance}`
        : "Material is equal";

  const renderList = (items, capturedColor) => {
    if (items.length === 0) {
      return <span className="text-slate-500">none</span>;
    }
    const icons = [];
    for (const item of items) {
      for (let index = 0; index < item.count; index += 1) {
        icons.push(
          <span
            key={`${capturedColor}-${item.piece}-${index}`}
            className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-slate-300 bg-white/90 text-lg leading-none text-slate-900"
            title={item.piece}
          >
            {PIECE_ICONS[capturedColor][item.piece]}
          </span>
        );
      }
    }
    return icons;
  };

  return (
    <section className="panel rounded-2xl p-4">
      <h3 className="font-heading text-base font-bold text-ink">Material</h3>
      <p className="mt-1 text-sm font-semibold text-slate-700">{imbalanceText}</p>

      <div className="mt-3 space-y-2 text-sm">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Captured by White</p>
          <div className="flex flex-wrap gap-1">{renderList(material.capturedByWhite, "b")}</div>
        </div>
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Captured by Black</p>
          <div className="flex flex-wrap gap-1">{renderList(material.capturedByBlack, "w")}</div>
        </div>
      </div>
    </section>
  );
}
