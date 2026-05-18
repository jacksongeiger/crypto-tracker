# crypto-tracker

Autonomous daily crypto market brief built on the OpenClaw agent platform. Synthesizes news, on-chain, macro, prediction-market, and sentiment signals from the last 24 hours into 3–5 editorial themes with conviction scoring and cross-source-type corroboration.

Live: https://192-18-128-170.nip.io/news/overview

---

## What it does

Each morning at 06:30 PT, a system-cron-driven OpenClaw pipeline ingests fresh signals across five source types into Postgres. At 06:50 PT a synthesis skill calls Gemini 2.5 Flash with the v7.1 prompt, which selects the day's 3–5 most consequential events and assigns each a conviction score on the basis of how many *independent sources* (not signals) corroborate it. The resulting brief is rendered server-side at the live URL above.

The editorial premise: a story that shows up across different *kinds* of sources (news + on-chain + prediction market) is more real than one that lives in news alone. The system optimizes for selection — most signals do not appear in the brief — and surfaces cross-type corroboration as the highest-value signal. Conviction-5 themes require ≥2 distinct source types; the validator enforces this and downgrades anything declared above what its source distribution can justify.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Daily cron (06:30–06:50 PT, system crontab, staggered jobs)     │
└──────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────┐  ┌───────────────┐  ┌──────────────┐  ┌──────────┐  ┌─────────────┐
│ news_rss      │  │ on_chain      │  │ macro        │  │ predict. │  │ sentiment   │
│ (RSS feeds)   │  │ (Defillama)   │  │ (FRED)       │  │ (Poly.)  │  │ (alt.me)    │
└──────┬────────┘  └──────┬────────┘  └──────┬───────┘  └────┬─────┘  └──────┬──────┘
       └──────────────────┴──────────────────┴───────────────┴────────────────┘
                                            │
                              OpenClaw skills (skills/*)
                                            │
                                            ▼
                                ┌────────────────────────┐
                                │ Postgres: raw_signals  │
                                └────────────┬───────────┘
                                             │
                                             ▼
                                ┌────────────────────────┐
                                │ synthesize-brief skill │
                                │ Gemini 2.5 Flash,      │
                                │ prompts/synthesis_v7.md│
                                │ + sanitize_response()  │
                                └────────────┬───────────┘
                                             │
                                             ▼
                                ┌────────────────────────┐
                                │ Postgres: briefs,      │
                                │ brief_themes           │
                                └────────────┬───────────┘
                                             │
                                             ▼
                                ┌────────────────────────┐
                                │ Next.js 14 (SSR)       │
                                │ → Caddy → public HTTPS │
                                └────────────────────────┘
```

**Stack:** Python 3.12 + SQLAlchemy backend, Next.js 14 (App Router) frontend, Postgres 16, Caddy + Let's Encrypt, pm2 + system cron, deployed to Oracle Cloud ARM (aarch64).

---

## OpenClaw integration

OpenClaw is the agent platform that hosts the six skills in `skills/`. Each skill is a self-contained directory with a `SKILL.md` (frontmatter + instructions), a `scripts/` directory (the actual implementation), and a declared set of required binaries and environment variables.

The six skills:

| Skill | Source | What it ingests | API |
|---|---|---|---|
| `news` (`crypto-news-ingest`) | CoinDesk, The Block, Decrypt, Bankless RSS | News articles → `raw_signals(signal_type='news_article')` | RSS feeds |
| `onchain` (`onchain-ingest`) | Defillama | TVL by chain, top protocol fees, top DEX volumes, stablecoin supply | api.llama.fi |
| `sentiment` (`sentiment-fear-greed`) | alternative.me | Daily Crypto Fear & Greed Index (one signal per day, deduped on date) | api.alternative.me |
| `macro` (`macro-fred`) | FRED | 10 indicators: DGS2, DGS10, DXY, CPI YoY, FEDFUNDS, M2SL, UNRATE, SP500, VIXCLS (+ gold, currently 400) | api.stlouisfed.org |
| `predictions` (`predictions-polymarket`) | Polymarket | Top crypto-keyword markets with YES probability, 24h volume, time-to-resolution | gamma-api.polymarket.com |
| `synthesize-brief` | Postgres + Gemini | Reads 24h of raw_signals across all types; writes briefs + brief_themes | Gemini 2.5 Flash |

The five ingestion skills run as isolated OpenClaw agent turns at 06:30 / 06:35 / 06:35 / 06:40 / 06:40 PT; synthesis fires at 06:50 PT once the corpus is warm. Each turn restricts the `exec` tool to its single shell command, so an ingestion skill cannot reach outside its declared scope. Logs land in `~/crypto-tracker/logs/<job>.log` and are tail-scanned by `scripts/verify_pipeline.py` for status.

The synthesis skill specifically:

1. Pulls every `raw_signal` with `occurred_at >= now() - 24h` across all source types (joined to `Source` for type + name + id).
2. Refuses to synthesize if fewer than `MIN_SIGNALS=20` are available (returns exit code 2).
3. Loads the v7 system prompt and renders the signal corpus as a user message.
4. Calls Gemini 2.5 Flash with `response_mime_type=application/json` for structured output.
5. Runs `sanitize_response()`, which:
   - Drops hallucinated signal IDs (model invents UUIDs occasionally).
   - Promotes a new primary signal if the declared primary was hallucinated but a corroborator survives.
   - Rebuilds `source_types` from the cited signals (truth wins over what the model claimed).
   - Caps conviction by `max_conviction_for_counts(distinct_sources, distinct_types)`: 1 source → 2, 2 same-type → 3, 3+ same-type → 4, ≥2 types → 5.
   - Logs every correction into `brief.generation_metadata.sanitization` for auditing.
6. Retries once on systemic failure (e.g. >50% of themes had to be dropped).
7. Persists `briefs` + `brief_themes` in a single transaction.

**Why OpenClaw over plain cron + Python:** skill-level isolation (a misbehaving ingester can't side-effect anything outside its declared scope), declarative config (`SKILL.md` frontmatter declares required env + bins, so a missing `FRED_API_KEY` is caught at load rather than 5 minutes into a run), observable skill runs (each run is an addressable agent turn with structured output), and model routing (the synthesis skill can switch underlying models without changing surface). For *this* project, the most useful property is the SKILL.md/scripts split — it makes each ingestion source a unit you can run, test, and revise in isolation. The platform does not replace cron for scheduling; system cron still calls `openclaw skill run` for each job.

---

## Synthesis design

Each theme in a brief has:

```json
{
  "title": "<sentence about a specific event>",
  "body": "<2–4 sentences, concrete and sourced>",
  "primary_signal_id": "<uuid — the single central event>",
  "source_signal_ids": ["<primary_id>", "<same-event corroborators>"],
  "categories": ["<1–2 of: policy, markets, tech, adoption, ai, misc>"],
  "source_types": ["<unique source_type values cited>"],
  "conviction_score": 1-5
}
```

Two structural rules carry most of the editorial weight:

1. **`primary_signal_id`** — every theme must point at *one* specific event. If you can't honestly name which signal is the center of a theme, the theme is bucketing — split or drop. This is enforced as a DB column with a foreign key, not just a prompt rule.

2. **Same-event constraint** — every signal in `source_signal_ids` must report the *same event* as the primary, not the same topic, the same company, or the same category. A Circle Arc presale theme can cite multiple reports of the presale, but cannot fold in a Circle Q1 earnings story or a Circle product launch. Conviction is scored on corroboration of that one event, not on the count of tangentially-related signals.

**Conviction rubric (v7.1):**

| Score | Required |
|---|---|
| 1 | 1 source, speculative or opinion |
| 2 | 1 source, concrete factual claim |
| 3 | 2 distinct same-type sources |
| 4 | 3+ distinct same-type sources |
| 5 | ≥2 distinct source types (cross-type corroboration) |

The rubric is prompt-level *and* validator-level. The validator computes distinct-source-count and distinct-source-type-count from the cited signal IDs and auto-downgrades anything above its ceiling. "Two articles from the same outlet are one source." Eight Defillama snapshots — TVL on Solana + TVL on Ethereum + Raydium volume + Aave fees + Lido stakes etc. — are one source. Cross-source-type corroboration (news + macro + predictions all pointing at the same specific claim) is the only path to conviction 5.

For the full evolution history (v1 prose-only → v4 schema constraint → v6 multi-type → v7 same-event → v7.1 unique-sources ceiling), see [`docs/synthesis-evolution.md`](docs/synthesis-evolution.md). That doc is the canonical record of what worked, what didn't, and which prompt experiments shipped.

---

## Frontend

- `/news/overview` — today's brief, conviction-weighted
- `/news/{policy,markets,tech,adoption,ai,misc}` — category page with today's themes + 7-day fallback when today is empty + per-category TL;DR derived deterministically from the data
- `/news/weekly` — 7-day roundup with cross-day persistence detection (themes that recur with overlapping signal sets cluster together)
- `/news/history` — every persisted brief with detail view at `/news/history/<brief_id>`
- `/dashboard` — live price strip (CoinGecko), on-chain TVL/fees (Defillama), fear & greed (alt.me), top prediction markets (Polymarket)

Server-rendered (Next.js App Router); no client-side fetching for brief content. Postgres queries live in `frontend/src/lib/queries.ts`. Design system documented in [`docs/coinbase-design-tokens.md`](docs/coinbase-design-tokens.md) — DM Mono for metadata, Inter for body, Coinbase brand-blue accents, restrained motion.

A standalone macOS app wrapper lives at `~/projects/crypto-tracker-app/` (not in this repo) — opens the live URL as a new tab in Chrome from the Dock.

---

## Deployment

- **Production host:** Oracle Cloud ARM instance (Ampere A1, 4 vCPU, 23 GB RAM, aarch64) at `192.18.128.170`
- **Process management:** pm2 for `openclaw-gateway` and `crypto-tracker-next` (Next.js prod server on `:3000`); systemd for Caddy; system cron for the 6 daily skill runs
- **HTTPS:** Caddy 2.11 with Let's Encrypt via tls-alpn-01 against `192-18-128-170.nip.io` (HTTP/2 + TLS 1.3, valid through 2026-08-11, auto-renews)
- **Database:** Postgres 16, Unix socket auth via `PGHOST=/var/run/postgresql` (no TCP exposure)
- **Logs:** `~/crypto-tracker/logs/<job>.log` per skill, tail-scanned by `scripts/verify_pipeline.py`
- **Schema:** alembic migrations in `backend/alembic/versions/`

There is no Docker, no Kubernetes, no CI. The deploy procedure is `rsync` to the server, `npm run build` in `frontend/`, `pm2 restart crypto-tracker-next`. The project is single-user, single-machine; multi-tenant is explicitly out of scope.

---

## What's not done

Honest list, not aspirational:

- **v8 synthesis** — cross-entity within-type bucketing ("DTCC + Franklin Templeton" or "DEX volumes + chain fees" titles still slip through). Gated on the pattern recurring across 3+ production runs before investing in a structural fix. The two-pass architecture (enumerate events → select 3–5) is the candidate.
- **Telegram delivery** — bot token provisioned on the server; no skill consumes it yet.
- **Ingestion idempotency on manual re-runs** — `macro` and `predictions` crash with `UniqueViolation` on `uq_raw_signals_url` when re-run the same day. Scheduled morning runs succeed because data is fresh; this is a manual-rerun safety bug only. Fix is `ON CONFLICT (url) DO NOTHING`.
- **Macro gold series** — `GOLDAMGBD228NLBM` and `GOLDPMGBD228NLBM` both 400 from FRED (LBMA fix series discontinued). Need a replacement series ID. The other 9 indicators ingest cleanly.
- **No alerting** beyond log files. Cron-job heartbeat detection is read-only via `verify_pipeline.py`.
- **Category coverage** — v7 can produce zero-themed categories on a light news day. The frontend handles this gracefully with a 7-day fallback per category, but the underlying behavior (model dropping a whole category) is unconstrained.
- **Synthesis SDK migration** — `google-generativeai` is end-of-life per Google; the synthesis skill still uses it with a suppressed `FutureWarning`. New `google-genai` SDK migration pending.

See [`TODO.md`](TODO.md) for the full punch list with gating conditions.

---

## Engineering decisions worth flagging

A few non-obvious choices that aren't visible from the file tree:

**Schema constraint over prompt rules for anti-bucketing.** v1–v3 tried prose-only fixes for the "category bucket" failure mode (model groups DTCC + Franklin + Elliptic under "Institutional Adoption Deepens"). Each prose iteration produced the bug it was trying to forbid — v2 used the bad pattern from its own anti-example as a template; v3 copied "Adoption Deepens" verbatim from the banned-noun list. v4 added a `primary_signal_id` FK column to `brief_themes`: every theme must declare one specific event as its center, enforced by both the validator and the DB. The bucketing pattern that prose couldn't kill collapsed under the schema constraint in one iteration. **Lesson:** when the model's default behavior is the bug, change the shape of the output, not the wording of the prompt.

**Filter by `occurred_at`, not `ingested_at`.** The original synthesis query filtered on `ingested_at >= now() - 24h`. This was wrong: when a new RSS feed source is added that exposes its full archive on first poll, hundreds of months-old articles flood the next day's brief. Switching to `occurred_at` (publication timestamp for news, snapshot timestamp for non-news) made the corpus honest. Snapshot signals all use `occurred_at=now()` so they were unaffected. Caught the day after adding a new feed source — not from monitoring, from reading that day's brief and noticing 2024 articles in the cited sources.

**JSONB for `categories` and `source_types` instead of a join table.** Both fields are 1–2 small string enums per theme. A `theme_categories` join table would be normalized but every read of a theme would need a join + array_agg. JSONB lets the entire theme load as a single row with array access in a single query, which matters because the news/overview page renders 5 themes × 1–2 categories × N corroborators on every page load. Trade-off: lose referential integrity on the category strings, but they're enum-checked in code at every write and the cost of a bad value is one un-styled chip.

**Deterministic TL;DRs for category pages instead of per-page LLM calls.** Each `/news/<category>` page has a one-paragraph TL;DR at the top. Generating it server-side per request would add a Gemini call per page view (cost + latency). Generating it once per brief and storing it would add another model output to validate. Instead, `frontend/src/lib/category-summary.ts` derives the TL;DR from the category's themes deterministically — the highest-conviction theme's primary fact, plus a count. No LLM cost, no caching layer, no surface area for drift.

**Single-pass synthesis + validator over two-pass.** The v7 experiment set included a two-pass design (Exp 4: enumerate 20–40 distinct events → select 3–5). Two-pass would be the most defensible architecture but costs ~2× tokens and quota slots. v7 Exp 1 (the same-event prompt constraint) hit the 80% single-event-themes bar without the two-pass cost, so it shipped. The structural option is parked as the v8 candidate if/when prose-level approaches plateau. **Lesson:** the most defensible architecture is not necessarily the right starting architecture.

---

## Project structure

```
backend/
├── prompts/
│   ├── synthesis_v7.md          ← current production prompt (v7.1)
│   ├── synthesis_v6.md          ← multi-source-type, conviction-5 gate
│   ├── synthesis_v5.md          ← added categories
│   ├── synthesis_v4.md          ← introduced primary_signal_id
│   ├── synthesis_v3.md          ← prose-only iteration (failed)
│   ├── synthesis_v2.md
│   └── synthesis_v1.md
├── models.py                    ← Source, RawSignal, Brief, BriefTheme
├── db.py
├── alembic/                     ← schema migrations
└── tests/                       ← 73 pytest cases
skills/
├── news/SKILL.md                ← RSS ingestion
├── onchain/SKILL.md             ← Defillama
├── sentiment/SKILL.md           ← Fear & Greed
├── macro/SKILL.md               ← FRED
├── predictions/SKILL.md         ← Polymarket
└── synthesize-brief/
    ├── SKILL.md
    └── scripts/synthesize.py    ← sanitize_response, max_conviction_for_counts
frontend/
├── src/
│   ├── app/
│   │   ├── news/                ← overview, history, weekly, [category]
│   │   └── dashboard/
│   ├── components/
│   │   ├── brief/               ← theme-card, conviction-badge, source-popover
│   │   └── dashboard/
│   └── lib/
│       ├── queries.ts           ← all Postgres reads
│       ├── category-summary.ts  ← deterministic TL;DR
│       └── weekly.ts            ← cross-day persistence clustering
└── tests/                       ← 37 Vitest + 9 Playwright specs
scripts/
├── install_system_cron.sh       ← installs the 6 daily jobs
├── run_cron_job.sh              ← wrapper with structured logging
├── verify_pipeline.py           ← heartbeat / health check
├── read_brief.py                ← render the latest brief in the terminal
├── rescore_conviction.py        ← retroactively apply rubric updates
├── seed_sources.py
└── backfill_categories.py
docs/
├── synthesis-evolution.md       ← prompt iteration history (canonical)
└── coinbase-design-tokens.md    ← frontend design system
```

---

## Local development

```bash
# Prereqs: Python 3.12, Node 20, Postgres 16, OpenClaw configured
python3.12 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cp backend/.env.example backend/.env       # add GOOGLE_API_KEY + FRED_API_KEY
createdb crypto_tracker_dev
( cd backend && .venv/bin/alembic upgrade head )
backend/.venv/bin/python scripts/seed_sources.py
( cd frontend && npm install && npm run dev )
```

To register the skills with the local OpenClaw gateway:

```bash
openclaw config set skills.load.extraDirs '["'"$(pwd)"'/skills"]' --strict-json
openclaw skills list | grep crypto-news-ingest   # verify
```

To run the pipeline end-to-end manually:

```bash
openclaw skill run crypto-news-ingest
openclaw skill run onchain-ingest
openclaw skill run sentiment-fear-greed
openclaw skill run macro-fred
openclaw skill run predictions-polymarket
openclaw skill run synthesize-brief
backend/.venv/bin/python scripts/read_brief.py
```

---

## Author

Built by Jackson Geiger as preparation for a Coinbase APM internship starting May 26, 2026. Berkeley Haas business student, no formal CS background. The project's purpose was twofold: build fluency with OpenClaw and agent-platform composition, and ship a concrete artifact that demonstrates production engineering judgment — schema-level fixes over prompt patching, deterministic computation over LLM calls when the LLM adds no signal, and honest assessment of remaining failure modes over feature-list marketing.
