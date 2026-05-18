"use client";

import { useEffect, useRef, useState } from "react";

function pipsClass(score: number) {
  if (score >= 5) return "text-brand-500";
  if (score >= 4) return "text-ink";
  if (score >= 3) return "text-ink-muted";
  return "text-ink-subtle";
}

const SCALE = [
  { score: 1, label: "Single source, speculative or opinion" },
  { score: 2, label: "Single source, concrete factual claim" },
  { score: 3, label: "Two same-type sources" },
  { score: 4, label: "Three+ same-type sources" },
  { score: 5, label: "Cross-source-type corroboration (≥2 source types)" },
];

export function ConvictionBadge({ score }: { score: number | null }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    }
    if (open) {
      document.addEventListener("mousedown", handler);
      return () => document.removeEventListener("mousedown", handler);
    }
  }, [open]);

  if (score === null) {
    return (
      <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-subtle">
        unscored
      </span>
    );
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={`Conviction ${score} of 5 — click for scale`}
        className={`inline-flex items-center gap-1.5 rounded-sm px-2 py-1 transition-colors duration-150 ease-coinbase ${pipsClass(score)} hover:bg-surface-muted`}
      >
        <span className="flex items-center gap-[3px]">
          {Array.from({ length: 5 }).map((_, i) => (
            <span
              key={i}
              className={`block h-[5px] w-[5px] rounded-full ${
                i < score ? "bg-current" : "bg-line"
              }`}
            />
          ))}
        </span>
        <span className="font-mono tabular-nums text-[11px] font-semibold">
          {score}/5
        </span>
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Conviction scale"
          className="absolute right-0 top-full z-30 mt-2 w-72 rounded-md border border-line bg-surface p-3 shadow-md"
        >
          <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-subtle">
            Conviction scale
          </div>
          <ul className="space-y-1.5">
            {SCALE.map((row) => (
              <li
                key={row.score}
                className={`flex items-start gap-2 text-[12px] ${
                  row.score === score ? "text-ink font-medium" : "text-ink-muted"
                }`}
              >
                <span className="font-mono tabular-nums w-4 shrink-0 text-right">
                  {row.score}
                </span>
                <span>{row.label}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
