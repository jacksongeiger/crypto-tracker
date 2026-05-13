import { describe, expect, it } from "vitest";
import { buildCategorySummary } from "@/lib/category-summary";
import type { BriefTheme } from "@/types/brief";

function makeTheme(title: string, conviction = 4): BriefTheme {
  return {
    id: "t",
    display_order: 0,
    title,
    body: "",
    conviction_score: conviction,
    primary_signal_id: "p",
    primary_source_name: "Src",
    primary_signal_title: "",
    primary_signal_url: null,
    corroborating_count: 0,
    categories: ["markets"],
    corroborating_sources: [],
  };
}

describe("buildCategorySummary", () => {
  it("returns a real editorial summary when themes are present", () => {
    const s = buildCategorySummary("markets", [
      makeTheme("JPMorgan launches tokenized fund"),
      makeTheme("Schwab opens spot crypto trading to retail"),
    ]);
    expect(s).toContain("JPMorgan launches tokenized fund");
    expect(s).toContain("Schwab opens spot crypto trading to retail");
    expect(s).not.toMatch(/Highest-conviction first/);
    expect(s).not.toMatch(/^\d+ themes? in Markets today\.$/);
  });

  it("includes a plus-N tail when there are more than 3 themes", () => {
    const s = buildCategorySummary("markets", [
      makeTheme("Theme one"),
      makeTheme("Theme two"),
      makeTheme("Theme three"),
      makeTheme("Theme four"),
      makeTheme("Theme five"),
    ]);
    expect(s).toMatch(/Plus 2 more themes tagged Markets/);
  });

  it("falls back to a clear empty-state message when there are no themes", () => {
    const s = buildCategorySummary("policy", []);
    expect(s).toMatch(/No Policy themes in today's brief/);
    expect(s).toMatch(/past week/i);
  });

  it("never returns the old count-meta placeholder", () => {
    const s = buildCategorySummary("markets", [makeTheme("x")]);
    expect(s).not.toMatch(/Highest-conviction first/i);
  });
});
