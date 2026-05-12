import { fetchTopChainsByTvl, fetchDexVolume, fetchStablecoinSupply } from "@/lib/data-sources/defillama";
import { fetchGlobalStats } from "@/lib/data-sources/coingecko";
import { fmtPct, fmtUSD } from "./format";
import { ErrorCard } from "./error-card";

async function safe<T>(p: Promise<T>): Promise<T | null> {
  try {
    return await p;
  } catch {
    return null;
  }
}

function StatTile({
  label,
  value,
  change,
  source,
}: {
  label: string;
  value: string;
  change?: number | null;
  source?: string;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-md border border-line bg-surface p-5 transition-colors duration-150 ease-coinbase hover:border-brand-200">
      <div className="flex items-center justify-between">
        <span className="font-mono text-caption uppercase text-ink-subtle">
          {label}
        </span>
        {source && (
          <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-subtle">
            {source}
          </span>
        )}
      </div>
      <div className="font-mono text-xl font-semibold tabular-nums text-ink">
        {value}
      </div>
      {typeof change === "number" && (
        <div
          className={`font-mono text-[11px] tabular-nums ${
            change >= 0 ? "text-success" : "text-danger"
          }`}
        >
          {fmtPct(change)} 24h
        </div>
      )}
    </div>
  );
}

export async function OnChainStats() {
  const [chains, dex, stables, global] = await Promise.all([
    safe(fetchTopChainsByTvl(5)),
    safe(fetchDexVolume()),
    safe(fetchStablecoinSupply()),
    safe(fetchGlobalStats()),
  ]);

  if (!chains && !dex && !stables && !global) {
    return <ErrorCard title="On-chain" />;
  }

  return (
    <section className="rounded-md border border-line bg-surface p-6 sm:p-7">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-mono text-caption uppercase text-ink-subtle">
            On-chain
          </div>
          <div className="mt-1 text-h3 font-semibold text-ink">
            Liquidity, flows, supply
          </div>
        </div>
        <span className="font-mono text-caption uppercase text-ink-subtle">
          defillama · coingecko
        </span>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-2">
        {dex ? (
          <StatTile
            label="DEX volume 24h"
            value={fmtUSD(dex.total_24h_usd, { compact: true })}
            change={dex.change_1d}
            source="defillama"
          />
        ) : null}
        {stables ? (
          <StatTile
            label="Stablecoin supply"
            value={fmtUSD(stables.total_supply_usd, { compact: true })}
            source="defillama"
          />
        ) : null}
        {global ? (
          <>
            <StatTile
              label="BTC dominance"
              value={`${global.btc_dominance.toFixed(2)}%`}
              source="coingecko"
            />
            <StatTile
              label="Total market cap"
              value={fmtUSD(global.total_market_cap_usd, { compact: true })}
              source="coingecko"
            />
          </>
        ) : null}
      </div>

      {chains && chains.length > 0 && (
        <div className="mt-6">
          <div className="mb-3 font-mono text-caption uppercase text-ink-subtle">
            Top chains by TVL
          </div>
          <ul className="divide-y divide-line-subtle">
            {chains.map((c, i) => (
              <li
                key={c.name}
                className="flex items-center justify-between py-2.5 text-bodySm"
              >
                <span className="flex items-center gap-3">
                  <span className="font-mono w-5 tabular-nums text-ink-subtle">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="font-medium text-ink">{c.name}</span>
                </span>
                <span className="flex items-center gap-3">
                  <span className="font-mono tabular-nums text-ink">
                    {fmtUSD(c.tvl_usd, { compact: true })}
                  </span>
                  {c.change_1d !== null && (
                    <span
                      className={`font-mono w-16 text-right tabular-nums text-[11px] ${
                        c.change_1d >= 0 ? "text-success" : "text-danger"
                      }`}
                    >
                      {fmtPct(c.change_1d)}
                    </span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
