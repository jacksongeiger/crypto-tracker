---
name: synthesize-brief
description: Produce a daily anti-noise crypto brief by synthesizing the last 24h of news_article signals with Gemini 2.5 Flash. Use when the user asks for today's brief, a synthesis, or a daily summary.
metadata: { "openclaw": { "emoji": "🧭", "requires": { "bins": ["bash", "python3"], "env": ["GOOGLE_API_KEY"] } } }
---

# synthesize-brief

Generate the daily crypto brief: a 2–3 sentence summary plus 3–5 themes
drawn from the last 24 hours of `news_article` signals in the crypto-tracker
database. Each theme is sourced (provenance via `source_signal_ids`) and
conviction-scored 1–5 based on independent-source corroboration.

## When to use

- "Generate today's brief"
- "Synthesize the news"
- "What's the daily?" / "What happened today in crypto?"

## When NOT to use

- The user wants raw articles, not synthesis — query `raw_signals` directly.
- The user wants a brief for a specific past date — this skill always uses
  the last 24h relative to now. Backfill is not implemented yet.
- The user wants to ingest news — that's `crypto-news-ingest`. Run that
  first, then this.

## How to run

Invoke the wrapper script:

```bash
{baseDir}/scripts/run.sh
```

The wrapper uses the project's `backend/.venv` interpreter and resolves
all paths relative to itself.

## Prerequisites

- `GOOGLE_API_KEY` must be set in `backend/.env` (Gemini API key).
- At least 5 `news_article` rows from the last 24h. If there are fewer, the
  skill exits 2 with a clear message — run `crypto-news-ingest` first.

## Expected output

```
brief_id: <uuid>
brief_date: 2026-05-12
input_signals: 178
themes: 4
tokens: 8421

======================================================================
SUMMARY:
<2-3 sentences>
======================================================================

[1] <theme title>  (conviction 4, primary=abcd1234…, +2 corroborators)
    <theme body>

[2] ...
```

The brief is persisted to `briefs` and `brief_themes` in one transaction.

## Behavior guarantees

- Every theme has a single `primary_signal_id` (the central event) plus a
  `source_signal_ids` array (primary + corroborating signals). Validator
  enforces: primary must exist in the input and must appear in
  source_signal_ids. This is the schema-level anti-bucketing constraint.
- IDs that don't match a real input signal cause a validation error
  (hallucination guard).
- `conviction_score` is an integer 1–5; anything else fails validation.
- Max 5 themes — the prompt enforces this; the validator double-checks.
- Exit 0 on success, 2 if not enough signals, 3 if Gemini fails or returns
  malformed JSON. The raw response is logged to stderr on parse failure.

## After running

The user usually wants to read the brief. It's already on stdout. To
re-display past briefs:

```sql
SELECT b.brief_date, t.display_order, t.title, t.conviction_score
FROM briefs b JOIN brief_themes t ON t.brief_id = b.id
WHERE b.brief_date = CURRENT_DATE
ORDER BY t.display_order;
```
