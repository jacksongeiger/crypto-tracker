# Synthesis prompt evolution — running notes

Short, candid notes on how each prompt iteration changed brief quality.
For full prompt files see `backend/prompts/synthesis_v{N}.md`. Tracked
to make quality regressions and improvements visible over time.

## v1 → v2 → v3 (news-only, prompt-only iteration)

Pure-prompt attempts to fix one persistent failure mode: the model
groups multiple unrelated TradFi/institutional events under a single
"category bucket" theme (e.g. "Institutional Adoption Deepens"
stacking DTCC + Franklin + Elliptic).

- **v1** baseline. Anti-bucketing rule present as a single bullet.
  Reproduced the bucket every run.
- **v2** added explicit anti-example naming the exact bucket pattern.
  Model used the anti-example as a template — reproduced the exact
  thing the prompt forbade.
- **v3** added a constructive decomposition example, banned-noun list
  for titles ("Adoption Deepens", "Landscape Evolves"), and a
  self-check pass. Still bucketed; sometimes copied "Adoption Deepens"
  verbatim from the banned-list.

**Lesson:** prompt prose and anti-examples are weak against the
model's default to organize input by category. Negative examples can
anchor on the bad pattern.

## v4 (schema-level fix)

Added `primary_signal_id` (single FK on the brief_themes table). Each
theme must declare ONE central event. Validator + DB column both
enforce. The model can no longer write a bucket theme and call it
"5 sources" — it has to pick one signal as the center, and bucketing
becomes structurally awkward.

**Result:** TradFi mega-buckets gone. The 5 unrelated TradFi events
are now either separate single-event themes or dropped. Residual
issue: within-company multi-event buckets (Circle Arc presale + Circle
AI agent launch under one theme) still happen because picking one as
"primary" is plausible.

## v5 (categories)

Same v4 anti-bucketing core, plus a `categories` JSONB tag column on
each theme (1–2 of policy/markets/tech/adoption/misc). No regression
on bucketing. Filtering and routing in the frontend now key off this.

## v6 — first run (no macro)

Multi-source-type input: news + on-chain + prediction_market + macro.
Validator gates conviction 5 on multiple distinct source_types.

Run with 260 signals (198 news, 42 on-chain, 19 prediction-market,
1 sentiment, 0 macro because FRED_API_KEY unset).

- Theme 1: "Senate Confirms Kevin Warsh to Fed Board" — conviction 5
  via `[news_rss, prediction_market]`. **First true cross-type theme.**
- Themes 2–4: news-only conviction 4 (TradFi bucket, Circle bucket,
  prediction-market regulatory bucket).
- Theme 5: on-chain only — `[on_chain]` bucketing returns ("DEX
  Activity surges" stacking 6 unrelated DEX/chain moves).

Brief id: `6a8a62d1-3e1e-4730-9435-6c91a23f0eb2`.

## v6 — second run (with macro = 9 FRED indicators)

Added 9 FRED signals (DXY, 2Y/10Y, Fed Funds, CPI YoY, M2,
unemployment, S&P 500, VIX — gold series 400'd, see TODO). Total 269
signals. Same v6 prompt, no other changes.

- Theme 1: "Inflation Data Dampens Rate Cut Hopes, Leading to
  Broader Market Risk-Off Sentiment" — conviction 5 via
  **`[news_rss, macro, prediction_market]`**. Cites CoinDesk on the
  inflation print + BTC dipping below $80k, DGS2 +1.28% / DGS10 +0.91%
  / VIX +6.92% from FRED, and Polymarket's 97.5% no-rate-change June
  reading. **Three independent source types corroborating one
  specific claim.** This is the editorial value-add the v6 design was
  built for.
- Themes 2–4: same single-type news conviction-4 themes as run 1
  (TradFi bucket, Circle bucket, CLARITY/CFTC bucket). Adding macro
  didn't fix the news-only bucketing — those stories don't have
  natural cross-type evidence in the corpus.
- Theme 5: same on-chain bucket as run 1 (now with 14 corroborators
  instead of 6).

Brief id: `<latest>` — `read_brief.py` shows the rendered version.

**Net assessment:** macro signals materially upgraded one theme from
2-type to 3-type cross-corroboration. The brief now has a real macro
top-line that wasn't there before. Single-type bucketing on
peripheral themes persists — same v4-era issue, separate fix.

## What the next prompt iteration (v7) should target

- Same-source-type bucketing inside `on_chain` (Theme 5 today). The
  primary_signal_id rule applies, but Defillama snapshots are all
  similarly weighted, so picking "primary" doesn't surface an
  editorial center. Candidate fix: in the prompt, treat on-chain
  bucket themes as illegal unless the body cites a *narrative*
  connecting the metrics (not just "all up").
- Within-company news bucketing (Circle, Theme 3). v4 didn't fix it,
  v5 didn't fix it, v6 didn't fix it. Candidate fix: a stricter
  same-event check in the validator that compares titles for entity
  overlap *and* event overlap, or a model self-check pass.
- More macro signal types beyond FRED: oil, real yields, crypto-
  specific positioning data (CME OI), would lift more themes from
  2-type to 3-type.
