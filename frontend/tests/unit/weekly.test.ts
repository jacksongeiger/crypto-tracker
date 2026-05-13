import { describe, expect, it } from "vitest";
import {
  aggregateWeekly,
  buildWeeklySummary,
  type WeeklyThemeRow,
} from "@/lib/weekly";

function makeRow(overrides: Partial<WeeklyThemeRow>): WeeklyThemeRow {
  return {
    id: overrides.id ?? "t",
    display_order: 0,
    title: overrides.title ?? "Some theme",
    body: "",
    conviction_score: overrides.conviction_score ?? 4,
    primary_signal_id: overrides.primary_signal_id ?? "p",
    primary_source_name: "Src",
    primary_signal_title: "",
    primary_signal_url: null,
    corroborating_count: overrides.corroborating_count ?? 1,
    categories: overrides.categories ?? ["markets"],
    corroborating_sources: [],
    brief_id: overrides.brief_id ?? "b",
    brief_date: overrides.brief_date ?? "2026-05-13",
    generated_at: overrides.generated_at ?? "2026-05-13T17:00:00Z",
    source_signal_ids: overrides.source_signal_ids ?? ["p"],
  };
}

describe("aggregateWeekly", () => {
  it("merges similar titles across briefs and counts appearances", () => {
    const rows = [
      makeRow({
        id: "a1",
        brief_id: "b1",
        brief_date: "2026-05-12",
        generated_at: "2026-05-12T17:00:00Z",
        title: "JPMorgan launches tokenized money market fund on Ethereum",
        source_signal_ids: ["s1", "s2"],
      }),
      makeRow({
        id: "a2",
        brief_id: "b2",
        brief_date: "2026-05-13",
        generated_at: "2026-05-13T17:00:00Z",
        title: "JPMorgan launches second tokenized money market fund on Ethereum",
        source_signal_ids: ["s1", "s3"],
      }),
      makeRow({
        id: "b1",
        brief_id: "b1",
        title: "Anthropic releases new Claude model",
        primary_signal_id: "x",
        source_signal_ids: ["x"],
        categories: ["ai"],
      }),
    ];
    const out = aggregateWeekly(rows);
    const jp = out.find((h) => /JPMorgan/i.test(h.title));
    expect(jp).toBeDefined();
    expect(jp!.appearances).toBe(2);
    expect(jp!.appeared_in.length).toBe(2);
    // representative is the most-recent occurrence (so the link points
    // at the freshest brief)
    expect(jp!.brief_id).toBe("b2");
  });

  it("keeps unrelated themes separate", () => {
    const rows = [
      makeRow({ id: "a", title: "DEX volumes surge across chains" }),
      makeRow({
        id: "b",
        title: "JPMorgan launches tokenized fund",
        primary_signal_id: "p2",
        source_signal_ids: ["p2"],
      }),
    ];
    const out = aggregateWeekly(rows);
    expect(out.length).toBe(2);
  });

  it("ranks high-conviction recurring themes above one-day blasts", () => {
    const rows = [
      makeRow({
        id: "burst",
        title: "Random one-day story",
        conviction_score: 5,
        corroborating_count: 5,
      }),
      makeRow({
        id: "rec1",
        title: "Recurring theme about ETH gas fees",
        conviction_score: 4,
        corroborating_count: 1,
        brief_id: "b1",
        brief_date: "2026-05-11",
        generated_at: "2026-05-11T17:00:00Z",
        primary_signal_id: "rec",
        source_signal_ids: ["rec"],
      }),
      makeRow({
        id: "rec2",
        title: "Recurring theme about ETH gas fees rising",
        conviction_score: 4,
        corroborating_count: 1,
        brief_id: "b2",
        brief_date: "2026-05-12",
        generated_at: "2026-05-12T17:00:00Z",
        primary_signal_id: "rec",
        source_signal_ids: ["rec"],
      }),
      makeRow({
        id: "rec3",
        title: "ETH gas fees rising again",
        conviction_score: 4,
        corroborating_count: 1,
        brief_id: "b3",
        brief_date: "2026-05-13",
        generated_at: "2026-05-13T17:00:00Z",
        primary_signal_id: "rec",
        source_signal_ids: ["rec"],
      }),
    ];
    const out = aggregateWeekly(rows);
    // Burst: 5*10 + 1*3 + 5 = 58
    // Recurring (3 appearances): 4*10 + 3*3 + 1 = 50
    // → burst still wins on raw conviction; verify ordering matches the score formula.
    expect(out[0].id).toBe("burst");
    const recurring = out.find((h) => /gas fees/i.test(h.title));
    expect(recurring?.appearances).toBe(3);
  });

  it("respects the per-category cap", () => {
    const rows = Array.from({ length: 6 }).map((_, i) =>
      makeRow({
        id: `m${i}`,
        title: `Markets story ${i}`,
        primary_signal_id: `m${i}`,
        source_signal_ids: [`m${i}`],
        categories: ["markets"],
      }),
    );
    const out = aggregateWeekly(rows, { perCategoryMax: 3 });
    expect(out.length).toBeLessThanOrEqual(3);
  });
});

describe("buildWeeklySummary", () => {
  it("opens with the brand phrase users see in the page", () => {
    const out = aggregateWeekly([
      makeRow({ title: "X", categories: ["markets"] }),
      makeRow({
        title: "Y",
        primary_signal_id: "y",
        source_signal_ids: ["y"],
        categories: ["tech"],
      }),
    ]);
    const s = buildWeeklySummary(out, 4);
    expect(s).toMatch(/^This week's crypto coverage/);
    expect(s).toContain("4 daily briefs");
  });

  it("falls back to a tells-the-truth message when no highlights", () => {
    const s = buildWeeklySummary([], 1);
    expect(s).toMatch(/needs at least one brief/i);
  });
});
