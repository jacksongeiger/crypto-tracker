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

export type BriefHistoryRow = {
  id: string;
  brief_date: string;
  generated_at: string;
  summary: string;
  model_used: string;
  input_signal_count: number;
  theme_count: number;
  max_conviction: number | null;
  categories: Category[];
  top_themes: { title: string; display_order: number }[];
};

type RawHistoryRow = {
  id: string;
  brief_date: Date;
  generated_at: Date;
  summary: string;
  model_used: string;
  input_signal_count: number;
  theme_count: number | string;
  max_conviction: number | null;
  categories: string[] | null;
  top_themes: { title: string; display_order: number }[] | null;
};

export async function getBriefHistory({
  limit = 20,
  offset = 0,
}: { limit?: number; offset?: number } = {}): Promise<BriefHistoryRow[]> {
  const rows = await sql<RawHistoryRow[]>`
    SELECT
      b.id,
      b.brief_date,
      b.generated_at,
      b.summary,
      b.model_used,
      b.input_signal_count,
      (SELECT count(*) FROM brief_themes WHERE brief_id = b.id) AS theme_count,
      (SELECT max(conviction_score) FROM brief_themes WHERE brief_id = b.id) AS max_conviction,
      (
        SELECT COALESCE(jsonb_agg(DISTINCT cat), '[]'::jsonb)
        FROM brief_themes bt, jsonb_array_elements_text(bt.categories) cat
        WHERE bt.brief_id = b.id
      ) AS categories,
      (
        SELECT COALESCE(jsonb_agg(json_build_object('title', t.title, 'display_order', t.display_order) ORDER BY t.display_order), '[]'::jsonb)
        FROM (
          SELECT title, display_order
          FROM brief_themes
          WHERE brief_id = b.id
          ORDER BY display_order ASC
          LIMIT 3
        ) AS t
      ) AS top_themes
    FROM briefs b
    ORDER BY b.brief_date DESC, b.generated_at DESC
    LIMIT ${limit} OFFSET ${offset}
  `;
  return rows.map((r) => ({
    id: r.id,
    brief_date: r.brief_date.toISOString().slice(0, 10),
    generated_at: r.generated_at.toISOString(),
    summary: r.summary,
    model_used: r.model_used,
    input_signal_count: r.input_signal_count,
    theme_count: Number(r.theme_count),
    max_conviction: r.max_conviction,
    categories: (r.categories ?? []) as Category[],
    top_themes: r.top_themes ?? [],
  }));
}

export async function getBriefCount(): Promise<number> {
  const rows = await sql<{ count: string }[]>`SELECT count(*)::text AS count FROM briefs`;
  return Number(rows[0]?.count ?? 0);
}

export async function getBriefById(
  id: string,
): Promise<BriefWithThemes | null> {
  const rows = await sql<BriefRow[]>`
    SELECT id, brief_date, generated_at, summary, model_used, input_signal_count
    FROM briefs
    WHERE id = ${id}
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

export type RecentCategoryTheme = BriefTheme & {
  brief_id: string;
  brief_date: string;
};

// Pull recent themes tagged with the given category from briefs in the
// last `days` days, excluding any brief whose id is in `excludeBriefIds`
// (used to skip the latest brief on the category page so we don't repeat
// what's already at the top). One theme per source story — we de-dupe by
// primary_signal_id since the same upstream signal can show up across
// same-day re-synthesis runs.
export async function getRecentCategoryThemes(
  category: Category,
  { days = 7, limit = 6, excludeBriefIds = [] }: {
    days?: number;
    limit?: number;
    excludeBriefIds?: string[];
  } = {},
): Promise<RecentCategoryTheme[]> {
  const rows = await sql<
    (ThemeRow & { brief_id: string; brief_date: Date })[]
  >`
    SELECT DISTINCT ON (bt.primary_signal_id)
      bt.id,
      bt.display_order,
      bt.title,
      bt.body,
      bt.conviction_score,
      bt.primary_signal_id,
      bt.source_signal_ids,
      bt.categories,
      bt.brief_id,
      b.brief_date,
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
    JOIN briefs b       ON b.id = bt.brief_id
    JOIN raw_signals rs ON rs.id = bt.primary_signal_id
    JOIN sources s      ON s.id = rs.source_id
    WHERE b.brief_date >= current_date - ${days}::int
      AND bt.categories @> ${JSON.stringify([category])}::jsonb
      AND NOT (bt.brief_id = ANY(${excludeBriefIds}::uuid[]))
    ORDER BY bt.primary_signal_id, b.generated_at DESC
  `;

  return rows
    .map((t) => ({
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
      brief_id: t.brief_id,
      brief_date: t.brief_date.toISOString().slice(0, 10),
    }))
    .sort((a, b) => {
      if (a.brief_date !== b.brief_date) return a.brief_date < b.brief_date ? 1 : -1;
      return (b.conviction_score ?? 0) - (a.conviction_score ?? 0);
    })
    .slice(0, limit);
}
