import type { Category } from "@/types/brief";
import { CATEGORY_LABELS } from "@/types/brief";

function formatDateLong(iso: string) {
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function BriefHeader({
  briefDate,
  modelUsed,
  inputSignalCount,
  generatedAt,
  category,
  themeCount,
}: {
  briefDate: string;
  modelUsed: string;
  inputSignalCount: number;
  generatedAt: string;
  category?: Category | "overview";
  themeCount?: number;
}) {
  const eyebrow =
    category && category !== "overview"
      ? `News · ${CATEGORY_LABELS[category]}`
      : "Daily Brief";
  const gen = new Date(generatedAt).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
    timeZoneName: "short",
  });
  return (
    <header className="relative isolate overflow-hidden border-b border-line-subtle bg-gradient-to-b from-brand-50/60 to-surface">
      <span
        aria-hidden
        className="absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r from-brand-500 via-brand-600 to-brand-500"
      />
      <div className="mx-auto max-w-3xl px-6 py-12 sm:px-8 sm:py-16">
        <div className="font-mono text-caption uppercase text-brand-700">
          {eyebrow}
        </div>
        <h1 className="mt-3 text-display font-semibold tracking-tight text-ink">
          {formatDateLong(briefDate)}
        </h1>
        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-bodySm text-ink-muted">
          <span className="font-mono text-ink">{modelUsed}</span>
          <span aria-hidden className="text-line">
            ·
          </span>
          <span className="tabular-nums">
            {inputSignalCount} input signals
          </span>
          <span aria-hidden className="text-line">
            ·
          </span>
          <span className="tabular-nums">generated {gen}</span>
          {typeof themeCount === "number" && (
            <>
              <span aria-hidden className="text-line">
                ·
              </span>
              <span className="tabular-nums">
                {themeCount} theme{themeCount === 1 ? "" : "s"}
              </span>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
