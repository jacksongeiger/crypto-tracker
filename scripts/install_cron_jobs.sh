#!/usr/bin/env bash
# Install the 6 crypto-tracker cron jobs into the local OpenClaw gateway.
#
# Idempotent-ish: re-running adds duplicate jobs (OpenClaw cron has no
# upsert). If you need to re-install, run `openclaw cron rm <id>` first
# for each one, or `openclaw cron list` to find them.
#
# Requires the calling device to have operator.write scope on the
# Gateway. If you see "scope upgrade pending approval", run:
#   openclaw devices list
#   openclaw devices approve <device-id>

set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &> /dev/null && pwd)"
TZ_NAME="America/Los_Angeles"

# Job spec: name | cron expression (5-field) | wrapper script path (relative to repo root)
JOBS=(
  "crypto-tracker-news|30 6 * * *|skills/news/scripts/run.sh"
  "crypto-tracker-onchain|35 6 * * *|skills/onchain/scripts/run.sh"
  "crypto-tracker-sentiment|35 6 * * *|skills/sentiment/scripts/run.sh"
  "crypto-tracker-macro|40 6 * * *|skills/macro/scripts/run.sh"
  "crypto-tracker-predictions|40 6 * * *|skills/predictions/scripts/run.sh"
  "crypto-tracker-synthesis|50 6 * * *|skills/synthesize-brief/scripts/run.sh"
)

for entry in "${JOBS[@]}"; do
  IFS="|" read -r name sched script <<< "$entry"
  abs_script="$REPO_ROOT/$script"
  msg="Execute the bash command: $abs_script
Report the exit code and the last 15 lines of combined stdout/stderr.
Keep the total reply under 30 lines. Do not edit any files, do not run
any other commands, only this one shell invocation."
  echo "→ adding $name  ($sched $TZ_NAME)"
  openclaw cron add \
    --name "$name" \
    --cron "$sched" \
    --tz "$TZ_NAME" \
    --session isolated \
    --message "$msg" \
    --tools "exec" \
    --model "google/gemini-2.5-flash" \
    --timeout-seconds 240 \
    --no-deliver \
    --exact 2>&1 | grep -vE "^(Config:|Bind:|Source:|Gateway target:|No --agent specified)" | sed 's/^/    /' || true
done

echo
echo "Done. Verify with:  openclaw cron list"
