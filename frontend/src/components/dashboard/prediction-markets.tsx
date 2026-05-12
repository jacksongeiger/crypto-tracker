import { fetchTopCryptoMarkets } from "@/lib/data-sources/polymarket";
import { fmtRelativeTime, fmtUSD } from "./format";
import { ErrorCard } from "./error-card";

function ProbBar({ p }: { p: number }) {
  const pct = Math.round(p * 100);
  const tone =
    pct >= 60
      ? "bg-success"
      : pct >= 40
        ? "bg-brand-500"
        : "bg-danger";
  return (
    <div className="flex items-center gap-2">
      <div className="relative h-1.5 w-24 overflow-hidden rounded-full bg-line-subtle">
        <span
          className={`absolute inset-y-0 left-0 ${tone}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="font-mono tabular-nums text-bodySm text-ink">
        {pct}%
      </span>
    </div>
  );
}

export async function PredictionMarketsCard() {
  let markets;
  try {
    markets = await fetchTopCryptoMarkets(5);
  } catch {
    return <ErrorCard title="Prediction markets" />;
  }
  if (!markets.length) {
    return <ErrorCard title="Prediction markets" />;
  }
  return (
    <section className="rounded-md border border-line bg-surface p-6 sm:p-7">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-mono text-caption uppercase text-ink-subtle">
            Prediction markets · crypto
          </div>
          <div className="mt-1 text-h3 font-semibold text-ink">
            Top by 24h volume
          </div>
        </div>
        <span className="font-mono text-caption uppercase text-ink-subtle">
          polymarket
        </span>
      </div>
      <ul className="mt-5 divide-y divide-line-subtle">
        {markets.map((m) => (
          <li key={m.id} className="py-4 first:pt-0 last:pb-0">
            <a
              href={
                m.slug ? `https://polymarket.com/market/${m.slug}` : "#"
              }
              target="_blank"
              rel="noreferrer"
              className="group flex flex-col gap-3"
            >
              <div className="text-bodySm text-ink group-hover:text-brand-700">
                {m.question}
              </div>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <ProbBar p={m.yes_probability} />
                <div className="flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-subtle">
                  <span className="tabular-nums">
                    {fmtUSD(m.volume_24h_usd, { compact: true })} 24h
                  </span>
                  <span>·</span>
                  <span>{fmtRelativeTime(m.end_date)}</span>
                </div>
              </div>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
