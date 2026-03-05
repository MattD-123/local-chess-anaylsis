import React, { useEffect, useMemo, useState } from "react";

import Board from "./components/Board";
import Commentary from "./components/Commentary";
import EvalBar from "./components/EvalBar";
import MoveHistory from "./components/MoveHistory";
import OpeningDisplay from "./components/OpeningDisplay";
import Settings from "./components/Settings";
import MaterialPanel from "./components/MaterialPanel";
import AnalysisBoard from "./components/AnalysisBoard";
import { useGame } from "./providers/GameProvider";

export default function App() {
  const {
    state,
    startGame,
    makeMove,
    requestHint,
    resign,
    saveSettings,
    setViewFen,
    importGamePgn,
    exportGamePgn,
  } = useGame();
  const [dismissedGameOverFor, setDismissedGameOverFor] = useState(null);
  const [activeSection, setActiveSection] = useState("play");

  useEffect(() => {
    setDismissedGameOverFor(null);
  }, [state.gameId]);

  const showGameOverModal =
    state.gameOver && state.gameId && dismissedGameOverFor !== state.gameId;

  const gameOverTitle = useMemo(() => {
    const reason = (state.terminationReason || "").toLowerCase();
    if (reason === "checkmate") {
      return "Checkmate";
    }
    if (reason === "stalemate" || reason.includes("draw")) {
      return "Draw";
    }
    if (reason === "resigned") {
      return "Resignation";
    }
    return "Game Over";
  }, [state.terminationReason]);

  return (
    <main className="mx-auto max-w-[1400px] px-4 py-6 md:px-6 md:py-8">
      <header className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="font-heading text-3xl font-black text-ink md:text-4xl">Interactive Chess Coach</h1>
          <p className="text-sm text-slate-600">Stockfish-backed play with live LLM commentary and opening awareness.</p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-white"
            onClick={() => startGame("white")}
          >
            New Game as White
          </button>
          <button
            type="button"
            className="rounded-lg border border-slate-500 px-4 py-2 text-sm font-semibold text-slate-700"
            onClick={() => startGame("black")}
          >
            New Game as Black
          </button>
        </div>
      </header>

      <section className="mb-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          className={`rounded-lg px-4 py-2 text-sm font-semibold ${
            activeSection === "play"
              ? "bg-ink text-white"
              : "border border-slate-400 bg-white/70 text-slate-700"
          }`}
          onClick={() => setActiveSection("play")}
        >
          Play
        </button>
        <button
          type="button"
          className={`rounded-lg px-4 py-2 text-sm font-semibold ${
            activeSection === "analyze"
              ? "bg-ink text-white"
              : "border border-slate-400 bg-white/70 text-slate-700"
          }`}
          onClick={() => setActiveSection("analyze")}
        >
          Analyze
        </button>
      </section>

      {state.health && (state.health.engine.status !== "ok" || state.health.llm.status !== "ok" || state.health.openings.status !== "ok") ? (
        <aside className="mb-4 rounded-xl border border-amber-300 bg-amber-100/70 px-4 py-2 text-sm text-amber-900">
          <strong>Provider warning:</strong> engine={state.health.engine.status}, llm={state.health.llm.status}, openings={state.health.openings.status}
        </aside>
      ) : null}

      {state.error ? (
        <aside className="mb-4 rounded-xl border border-red-300 bg-red-100/70 px-4 py-2 text-sm text-red-900">{state.error}</aside>
      ) : null}

      {activeSection === "play" ? (
        <section className="grid gap-4 lg:grid-cols-[90px_minmax(0,1fr)_360px]">
          <EvalBar evaluation={state.currentEval} />

          <div className="grid min-w-0 gap-4">
            <Board state={state} makeMove={makeMove} />
            <MaterialPanel fen={state.fen === "start" ? undefined : state.fen} playerColor={state.playerColor} />
            <MoveHistory state={state} setViewFen={setViewFen} />
          </div>

          <div className="grid min-w-0 gap-4">
            <OpeningDisplay opening={state.opening} />
            <Commentary state={state} />
            <Settings
              config={state.config}
              gameOptions={state.gameOptions}
              saveSettings={saveSettings}
              requestHint={requestHint}
              resign={resign}
              hint={state.hint}
              gameId={state.gameId}
              playerColor={state.playerColor}
              importGamePgn={importGamePgn}
              exportGamePgn={exportGamePgn}
            />
          </div>
        </section>
      ) : (
        <section className="grid gap-4 lg:grid-cols-[90px_minmax(360px,520px)_minmax(0,1fr)]">
          <EvalBar evaluation={state.currentEval} />

          <div className="grid min-w-0 gap-4">
            <Board state={state} makeMove={makeMove} interactive={false} />
            <MaterialPanel fen={state.fen === "start" ? undefined : state.fen} playerColor={state.playerColor} />
            <MoveHistory state={state} setViewFen={setViewFen} showAnalyzeControls />
          </div>

          <div className="grid min-w-0 gap-4">
            <AnalysisBoard state={state} setViewFen={setViewFen} />
            <OpeningDisplay opening={state.opening} />
          </div>
        </section>
      )}

      {state.gameOver ? (
        <footer className="mt-4 rounded-xl border border-slate-300 bg-white/70 px-4 py-2 text-sm text-slate-700">
          Game over: <strong>{state.result}</strong> ({state.terminationReason})
        </footer>
      ) : null}

      {showGameOverModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-300 bg-white p-5 shadow-2xl">
            <h2 className="font-heading text-2xl font-black text-ink">{gameOverTitle}</h2>
            <p className="mt-2 text-sm text-slate-700">
              Result: <strong>{state.result}</strong>
            </p>
            <p className="mt-1 text-sm text-slate-700">
              Termination: <strong>{state.terminationReason}</strong>
            </p>

            <div className="mt-5 flex flex-wrap gap-2">
              <button
                type="button"
                className="rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-white"
                onClick={() => startGame(state.playerColor || "white")}
              >
                New Game
              </button>
              <button
                type="button"
                className="rounded-lg border border-slate-400 px-4 py-2 text-sm font-semibold text-slate-700"
                onClick={() => setDismissedGameOverFor(state.gameId)}
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
