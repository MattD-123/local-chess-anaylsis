import React, { useEffect, useMemo, useState } from "react";
import { Chess } from "chess.js";
import { Chessboard } from "react-chessboard";

import { selectDisplayedFen } from "../../providers/GameProvider";

function uciToSquares(uci) {
  if (!uci || uci.length < 4) {
    return [null, null];
  }
  return [uci.slice(0, 2), uci.slice(2, 4)];
}

export default function Board({ state, makeMove }) {
  const [selectedSquare, setSelectedSquare] = useState(null);
  const [legalTargets, setLegalTargets] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [optimisticFen, setOptimisticFen] = useState(null);

  const position = optimisticFen || selectDisplayedFen(state);
  const liveBoard = state.viewFen == null;

  const board = useMemo(() => {
    const game = new Chess();
    if (position) {
      game.load(position);
    }
    return game;
  }, [position]);

  const isPlayerTurn = useMemo(() => {
    const playerColor = state.playerColor === "black" ? "black" : "white";
    const turn = board.turn();
    if (playerColor === "white") {
      return turn === "w";
    }
    return turn === "b";
  }, [board, state.playerColor]);

  const canMovePieces = liveBoard && !state.gameOver && !submitting && isPlayerTurn;

  const applyMoveOptimistically = (from, to, promotion = "q") => {
    const next = new Chess();
    const baseFen = selectDisplayedFen(state);
    if (baseFen) {
      next.load(baseFen);
    }
    const result = next.move({ from, to, promotion });
    if (!result) {
      return null;
    }
    return next.fen();
  };

  const submitMoveOptimistic = (uciMove, nextFen) => {
    setSubmitting(true);
    setOptimisticFen(nextFen);
    makeMove(uciMove)
      .catch(() => {
        setOptimisticFen(null);
      })
      .finally(() => {
        setSubmitting(false);
      });
  };

  const onSquareClick = async (square) => {
    if (!canMovePieces) {
      return;
    }

    // Click-to-move fallback: if target is legal for selected source, submit immediately.
    if (selectedSquare && legalTargets.includes(square)) {
      const piece = board.get(selectedSquare);
      const promotion =
        piece?.type === "p" && (square.endsWith("8") || square.endsWith("1")) ? "q" : "";
      const nextFen = applyMoveOptimistically(selectedSquare, square, promotion || "q");
      if (!nextFen) {
        return;
      }
      submitMoveOptimistic(`${selectedSquare}${square}${promotion}`, nextFen);
      setSelectedSquare(null);
      setLegalTargets([]);
      return;
    }

    if (selectedSquare === square) {
      setSelectedSquare(null);
      setLegalTargets([]);
      return;
    }

    const moves = board.moves({ square, verbose: true });
    if (moves.length === 0) {
      setSelectedSquare(null);
      setLegalTargets([]);
      return;
    }

    setSelectedSquare(square);
    setLegalTargets(moves.map((move) => move.to));
  };

  const onPieceDrop = async (sourceSquare, targetSquare, piece) => {
    if (!canMovePieces) {
      return false;
    }

    const promotion =
      piece?.toLowerCase() === "wp" && targetSquare.endsWith("8")
        ? "q"
        : piece?.toLowerCase() === "bp" && targetSquare.endsWith("1")
          ? "q"
          : "";

    const nextFen = applyMoveOptimistically(sourceSquare, targetSquare, promotion || "q");
    if (!nextFen) {
      return false;
    }
    submitMoveOptimistic(`${sourceSquare}${targetSquare}${promotion}`, nextFen);
    setSelectedSquare(null);
    setLegalTargets([]);
    return true;
  };

  useEffect(() => {
    // Clear optimistic board once canonical FEN updates from API/SSE.
    if (optimisticFen && !submitting) {
      setOptimisticFen(null);
    }
  }, [optimisticFen, state.fen, submitting]);

  const lastMove = state.moveHistory[state.moveHistory.length - 1];
  const [lastFrom, lastTo] = uciToSquares(lastMove?.uci);
  const analysisMove = state.viewFen
    ? state.moveHistory.find((move) => move.fen_after === state.viewFen)
    : null;
  const bestMoveUci = analysisMove?.best_move || null;
  const [bestFrom, bestTo] = uciToSquares(bestMoveUci);

  const customSquareStyles = {
    ...(lastFrom
      ? {
          [lastFrom]: { backgroundColor: "rgba(194, 65, 12, 0.22)" },
        }
      : {}),
    ...(lastTo
      ? {
          [lastTo]: { backgroundColor: "rgba(20, 83, 45, 0.26)" },
        }
      : {}),
    ...(selectedSquare
      ? {
          [selectedSquare]: { boxShadow: "inset 0 0 0 3px rgba(12, 74, 110, 0.55)" },
        }
      : {}),
    ...Object.fromEntries(
      legalTargets.map((target) => [
        target,
        {
          background:
            "radial-gradient(circle, rgba(15, 118, 110, 0.45) 24%, rgba(15, 118, 110, 0.14) 25%)",
        },
      ])
    ),
  };
  const customArrows = bestFrom && bestTo ? [[bestFrom, bestTo, "rgba(29, 78, 216, 0.72)"]] : [];

  return (
    <section className="panel rounded-2xl p-4 md:p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-heading text-lg font-bold text-ink">Board</h2>
        {state.engineThinking && !isPlayerTurn ? (
          <span className="inline-flex items-center gap-2 text-sm font-semibold text-ember">
            <span className="h-2.5 w-2.5 rounded-full bg-ember animate-pulseSoft" />
            Engine thinking
          </span>
        ) : null}
      </div>
      {!liveBoard ? (
        <p className="mb-3 rounded-md border border-slate-300 bg-white/70 px-2 py-1 text-xs text-slate-600">
          Viewing a past position. Click "Live Position" in Move History to play moves.
        </p>
      ) : null}

      <div className="relative mx-auto max-w-[620px]">
        <Chessboard
          id="main-board"
          boardOrientation={state.playerColor || "white"}
          position={position}
          arePiecesDraggable={canMovePieces}
          onPieceDrop={onPieceDrop}
          onSquareClick={onSquareClick}
          customSquareStyles={customSquareStyles}
          customArrows={customArrows}
          animationDuration={300}
          customDarkSquareStyle={{ backgroundColor: "#6b7280" }}
          customLightSquareStyle={{ backgroundColor: "#e5e7eb" }}
        />
      </div>
      {!liveBoard && bestMoveUci ? (
        <p className="mt-3 text-xs font-semibold text-blue-700">Best move suggestion: {bestMoveUci}</p>
      ) : null}
    </section>
  );
}
