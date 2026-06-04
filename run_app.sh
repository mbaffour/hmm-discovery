#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8081}"
PYTHON="${PYTHON:-}"

if [[ -z "$PYTHON" ]]; then
  if command -v python >/dev/null 2>&1; then
    PYTHON="python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
  else
    echo "Could not find python or python3 on PATH. Activate the hmm-discovery environment and try again." >&2
    exit 127
  fi
fi

"$PYTHON" -m shiny run app.py --host "$HOST" --port "$PORT"
