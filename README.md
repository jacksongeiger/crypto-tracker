# crypto-tracker

Anti-noise daily crypto context brief.

Status: WIP

## Setup

### Backend (FastAPI + Postgres)

Requires Python 3.12 and Postgres 16 running locally.

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cp backend/.env.example backend/.env   # adjust DATABASE_URL if not localhost
createdb crypto_tracker_dev
( cd backend && .venv/bin/alembic upgrade head )
backend/.venv/bin/python scripts/seed_sources.py
```

### OpenClaw skill registration (per machine)

Skills under `/skills` are not auto-discovered — each machine must register
this directory once with the local OpenClaw gateway:

```bash
openclaw config set skills.load.extraDirs \
  '["'"$(pwd)"'/skills"]' --strict-json
openclaw skills list | grep crypto-news-ingest   # verify
```

The path must be absolute. `config set` overwrites `skills.load.extraDirs`
wholesale — if you already have other extra dirs configured, fetch the
current value first (`openclaw config get skills.load.extraDirs`) and pass
the merged list.

The skills watcher picks up `SKILL.md` files automatically; no gateway
restart needed.

## Automation

The full pipeline runs daily via OpenClaw cron (Gateway-backed
scheduler). Six jobs fire each morning in America/Los_Angeles time:

| Time (PT) | Job name                       | What runs                            |
| --------- | ------------------------------ | ------------------------------------ |
| 06:30     | `crypto-tracker-news`          | `skills/news/scripts/run.sh`         |
| 06:35     | `crypto-tracker-onchain`       | `skills/onchain/scripts/run.sh`      |
| 06:35     | `crypto-tracker-sentiment`     | `skills/sentiment/scripts/run.sh`    |
| 06:40     | `crypto-tracker-macro`         | `skills/macro/scripts/run.sh`        |
| 06:40     | `crypto-tracker-predictions`   | `skills/predictions/scripts/run.sh`  |
| 06:50     | `crypto-tracker-synthesis`     | `skills/synthesize-brief/scripts/run.sh` |

Each job runs as an **isolated agent turn** (`--session isolated`)
with the `exec` tool restricted to its single shell command. The
agent dispatch costs ~1 Gemini Flash request per fire (≤7/day total),
trivial against free-tier quota.

### Install

The CLI device needs `operator.write` scope. If not already approved:

```bash
openclaw devices list
openclaw devices approve <your-device-id>   # one-time
```

Then install all 6 jobs:

```bash
bash scripts/install_cron_jobs.sh
```

The script is **not** idempotent — re-running creates duplicates.
Remove stale jobs first with `openclaw cron rm <jobId>` if reinstalling.

### Status

Pipeline health summary (cron registration, last-run timestamps, today's
signals + brief):

```bash
backend/.venv/bin/python scripts/verify_pipeline.py
# Add --json for machine-readable output.
```

Native OpenClaw commands:

```bash
openclaw cron list              # all registered jobs
openclaw cron status            # scheduler health
openclaw cron show <jobId>      # job details + last run
openclaw cron runs --id <jobId> --limit 10   # JSONL run history
```

### Manual trigger

Force a job to run now (debug):

```bash
openclaw cron run <jobId>           # force
openclaw cron run <jobId> --due     # only if due
```

Or invoke the wrapper script directly, bypassing cron entirely:

```bash
skills/news/scripts/run.sh
```

### Disable / re-enable

```bash
openclaw cron disable <jobId>
openclaw cron enable  <jobId>
```

Or globally: set `cron.enabled: false` in `~/.openclaw/openclaw.json`,
or `OPENCLAW_SKIP_CRON=1` in the Gateway's environment.

### Logs

Run history persists to `~/.openclaw/cron/runs.jsonl` (auto-rotated;
defaults: `runLog.maxBytes=2mb`, `runLog.keepLines=2000`). View via
`openclaw cron runs --id <jobId>` rather than reading the file
directly.

### Known limitation — laptop sleep

Cron only fires while the Gateway is running. If the laptop is asleep
at 06:30 PT, **the morning runs are skipped** — they do *not* catch up
on wake. This is the central reason a future deployment to a
permanently-on host (Oracle ARM, a Mac mini, etc.) is on the roadmap.
