---
name: crypto-news-ingest
description: Pull the latest entries from active news_rss sources in the crypto-tracker DB and insert new ones into raw_signals. Use when the user asks to fetch, refresh, or ingest crypto news.
metadata: { "openclaw": { "emoji": "📰", "requires": { "bins": ["bash", "python3"] } } }
---

# crypto-news-ingest

Ingest fresh items from the RSS feeds registered as active `news_rss` sources
in the crypto-tracker Postgres database into the `raw_signals` table.

## When to use

- "Ingest the latest crypto news"
- "Refresh the news feeds"
- "Pull new articles into the database"

## When NOT to use

- One-off scraping of a single URL — use `exec` + `curl` or a fetch tool.
- Backfilling historical data — RSS feeds only expose a recent window.
- Adding new sources — insert into `sources` directly (or use the seed script).

## How to run

Invoke the wrapper script. It resolves all paths relative to itself, so it
works regardless of where the repo is cloned:

```bash
{baseDir}/scripts/run.sh
```

The wrapper activates the project's `backend/.venv` interpreter automatically.

## Expected output

A summary table on stdout, one row per source, plus a total. Example:

```
source       fetched   new   dup  no-date
--------------------------------------------
Bankless          25     3     22        0
CoinDesk          50     7     43        0
Decrypt           40     2     38        0
The Block         30     4     26        0
--------------------------------------------
total new rows: 16
```

## Behavior guarantees

- One feed failing (404, network error, malformed XML) does **not** abort the
  run — that source's row shows `ERROR: <reason>` and the loop continues.
- Entries without a `published_parsed` / `updated_parsed` date are skipped
  (visible in the `no-date` column).
- Entries whose `link` already exists in `raw_signals.url` are skipped
  (visible in the `dup` column). A UNIQUE partial index enforces this at the
  DB level as a backstop against races.
- Exit code is always 0 — read the summary for per-source status.

## After running

If new rows were inserted, the user usually wants to see the top headlines or
filter by source. Use SQL through `psql -d crypto_tracker_dev`:

```sql
SELECT s.name, rs.title, rs.occurred_at
FROM raw_signals rs JOIN sources s ON s.id = rs.source_id
ORDER BY rs.ingested_at DESC LIMIT 20;
```
