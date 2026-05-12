#!/usr/bin/env bash
# Wrapper for the synthesis script. Resolves paths relative to this file so
# the skill works wherever the repo is cloned.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../../.." &> /dev/null && pwd)"
VENV_PY="$REPO_ROOT/backend/.venv/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
  echo "error: missing venv interpreter at $VENV_PY" >&2
  echo "       run 'python3.12 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt'" >&2
  exit 1
fi

exec "$VENV_PY" "$SCRIPT_DIR/synthesize.py" "$@"
