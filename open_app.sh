#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# open_app.sh  —  Start the HMM Discovery App
#
# Usage:
#   bash open_app.sh          # default port 8081
#   bash open_app.sh 8888     # custom port
# ─────────────────────────────────────────────────────────────

PORT="${1:-8081}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONDA_ENV="hmm_env"

# ── Locate conda ──────────────────────────────────────────────
if [ -f "$HOME/miniforge3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniforge3/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
else
    echo "❌  Could not find conda. Please activate hmm_env manually and run:"
    echo "    shiny run \"$SCRIPT_DIR/app.py\" --port $PORT"
    exit 1
fi

# ── Activate environment ──────────────────────────────────────
conda activate "$CONDA_ENV" 2>/dev/null || {
    echo "❌  Conda environment '$CONDA_ENV' not found."
    echo "    Create it with:  conda create -n $CONDA_ENV python=3.11"
    echo "    Then run:        bash setup_environment.sh"
    exit 1
}

echo ""
echo "🧬  HMM Discovery App"
echo "    Project dir : $SCRIPT_DIR"
echo "    URL         : http://localhost:$PORT"
echo "    Stop with   : Ctrl+C"
echo ""

# ── Open browser after a short delay ─────────────────────────
sleep 2 && open "http://localhost:$PORT" &

# ── Start Shiny server ────────────────────────────────────────
shiny run "$SCRIPT_DIR/app.py" --port "$PORT" --host 127.0.0.1
