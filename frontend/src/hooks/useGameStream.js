import { useEffect } from "react";

import { createCommentarySource } from "../api/client";

export function useGameStream(gameId, handlers) {
  useEffect(() => {
    if (!gameId) {
      return undefined;
    }

    const source = createCommentarySource(gameId);

    const bind = (eventName, handler) => {
      source.addEventListener(eventName, (event) => {
        if (!handler) {
          return;
        }
        try {
          const payload = JSON.parse(event.data || "{}");
          handler(payload);
        } catch {
          handler({});
        }
      });
    };

    bind("commentary_chunk", handlers?.onCommentaryChunk);
    bind("commentary_done", handlers?.onCommentaryDone);
    bind("engine_move", handlers?.onEngineMove);
    bind("opening_update", handlers?.onOpeningUpdate);
    bind("status", handlers?.onStatus);
    bind("error", handlers?.onError);
    bind("heartbeat", handlers?.onHeartbeat);

    source.onerror = () => {
      handlers?.onError?.({ message: "Commentary stream disconnected." });
    };

    return () => {
      source.close();
    };
  }, [gameId, handlers]);
}
