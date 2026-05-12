---
name: predictions-polymarket
description: Pull top crypto-keyword Polymarket markets into raw_signals with YES probability, 24h volume, and time-to-resolution. Use when the user asks to refresh prediction-market context.
metadata: { "openclaw": { "emoji": "🎲", "requires": { "bins": ["bash", "python3"] } } }
---

# predictions-polymarket

Snapshot ingestion of the top 30 crypto-relevant Polymarket markets by
24h volume. signal_type=`prediction_market`. Each insert captures the
YES/NO probability, volumes, and time-to-resolution at that moment, so
the table becomes a per-market time series of probability moves.

## Run

```bash
{baseDir}/scripts/run.sh
```

## Behavior

- Fetches up to 200 markets from gamma-api, filters to crypto keywords
  (broader than the dashboard's set — see `CRYPTO_KEYWORDS` in the
  script), takes the top 30 by 24h volume.
- Dedupe window: `DEDUPE_HOURS = 6`. A given market_slug is only
  re-snapshotted after the window expires, so re-runs within 6h are
  cheap no-ops on already-ingested markets.
- raw_payload includes `market_slug`, `yes_probability`, volumes, and
  `change_pp_24h` (probability change in percentage points) when the
  API exposes it.
- One Source row "Polymarket" with source_type=`prediction_market`.
  Seed via `scripts/seed_sources.py` before first run.
