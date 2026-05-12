// CoinGecko free public API. No auth. Free-tier limits: ~30 req/min.
// Docs: https://www.coingecko.com/api/documentation

const BASE = "https://api.coingecko.com/api/v3";

export type CoinMarket = {
  id: string;
  symbol: string;
  name: string;
  current_price: number;
  price_change_percentage_24h: number | null;
  market_cap: number;
  sparkline: number[];
};

export type GlobalStats = {
  btc_dominance: number;
  eth_dominance: number;
  total_market_cap_usd: number;
};

const COIN_IDS = [
  "bitcoin",
  "ethereum",
  "solana",
  "binancecoin",
  "ripple",
  "tether",
  "usd-coin",
  "cardano",
  "dogecoin",
  "tron",
  "avalanche-2",
  "chainlink",
] as const;

type GeckoMarketsRow = {
  id: string;
  symbol: string;
  name: string;
  current_price: number;
  price_change_percentage_24h_in_currency: number | null;
  market_cap: number;
  sparkline_in_7d?: { price: number[] };
};

export async function fetchCoinMarkets(): Promise<CoinMarket[]> {
  const url = `${BASE}/coins/markets?vs_currency=usd&ids=${COIN_IDS.join(
    ",",
  )}&order=market_cap_desc&per_page=${COIN_IDS.length}&sparkline=true&price_change_percentage=24h`;
  const res = await fetch(url, { next: { revalidate: 60 } });
  if (!res.ok) {
    throw new Error(`CoinGecko markets ${res.status}`);
  }
  const data = (await res.json()) as GeckoMarketsRow[];
  return data.map((c) => ({
    id: c.id,
    symbol: c.symbol.toUpperCase(),
    name: c.name,
    current_price: c.current_price,
    price_change_percentage_24h: c.price_change_percentage_24h_in_currency,
    market_cap: c.market_cap,
    sparkline: c.sparkline_in_7d?.price ?? [],
  }));
}

type GeckoGlobal = {
  data: {
    market_cap_percentage: Record<string, number>;
    total_market_cap: Record<string, number>;
  };
};

export async function fetchGlobalStats(): Promise<GlobalStats> {
  const res = await fetch(`${BASE}/global`, { next: { revalidate: 300 } });
  if (!res.ok) throw new Error(`CoinGecko global ${res.status}`);
  const json = (await res.json()) as GeckoGlobal;
  return {
    btc_dominance: json.data.market_cap_percentage.btc ?? 0,
    eth_dominance: json.data.market_cap_percentage.eth ?? 0,
    total_market_cap_usd: json.data.total_market_cap.usd ?? 0,
  };
}
