// Polymarket gamma-api public endpoint. Free, no auth required.
// Docs: https://docs.polymarket.com/

const BASE = "https://gamma-api.polymarket.com";

export type PolyMarket = {
  id: string;
  question: string;
  slug: string;
  volume_24h_usd: number;
  end_date: string | null;
  yes_probability: number; // 0-1
};

type GammaMarket = {
  id?: string;
  question?: string;
  slug?: string;
  volume24hr?: number;
  endDate?: string;
  closed?: boolean;
  active?: boolean;
  outcomePrices?: string;
};

const CRYPTO_KEYWORDS = [
  "bitcoin",
  "btc",
  "ethereum",
  "eth",
  "solana",
  "sol",
  "crypto",
  "sec",
  "etf",
  "stablecoin",
  "ripple",
  "xrp",
];

function looksCrypto(question: string): boolean {
  const q = question.toLowerCase();
  return CRYPTO_KEYWORDS.some((kw) => q.includes(kw));
}

function parseYes(prices?: string): number {
  if (!prices) return 0;
  try {
    const arr = JSON.parse(prices) as string[];
    const first = Number(arr[0]);
    return Number.isFinite(first) ? first : 0;
  } catch {
    return 0;
  }
}

export async function fetchTopCryptoMarkets(limit = 5): Promise<PolyMarket[]> {
  // Fetch a generous batch sorted by 24h volume so we have enough to filter
  const url = `${BASE}/markets?active=true&closed=false&order=volume24hr&ascending=false&limit=80`;
  const res = await fetch(url, { next: { revalidate: 300 } });
  if (!res.ok) throw new Error(`Polymarket markets ${res.status}`);
  const rows = (await res.json()) as GammaMarket[];
  const filtered = rows
    .filter((m) => m.question && looksCrypto(m.question))
    .filter((m) => (m.volume24hr ?? 0) > 100)
    .slice(0, limit);
  return filtered.map((m) => ({
    id: m.id ?? "",
    question: m.question ?? "",
    slug: m.slug ?? "",
    volume_24h_usd: m.volume24hr ?? 0,
    end_date: m.endDate ?? null,
    yes_probability: parseYes(m.outcomePrices),
  }));
}
