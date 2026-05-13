#!/usr/bin/env bash
# Wrapper used by `install_system_cron.sh`-generated crontab entries.
#
# Usage:   run_cron_job.sh <job-name> <path-to-skill-wrapper>
#
# Runs the skill wrapper, captures combined stdout/stderr to a job-specific
# log, and appends a single status line to the same log so verify_pipeline.py
# can read run status from `tail -n 1 <log>`.
set -euo pipefail

JOB_NAME=${1:?usage: run_cron_job.sh <job> <script>}
SCRIPT=${2:?usage: run_cron_job.sh <job> <script>}
REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &> /dev/null && pwd)"
LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/${JOB_NAME}.log"

start_ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
start_epoch=$(date +%s)

{
  echo
  echo "===== ${JOB_NAME} run start ${start_ts} ====="
} >> "$LOG"

set +e
"$SCRIPT" >> "$LOG" 2>&1
rc=$?
set -e

end_epoch=$(date +%s)
dur=$((end_epoch - start_epoch))
status=$([[ $rc -eq 0 ]] && echo "OK" || echo "FAIL")

# Status line at the end — verify_pipeline.py greps for these lines.
printf "STATUS %s %s rc=%d dur=%ds\n" "$start_ts" "${status} ${JOB_NAME}" "$rc" "$dur" >> "$LOG"

# Truncate logs over 10 MB (keep last ~5 MB).
if [[ -f "$LOG" && $(stat -c %s "$LOG" 2>/dev/null || stat -f %z "$LOG") -gt 10485760 ]]; then
  tmp=$(mktemp)
  tail -c 5242880 "$LOG" > "$tmp"
  mv "$tmp" "$LOG"
fi

exit "$rc"
