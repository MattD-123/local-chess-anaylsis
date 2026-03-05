import React, { useEffect, useMemo, useRef } from "react";

import { selectCommentaryEntries } from "../../providers/GameProvider";

export default function Commentary({ state }) {
  const entries = useMemo(() => selectCommentaryEntries(state), [state]);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries, state.typing]);

  return (
    <section className="panel flex h-[320px] flex-col rounded-2xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-heading text-base font-bold text-ink">Commentary</h3>
        {state.typing ? (
          <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-ember">
            <span className="h-2 w-2 rounded-full bg-ember animate-pulseSoft" />
            generating
          </span>
        ) : null}
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto pr-1 text-sm text-slate-700">
        {entries.length === 0 ? (
          <p className="text-slate-500">Commentary will stream here as moves are played.</p>
        ) : null}

        {entries.map((entry) => (
          <article
            key={entry.key}
            className="animate-riseIn rounded-xl border border-slate-300/60 bg-white/70 p-3 leading-relaxed"
          >
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
              {entry.moveNumber ? `Move ${entry.moveNumber} ${entry.color}` : "Live"}
            </p>
            <p>{entry.text}</p>
          </article>
        ))}
        <div ref={bottomRef} />
      </div>
    </section>
  );
}
