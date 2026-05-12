import { fetchCoinMarkets } from "@/lib/data-sources/coingecko";
import { fmtPct, fmtUSD } from "./format";
import { Sparkline } from "./sparkline";
import { ErrorCard } from "./error-card";

export async function PriceStrip() {
  let coins;
  try {
    coins = await fetchCoinMarkets();
  } catch {
    return <ErrorCard title="Live prices" />;
  }
  return (
    <section aria-label="Live prices" className="relative">
      <div className="mb-3 flex items-center justify-between">
        <div className="font-mono text-caption uppercase text-ink-subtle">
          Live prices
        </div>
        <div className="font-mono text-caption uppercase text-ink-subtle">
          CoinGecko · 60s
        </div>
      </div>
      <div
        className="scrollbar-none -mx-2 flex gap-3 overflow-x-auto px-2 pb-1"
        tabIndex={0}
        role="region"
        aria-label="Live prices, scrollable"
      >
        {coins.map((c) => {
          const change = c.price_change_percentage_24h ?? 0;
          const positive = change >= 0;
          return (
            <div
              key={c.id}
              className="flex min-w-[180px] flex-col justify-between gap-3 rounded-md border border-line-subtle bg-surface p-4 transition-colors duration-150 ease-coinbase hover:border-brand-200"
            >
              <div className="flex items-baseline justify-between">
                <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink-subtle">
                  {c.symbol}
                </span>
                <span
                  className={`font-mono text-[11px] tabular-nums ${
                    positive ? "text-success-dark" : "text-danger-dark"
                  }`}
                >
                  {fmtPct(change)}
                </span>
              </div>
              <div className="font-mono text-base font-semibold tabular-nums text-ink">
                {fmtUSD(c.current_price)}
              </div>
              <Sparkline
                values={c.sparkline.slice(-40)}
                positive={positive}
                width={160}
                height={28}
              />
            </div>
          );
        })}
      </div>
    </section>
  );
}
