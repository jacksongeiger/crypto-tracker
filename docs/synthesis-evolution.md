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

## v7 — same-event constraint (winner of A/B/C/D experiment)

Designed four experiments to crack the within-type/within-entity
bucketing v4 didn't fix:

1. **Exp 1 — same-event constraint.** Adds explicit prompt rule that
   `source_signal_ids` must contain ONLY signals about the SAME event
   as the primary, with a worked example (Circle Arc presale only,
   not Arc + Q1 earnings + AI agent launch).
2. **Exp 2 — split-or-die.** Adds a 5-word self-check ("name your
   theme's single event in 5 words") and worked example of splitting
   1 draft into 2 themes.
3. **Exp 3 — title hard constraints.** Banned words list in titles
   (`and`, `+`, `while`, `&`, `amid`, `alongside`).
4. **Exp 4 — two-pass.** Pass 1 enumerates 20–40 distinct events;
   Pass 2 selects 3–5 from the event list.

### Comparison table (run against the same 269-signal corpus)

| Exp | Single-event % | AND titles | Within-entity split | Within-type split | Themes | Cross-type ★5 | Cost vs v6 |
|-----|----------------|------------|---------------------|-------------------|--------|----------------|------------|
| v6 baseline | 1/5 (20%)   | 2 (T2, T5) | ✗ Circle merged    | ✗ DEX bucket      | 5 | 1 (CPI/macro/preds) | 1.0× |
| **Exp 1**   | **5/5 (100%)** | **0**      | ✓ Circle = Arc only | ✓ no on-chain bucket | 5 | **2 (Fed, MSTR)**     | 1.0× |
| Exp 2       | 3/5 (60%)   | 1 (T4: "DEX Volumes and Chain Fees") | ✓ Circle split | ✗ DEX/fees bucket | 5 | 0           | 1.1× |
| Exp 3       | 1/5 (20% by body) | 0 (titles clean) | ✗ body still buckets Arc+AI+Ark | ✗ Bhutan+Exodus+MSTR in body | 5 | 1 (suspect)        | 1.05× |
| Exp 4       | (could not run; daily Flash quota exhausted on retries) | | | | | | ~2× |

### Decision: ship Exp 1

Per the spec rule — "If any prose-only experiment achieves >80%
single-event themes AND 0 AND-titles AND retains cross-type
conviction-5 themes, use that one" — **Exp 1 satisfies all three**:

- 5/5 single-event themes (Fed, MSTR, Franklin/Payward, Circle Arc, DTCC each isolated)
- 0 banned conjunctions in titles
- 2 cross-type ★5 themes (Fed/Warsh + MSTR), one MORE than v6

Did not run Exp 4. The structural fallback wasn't needed because a
prose experiment cleared the bar. Two-pass would have cost ~2× tokens
+ extra quota slots for the same outcome — keeping it as a v8
candidate if Exp 1's win turns out to be sampling-luck rather than
real.

### Why Exp 1 worked when Exp 3 didn't

Exp 3 banned conjunctions in titles, and the model complied — but
hid the bucketed events in the body instead. Theme 5 in Exp 3:
"Circle raises $222M for Arc institutional blockchain" (clean title)
+ body that bundles Arc presale, AI agents, AND Ark Invest's Circle
share buy. The title constraint is a surface fix; the body remains
the bucket.

Exp 1 attacks the right level: every signal in `source_signal_ids`
must be about the SAME event as the primary. With that rule, the
Arc presale theme drops the AI agent and Ark Invest signals from
sources, and the model cannot smuggle them into the body without
violating the same-event filter.

### Tests

`backend/tests/test_v7_anti_bucketing.py` — 8 passing pytest cases
plus 1 deliberate skip:

- `TestNoAndInTitles`: regex check for `+`, `&`, `while`, `amid`,
  `alongside` and capitalized "X and Y" subjects
- `TestSingleEventInBody`: heuristic — body shouldn't introduce
  more than 1 known entity not named in the title
- `TestV7AgainstKnownBadBrief`: feeds the v6 on-chain bucket and
  TradFi bucket through the validators and asserts they fail
- `test_primary_event_dominance` skipped per spec (semantic LLM
  judge not in scope)

### Remaining failure modes (honest)

- Exp 1 dropped on-chain themes entirely from this run. May be the
  honest call (no single on-chain event was uniquely consequential
  today) or may indicate v7 over-rejects. Watch on future runs.
- The "same-event filter" is enforced by prompt only — the
  validator catches title-level and entity-overlap issues but not
  semantic same-event drift. A v8 would either add an LLM judge
  pass or rerun with the two-pass architecture.
- Cross-type 5 went from 1 to 2 in this run but that's variance-
  prone; want N≥3 brief runs over different days to confirm the
  improvement is structural not lucky.
