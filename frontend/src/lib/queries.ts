import { sql } from "./db";
import type { Brief, BriefTheme, BriefWithThemes } from "@/types/brief";

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
  primary_source_name: string;
  primary_signal_title: string;
  primary_signal_url: string | null;
};

export async function getLatestBrief(): Promise<BriefWithThemes | null> {
  const briefRows = await sql<BriefRow[]>`
    SELECT id, brief_date, generated_at, summary, model_used, input_signal_count
    FROM briefs
    ORDER BY generated_at DESC
    LIMIT 1
  `;
  if (briefRows.length === 0) return null;
  const row = briefRows[0];

  const themeRows = await sql<ThemeRow[]>`
    SELECT
      bt.id,
      bt.display_order,
      bt.title,
      bt.body,
      bt.conviction_score,
      bt.primary_signal_id,
      bt.source_signal_ids,
      s.name AS primary_source_name,
      rs.title AS primary_signal_title,
      rs.url   AS primary_signal_url
    FROM brief_themes bt
    JOIN raw_signals rs ON rs.id = bt.primary_signal_id
    JOIN sources s      ON s.id = rs.source_id
    WHERE bt.brief_id = ${row.id}
    ORDER BY bt.display_order ASC
  `;

  const brief: Brief = {
    id: row.id,
    brief_date: row.brief_date.toISOString().slice(0, 10),
    generated_at: row.generated_at.toISOString(),
    summary: row.summary,
    model_used: row.model_used,
    input_signal_count: row.input_signal_count,
  };

  const themes: BriefTheme[] = themeRows.map((t) => ({
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
  }));

  return { brief, themes };
}
