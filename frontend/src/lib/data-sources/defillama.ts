// DefiLlama public API — free, no auth.
// Docs: https://defillama.com/docs/api

const BASE = "https://api.llama.fi";
const COINS_BASE = "https://coins.llama.fi";

export type ChainTvl = {
  name: string;
  tvl_usd: number;
  change_1d: number | null;
};

export type DexVolumeSnapshot = {
  total_24h_usd: number;
  change_1d: number | null;
};

type LlamaChainRow = {
  name: string;
  tvl: number;
  tokenSymbol?: string | null;
  change_1d?: number | null;
};

export async function fetchTopChainsByTvl(limit = 5): Promise<ChainTvl[]> {
  const res = await fetch(`${BASE}/v2/chains`, {
    next: { revalidate: 300 },
  });
  if (!res.ok) throw new Error(`DefiLlama chains ${res.status}`);
  const rows = (await res.json()) as LlamaChainRow[];
  rows.sort((a, b) => (b.tvl ?? 0) - (a.tvl ?? 0));
  return rows.slice(0, limit).map((r) => ({
    name: r.name,
    tvl_usd: r.tvl ?? 0,
    change_1d: r.change_1d ?? null,
  }));
}

type DexOverview = {
  total24h?: number;
  change_1d?: number;
};

export async function fetchDexVolume(): Promise<DexVolumeSnapshot> {
  const res = await fetch(
    `${BASE}/overview/dexs?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true`,
    { next: { revalidate: 300 } },
  );
  if (!res.ok) throw new Error(`DefiLlama dex overview ${res.status}`);
  const json = (await res.json()) as DexOverview;
  return {
    total_24h_usd: json.total24h ?? 0,
    change_1d: json.change_1d ?? null,
  };
}

export type StablecoinTotal = {
  total_supply_usd: number;
};

type StableRow = {
  totalCirculatingUSD?: { peggedUSD?: number };
};

export async function fetchStablecoinSupply(): Promise<StablecoinTotal> {
  const res = await fetch(
    "https://stablecoins.llama.fi/stablecoincharts/all",
    { next: { revalidate: 900 } },
  );
  if (!res.ok) throw new Error(`DefiLlama stablecoins ${res.status}`);
  const rows = (await res.json()) as StableRow[];
  const last = rows[rows.length - 1];
  return {
    total_supply_usd: last?.totalCirculatingUSD?.peggedUSD ?? 0,
  };
}
// Avoid lint warning on unused COINS_BASE reserved for future endpoints
void COINS_BASE;
