import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { fetchCoinMarkets } from "@/lib/data-sources/coingecko";
import { fetchFearGreed } from "@/lib/data-sources/fearGreed";
import { fetchTopChainsByTvl } from "@/lib/data-sources/defillama";
import { fetchTopCryptoMarkets } from "@/lib/data-sources/polymarket";

const realFetch = global.fetch;

function mockResponse(body: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    json: async () => body,
  } as Response;
}

beforeEach(() => {
  global.fetch = vi.fn();
});
afterEach(() => {
  global.fetch = realFetch;
});

describe("coingecko", () => {
  it("maps markets rows to typed CoinMarket shape", async () => {
    (global.fetch as any).mockResolvedValueOnce(
      mockResponse([
        {
          id: "bitcoin",
          symbol: "btc",
          name: "Bitcoin",
          current_price: 70000,
          price_change_percentage_24h_in_currency: 1.5,
          market_cap: 1_350_000_000_000,
          sparkline_in_7d: { price: [1, 2, 3] },
        },
      ]),
    );
    const out = await fetchCoinMarkets();
    expect(out[0].symbol).toBe("BTC");
    expect(out[0].current_price).toBe(70000);
    expect(out[0].sparkline).toEqual([1, 2, 3]);
  });

  it("throws on 429", async () => {
    (global.fetch as any).mockResolvedValueOnce(mockResponse(null, false, 429));
    await expect(fetchCoinMarkets()).rejects.toThrow(/429/);
  });
});

describe("fearGreed", () => {
  it("returns current + reversed history", async () => {
    (global.fetch as any).mockResolvedValueOnce(
      mockResponse({
        data: [
          { value: "70", value_classification: "Greed", timestamp: "3" },
          { value: "50", value_classification: "Neutral", timestamp: "2" },
          { value: "30", value_classification: "Fear", timestamp: "1" },
        ],
      }),
    );
    const out = await fetchFearGreed();
    expect(out.current.value).toBe(70);
    expect(out.history[0].value).toBe(30);
    expect(out.history[2].value).toBe(70);
  });

  it("throws on 500", async () => {
    (global.fetch as any).mockResolvedValueOnce(mockResponse(null, false, 500));
    await expect(fetchFearGreed()).rejects.toThrow();
  });
});

describe("defillama chains", () => {
  it("returns top N sorted desc by tvl", async () => {
    (global.fetch as any).mockResolvedValueOnce(
      mockResponse([
        { name: "B", tvl: 100, change_1d: 1 },
        { name: "A", tvl: 200, change_1d: -2 },
        { name: "C", tvl: 50, change_1d: null },
      ]),
    );
    const out = await fetchTopChainsByTvl(2);
    expect(out.map((c) => c.name)).toEqual(["A", "B"]);
    expect(out[0].tvl_usd).toBe(200);
  });
});

describe("polymarket", () => {
  it("filters to crypto-keyword markets and parses YES probability", async () => {
    (global.fetch as any).mockResolvedValueOnce(
      mockResponse([
        {
          id: "1",
          question: "Will Bitcoin hit $100k by Dec 31?",
          slug: "btc-100k",
          volume24hr: 50_000,
          endDate: "2030-12-31T00:00:00Z",
          outcomePrices: '["0.62","0.38"]',
        },
        {
          id: "2",
          question: "Will the Lakers win the championship?",
          slug: "lakers",
          volume24hr: 9_999_999,
          outcomePrices: '["0.5","0.5"]',
        },
      ]),
    );
    const out = await fetchTopCryptoMarkets(5);
    expect(out.length).toBe(1);
    expect(out[0].yes_probability).toBeCloseTo(0.62);
  });
});
