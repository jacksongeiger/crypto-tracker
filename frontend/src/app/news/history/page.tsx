import Link from "next/link";
import { getBriefHistory, getBriefCount } from "@/lib/queries";
import { CategoryChip } from "@/components/brief/category-chip";
import type { BriefHistoryRow } from "@/lib/queries";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 20;

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

function truncate(s: string, n: number) {
  return s.length <= n ? s : s.slice(0, n - 1).trimEnd() + "…";
}

function convictionTone(score: number | null) {
  if (score === null) return "text-ink-subtle";
  if (score >= 5) return "text-brand-500";
  if (score >= 4) return "text-ink";
  if (score >= 3) return "text-ink-muted";
  return "text-ink-subtle";
}

function HistoryCard({ row }: { row: BriefHistoryRow }) {
  const dateStr = formatDateLong(row.brief_date);
  const maxConv = row.max_conviction ?? 0;
  return (
    <Link
      href={`/news/history/${row.id}`}
      className="group block rounded-md border border-line bg-surface p-7 transition-all duration-150 ease-coinbase hover:border-brand-200 hover:shadow-sm sm:p-8"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="font-mono text-caption uppercase text-ink-subtle">
            {row.brief_date}
          </div>
          <h2 className="mt-2 text-h2 font-semibold tracking-tight text-ink group-hover:text-brand-700">
            {dateStr}
          </h2>
        </div>
        {row.max_conviction !== null && (
          <div
            className={`inline-flex items-center gap-1.5 rounded-sm px-2 py-1 ${convictionTone(row.max_conviction)}`}
            aria-label={`Max conviction ${row.max_conviction} of 5`}
          >
            <span className="flex items-center gap-[3px]">
              {Array.from({ length: 5 }).map((_, i) => (
                <span
                  key={i}
                  className={`block h-[5px] w-[5px] rounded-full ${
                    i < maxConv ? "bg-current" : "bg-line"
                  }`}
                />
              ))}
            </span>
            <span className="font-mono tabular-nums text-[11px] font-semibold">
              {row.max_conviction}/5
            </span>
          </div>
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-bodySm text-ink-muted">
        <span className="tabular-nums">{row.theme_count} themes</span>
        <span aria-hidden className="text-line">·</span>
        <span className="tabular-nums">{row.input_signal_count} signals</span>
        <span aria-hidden className="text-line">·</span>
        <span className="font-mono text-xs">{row.model_used}</span>
      </div>

      <p className="mt-4 text-[1.0625rem] leading-[1.7] text-ink/85">
        {truncate(row.summary, 200)}
      </p>

      {row.top_themes.length > 0 && (
        <ul className="mt-5 space-y-1.5 border-l-2 border-line-subtle pl-4">
          {row.top_themes.map((t) => (
            <li key={t.display_order} className="flex items-baseline gap-2 text-bodySm text-ink/90">
              <span className="font-mono tabular-nums text-[10px] text-ink-subtle">
                {String(t.display_order + 1).padStart(2, "0")}
              </span>
              <span>{t.title}</span>
            </li>
          ))}
        </ul>
      )}

      {row.categories.length > 0 && (
        <div className="mt-6 flex flex-wrap items-center gap-1.5">
          {row.categories.map((c) => (
            <CategoryChip key={c} category={c} asLink={false} />
          ))}
        </div>
      )}
    </Link>
  );
}

export default async function HistoryPage({
  searchParams,
}: {
  searchParams: { page?: string };
}) {
  const page = Math.max(1, Number(searchParams.page ?? "1") || 1);
  const offset = (page - 1) * PAGE_SIZE;
  const [rows, total] = await Promise.all([
    getBriefHistory({ limit: PAGE_SIZE, offset }),
    getBriefCount(),
  ]);
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <main>
      <header className="relative isolate overflow-hidden border-b border-line-subtle bg-gradient-to-b from-brand-50/60 to-surface">
        <span
          aria-hidden
          className="absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r from-brand-500 via-brand-600 to-brand-500"
        />
        <div className="mx-auto max-w-5xl px-6 py-12 sm:px-8 sm:py-16">
          <div className="font-mono text-caption uppercase text-brand-700">
            News · History
          </div>
          <h1 className="mt-3 text-display font-semibold tracking-tight text-ink">
            Brief History
          </h1>
          <p className="mt-4 text-bodyLg text-ink-muted">
            Past daily briefs, newest first. Click any card to read in full.
          </p>
          <p className="mt-3 font-mono text-xs uppercase tracking-[0.12em] text-ink-subtle">
            {total} brief{total === 1 ? "" : "s"} stored
          </p>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-6 pb-20 pt-8 sm:px-8 sm:pt-10">
        {rows.length === 0 ? (
          <section className="rounded-md border border-line-subtle bg-surface-raised p-10 text-center">
            <p className="font-mono text-caption uppercase text-ink-subtle">
              No briefs yet
            </p>
            <p className="mt-3 text-bodyLg text-ink-muted">
              Run synthesis to generate your first brief.
            </p>
            <pre className="mt-4 inline-block bg-surface-muted px-4 py-2 text-sm text-ink border border-line-subtle">
              skills/synthesize-brief/scripts/run.sh
            </pre>
          </section>
        ) : (
          <>
            <div className="space-y-5">
              {rows.map((r) => (
                <HistoryCard key={r.id} row={r} />
              ))}
            </div>

            {totalPages > 1 && (
              <nav
                className="mt-10 flex items-center justify-between border-t border-line-subtle pt-5 text-bodySm"
                aria-label="Pagination"
              >
                <Link
                  aria-disabled={page <= 1}
                  href={page > 1 ? `/news/history?page=${page - 1}` : "#"}
                  className={`inline-flex items-center gap-1 rounded-sm px-3 py-1.5 ${
                    page > 1
                      ? "text-brand-700 hover:bg-brand-50"
                      : "pointer-events-none text-ink-subtle"
                  }`}
                >
                  ← Newer
                </Link>
                <span className="font-mono text-xs text-ink-subtle">
                  page {page} of {totalPages}
                </span>
                <Link
                  aria-disabled={page >= totalPages}
                  href={
                    page < totalPages ? `/news/history?page=${page + 1}` : "#"
                  }
                  className={`inline-flex items-center gap-1 rounded-sm px-3 py-1.5 ${
                    page < totalPages
                      ? "text-brand-700 hover:bg-brand-50"
                      : "pointer-events-none text-ink-subtle"
                  }`}
                >
                  Older →
                </Link>
              </nav>
            )}
          </>
        )}
      </div>
    </main>
  );
}
