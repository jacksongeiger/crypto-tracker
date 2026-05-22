#!/usr/bin/env bash
# Wrapper for scripts/daily_digest.py — invoked by run_cron_job.sh at 6:30 PT.
# Uses the project venv so SendGrid + SQLAlchemy resolve identically to dev.
set -euo pipefail
REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &> /dev/null && pwd)"
exec "$REPO_ROOT/backend/.venv/bin/python" "$REPO_ROOT/scripts/daily_digest.py"
