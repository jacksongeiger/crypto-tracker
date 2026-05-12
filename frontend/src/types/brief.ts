export type Brief = {
  id: string;
  brief_date: string; // ISO date (yyyy-mm-dd) as serialized
  generated_at: string; // ISO timestamp
  summary: string;
  model_used: string;
  input_signal_count: number;
};

export type BriefTheme = {
  id: string;
  display_order: number;
  title: string;
  body: string;
  conviction_score: number | null;
  primary_signal_id: string;
  primary_source_name: string;
  primary_signal_title: string;
  primary_signal_url: string | null;
  corroborating_count: number; // length(source_signal_ids) - 1
};

export type BriefWithThemes = {
  brief: Brief;
  themes: BriefTheme[];
};
