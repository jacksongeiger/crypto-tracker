#!/usr/bin/env bash
# Install the 6 crypto-tracker pipeline jobs into the system crontab.
#
# Why system cron not OpenClaw cron on the server:
# OpenClaw cron requires `operator.write + operator.admin` scope on the
# device that calls `cron add`. On a single-device server the bootstrap
# device only has `operator.read + operator.pairing`, and the documented
# upgrade path (`openclaw devices approve`) requires a SECOND device
# with `operator.approvals` to grant the upgrade. The original deploy
# spec authorized falling back to system cron when heartbeats prove
# inadequate — this is that case.
#
# Each job writes a line to /home/ubuntu/crypto-tracker/logs/<job>.log
# of the form:
#   2026-05-13 13:30:00Z [OK|FAIL] news in 12s
# `scripts/verify_pipeline.py` reads the tail of each log for status.
#
# Idempotent: the marker block is replaced on each run.

set -euo pipefail
REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &> /dev/null && pwd)"
LOG_DIR="$REPO_ROOT/logs"
RUNNER="$REPO_ROOT/scripts/run_cron_job.sh"
TZ_NAME="America/Los_Angeles"

mkdir -p "$LOG_DIR"

JOBS=(
  "news|30 6 * * *|skills/news/scripts/run.sh"
  "onchain|35 6 * * *|skills/onchain/scripts/run.sh"
  "sentiment|35 6 * * *|skills/sentiment/scripts/run.sh"
  "macro|40 6 * * *|skills/macro/scripts/run.sh"
  "predictions|40 6 * * *|skills/predictions/scripts/run.sh"
  "synthesis|50 6 * * *|skills/synthesize-brief/scripts/run.sh"
)

# Build the marker block
BLOCK=$(printf '%s\n' "# >>> crypto-tracker cron (managed by install_system_cron.sh) >>>" "CRON_TZ=$TZ_NAME")
for entry in "${JOBS[@]}"; do
  IFS="|" read -r name sched script <<< "$entry"
  BLOCK+=$'\n'"$sched $RUNNER $name $REPO_ROOT/$script"
done
BLOCK+=$'\n# <<< crypto-tracker cron <<<'

# Pull existing crontab, strip any prior crypto-tracker block, append fresh
TMP=$(mktemp)
crontab -l 2>/dev/null | awk '
  /^# >>> crypto-tracker cron/ {skip=1; next}
  /^# <<< crypto-tracker cron/ {skip=0; next}
  !skip {print}
' > "$TMP"
{ echo; echo "$BLOCK"; } >> "$TMP"
crontab "$TMP"
rm "$TMP"

echo "→ installed 6 jobs at:"
printf "  %s\n" "30 6 * * * (news)" "35 6 * * * (onchain, sentiment)" \
                "40 6 * * * (macro, predictions)" "50 6 * * * (synthesis)"
echo "→ timezone: $TZ_NAME"
echo "→ logs: $LOG_DIR/<job>.log"
echo
echo "Verify with:"
echo "  crontab -l | sed -n '/crypto-tracker cron/,/cron </p'"
echo "  scripts/verify_pipeline.py"
