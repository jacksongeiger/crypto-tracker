"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type SourceGroup = { name: string; count: number };

// Group corroborating signals by source.name, then sort by count desc then
// alphabetically. Conviction is judged on unique sources, not signal count —
// so the popover displays one row per distinct source with a count for
// repeat contributors (e.g. "Defillama (7 signals)" instead of 7 rows).
export function groupCorroborators(
  corroborators: { id: string; name: string }[],
): SourceGroup[] {
  const counts = new Map<string, number>();
  for (const c of corroborators) {
    counts.set(c.name, (counts.get(c.name) ?? 0) + 1);
  }
  return Array.from(counts, ([name, count]) => ({ name, count })).sort(
    (a, b) => b.count - a.count || a.name.localeCompare(b.name),
  );
}

// The "+N" chip counts UNIQUE independent sources that differ from the
// primary, not the raw signal count. A theme whose 7 Defillama
// corroborators come from the same source as the primary ("Defillama")
// plus 1 Fear & Greed signal has 1 independent corroborator, not 8.
export function uniqueIndependentSourceCount(
  primaryName: string,
  corroborators: { id: string; name: string }[],
): number {
  const names = new Set<string>();
  for (const c of corroborators) {
    if (c.name !== primaryName) names.add(c.name);
  }
  return names.size;
}

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

  const grouped = useMemo(() => groupCorroborators(corroborators), [corroborators]);
  const badgeCount = useMemo(
    () => uniqueIndependentSourceCount(primaryName, corroborators),
    [primaryName, corroborators],
  );

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
        {badgeCount > 0 && (
          <span
            className="ml-1 font-mono tabular-nums text-[11px] text-ink-muted"
            aria-label={`${badgeCount} corroborating source${badgeCount === 1 ? "" : "s"}`}
          >
            +{badgeCount} {badgeCount === 1 ? "source" : "sources"}
          </span>
        )}
      </button>

      {open && grouped.length > 0 && (
        <div
          role="dialog"
          aria-label="Corroborating sources"
          className="absolute left-0 top-full z-30 mt-2 w-72 rounded-md border border-line bg-surface p-3 shadow-md"
        >
          <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-subtle">
            Corroborating sources ({grouped.length})
          </div>
          <ul className="space-y-1.5">
            {grouped.map((g) => (
              <li
                key={g.name}
                className="flex items-center gap-2 text-bodySm text-ink"
              >
                <span aria-hidden className="block h-1 w-1 rounded-full bg-brand-500" />
                <span className="font-medium">{g.name}</span>
                {g.count > 1 && (
                  <span className="font-mono tabular-nums text-[11px] text-ink-muted">
                    ({g.count} signals)
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      {open && grouped.length === 0 && (
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
