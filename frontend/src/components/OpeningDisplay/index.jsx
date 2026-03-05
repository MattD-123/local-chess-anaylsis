import React from "react";

export default function OpeningDisplay({ opening }) {
  const inOpening = opening?.in_opening !== false && Boolean(opening?.name);

  return (
    <section
      className={`panel rounded-2xl p-4 transition-opacity duration-500 ${inOpening ? "opacity-100" : "opacity-40"}`}
    >
      <h3 className="font-heading text-base font-bold text-ink">Opening</h3>
      {opening?.name ? (
        <div className="group relative mt-2">
          <p className="text-sm font-semibold text-dusk">
            {opening.name} <span className="text-slate-500">({opening.eco})</span>
          </p>
          <p className="text-xs text-slate-500">
            {opening.in_opening ? `${opening.moves_remaining} theory moves remaining` : "Out of book"}
          </p>

          <div className="pointer-events-none absolute left-0 top-full z-10 mt-2 hidden w-64 rounded-lg border border-slate-300 bg-white p-2 text-xs text-slate-700 shadow-lg group-hover:block">
            {opening.variation || "Classical strategic themes and typical tactical motifs."}
          </div>
        </div>
      ) : (
        <p className="mt-2 text-sm text-slate-500">Opening not identified yet.</p>
      )}
    </section>
  );
}
