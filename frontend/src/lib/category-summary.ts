import type { BriefTheme, Category } from "@/types/brief";
import { CATEGORY_LABELS } from "@/types/brief";

const MAX_LEAD_THEMES = 3;

// Strip a trailing period if one exists, so we can re-attach uniformly.
function trimTrailingDot(s: string): string {
  return s.replace(/[.!?]+\s*$/, "").trim();
}

// Compose a deterministic editorial TL;DR for a category page from its
// filtered themes. The themes are passed in display order (highest
// conviction first by convention). We take the top three titles and
// render them as a paragraph — three short sentences read like a lede.
export function buildCategorySummary(
  category: Category,
  themes: BriefTheme[],
): string {
  if (themes.length === 0) {
    return `No ${CATEGORY_LABELS[category]} themes in today's brief. Recent ${CATEGORY_LABELS[category]} highlights from the past week are below.`;
  }

  const lead = themes.slice(0, MAX_LEAD_THEMES).map((t) => trimTrailingDot(t.title) + ".");
  const remainder = themes.length - lead.length;
  if (remainder > 0) {
    lead.push(
      `Plus ${remainder} more theme${remainder === 1 ? "" : "s"} tagged ${CATEGORY_LABELS[category]}.`,
    );
  }
  return lead.join(" ");
}
