---
name: onchain-ingest
description: Pull on-chain snapshots (TVL by chain, top protocol fees, top DEX volumes, stablecoin supply) from DefiLlama into raw_signals. Use when the user asks to refresh on-chain data, ingest TVL, or pull DefiLlama numbers.
metadata: { "openclaw": { "emoji": "⛓️", "requires": { "bins": ["bash", "python3"] } } }
---

# onchain-ingest

Snapshot ingestion from DefiLlama free public API. Inserts a row in
`raw_signals` for each metric, tagged by signal_type subtype:

- `tvl_change` — per-chain TVL with 24h/7d % change (8 majors)
- `fee_revenue` — top 20 protocols by 24h fees
- `dex_volume` — top 10 DEXes by 24h volume
- `stablecoin_supply` — USDC, USDT, DAI, FDUSD supply with deltas

## Run

```bash
{baseDir}/scripts/run.sh
```

## Behavior

- Snapshots use `occurred_at = now()`; no dedupe against past snapshots
  (each run inserts a fresh point in the time series).
- One Source row of `source_type='on_chain'` named "Defillama" — seed
  it via `scripts/seed_sources.py` before first run.
- Exit 0 on success, 1 if Source missing, 2 on API failure.
