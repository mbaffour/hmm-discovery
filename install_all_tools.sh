#!/usr/bin/env bash
###############################################################################
# install_all_tools.sh
#
# One-shot installer for the COMPLETE HMM Discovery toolchain, verified to
# produce a fully-working app (every pipeline function + every analysis tab).
#
# It creates / updates two conda environments:
#   • hmm_env       — the app runtime (Python 3.x, Shiny, all fast binaries)
#   • meme-tools    — a Python 3.11 helper env for tools that cannot install
#                     alongside a very new Python (MEME suite, clinker,
#                     ghostscript). Their binaries are symlinked into hmm_env.
#
# After running this, `find_tool()` in pipeline/utils.py resolves all of:
#   mafft trimal clustalo hmmbuild hmmsearch iqtree prodigal cd-hit mmseqs
#   meme fimo clinker gs    (+ pygenomeviz as a Python package)
#
# Usage:
#   bash install_all_tools.sh                 # uses default conda
#   CONDA=/path/to/conda bash install_all_tools.sh
###############################################################################
set -euo pipefail

CONDA="${CONDA:-conda}"
if ! command -v "$CONDA" >/dev/null 2>&1; then
    for c in "$HOME/miniforge3/bin/conda" "$HOME/miniconda3/bin/conda" \
             "$HOME/anaconda3/bin/conda" /opt/miniconda3/bin/conda; do
        [ -x "$c" ] && CONDA="$c" && break
    done
fi
echo "Using conda: $CONDA"

HMM_ENV="hmm_env"
HELPER_ENV="meme-tools"

env_prefix() { "$CONDA" env list | awk -v n="$1" '$1==n {print $NF}'; }

# ---------------------------------------------------------------------------
# 1. Core runtime env (hmm_env) — fast C/C++ binaries + Python app deps
# ---------------------------------------------------------------------------
echo ""
echo "=== [1/4] Core bioinformatics binaries → $HMM_ENV ==="
"$CONDA" create -n "$HMM_ENV" -y python=3.11 2>/dev/null || \
    echo "  ($HMM_ENV already exists — updating)"

# These install cleanly regardless of Python version
"$CONDA" install -n "$HMM_ENV" -y -c bioconda -c conda-forge \
    hmmer mafft trimal clustalo iqtree prodigal cd-hit mmseqs2 \
    diamond foldseek

# ---------------------------------------------------------------------------
# 2. Python app dependencies (into hmm_env)
# ---------------------------------------------------------------------------
echo ""
echo "=== [2/4] Python app dependencies → $HMM_ENV ==="
HMM_PREFIX="$(env_prefix "$HMM_ENV")"
HMM_PY="$HMM_PREFIX/bin/python"
"$HMM_PY" -m pip install --quiet --upgrade pip
"$HMM_PY" -m pip install --quiet \
	    "shiny>=1.5" shinyswatch plotly jinja2 faicons aiohttp aiofiles \
	    "pandas>=2.0" "numpy>=1.24" scipy matplotlib openpyxl biopython \
	    "urllib3<2" "toytree>=3.0.0,<3.0.11" toyplot pygenomeviz kaleido

# ---------------------------------------------------------------------------
# 3. Helper env for MEME / clinker / ghostscript (need Python 3.11 stack)
# ---------------------------------------------------------------------------
echo ""
echo "=== [3/4] MEME suite + clinker + ghostscript → $HELPER_ENV ==="
"$CONDA" create -n "$HELPER_ENV" -y python=3.11 2>/dev/null || \
    echo "  ($HELPER_ENV already exists — updating)"
"$CONDA" install -n "$HELPER_ENV" -y -c bioconda -c conda-forge \
    meme ghostscript pip
HELPER_PREFIX="$(env_prefix "$HELPER_ENV")"
"$HELPER_PREFIX/bin/pip" install --quiet "git+https://github.com/gamcil/clinker.git" || \
    echo "  (clinker install via git failed — synteny clinker view will be unavailable)"

# ---------------------------------------------------------------------------
# 4. Symlink helper-env binaries into hmm_env so find_tool() resolves them
# ---------------------------------------------------------------------------
echo ""
echo "=== [4/4] Linking helper binaries into $HMM_ENV ==="
for tool in meme fimo mast meme-chip ama gs clinker; do
    src="$HELPER_PREFIX/bin/$tool"
    dst="$HMM_PREFIX/bin/$tool"
    if [ -e "$src" ] && [ ! -e "$dst" ]; then
        ln -sf "$src" "$dst" && echo "  linked $tool"
    fi
done

# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
echo ""
echo "=== Verification ==="
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$HMM_PY" - "$SCRIPT_DIR" <<'PYEOF'
import sys, importlib.util
sys.path.insert(0, sys.argv[1])
from pipeline.utils import ensure_tools_on_path, find_tool
ensure_tools_on_path()
tools = ["mafft","trimal","clustalo","hmmbuild","hmmsearch","iqtree",
         "prodigal","cd-hit","mmseqs","diamond","foldseek",
         "meme","fimo","clinker","gs"]
missing = [t for t in tools if not find_tool(t)]
for t in tools:
    print(f"  {'OK ' if find_tool(t) else 'MISS'}  {t}")
for pkg in ["pygenomeviz","toytree","toyplot","scipy","kaleido","shiny","plotly","Bio"]:
    ok = importlib.util.find_spec(pkg) is not None
    print(f"  {'OK ' if ok else 'MISS'}  {pkg} (py)")
print()
print("ALL TOOLS PRESENT" if not missing else f"MISSING: {missing}")
PYEOF

echo ""
echo "Done. Launch the app with:"
echo "  $HMM_PREFIX/bin/shiny run \"$SCRIPT_DIR/app.py\" --port 8080"
