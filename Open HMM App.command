#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# "Open HMM App.command"  —  macOS double-click launcher
#
# 1. Double-click this file in Finder to open the app.
#    (First time: right-click → Open to bypass Gatekeeper)
# 2. A Terminal window opens, the server starts, and your browser
#    opens automatically at http://localhost:8081.
# ─────────────────────────────────────────────────────────────

PORT=8081
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONDA_ENV="hmm_env"

# ── Locate conda ──────────────────────────────────────────────
for candidate in \
    "$HOME/miniforge3/etc/profile.d/conda.sh" \
    "$HOME/anaconda3/etc/profile.d/conda.sh" \
    "$HOME/miniconda3/etc/profile.d/conda.sh" \
    "/opt/homebrew/Caskroom/miniforge/base/etc/profile.d/conda.sh"
do
    if [ -f "$candidate" ]; then
        source "$candidate"
        break
    fi
done

# ── Activate environment ──────────────────────────────────────
conda activate "$CONDA_ENV" 2>/dev/null || {
    osascript -e 'display alert "HMM App" message "Conda environment '"'"'hmm_env'"'"' not found.\nRun setup_environment.sh first." as critical'
    exit 1
}

echo ""
echo "🧬  HMM Discovery App"
echo "    URL : http://localhost:$PORT"
echo "    Stop: close this window (Ctrl+C)"
echo ""

# ── Open browser after a short delay ─────────────────────────
sleep 2 && open "http://localhost:$PORT" &

# ── Start Shiny server ────────────────────────────────────────
shiny run "$SCRIPT_DIR/app.py" --port "$PORT" --host 127.0.0.1
