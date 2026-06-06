#!/usr/bin/env bash
# HMM Discovery App — launcher
# Activates the hmm_env conda environment and starts the Shiny server.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-8081}"
APP="$SCRIPT_DIR/app.py"

# Try to find the conda-env Shiny executable
SHINY="$(conda run -n hmm_env which shiny 2>/dev/null)" \
  || SHINY="$HOME/miniforge3/envs/hmm_env/bin/shiny"

if [ ! -f "$SHINY" ]; then
  echo "ERROR: shiny not found. Run: bash setup_environment.sh"
  exit 1
fi

echo "──────────────────────────────────────"
echo "  🧬 HMM Discovery App"
echo "  http://127.0.0.1:$PORT"
echo "──────────────────────────────────────"
sleep 2 && open "http://127.0.0.1:$PORT" >/dev/null 2>&1 &
"$SHINY" run "$APP" --port "$PORT" --host 127.0.0.1
