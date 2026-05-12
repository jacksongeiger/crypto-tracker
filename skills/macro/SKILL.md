---
name: macro-fred
description: Pull 10 macro indicators from FRED (DXY proxy, 2Y/10Y yields, Fed Funds, CPI YoY, M2, unemployment, gold, S&P 500, VIX) into raw_signals. Use when the user asks to refresh macro context for a brief.
metadata: { "openclaw": { "emoji": "📈", "requires": { "bins": ["bash", "python3"], "env": ["FRED_API_KEY"] } } }
---

# macro-fred

Daily ingestion of 10 FRED indicators that bear on crypto:

| subtype          | FRED series         | meaning                     |
| ---------------- | ------------------- | --------------------------- |
| `dxy`            | DTWEXBGS            | Trade-weighted USD          |
| `treasury_10y`   | DGS10               | 10Y Treasury yield          |
| `treasury_2y`    | DGS2                | 2Y Treasury yield           |
| `fed_funds`      | DFF                 | Effective Fed Funds rate    |
| `cpi_yoy`        | CPIAUCSL → YoY %    | Headline CPI year-over-year |
| `m2_supply`      | M2SL                | M2 money supply             |
| `unemployment`   | UNRATE              | U-3 unemployment            |
| `gold_price`     | GOLDAMGBD228NLBM    | London AM gold fix          |
| `sp500`          | SP500               | S&P 500 index level         |
| `vix`            | VIXCLS              | CBOE VIX close              |

## Run

```bash
{baseDir}/scripts/run.sh
```

## Behavior

- Requires `FRED_API_KEY` in `backend/.env` (free key from
  <https://fredaccount.stlouisfed.org/apikey>). If unset, the skill
  exits 0 with a clear "skip" message — synthesis tolerates missing
  macro signals.
- Idempotent per indicator: inserts only when FRED's latest
  observation is newer than this skill's most recent signal of the
  same subtype. Re-running on the same day is a no-op.
- For `cpi_yoy`, the script computes year-over-year % change from the
  monthly level series (CPIAUCSL) so the signal is directly readable.
- One Source row "FRED" with source_type=`macro`. Seed via
  `scripts/seed_sources.py` before first run.
