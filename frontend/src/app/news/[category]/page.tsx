import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getLatestBriefByCategory,
  getRecentCategoryThemes,
  type RecentCategoryTheme,
} from "@/lib/queries";
import { BriefHeader } from "@/components/brief/brief-header";
import { BriefMeta } from "@/components/brief/brief-meta";
import { SummaryCard } from "@/components/brief/summary-card";
import { ThemeCard } from "@/components/brief/theme-card";
import { buildCategorySummary } from "@/lib/category-summary";
import type { Category } from "@/types/brief";
import { CATEGORIES, CATEGORY_LABELS } from "@/types/brief";

export const dynamic = "force-dynamic";

function isCategory(v: string): v is Category {
  return (CATEGORIES as readonly string[]).includes(v);
}

function formatShortDate(iso: string) {
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

export default async function CategoryPage({
  params,
}: {
  params: { category: string };
}) {
  if (params.category === "overview") notFound();
  if (!isCategory(params.category)) notFound();
  const category = params.category as Category;
  const data = await getLatestBriefByCategory(category);

  if (!data) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-24 sm:px-8">
        <p className="font-mono text-caption uppercase text-ink-subtle">
          News · {CATEGORY_LABELS[category]}
        </p>
        <h1 className="mt-3 text-display font-semibold text-ink">
          No brief yet
        </h1>
        <p className="mt-4 text-bodyLg text-ink-muted">
          Generate one with the synthesize-brief skill.
        </p>
      </main>
    );
  }

  const themeCount = data.themes.length;
  const summary = buildCategorySummary(category, data.themes);

  // When today is empty for this category, pull the past 7 days of
  // themes tagged with it (excluding today's already-empty brief). This
  // turns "quiet day" pages from dead-ends into "what was happening here
  // recently" — which is what users actually want.
  const fallback: RecentCategoryTheme[] =
    themeCount === 0
      ? await getRecentCategoryThemes(category, {
          days: 7,
          limit: 5,
          excludeBriefIds: [data.brief.id],
        })
      : [];

  return (
    <main>
      <BriefHeader
        briefDate={data.brief.brief_date}
        modelUsed={data.brief.model_used}
        inputSignalCount={data.brief.input_signal_count}
        generatedAt={data.brief.generated_at}
        category={category}
        themeCount={themeCount}
      />

      <div className="mx-auto max-w-5xl px-6 pb-20 sm:px-8">
        <div className="-mt-6 sm:-mt-8">
          <SummaryCard
            summary={summary}
            label={`${CATEGORY_LABELS[category]} TL;DR`}
          />
        </div>

        {themeCount > 0 ? (
          <section className="mt-12">
            <div className="mb-5 font-mono text-caption uppercase text-ink-subtle">
              Themes ({themeCount})
            </div>
            <div className="space-y-5">
              {data.themes.map((theme, i) => (
                <ThemeCard
                  key={theme.id}
                  theme={{ ...theme, display_order: i }}
                  total={themeCount}
                />
              ))}
            </div>
          </section>
        ) : fallback.length > 0 ? (
          <section className="mt-12">
            <div className="mb-5 flex items-baseline justify-between gap-4">
              <div className="font-mono text-caption uppercase text-ink-subtle">
                Recent {CATEGORY_LABELS[category]} · past 7 days
              </div>
              <Link
                href="/news/history"
                className="text-bodySm text-brand-700 hover:underline"
              >
                Full history →
              </Link>
            </div>
            <div className="space-y-5">
              {fallback.map((theme, i) => (
                <div key={theme.id} className="relative">
                  <Link
                    href={`/news/history/${theme.brief_id}`}
                    className="absolute right-7 top-7 z-10 font-mono text-caption uppercase text-ink-subtle hover:text-brand-700"
                    title="Jump to the brief this theme came from"
                  >
                    {formatShortDate(theme.brief_date)} ↗
                  </Link>
                  <ThemeCard
                    theme={{ ...theme, display_order: i }}
                    total={fallback.length}
                  />
                </div>
              ))}
            </div>
          </section>
        ) : (
          <section className="mt-12 rounded-md border border-line-subtle bg-surface-raised p-10 text-center">
            <p className="font-mono text-caption uppercase text-ink-subtle">
              No coverage
            </p>
            <p className="mt-3 text-bodyLg text-ink-muted">
              Nothing tagged {CATEGORY_LABELS[category]} in the past week.
            </p>
            <Link
              href="/news/overview"
              className="mt-4 inline-flex items-center gap-1.5 text-brand-700 hover:underline"
            >
              See today&apos;s full brief →
            </Link>
          </section>
        )}

        <BriefMeta
          briefId={data.brief.id}
          generatedAt={data.brief.generated_at}
          inputSignalCount={data.brief.input_signal_count}
          modelUsed={data.brief.model_used}
        />
      </div>
    </main>
  );
}
