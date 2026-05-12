"use client";

import { useEffect, useRef, useState } from "react";

export function SourceChip({
  primaryName,
  corroborators,
}: {
  primaryName: string;
  corroborators: { id: string; name: string }[];
}) {
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

  const total = corroborators.length;

  return (
    <div ref={ref} className="relative inline-flex">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="dialog"
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 rounded-sm border border-line-subtle bg-surface px-2 py-1 text-bodySm transition-colors duration-150 ease-coinbase hover:border-brand-200 hover:bg-brand-50"
      >
        <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-subtle">
          primary
        </span>
        <span className="font-medium text-ink">{primaryName}</span>
        {total > 0 && (
          <span className="ml-1 font-mono tabular-nums text-[11px] text-ink-muted">
            +{total}
          </span>
        )}
      </button>

      {open && total > 0 && (
        <div
          role="dialog"
          aria-label="Corroborating sources"
          className="absolute left-0 top-full z-30 mt-2 w-64 rounded-md border border-line bg-surface p-3 shadow-md"
        >
          <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-subtle">
            Corroborating sources ({total})
          </div>
          <ul className="space-y-1.5">
            {corroborators.map((c) => (
              <li
                key={c.id}
                className="flex items-center gap-2 text-bodySm text-ink"
              >
                <span aria-hidden className="block h-1 w-1 rounded-full bg-brand-500" />
                {c.name}
              </li>
            ))}
          </ul>
        </div>
      )}
      {open && total === 0 && (
        <div
          role="dialog"
          aria-label="Corroborating sources"
          className="absolute left-0 top-full z-30 mt-2 w-64 rounded-md border border-line bg-surface p-3 shadow-md text-bodySm text-ink-muted"
        >
          Single-sourced — no corroborators.
        </div>
      )}
    </div>
  );
}
