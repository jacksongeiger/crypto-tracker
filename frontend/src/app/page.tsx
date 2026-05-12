import { getLatestBrief } from "@/lib/queries";
import type { BriefTheme } from "@/types/brief";

export const dynamic = "force-dynamic";

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

function formatGeneratedAt(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
    timeZoneName: "short",
  });
}

function convictionClasses(score: number | null) {
  if (score === null) return "text-zinc-400";
  if (score >= 5) return "text-[var(--brand)]";
  if (score >= 4) return "text-zinc-900";
  if (score >= 3) return "text-zinc-700";
  return "text-zinc-500";
}

function ConvictionPip({ score }: { score: number | null }) {
  if (score === null) {
    return <span className="text-zinc-400">unscored</span>;
  }
  const total = 5;
  return (
    <span
      className={`inline-flex items-center gap-1.5 ${convictionClasses(score)}`}
      aria-label={`conviction ${score} of ${total}`}
    >
      <span className="flex items-center gap-[3px]">
        {Array.from({ length: total }).map((_, i) => (
          <span
            key={i}
            className={`block h-[5px] w-[5px] rounded-full ${
              i < score ? "bg-current" : "bg-zinc-200"
            }`}
          />
        ))}
      </span>
      <span className="font-mono tabular-nums text-xs">
        {score}/{total}
      </span>
    </span>
  );
}

function ThemeCard({ theme, total }: { theme: BriefTheme; total: number }) {
  const index = theme.display_order + 1;
  const corroborators = theme.corroborating_count;
  return (
    <article className="border-t border-zinc-200 py-12 first:border-t-0 sm:py-14">
      <div className="font-mono text-xs tabular-nums tracking-[0.18em] text-zinc-400">
        {String(index).padStart(2, "0")} / {String(total).padStart(2, "0")}
      </div>
      <h2 className="mt-4 text-[1.625rem] leading-[1.2] font-semibold tracking-tight text-zinc-950 sm:text-[1.75rem]">
        {theme.title}
      </h2>
      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm">
        <ConvictionPip score={theme.conviction_score} />
        <span className="text-zinc-300" aria-hidden>
          ·
        </span>
        <span className="text-zinc-600">
          <span className="text-zinc-500">primary</span>{" "}
          <span className="font-medium text-zinc-900">
            {theme.primary_source_name}
          </span>
        </span>
        <span className="text-zinc-300" aria-hidden>
          ·
        </span>
        <span className="text-zinc-600 tabular-nums">
          {corroborators === 0
            ? "single-sourced"
            : `+${corroborators} corroborating`}
        </span>
      </div>
      <p className="mt-6 text-[1.0625rem] leading-[1.7] text-zinc-800">
        {theme.body}
      </p>
      <div className="mt-6 flex items-start gap-3 border-l-2 border-zinc-200 pl-4 text-sm leading-snug">
        <span className="mt-0.5 shrink-0 text-zinc-400">primary article</span>
        {theme.primary_signal_url ? (
          <a
            href={theme.primary_signal_url}
            target="_blank"
            rel="noreferrer"
            className="text-zinc-900 underline decoration-zinc-300 underline-offset-4 transition-colors hover:decoration-[var(--brand)] hover:text-[var(--brand)]"
          >
            {theme.primary_signal_title}
            <span className="ml-1 text-zinc-400">↗</span>
          </a>
        ) : (
          <span className="text-zinc-900">{theme.primary_signal_title}</span>
        )}
      </div>
    </article>
  );
}

function EmptyState() {
  return (
    <div className="mt-24 border border-zinc-200 px-8 py-16 text-center">
      <p className="font-mono text-xs uppercase tracking-[0.18em] text-zinc-500">
        no briefs yet
      </p>
      <p className="mt-3 text-base text-zinc-700">
        Generate one with the synthesis skill:
      </p>
      <pre className="mt-4 inline-block bg-zinc-50 px-4 py-2 text-sm text-zinc-800 border border-zinc-200">
        skills/synthesize-brief/scripts/run.sh
      </pre>
    </div>
  );
}

export default async function Page() {
  const data = await getLatestBrief();

  return (
    <main className="mx-auto max-w-2xl px-6 pb-24 pt-16 sm:px-8 sm:pt-24">
      <header>
        <div className="font-mono text-xs uppercase tracking-[0.22em] text-zinc-500">
          Daily Brief
        </div>
        {data ? (
          <>
            <h1 className="mt-3 text-[2.25rem] leading-[1.1] font-semibold tracking-tight text-zinc-950 sm:text-[2.75rem]">
              {formatDateLong(data.brief.brief_date)}
            </h1>
            <p className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-zinc-500">
              <span className="font-mono text-zinc-600">
                {data.brief.model_used}
              </span>
              <span className="text-zinc-300" aria-hidden>
                ·
              </span>
              <span className="tabular-nums">
                {data.brief.input_signal_count} input signals
              </span>
              <span className="text-zinc-300" aria-hidden>
                ·
              </span>
              <span className="tabular-nums">
                generated {formatGeneratedAt(data.brief.generated_at)}
              </span>
            </p>
          </>
        ) : (
          <h1 className="mt-3 text-[2.25rem] leading-[1.1] font-semibold tracking-tight text-zinc-950 sm:text-[2.75rem]">
            No brief yet
          </h1>
        )}
      </header>

      {data ? (
        <>
          <section className="mt-14 border-t border-zinc-200 pt-10">
            <div className="font-mono text-xs uppercase tracking-[0.18em] text-zinc-500">
              Summary
            </div>
            <p className="mt-4 text-[1.1875rem] leading-[1.65] text-zinc-900">
              {data.brief.summary}
            </p>
          </section>

          <section className="mt-12">
            <div className="font-mono text-xs uppercase tracking-[0.18em] text-zinc-500">
              Themes
            </div>
            <div className="mt-2">
              {data.themes.map((theme) => (
                <ThemeCard
                  key={theme.id}
                  theme={theme}
                  total={data.themes.length}
                />
              ))}
            </div>
          </section>

          <footer className="mt-20 border-t border-zinc-200 pt-6 font-mono text-xs text-zinc-400">
            brief {data.brief.id}
          </footer>
        </>
      ) : (
        <EmptyState />
      )}
    </main>
  );
}
