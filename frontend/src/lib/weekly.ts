import type { BriefTheme, Category } from "@/types/brief";

// Theme rows pulled across the past 7 days, before similarity grouping.
export type WeeklyThemeRow = BriefTheme & {
  brief_id: string;
  brief_date: string; // yyyy-mm-dd
  generated_at: string;
  source_signal_ids: string[];
};

// The aggregated, ranked output the page renders.
export type WeeklyHighlight = BriefTheme & {
  brief_id: string; // the brief this representative came from
  brief_date: string;
  appearances: number; // distinct briefs the theme appeared in (>=1)
  appeared_in: { brief_id: string; brief_date: string }[];
};

const STOPWORDS = new Set([
  "a", "an", "and", "the", "to", "of", "in", "on", "for", "by", "with",
  "is", "are", "was", "were", "as", "at", "from", "into", "after",
  "amid", "before", "over", "this", "that", "these", "those", "or",
  "vs", "vs.", "but", "be", "it", "its", "than",
]);

function tokenize(s: string): Set<string> {
  return new Set(
    s
      .toLowerCase()
      .replace(/[^a-z0-9\s]+/g, " ")
      .split(/\s+/)
      .filter((w) => w.length > 2 && !STOPWORDS.has(w)),
  );
}

function jaccard(a: Set<string>, b: Set<string>): number {
  if (a.size === 0 || b.size === 0) return 0;
  let intersection = 0;
  a.forEach((t) => {
    if (b.has(t)) intersection++;
  });
  const union = a.size + b.size - intersection;
  return intersection / union;
}

function sharedIds(a: string[], b: string[]): number {
  const set = new Set(a);
  let n = 0;
  for (let i = 0; i < b.length; i++) if (set.has(b[i])) n++;
  return n;
}

// Two themes are "the same recurring theme" when EITHER their titles
// share enough tokens (Jaccard ≥ 0.40 on stop-word-stripped lowercase
// tokens) OR they share more than half of their source signal ids.
// The 0.40 threshold was picked empirically against the existing 7-day
// corpus — high enough that "JPMorgan tokenized fund" doesn't merge
// with "JPMorgan stablecoin custody", low enough that the same story
// re-bucketed under slightly different wording day-over-day does merge.
const JACCARD_THRESHOLD = 0.4;

function isSameRecurringTheme(
  a: { title: string; source_signal_ids: string[] },
  b: { title: string; source_signal_ids: string[] },
): boolean {
  const titleSim = jaccard(tokenize(a.title), tokenize(b.title));
  if (titleSim >= JACCARD_THRESHOLD) return true;
  const shared = sharedIds(a.source_signal_ids, b.source_signal_ids);
  const minLen = Math.min(a.source_signal_ids.length, b.source_signal_ids.length);
  return minLen > 0 && shared / minLen > 0.5;
}

type Cluster = {
  representative: WeeklyThemeRow; // highest-conviction member
  members: WeeklyThemeRow[];
  uniqueBriefs: Map<string, string>; // brief_id → brief_date
};

function score(c: Cluster): number {
  const rep = c.representative;
  const conviction = rep.conviction_score ?? 0;
  const corroborators = rep.corroborating_count;
  const appearances = c.uniqueBriefs.size;
  // Conviction is the dominant signal (×10). Cross-day persistence
  // ranks above source breadth because a theme that recurs is a
  // stronger weekly story than a one-day blast with many sources.
  return conviction * 10 + appearances * 3 + corroborators;
}

export function aggregateWeekly(
  rows: WeeklyThemeRow[],
  { limit = 10, perCategoryMax = 3 }: { limit?: number; perCategoryMax?: number } = {},
): WeeklyHighlight[] {
  const clusters: Cluster[] = [];

  // Order rows newest-first so the representative we keep for a cluster
  // is the most recent occurrence of that story (more useful link).
  const sorted = [...rows].sort((a, b) =>
    a.generated_at < b.generated_at ? 1 : -1,
  );

  for (const row of sorted) {
    const existing = clusters.find((c) =>
      c.members.some((m) => isSameRecurringTheme(m, row)),
    );
    if (existing) {
      existing.members.push(row);
      existing.uniqueBriefs.set(row.brief_id, row.brief_date);
      // Upgrade representative if this row has higher conviction
      const repC = existing.representative.conviction_score ?? 0;
      const rowC = row.conviction_score ?? 0;
      if (rowC > repC) existing.representative = row;
    } else {
      clusters.push({
        representative: row,
        members: [row],
        uniqueBriefs: new Map([[row.brief_id, row.brief_date]]),
      });
    }
  }

  clusters.sort((a, b) => score(b) - score(a));

  // Apply per-category diversity cap. A theme can have multiple
  // categories — we count it against the cap of its FIRST category to
  // keep the rule simple, since the first category is the one the
  // synthesis treated as primary.
  const perCategoryCount = new Map<Category, number>();
  const out: WeeklyHighlight[] = [];
  for (const c of clusters) {
    const primaryCat = c.representative.categories[0] as Category | undefined;
    if (primaryCat) {
      const used = perCategoryCount.get(primaryCat) ?? 0;
      if (used >= perCategoryMax) continue;
      perCategoryCount.set(primaryCat, used + 1);
    }
    out.push({
      ...c.representative,
      appearances: c.uniqueBriefs.size,
      appeared_in: Array.from(c.uniqueBriefs.entries())
        .map(([brief_id, brief_date]) => ({ brief_id, brief_date }))
        .sort((a, b) => (a.brief_date < b.brief_date ? 1 : -1)),
    });
    if (out.length >= limit) break;
  }
  return out;
}

export function buildWeeklySummary(
  highlights: WeeklyHighlight[],
  briefCount: number,
): string {
  if (highlights.length === 0) {
    return `Weekly roundup needs at least one brief with themes — found ${briefCount}. Check back after tomorrow's synthesis.`;
  }
  const catCounts = new Map<Category, number>();
  for (const h of highlights) {
    for (const c of h.categories) {
      catCounts.set(c, (catCounts.get(c) ?? 0) + 1);
    }
  }
  const topCats = Array.from(catCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .map(([c]) => c);
  const highConvictionCount = highlights.filter(
    (h) => (h.conviction_score ?? 0) >= 5,
  ).length;
  const top = highlights[0];
  const catPhrase =
    topCats.length === 2
      ? `${capitalize(topCats[0])} and ${capitalize(topCats[1])}`
      : topCats.length === 1
        ? capitalize(topCats[0])
        : "a mix of categories";
  const convictionPhrase =
    highConvictionCount > 0
      ? ` ${highConvictionCount} theme${highConvictionCount === 1 ? "" : "s"} hit conviction 5.`
      : "";
  return `This week's crypto coverage was dominated by ${catPhrase} across ${briefCount} daily brief${briefCount === 1 ? "" : "s"}.${convictionPhrase} Top story: ${top.title}.`;
}

function capitalize(s: string): string {
  return s.length === 0 ? s : s[0].toUpperCase() + s.slice(1);
}
