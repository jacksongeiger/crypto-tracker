import Link from "next/link";
import { notFound } from "next/navigation";
import { getBriefById } from "@/lib/queries";
import { BriefHeader } from "@/components/brief/brief-header";
import { BriefMeta } from "@/components/brief/brief-meta";
import { SummaryCard } from "@/components/brief/summary-card";
import { ThemeCard } from "@/components/brief/theme-card";

export const dynamic = "force-dynamic";

export default async function HistoricalBriefPage({
  params,
}: {
  params: { brief_id: string };
}) {
  const data = await getBriefById(params.brief_id);
  if (!data) notFound();

  return (
    <main>
      {/* Historical banner — distinguishes this from /news/overview which
          always shows the latest brief. */}
      <div className="border-b border-line-subtle bg-surface-muted">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-6 py-2 text-bodySm sm:px-8">
          <span className="text-ink-muted">
            <span className="font-mono text-caption uppercase text-ink-subtle">
              Historical
            </span>{" "}
            · viewing brief from {data.brief.brief_date}
          </span>
          <Link
            href="/news/history"
            className="text-brand-700 hover:underline"
          >
            ← Back to history
          </Link>
        </div>
      </div>

      <BriefHeader
        briefDate={data.brief.brief_date}
        modelUsed={data.brief.model_used}
        inputSignalCount={data.brief.input_signal_count}
        generatedAt={data.brief.generated_at}
        category="overview"
        themeCount={data.themes.length}
      />

      <div className="mx-auto max-w-5xl px-6 pb-20 sm:px-8">
        <div className="-mt-6 sm:-mt-8">
          <SummaryCard summary={data.brief.summary} />
        </div>

        <section className="mt-12">
          <div className="mb-5 font-mono text-caption uppercase text-ink-subtle">
            Themes ({data.themes.length})
          </div>
          <div className="space-y-5">
            {data.themes.map((theme) => (
              <ThemeCard
                key={theme.id}
                theme={theme}
                total={data.themes.length}
              />
            ))}
          </div>
        </section>

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
