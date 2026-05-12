import { sql } from "./db";
import type {
  Brief,
  BriefTheme,
  BriefWithThemes,
  Category,
} from "@/types/brief";

type BriefRow = {
  id: string;
  brief_date: Date;
  generated_at: Date;
  summary: string;
  model_used: string;
  input_signal_count: number;
};

type ThemeRow = {
  id: string;
  display_order: number;
  title: string;
  body: string;
  conviction_score: number | null;
  primary_signal_id: string;
  source_signal_ids: string[];
  categories: string[];
  primary_source_name: string;
  primary_signal_title: string;
  primary_signal_url: string | null;
  corroborating_sources: { id: string; name: string }[];
};

async function loadThemes(briefId: string): Promise<BriefTheme[]> {
  const rows = await sql<ThemeRow[]>`
    SELECT
      bt.id,
      bt.display_order,
      bt.title,
      bt.body,
      bt.conviction_score,
      bt.primary_signal_id,
      bt.source_signal_ids,
      bt.categories,
      s.name AS primary_source_name,
      rs.title AS primary_signal_title,
      rs.url   AS primary_signal_url,
      COALESCE(
        (
          SELECT json_agg(
                   json_build_object('id', rs2.id, 'name', s2.name)
                   ORDER BY s2.name
                 )
          FROM jsonb_array_elements_text(bt.source_signal_ids) sid
          JOIN raw_signals rs2 ON rs2.id::text = sid
          JOIN sources s2 ON s2.id = rs2.source_id
          WHERE rs2.id <> bt.primary_signal_id
        ),
        '[]'::json
      ) AS corroborating_sources
    FROM brief_themes bt
    JOIN raw_signals rs ON rs.id = bt.primary_signal_id
    JOIN sources s      ON s.id = rs.source_id
    WHERE bt.brief_id = ${briefId}
    ORDER BY bt.display_order ASC
  `;

  return rows.map((t) => ({
    id: t.id,
    display_order: t.display_order,
    title: t.title,
    body: t.body,
    conviction_score: t.conviction_score,
    primary_signal_id: t.primary_signal_id,
    primary_source_name: t.primary_source_name,
    primary_signal_title: t.primary_signal_title,
    primary_signal_url: t.primary_signal_url,
    corroborating_count: Math.max(0, t.source_signal_ids.length - 1),
    categories: (t.categories ?? []) as Category[],
    corroborating_sources: t.corroborating_sources ?? [],
  }));
}

function mapBrief(row: BriefRow): Brief {
  return {
    id: row.id,
    brief_date: row.brief_date.toISOString().slice(0, 10),
    generated_at: row.generated_at.toISOString(),
    summary: row.summary,
    model_used: row.model_used,
    input_signal_count: row.input_signal_count,
  };
}

export async function getLatestBrief(): Promise<BriefWithThemes | null> {
  const rows = await sql<BriefRow[]>`
    SELECT id, brief_date, generated_at, summary, model_used, input_signal_count
    FROM briefs
    ORDER BY generated_at DESC
    LIMIT 1
  `;
  if (rows.length === 0) return null;
  const brief = mapBrief(rows[0]);
  return { brief, themes: await loadThemes(brief.id) };
}

export async function getLatestBriefByCategory(
  category: Category,
): Promise<BriefWithThemes | null> {
  const data = await getLatestBrief();
  if (!data) return null;
  return {
    brief: data.brief,
    themes: data.themes.filter((t) => t.categories.includes(category)),
  };
}
