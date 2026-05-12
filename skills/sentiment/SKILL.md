---
name: sentiment-fear-greed
description: Pull the daily Crypto Fear & Greed Index from alternative.me into raw_signals. One signal per day, deduped by date.
metadata: { "openclaw": { "emoji": "😨", "requires": { "bins": ["bash", "python3"] } } }
---

# sentiment-fear-greed

Single-signal-per-day ingestion of the alternative.me Crypto Fear &
Greed Index. signal_type = `fear_greed`. Source row is "Fear & Greed
Index" (source_type=`macro`).

## Run

```bash
{baseDir}/scripts/run.sh
```

## Behavior

- Idempotent on date: if a `fear_greed` signal already exists for
  today's UTC date from this source, the script exits 0 with a
  "skipped" message.
- Stores yesterday's value + classification in raw_payload alongside
  today's, so synthesis can reason about day-over-day shifts.
- Exit 0 on insert or skip, 1 if Source missing, 2 on API failure.
