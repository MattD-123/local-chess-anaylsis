import React, { createContext, useCallback, useContext, useEffect, useMemo, useReducer } from "react";

import {
  exportPgn,
  getConfig,
  getHealth,
  getHint,
  importPgn,
  newGame,
  resignGame,
  submitMove,
  updateConfig,
} from "../api/client";
import { useGameStream } from "../hooks/useGameStream";

const GameContext = createContext(null);

const initialState = {
  gameId: null,
  playerColor: "white",
  fen: "start",
  viewFen: null,
  moveHistory: [],
  opening: null,
  currentEval: { normalized_pawns: 0 },
  commentaryDrafts: {},
  commentaryHistory: [],
  typing: false,
  engineThinking: false,
  gameOver: false,
  result: null,
  terminationReason: null,
  config: null,
  health: null,
  hint: null,
  error: null,
};

function keyForMove(move) {
  return `${move.move_number}-${move.color}`;
}

function reducer(state, action) {
  switch (action.type) {
    case "SET_CONFIG":
      return { ...state, config: action.payload };
    case "SET_HEALTH":
      return { ...state, health: action.payload };
    case "NEW_GAME":
      return {
        ...state,
        gameId: action.payload.game_id,
        playerColor: action.payload.player_color || state.playerColor || "white",
        fen: action.payload.fen,
        viewFen: null,
        moveHistory: [],
        opening: null,
        commentaryDrafts: {},
        commentaryHistory: [],
        typing: false,
        engineThinking: action.payload.engine_to_move,
        gameOver: false,
        result: null,
        terminationReason: null,
        hint: null,
        error: null,
      };
    case "MOVE_RESPONSE":
      return {
        ...state,
        viewFen: null,
        fen: action.payload.fen,
        moveHistory: action.payload.move_history,
        opening: action.payload.opening,
        currentEval: action.payload.current_eval,
        gameOver: action.payload.game_over,
        result: action.payload.result,
        terminationReason: action.payload.termination_reason,
        engineThinking: action.payload.engine_thinking,
      };
    case "IMPORT_GAME":
      return {
        ...state,
        gameId: action.payload.game_id,
        playerColor: action.payload.player_color || "white",
        fen: action.payload.fen,
        viewFen: null,
        moveHistory: action.payload.move_history || [],
        opening: action.payload.opening || null,
        currentEval: action.payload.current_eval || { normalized_pawns: 0 },
        commentaryDrafts: {},
        commentaryHistory: [],
        typing: false,
        engineThinking: false,
        gameOver: Boolean(action.payload.game_over),
        result: action.payload.result || null,
        terminationReason: action.payload.termination_reason || null,
        hint: null,
        error: null,
      };
    case "ENGINE_MOVE_EVENT":
      return {
        ...state,
        viewFen: null,
        fen: action.payload.fen ?? state.fen,
        currentEval: action.payload.eval ?? state.currentEval,
        moveHistory: action.payload.move
          ? [...state.moveHistory, action.payload.move]
          : state.moveHistory,
        engineThinking: false,
      };
    case "OPENING_UPDATE":
      return { ...state, opening: action.payload.opening ?? null };
    case "COMMENTARY_CHUNK": {
      const key = `${action.payload.move_number}-${action.payload.color}`;
      const previous = state.commentaryDrafts[key] || "";
      return {
        ...state,
        typing: true,
        commentaryDrafts: {
          ...state.commentaryDrafts,
          [key]: previous + (action.payload.chunk || ""),
        },
      };
    }
    case "COMMENTARY_DONE": {
      const key = `${action.payload.move_number}-${action.payload.color}`;
      const draftText = state.commentaryDrafts[key] || action.payload.text || "";
      const nextDrafts = { ...state.commentaryDrafts };
      delete nextDrafts[key];
      return {
        ...state,
        typing: false,
        commentaryDrafts: nextDrafts,
        commentaryHistory: [
          ...state.commentaryHistory,
          {
            key,
            moveNumber: action.payload.move_number,
            color: action.payload.color,
            text: draftText,
          },
        ],
      };
    }
    case "STATUS":
      return {
        ...state,
        typing: action.payload.typing ?? state.typing,
        engineThinking: action.payload.engine_thinking ?? state.engineThinking,
        gameOver: action.payload.game_over ?? state.gameOver,
        result: action.payload.result ?? state.result,
        terminationReason: action.payload.termination_reason ?? state.terminationReason,
      };
    case "SET_HINT":
      return { ...state, hint: action.payload };
    case "SET_ERROR":
      return { ...state, error: action.payload };
    case "SET_VIEW_FEN":
      return { ...state, viewFen: action.payload };
    default:
      return state;
  }
}

export function GameProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    getConfig()
      .then((result) => dispatch({ type: "SET_CONFIG", payload: result.config }))
      .catch((error) => dispatch({ type: "SET_ERROR", payload: error.message }));

    getHealth()
      .then((result) => dispatch({ type: "SET_HEALTH", payload: result }))
      .catch(() => {});
  }, []);

  const startGame = useCallback(async (playerColor = "white") => {
    const result = await newGame({ player_color: playerColor });
    const normalized = {
      ...result,
      player_color: result.player_color || playerColor,
    };
    dispatch({ type: "NEW_GAME", payload: normalized });
    return normalized;
  }, []);

  const makeMove = useCallback(
    async (move) => {
      if (!state.gameId) {
        throw new Error("Start a game before making moves.");
      }
      try {
        const result = await submitMove({ game_id: state.gameId, move });
        dispatch({ type: "MOVE_RESPONSE", payload: result });
        return result;
      } catch (error) {
        const message = error instanceof Error ? error.message : "Move failed";
        dispatch({ type: "SET_ERROR", payload: message });
        throw error;
      }
    },
    [state.gameId]
  );

  const requestHint = useCallback(async () => {
    if (!state.gameId) {
      return null;
    }
    const result = await getHint(state.gameId);
    dispatch({ type: "SET_HINT", payload: result.hint });
    return result.hint;
  }, [state.gameId]);

  const resign = useCallback(async () => {
    if (!state.gameId) {
      return null;
    }
    const result = await resignGame({ game_id: state.gameId });
    dispatch({ type: "STATUS", payload: result });
    return result;
  }, [state.gameId]);

  const saveSettings = useCallback(async (patch) => {
    const result = await updateConfig(patch);
    dispatch({ type: "SET_CONFIG", payload: result.config });
    return result.config;
  }, []);

  const setViewFen = useCallback((fen) => {
    dispatch({ type: "SET_VIEW_FEN", payload: fen });
  }, []);

  const importGamePgn = useCallback(
    async (pgnText, playerColor = state.playerColor || "white") => {
      const result = await importPgn({
        pgn: pgnText,
        player_color: playerColor,
      });
      dispatch({ type: "IMPORT_GAME", payload: result });
      return result;
    },
    [state.playerColor]
  );

  const exportGamePgn = useCallback(async () => {
    if (!state.gameId) {
      throw new Error("Start or import a game first.");
    }
    return exportPgn(state.gameId);
  }, [state.gameId]);

  const streamHandlers = useMemo(
    () => ({
      onCommentaryChunk: (payload) => dispatch({ type: "COMMENTARY_CHUNK", payload }),
      onCommentaryDone: (payload) => dispatch({ type: "COMMENTARY_DONE", payload }),
      onEngineMove: (payload) => dispatch({ type: "ENGINE_MOVE_EVENT", payload }),
      onOpeningUpdate: (payload) => dispatch({ type: "OPENING_UPDATE", payload }),
      onStatus: (payload) => dispatch({ type: "STATUS", payload }),
      onError: (payload) => dispatch({ type: "SET_ERROR", payload: payload.message || "Stream error" }),
      onHeartbeat: () => {},
    }),
    []
  );

  useGameStream(state.gameId, streamHandlers);

  const value = useMemo(
    () => ({
      state,
      startGame,
      makeMove,
      requestHint,
      resign,
      saveSettings,
      setViewFen,
      importGamePgn,
      exportGamePgn,
    }),
    [state, startGame, makeMove, requestHint, resign, saveSettings, setViewFen, importGamePgn, exportGamePgn]
  );

  return <GameContext.Provider value={value}>{children}</GameContext.Provider>;
}

export function useGame() {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error("useGame must be used within GameProvider");
  }
  return context;
}

export function selectDisplayedFen(state) {
  return state.viewFen || (state.fen === "start" ? undefined : state.fen);
}

export function selectMoveFen(state, index) {
  if (index < 0 || index >= state.moveHistory.length) {
    return null;
  }
  return state.moveHistory[index].fen_after;
}

export function selectCommentaryEntries(state) {
  const finished = state.commentaryHistory;
  const drafts = Object.entries(state.commentaryDrafts).map(([key, text]) => ({
    key,
    moveNumber: null,
    color: null,
    text,
    draft: true,
  }));
  return [...finished, ...drafts];
}

export function moveClassToColor(classification) {
  const normalized = (classification || "").toLowerCase();
  if (normalized === "best" || normalized === "excellent" || normalized === "good") {
    return "var(--good)";
  }
  if (normalized === "inaccuracy") {
    return "var(--inaccuracy)";
  }
  if (normalized === "forced") {
    return "#1d4ed8";
  }
  if (normalized === "mistake") {
    return "var(--mistake)";
  }
  if (normalized === "blunder") {
    return "var(--blunder)";
  }
  return "var(--text-dim)";
}
