import React from "react";

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

export default function EvalBar({ evaluation }) {
  const evalValue = clamp(evaluation?.normalized_pawns ?? 0, -10, 10);
  const whitePercent = clamp(((evalValue + 10) / 20) * 100, 0, 100);

  return (
    <section className="panel flex w-full flex-col items-center gap-3 rounded-2xl p-4">
      <h3 className="font-heading text-base font-bold text-ink">Eval</h3>
      <div className="relative h-64 w-12 overflow-hidden rounded-full border border-slate-400/50 bg-slate-900">
        <div
          className="absolute bottom-0 left-0 right-0 bg-ivory transition-all duration-500"
          style={{ height: `${whitePercent}%` }}
        />
      </div>
      <div className="rounded-lg bg-white/70 px-3 py-1 text-sm font-semibold text-dusk">
        {evalValue >= 0 ? "+" : ""}
        {evalValue.toFixed(2)}
      </div>
    </section>
  );
}
