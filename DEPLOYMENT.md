# HMM Discovery — Deployment Guide

A Shiny-for-Python web application for profile-HMM-based protein family
discovery. Works for any protein family (phage, bacterial, eukaryotic).

---

## 1. Install

Requires a working `conda` (miniforge / miniconda / anaconda).

```bash
cd hmm-discovery
bash install_all_tools.sh
```

This creates two conda environments:

| Env          | Purpose                                                        |
|--------------|---------------------------------------------------------------|
| `hmm_env`    | App runtime + all fast binaries (mafft, hmmer, iqtree, …)      |
| `meme-tools` | Python-3.11 helper for MEME, clinker, ghostscript (symlinked)  |

The script finishes with a verification table — every tool should read `OK`.

### Tools installed

**Required:** mafft, trimal, hmmbuild, hmmsearch
**Optional (all installed):** clustalo, iqtree, prodigal, cd-hit, mmseqs2,
meme, fimo, clinker, ghostscript (`gs`), pygenomeviz (Python pkg)

**Not installed by default** (licensed / very large — graceful fallback in app):
foldseek, phobius, tmhmm, diamond.

---

## 2. Launch

```bash
~/miniforge3/envs/hmm_env/bin/shiny run app.py --port 8081 --host 127.0.0.1
```

Then open http://127.0.0.1:8081

For production, put it behind a reverse proxy (nginx) and run with
`shiny run --host 0.0.0.0`. For multiple concurrent users, run several
workers behind the proxy (each Shiny process is single-session-stateful per
websocket but the app keeps all state on disk per project folder).

---

## 3. How it works

Each **project** is a folder on disk. All inputs, intermediates, and outputs
live there, and pipeline progress is tracked in `.pipeline_state.json`, so a
project can be closed and resumed at any time.

The workflow is 9 steps, shown as tabs:

1. **Input** — load seed FASTA (protein or nucleotide; ORF prediction for NT)
2. **MSA** — MAFFT/Clustal Omega alignment + trimAl trimming
3. **HMM Build** — hmmbuild profile + logo + seed self-recovery test
4. **Search** — hmmsearch vs local / streamed databases (6-frame for NT DBs), plus optional Pfam/VOGDB hmmscan annotation
5. **Calibrate** — score thresholds vs positive/negative controls
6. **Iterate** — expand seeds with high-confidence hits, rebuild, repeat
7. **Results** — interactive hits table, score/database/tier charts
8. **Analysis** — synteny, taxonomy, IQ-TREE phylogeny, presence/absence
   matrix, CD-HIT/MMseqs clustering, MEME/FIMO motifs, structure
9. **Export** — TSVs, FASTAs, multi-format figures (PNG/SVG/PDF), methods
   paragraph, reproducibility JSON, and a one-click ZIP of everything

The sidebar shows live step completion and supports creating new projects,
loading recent projects, saving session notes, and resetting a project.

---

## 4. Verifying a deployment

Run the bundled checks against any project folder:

```bash
~/miniforge3/envs/hmm_env/bin/python - <<'PY'
import sys; sys.path.insert(0, ".")
from pipeline.utils import ensure_tools_on_path, find_tool
ensure_tools_on_path()
need = ["mafft","trimal","hmmbuild","hmmsearch","iqtree","clustalo",
        "prodigal","cd-hit","mmseqs","meme","fimo","clinker","gs"]
missing = [t for t in need if not find_tool(t)]
print("All tools present" if not missing else f"MISSING: {missing}")
PY
```

---

## 5. Notes

* The app augments `PATH` at startup (`ensure_tools_on_path`) so in-process
  libraries (toyplot→ghostscript, pygenomeviz) find the conda binaries.
* PNG phylogenetic-tree export needs `gs`; SVG always works without it.
* Streaming database search (INPHARED, RefSeq, SwissProt) needs internet but
  no local disk — data streams through the search pipeline.
* VOGDB VFAM is the preferred viral ortholog annotation layer. It downloads
  VOGDB release 230 HMMs and annotations, runs `hmmpress`, then scans hit
  proteins with `hmmscan`.
* Acknowledgements and run-specific citation guidance live in
  `ACKNOWLEDGEMENTS.md`, `CITATION.cff`, `reports/METHODS_TEXT.txt`, and
  `reports/reproducibility.json`.
* Synteny neighbourhood fetching uses NCBI Entrez (needs internet + an email
  address) or local GenBank files.
