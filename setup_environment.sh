#!/usr/bin/env bash
# =============================================================================
# setup_environment.sh — Create and populate the HMM Discovery conda environment
#
# Usage:
#   bash setup_environment.sh           # create/update hmm_env
#   bash setup_environment.sh --check   # check tools only, no install
#   bash setup_environment.sh --name myenv  # use a different env name
#
# What this does:
#   1. Detects conda / mamba
#   2. Creates the hmm_env conda environment (or updates it)
#   3. Installs all required and optional bioinformatics tools
#   4. Installs Python packages
#   5. Prints a tool availability report
# =============================================================================

set -euo pipefail

ENV_NAME="hmm_env"
CHECK_ONLY=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---- Parse args ----------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case $1 in
        --check)   CHECK_ONLY=1 ;;
        --name)    ENV_NAME="$2"; shift ;;
        *)         echo "Unknown arg: $1"; exit 1 ;;
    esac
    shift
done

# ---- Colors ------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'

ok()   { echo -e "${GREEN}  ✓${NC}  $*"; }
warn() { echo -e "${YELLOW}  ⚠${NC}  $*"; }
fail() { echo -e "${RED}  ✗${NC}  $*"; }
info() { echo -e "${BLUE}  →${NC}  $*"; }

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   HMM Discovery App — Environment Setup          ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ---- 1. Find conda / mamba ---------------------------------------------------
info "Detecting package manager..."

CONDA_CMD=""
for cmd in mamba conda; do
    if command -v "$cmd" &>/dev/null; then
        CONDA_CMD="$cmd"
        ok "Found: $cmd at $(command -v "$cmd")"
        break
    fi
done

# Also try common install paths
if [[ -z "$CONDA_CMD" ]]; then
    for base in "$HOME/miniforge3" "$HOME/miniconda3" "$HOME/anaconda3" \
                "/opt/anaconda3" "/opt/miniconda3"; do
        for bin in "$base/bin/mamba" "$base/bin/conda"; do
            if [[ -x "$bin" ]]; then
                CONDA_CMD="$bin"
                ok "Found: $bin"
                break 2
            fi
        done
    done
fi

if [[ -z "$CONDA_CMD" ]]; then
    fail "conda/mamba not found."
    echo ""
    echo "  Install miniforge (recommended):"
    echo "    curl -L https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh | bash"
    echo ""
    exit 1
fi

if [[ $CHECK_ONLY -eq 1 ]]; then
    echo ""
    info "CHECK_ONLY mode — skipping environment creation."
else
    # ---- 2. Create / update environment --------------------------------------
    echo ""
    info "Setting up conda environment: $ENV_NAME ..."

    if "$CONDA_CMD" env list | grep -q "^${ENV_NAME} "; then
        ok "Environment '$ENV_NAME' already exists — updating..."
    else
        info "Creating new environment '$ENV_NAME' with Python 3.11..."
        "$CONDA_CMD" create -n "$ENV_NAME" python=3.11 -y --quiet
        ok "Environment created."
    fi

    ENV_PYTHON=$("$CONDA_CMD" run -n "$ENV_NAME" which python 2>/dev/null || echo "")
    if [[ -z "$ENV_PYTHON" ]]; then
        ENV_PREFIX=$("$CONDA_CMD" env list | grep "^${ENV_NAME}" | awk '{print $NF}')
        ENV_PYTHON="$ENV_PREFIX/bin/python"
    fi

    # ---- 3. Install bioinformatics tools ------------------------------------
    echo ""
    info "Installing bioinformatics tools (required)..."

    "$CONDA_CMD" install -n "$ENV_NAME" -c bioconda -c conda-forge -y --quiet \
        hmmer \
        mafft \
        trimal \
        2>&1 | tail -3 || warn "Some required tools may have failed to install."

    ok "Required tools installed: hmmbuild, hmmsearch, mafft, trimal"

    echo ""
    info "Installing bioinformatics tools (optional)..."

    # Install optional tools one by one so failure of one doesn't block others
    OPTIONAL_TOOLS=(
        "iqtree:iqtree2"
        "clustalo:clustalo"
        "prodigal:prodigal"
        "cd-hit:cd-hit"
        "mmseqs2:mmseqs2"
        "diamond:diamond"
        "foldseek:foldseek"
        "ghostscript:ghostscript"
        "meme:meme"
    )

    # Install synteny visualization tools via pip (after conda tools)
    echo ""
    info "Installing synteny visualization tools (optional)..."
    if [[ -x "$ENV_PYTHON" ]]; then
        # clinker — pairwise gene cluster comparison
        if "$ENV_PYTHON" -m pip install --quiet "clinker>=0.0.28" 2>/dev/null; then
            ok "Optional: clinker installed"
        else
            warn "Optional: clinker not available (app will work without it)"
        fi
        # pyGenomeViz — Python genome visualization library
        if "$ENV_PYTHON" -m pip install --quiet "pygenomeviz>=0.4.0" 2>/dev/null; then
            ok "Optional: pyGenomeViz installed"
        else
            warn "Optional: pyGenomeViz not available (app will work without it)"
        fi
    fi
    # EasyFig: standalone tool — not on pip; user must install manually
    warn "EasyFig: install manually from https://github.com/mjsull/Easyfig"
    warn "  After install, add 'easyfig' or 'Easyfig.py' to your PATH."

    for entry in "${OPTIONAL_TOOLS[@]}"; do
        name="${entry%%:*}"
        pkg="${entry##*:}"
        if "$CONDA_CMD" install -n "$ENV_NAME" -c bioconda -c conda-forge "$pkg" -y --quiet 2>/dev/null; then
            ok "Optional: $name installed"
        else
            warn "Optional: $name not available (app will work without it)"
        fi
    done

    # ---- 4. Install Python packages -----------------------------------------
    echo ""
    info "Installing Python packages..."

    if [[ -x "$ENV_PYTHON" ]]; then
        "$ENV_PYTHON" -m ensurepip --upgrade --quiet 2>/dev/null || true
        "$ENV_PYTHON" -m pip install --quiet --upgrade pip 2>/dev/null

        REQUIREMENTS="$SCRIPT_DIR/requirements.txt"
        if [[ -f "$REQUIREMENTS" ]]; then
            "$ENV_PYTHON" -m pip install --quiet -r "$REQUIREMENTS"
            ok "Python packages installed from requirements.txt"
        else
            "$ENV_PYTHON" -m pip install --quiet \
                "shiny>=1.5.0" "shinyswatch>=0.10.0" \
                "plotly>=5.0.0" "jinja2>=3.0.0" "faicons>=0.2.0" \
	                "aiohttp>=3.9.0" "aiofiles>=23.0.0" \
	                "pandas>=2.0.0" "numpy>=1.24.0" "scipy>=1.10.0" \
	                "matplotlib>=3.7.0" "biopython>=1.81" "openpyxl>=3.1.0" \
	                "urllib3<2" "toytree>=3.0.0,<3.0.11" "toyplot>=1.0.0" "pygenomeviz>=0.4.0" \
	                "kaleido>=0.2.1"
            ok "Python packages installed."
        fi
    else
        warn "Could not find Python in env; skipping pip install."
    fi
fi

# ---- 5. Tool availability check ---------------------------------------------
echo ""
echo "──────────────────────────────────────────────────"
info "Tool availability check for environment: $ENV_NAME"
echo "──────────────────────────────────────────────────"

# Find the env bin dir
ENV_BIN=""
for prefix_candidate in \
    "$("$CONDA_CMD" env list 2>/dev/null | grep "^${ENV_NAME} " | awk '{print $NF}')" \
    "$HOME/miniforge3/envs/$ENV_NAME" \
    "$HOME/miniconda3/envs/$ENV_NAME" \
    "$HOME/anaconda3/envs/$ENV_NAME"; do
    if [[ -d "$prefix_candidate/bin" ]]; then
        ENV_BIN="$prefix_candidate/bin"
        break
    fi
done

declare -A TOOLS
TOOLS=(
    ["hmmbuild"]="HMMER build (REQUIRED)"
    ["hmmsearch"]="HMMER search (REQUIRED)"
    ["mafft"]="Multiple alignment (REQUIRED)"
    ["trimal"]="Alignment trimming (REQUIRED)"
    ["iqtree2"]="Phylogenetics IQ-TREE (optional)"
    ["iqtree"]="Phylogenetics IQ-TREE (optional)"
    ["prodigal"]="ORF prediction (optional)"
    ["cd-hit"]="Sequence clustering (optional)"
    ["mmseqs"]="MMseqs2 clustering (optional)"
    ["diamond"]="DIAMOND BLAST (optional)"
    ["meme"]="Motif discovery (optional)"
    ["fimo"]="Motif scanning (optional)"
    ["clinker"]="Synteny: clinker (optional)"
    ["easyfig"]="Synteny: EasyFig (optional)"
    ["gs"]="Ghostscript figure export (optional)"
    ["foldseek"]="Structural similarity (optional)"
    ["phobius.pl"]="TM/signal peptide, manual/licensed (optional)"
    ["tmhmm"]="TM topology, manual/licensed (optional)"
)

REQUIRED=("hmmbuild" "hmmsearch" "mafft" "trimal")
MISSING_REQUIRED=()

for tool in "${!TOOLS[@]}"; do
    desc="${TOOLS[$tool]}"
    found_path=""
    if [[ -n "$ENV_BIN" ]] && [[ -x "$ENV_BIN/$tool" ]]; then
        found_path="$ENV_BIN/$tool"
    elif command -v "$tool" &>/dev/null; then
        found_path="$(command -v "$tool")"
    fi

    if [[ -n "$found_path" ]]; then
        ok "$tool — $desc"
    else
        if [[ " ${REQUIRED[*]} " =~ " $tool " ]]; then
            fail "$tool — $desc  ← REQUIRED, not found!"
            MISSING_REQUIRED+=("$tool")
        else
            warn "$tool — $desc  (not installed)"
        fi
    fi
done

echo ""
if [[ ${#MISSING_REQUIRED[@]} -gt 0 ]]; then
    fail "Missing required tools: ${MISSING_REQUIRED[*]}"
    echo ""
    echo "  To install manually:"
    echo "    conda install -n $ENV_NAME -c bioconda hmmer mafft trimal"
    exit 1
else
    ok "All required tools are available."
fi

# ---- 6. Activation instructions ---------------------------------------------
echo ""
echo "──────────────────────────────────────────────────"
info "To start the HMM Discovery App:"
echo ""
echo "    conda activate $ENV_NAME"
echo "    cd $(dirname "$SCRIPT_DIR")"
echo "    shiny run scripts/hmm_discovery_app/app.py --port 8080 --reload"
echo ""
echo "  Or use the helper script (if present):"
echo "    source activate_hmm.sh"
echo "──────────────────────────────────────────────────"
echo ""
ok "Environment setup complete!"
echo ""
