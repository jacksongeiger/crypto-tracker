import Link from "next/link";
import { getWeeklyThemes, getWeeklyWindow } from "@/lib/queries";
import { aggregateWeekly, buildWeeklySummary } from "@/lib/weekly";
import { SummaryCard } from "@/components/brief/summary-card";
import { ThemeCard } from "@/components/brief/theme-card";

export const dynamic = "force-dynamic";

const MIN_BRIEFS_FOR_USEFUL_ROUNDUP = 3;

function formatRange(first: string | null, last: string | null): string {
  if (!first || !last) return "past 7 days";
  const fmt = (iso: string) =>
    new Date(iso + "T00:00:00Z").toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      timeZone: "UTC",
    });
  return `${fmt(first)} – ${fmt(last)}`;
}

export default async function WeeklyPage() {
  const [rows, window] = await Promise.all([
    getWeeklyThemes(7),
    getWeeklyWindow(7),
  ]);
  const highlights = aggregateWeekly(rows, { limit: 10, perCategoryMax: 3 });
  const summary = buildWeeklySummary(highlights, window.briefCount);

  const isBelowMinimum =
    window.briefCount < MIN_BRIEFS_FOR_USEFUL_ROUNDUP;

  return (
    <main>
      <header className="relative isolate overflow-hidden border-b border-line-subtle bg-gradient-to-b from-brand-50/60 to-surface">
        <span
          aria-hidden
          className="absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r from-brand-500 via-brand-600 to-brand-500"
        />
        <div className="mx-auto max-w-5xl px-6 py-12 sm:px-8 sm:py-16">
          <div className="font-mono text-caption uppercase text-brand-700">
            News · Weekly
          </div>
          <h1 className="mt-3 text-display font-semibold tracking-tight text-ink">
            This Week
          </h1>
          <p className="mt-4 text-bodyLg text-ink-muted">
            The biggest stories from the past 7 days, ranked by conviction
            and cross-day persistence.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-bodySm text-ink-muted">
            <span className="tabular-nums">
              {formatRange(window.firstDate, window.lastDate)}
            </span>
            <span aria-hidden className="text-line">·</span>
            <span className="tabular-nums">
              {window.briefCount} brief{window.briefCount === 1 ? "" : "s"}
            </span>
            <span aria-hidden className="text-line">·</span>
            <span className="tabular-nums">
              {window.totalSignals} signals
            </span>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-6 pb-20 sm:px-8">
        <div className="-mt-6 sm:-mt-8">
          <SummaryCard summary={summary} label="This Week TL;DR" />
        </div>

        {isBelowMinimum || highlights.length === 0 ? (
          <section className="mt-12 rounded-md border border-line-subtle bg-surface-raised p-10 text-center">
            <p className="font-mono text-caption uppercase text-ink-subtle">
              Roundup pending
            </p>
            <p className="mt-3 text-bodyLg text-ink-muted">
              {isBelowMinimum
                ? `Weekly roundup needs at least ${MIN_BRIEFS_FOR_USEFUL_ROUNDUP} briefs to be useful. You have ${window.briefCount}.`
                : "No themes in the last 7 days yet."}{" "}
              Check back after the next daily synthesis.
            </p>
            <Link
              href="/news/overview"
              className="mt-4 inline-flex items-center gap-1.5 text-brand-700 hover:underline"
            >
              See today&apos;s brief →
            </Link>
          </section>
        ) : (
          <section className="mt-12">
            <div className="mb-5 font-mono text-caption uppercase text-ink-subtle">
              Top stories ({highlights.length})
            </div>
            <div className="space-y-5">
              {highlights.map((h, i) => (
                <div key={`${h.brief_id}-${h.id}`} className="relative">
                  {h.appearances > 1 && (
                    <span
                      className="absolute right-7 top-7 z-10 inline-flex items-center gap-1 rounded-full border border-brand-200 bg-brand-50 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.12em] text-brand-700"
                      aria-label={`Appeared in ${h.appearances} briefs this week`}
                    >
                      <span aria-hidden>×{h.appearances}</span>
                      <span>this week</span>
                    </span>
                  )}
                  <ThemeCard
                    theme={{ ...h, display_order: i }}
                    total={highlights.length}
                  />
                  <div className="mt-2 ml-1 flex flex-wrap items-baseline gap-2 text-bodySm text-ink-muted">
                    <Link
                      href={`/news/history/${h.brief_id}`}
                      className="text-brand-700 hover:underline"
                    >
                      View full brief from {formatShortDate(h.brief_date)} →
                    </Link>
                    {h.appearances > 1 && (
                      <span className="text-ink-subtle">
                        also in{" "}
                        {h.appeared_in
                          .filter((a) => a.brief_id !== h.brief_id)
                          .map((a) => formatShortDate(a.brief_date))
                          .join(", ")}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}

function formatShortDate(iso: string): string {
  return new Date(iso + "T00:00:00Z").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}
