import { Suspense } from "react";
import { PriceStrip } from "@/components/dashboard/price-strip";
import { FearGreedCard } from "@/components/dashboard/fear-greed";
import { OnChainStats } from "@/components/dashboard/on-chain";
import { PredictionMarketsCard } from "@/components/dashboard/prediction-markets";

export const dynamic = "force-dynamic";

function CardSkeleton({ title }: { title: string }) {
  return (
    <div className="animate-pulse rounded-md border border-line-subtle bg-surface-raised p-6">
      <div className="font-mono text-caption uppercase text-ink-subtle">
        {title}
      </div>
      <div className="mt-4 h-6 w-32 rounded bg-line-subtle" />
      <div className="mt-3 h-4 w-48 rounded bg-line-subtle" />
      <div className="mt-3 h-4 w-40 rounded bg-line-subtle" />
    </div>
  );
}

function StripSkeleton() {
  return (
    <div className="flex gap-3 overflow-x-auto">
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={i}
          className="min-w-[180px] animate-pulse rounded-md border border-line-subtle bg-surface-raised p-4"
        >
          <div className="h-3 w-10 rounded bg-line-subtle" />
          <div className="mt-3 h-5 w-20 rounded bg-line-subtle" />
          <div className="mt-3 h-6 w-full rounded bg-line-subtle" />
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <main>
      <header className="relative isolate overflow-hidden border-b border-line-subtle bg-gradient-to-b from-brand-50/60 to-surface">
        <span
          aria-hidden
          className="absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r from-brand-500 via-brand-600 to-brand-500"
        />
        <div className="mx-auto max-w-6xl px-6 py-12 sm:px-8 sm:py-14">
          <div className="font-mono text-caption uppercase text-brand-700">
            Dashboard
          </div>
          <h1 className="mt-3 text-display font-semibold tracking-tight text-ink">
            Live market signals
          </h1>
          <p className="mt-3 max-w-2xl text-bodyLg text-ink-muted">
            Prices, sentiment, on-chain liquidity, and prediction markets —
            sourced from public APIs (CoinGecko, alternative.me, DefiLlama,
            Polymarket). Cached for 1–5 minutes.
          </p>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-6 pb-20 pt-8 sm:px-8 sm:pt-10">
        <Suspense fallback={<StripSkeleton />}>
          <PriceStrip />
        </Suspense>

        <div className="mt-10 grid gap-5 lg:grid-cols-2">
          <Suspense fallback={<CardSkeleton title="Fear & Greed" />}>
            <FearGreedCard />
          </Suspense>
          <Suspense fallback={<CardSkeleton title="On-chain" />}>
            <OnChainStats />
          </Suspense>
        </div>

        <div className="mt-5">
          <Suspense fallback={<CardSkeleton title="Prediction markets" />}>
            <PredictionMarketsCard />
          </Suspense>
        </div>

        <footer className="mt-12 border-t border-line-subtle pt-5 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-subtle">
          Sources: CoinGecko · alternative.me · DefiLlama · Polymarket. Numbers
          refresh on cache expiry; reload the page to fetch latest.
        </footer>
      </div>
    </main>
  );
}
