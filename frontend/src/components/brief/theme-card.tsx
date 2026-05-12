import type { BriefTheme } from "@/types/brief";
import { CategoryChip } from "./category-chip";
import { ConvictionBadge } from "./conviction-badge";
import { SourceChip } from "./source-popover";

export function ThemeCard({
  theme,
  total,
}: {
  theme: BriefTheme;
  total: number;
}) {
  const index = theme.display_order + 1;
  return (
    <article className="group relative rounded-md border border-line bg-surface p-7 transition-all duration-150 ease-coinbase hover:border-brand-200 hover:shadow-sm sm:p-8">
      <div className="flex items-start justify-between gap-4">
        <div className="font-mono text-caption uppercase text-ink-subtle">
          {String(index).padStart(2, "0")} / {String(total).padStart(2, "0")}
        </div>
        <ConvictionBadge score={theme.conviction_score} />
      </div>

      <h2 className="mt-2 text-h2 font-semibold text-ink">{theme.title}</h2>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <SourceChip
          primaryName={theme.primary_source_name}
          corroborators={theme.corroborating_sources}
        />
      </div>

      <p className="mt-5 text-bodyLg text-ink/90">{theme.body}</p>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-line-subtle pt-5">
        <div className="flex flex-wrap items-center gap-1.5">
          {theme.categories.map((c) => (
            <CategoryChip key={c} category={c} />
          ))}
        </div>
        {theme.primary_signal_url ? (
          <a
            href={theme.primary_signal_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-sm px-3 py-1.5 text-bodySm font-medium text-brand-700 transition-colors duration-150 ease-coinbase hover:bg-brand-50"
          >
            Read primary article
            <span aria-hidden>→</span>
          </a>
        ) : (
          <span className="text-bodySm text-ink-muted">
            {theme.primary_signal_title}
          </span>
        )}
      </div>
    </article>
  );
}
