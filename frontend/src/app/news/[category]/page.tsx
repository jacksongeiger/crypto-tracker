import { notFound } from "next/navigation";
import { getLatestBriefByCategory } from "@/lib/queries";
import { BriefHeader } from "@/components/brief/brief-header";
import { BriefMeta } from "@/components/brief/brief-meta";
import { SummaryCard } from "@/components/brief/summary-card";
import { ThemeCard } from "@/components/brief/theme-card";
import type { Category } from "@/types/brief";
import { CATEGORIES, CATEGORY_LABELS } from "@/types/brief";

export const dynamic = "force-dynamic";

function isCategory(v: string): v is Category {
  return (CATEGORIES as readonly string[]).includes(v);
}

export default async function CategoryPage({
  params,
}: {
  params: { category: string };
}) {
  if (params.category === "overview") {
    notFound();
  }
  if (!isCategory(params.category)) {
    notFound();
  }
  const category = params.category as Category;
  const data = await getLatestBriefByCategory(category);

  if (!data) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-24 sm:px-8">
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

  // Derive a category-specific lead sentence from the filtered themes.
  // Falls back to the brief's overall summary if there are no themes here.
  const themeCount = data.themes.length;
  const lead =
    themeCount === 0
      ? `Today's brief had no themes tagged ${CATEGORY_LABELS[category]}. The full brief covers other categories.`
      : `${themeCount} theme${themeCount === 1 ? "" : "s"} in ${CATEGORY_LABELS[category]} today. Highest-conviction first.`;

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

      <div className="mx-auto max-w-3xl px-6 pb-20 sm:px-8">
        <div className="-mt-6 sm:-mt-8">
          <SummaryCard summary={lead} label={`${CATEGORY_LABELS[category]} TL;DR`} />
        </div>

        {themeCount === 0 ? (
          <section className="mt-12 rounded-md border border-line-subtle bg-surface-raised p-10 text-center">
            <p className="font-mono text-caption uppercase text-ink-subtle">
              No themes
            </p>
            <p className="mt-3 text-bodyLg text-ink-muted">
              Nothing in this category in today's brief.
            </p>
            <a
              href="/news/overview"
              className="mt-4 inline-flex items-center gap-1.5 text-brand-700 hover:underline"
            >
              See the full brief →
            </a>
          </section>
        ) : (
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
