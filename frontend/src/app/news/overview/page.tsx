import { getLatestBrief } from "@/lib/queries";
import { BriefHeader } from "@/components/brief/brief-header";
import { BriefMeta } from "@/components/brief/brief-meta";
import { SummaryCard } from "@/components/brief/summary-card";
import { ThemeCard } from "@/components/brief/theme-card";

export const dynamic = "force-dynamic";

export default async function OverviewPage() {
  const data = await getLatestBrief();

  if (!data) {
    return (
      <main>
        <div className="mx-auto max-w-3xl px-6 py-24 sm:px-8">
          <p className="font-mono text-caption uppercase text-ink-subtle">
            Daily Brief
          </p>
          <h1 className="mt-3 text-display font-semibold text-ink">
            No brief yet
          </h1>
          <p className="mt-4 text-bodyLg text-ink-muted">
            Generate one with{" "}
            <code className="rounded-sm bg-surface-muted px-1.5 py-0.5 font-mono text-[13px] text-ink">
              skills/synthesize-brief/scripts/run.sh
            </code>
            .
          </p>
        </div>
      </main>
    );
  }

  return (
    <main>
      <BriefHeader
        briefDate={data.brief.brief_date}
        modelUsed={data.brief.model_used}
        inputSignalCount={data.brief.input_signal_count}
        generatedAt={data.brief.generated_at}
        category="overview"
        themeCount={data.themes.length}
      />

      <div className="mx-auto max-w-3xl px-6 pb-20 sm:px-8">
        <div className="-mt-6 sm:-mt-8">
          <SummaryCard summary={data.brief.summary} />
        </div>

        <section className="mt-12">
          <div className="mb-5 flex items-center justify-between">
            <div className="font-mono text-caption uppercase text-ink-subtle">
              Themes ({data.themes.length})
            </div>
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
