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

## v7.1 — conviction is unique sources, not signal count

Prompt + validator change (no new model run). The v7 sanitizer
auto-downgraded conviction 5→4 when source_types dropped below 2
after cleaning, but there was no ceiling on conviction by **distinct
independent source count**. The "Two articles from the same outlet
are one source" rule was prompt-only, not enforced anywhere.

Effect: a theme with N signals from a single source (e.g. 8 Defillama
snapshots — TVL on Solana + TVL on Ethereum + Raydium volume + Uniswap
volume + Curve volume + Aave fees + Lido stakes + Aerodrome…) could
honestly be one Defillama datapoint stacked across DEXes, but the
model would call it conviction 4 because "8 signals corroborate."
That's the inflation pattern v7.1 closes.

### Changes

- `skills/synthesize-brief/scripts/synthesize.py`: `load_signals` now
  carries `Source.id` per signal so the sanitizer can compute
  `effective_source_count`. `sanitize_response` takes a new
  `signal_source_map` arg and applies `max_conviction_for_counts`:

  | distinct sources | distinct types | conviction ceiling |
  | ---------------: | -------------: | ------------------ |
  | 1                | 1              | 2                  |
  | 2                | 1              | 3                  |
  | 3+               | 1              | 4                  |
  | any              | 2+             | 5                  |

  Downgrades log a `conviction_downgraded_by_source_count` entry in
  `auto_corrected` and persist via `generation_metadata.sanitization`.

- `backend/prompts/synthesis_v7.md`: explicit unique-sources-not-signals
  block at the top of the conviction section, with a worked example
  (5 Defillama + 1 F&G = 2 sources, conviction 5 only because
  cross-type; pure 5 Defillama = max conviction 2). The score table
  rows for 3 and 4 now say "distinct" sources rather than just
  "independent."

- Frontend: `source-popover.tsx` dedupes corroborating signals by
  source name and renders one row per unique name with a "(N signals)"
  suffix when N>1. The "+N" chip counts unique source names that
  differ from the primary's source, so a primary-Defillama theme with
  7 other Defillama signals + 1 F&G renders "+1 source" instead of "+8".

### Retroactive re-score (2026-05-17)

Ran `scripts/rescore_conviction.py --apply` against the 6 production
briefs. 11/53 themes downgraded:

| count | shift | shape                              |
| ----: | ----- | ---------------------------------- |
|     6 | 4→2   | 1 source, 1 type — pure on-chain or pure prediction-market buckets |
|     4 | 4→3   | 2 sources, 1 type — same-type-only coverage |
|     1 | 5→4   | 4 sources, 1 type — Circle Arc bucket (news-only) |

The 5→4 case ("Circle Secures $222M for Arc Institutional Blockchain
and Launches AI") was already flagged in the TODO as same-entity
bucketing v7 didn't fully solve; the score-drop is downstream of that
same root cause and is correct. The 4→2 cases are the classic Defillama
or Polymarket signal-stacking pattern this v7.1 change exists to
prevent.

No themes were dropped or invalidated — only conviction scores moved.

### Why a re-score and not a re-synthesize

A re-synthesize would have cost an LLM call per brief and likely
produced *different* themes due to v7.1's prompt-level changes
(harder to compare against the original output). The re-score
applies *only* the math change, holding theme content constant. If
the new ceiling is wrong on a specific theme we can see it cleanly.

### Tests

`backend/tests/test_sanitize_response.py` adds 6 new cases covering
the source-count ceiling (8 same-source → max 2, cross-type imbalanced
→ 5 still valid, 2/3 same-type ladder, single-source 2 unchanged,
plus a table over `max_conviction_for_counts`). The existing 5→4
test was renamed and updated to assert the new `kind` value
(`conviction_downgraded_by_source_count`).

`frontend/tests/unit/source-popover.test.tsx` covers `groupCorroborators`,
`uniqueIndependentSourceCount`, and the user-reported scenario
(7 Defillama + 1 F&G with Defillama primary → "+1 source").
`frontend/tests/e2e/source-popover.spec.ts` asserts on the live
production data that no source name appears twice in the popover and
that the chip count matches the unique non-primary names.
