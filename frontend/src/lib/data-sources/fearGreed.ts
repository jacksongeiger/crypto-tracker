// alternative.me Fear & Greed Index — free, no auth.
// Docs: https://alternative.me/crypto/fear-and-greed-index/

const BASE = "https://api.alternative.me/fng/";

export type FearGreedPoint = {
  value: number; // 0-100
  classification: string; // "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
  timestamp: number; // unix seconds
};

export type FearGreedSeries = {
  current: FearGreedPoint;
  history: FearGreedPoint[]; // most recent first; we reverse for chart
};

type FngRow = {
  value: string;
  value_classification: string;
  timestamp: string;
};
type FngResponse = { data: FngRow[] };

export async function fetchFearGreed(): Promise<FearGreedSeries> {
  const url = `${BASE}?limit=30`;
  const res = await fetch(url, { next: { revalidate: 900 } });
  if (!res.ok) throw new Error(`FearGreed ${res.status}`);
  const json = (await res.json()) as FngResponse;
  const points: FearGreedPoint[] = json.data.map((r) => ({
    value: Number(r.value),
    classification: r.value_classification,
    timestamp: Number(r.timestamp),
  }));
  return {
    current: points[0],
    history: points.slice().reverse(),
  };
}
