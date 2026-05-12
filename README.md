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
