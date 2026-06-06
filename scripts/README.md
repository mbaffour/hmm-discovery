# HMM Discovery — Command-Line Pipeline

This folder contains the **command-line version** of the HMM Discovery workflow:
a chain of small, self-documenting scripts that take you from a handful of seed
protein sequences to a finished, publication-ready report.

These scripts call the **exact same** `pipeline/*` code as the Shiny web app — so
the science is identical. Use the app to explore interactively; use these scripts
when you want to:

- run on an **HPC cluster** or in a **cron / batch** job,
- **automate** or integrate the pipeline into your own scripts,
- produce an exact, copy-pasteable **Methods section** for a paper,
- run a step **headless** on a server with no browser.

> New here? The fastest way in is the interactive tour:
> ```bash
> python3 scripts/guide.py
> ```
> It explains each step, shows the command, and offers to run it for you.

---

## Table of contents

1. [Prerequisites](#prerequisites)
2. [Quick start](#quick-start)
3. [The interactive experience](#the-interactive-experience)
4. [Pipeline at a glance](#pipeline-at-a-glance)
5. [Per-step summary](#per-step-summary)
6. [Full flag & I/O reference](#full-flag--io-reference)
7. [Batch, HPC & Methods extraction](#batch-hpc--methods-extraction)
8. [Shared flags](#shared-flags-every-script)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

The scripts are pure Python (3.9+) but they drive external bioinformatics tools.
The simplest way to get everything is the project conda/mamba environment:

```bash
mamba env create -f environment.yml      # or: conda env create -f environment.yml
conda activate hmm-discovery
# or run the helper:
bash setup_environment.sh
```

Tools used (each only when you run the step that needs it):

| Tool | Used by | Step |
|------|---------|------|
| HMMER (`hmmbuild`, `hmmsearch`) | core search | 02, 03, 05, 06 |
| MAFFT / Clustal Omega | alignment | 01, 06 |
| trimAl | alignment trimming (optional) | 01 |
| IQ-TREE 2 | phylogeny | 09 |
| CD-HIT / MMseqs2 | clustering | 11 |
| MEME / FIMO | motif discovery | 12 |
| clinker / pyGenomeViz | synteny figures (optional) | 07 |
| Phobius / TMHMM | TM topology (optional) | 13 |

> You don't have to add the conda `bin/` directory to your `PATH` by hand — the
> scripts call `ensure_tools_on_path()` on startup, which finds tools inside the
> active conda environment automatically.

---

## Quick start

### Option A — run everything with one command

```bash
python3 scripts/run_pipeline.py
```

Run in a terminal, this **interviews you** for the seed file, database(s), and
project directory, shows the plan, and runs all 14 steps. Prefer to be explicit?

```bash
python3 scripts/run_pipeline.py \
  --seeds my_seeds.faa \
  --db databases/inphared.faa \
  --proj-dir my_project/ \
  --email you@uni.edu \
  --cpu 8 --yes
```

### Option B — the minimal manual chain

The shortest path from seeds to a hit table and report is five steps:

```bash
python3 scripts/01_align.py        --seeds my_seeds.faa --out-dir results/
python3 scripts/02_build_hmm.py    --aln results/seeds_aligned.faa --out-dir results/
python3 scripts/03_search.py       --hmm results/profile.hmm --db databases/inphared.faa
python3 scripts/05_classify_hits.py --hits results/hits_combined.tsv --db databases/inphared.faa
python3 scripts/14_report.py       --proj-dir .
```

Add steps 04 (tiering), 06 (iteration), and 07–13 (analysis) as needed.

---

## The interactive experience

Every script has **three behaviours**, chosen automatically from your terminal:

| Behaviour | When you see it | What it looks like |
|-----------|-----------------|--------------------|
| **Guided wizard** | required argument missing, in a terminal | asks "Path to your profile HMM?", "How strict?" with explanations |
| **Explain-and-confirm** | before each external tool runs | shows the exact command, explains it, asks "Proceed? `[Y/n]`" |
| **Narration** | always | running commentary that *interprets* results ("0 hits → raise `--evalue`") |

**Auto-detection rule:** a script is interactive only when **stdin and stdout are
both real terminals** and you did **not** pass `--yes`. Piped, redirected, or
`--yes` → every prompt resolves to its default, nothing blocks. This is what
makes the same script safe to run by hand *and* inside an HPC job.

```bash
python3 scripts/03_search.py              # human at a keyboard → prompts
python3 scripts/03_search.py < /dev/null  # piped               → silent
python3 scripts/03_search.py --yes        # forced              → silent
```

See [`docs/CLI_INTERACTIVE_GUIDE.md`](../docs/CLI_INTERACTIVE_GUIDE.md) for a full
walkthrough, or open the interactive
[`docs/cli_interactive_guide.html`](../docs/cli_interactive_guide.html) in a
browser.

---

## Pipeline at a glance

```
  seed proteins (my_seeds.faa)
        │  01_align.py
        ▼
  seeds_aligned.faa ──────────────┐
        │  02_build_hmm.py        │ (also feeds 09_phylogeny.py)
        ▼                         │
  profile.hmm                     │
        │  03_search.py           │
        ▼                         │
  hits_combined.tsv               │
        │  04_score_hits.py       │
        ▼                         │
  hits_scored.tsv                 │
        │  05_classify_hits.py    │
        ▼                         │
  hits_main.tsv  +  hits_proteins.faa
        │                  │
        │  (optional 06_iterate.py → seeds_expanded.faa, profile_final.hmm)
        │                  │
        ├── 07_synteny.py ─┤      → synteny_table.tsv, synteny_map.{png,svg,pdf}
        ├── 08_taxonomy.py        → taxonomy_table.tsv
        ├── 09_phylogeny.py ◄─────  (uses seeds_aligned.faa) → tree.treefile, tree.png
        ├── 10_matrix.py          → presence_absence_matrix.tsv, heatmap.png
        ├── 11_cluster.py ◄───────  (uses hits_proteins.faa)  → cluster_*.tsv
        ├── 12_motifs.py  ◄───────  (uses hits_proteins.faa)  → meme_out/, fimo_hits.tsv
        └── 13_annotate.py ◄──────  (uses hits_proteins.faa)  → annotation_summary.tsv
        │
        ▼  14_report.py
  report.html  +  methods.txt  +  reproducibility.json  +  export.zip
```

---

## Per-step summary

| Step | Script | What it does | Key input → output |
|------|--------|--------------|--------------------|
| 01 | `01_align.py` | Align seed proteins (MAFFT / Clustal Omega) | `--seeds` → `seeds_aligned.faa` |
| 02 | `02_build_hmm.py` | Build a profile HMM | `--aln` → `profile.hmm` |
| 03 | `03_search.py` | Search database(s) with the HMM | `--hmm --db` → `hits_combined.tsv` |
| 04 | `04_score_hits.py` | Sort hits into confidence tiers | `--hits` → `hits_scored.tsv` |
| 05 | `05_classify_hits.py` | Canonical hits table + extract sequences | `--hits --db` → `hits_main.tsv`, `hits_proteins.faa` |
| 06 | `06_iterate.py` | Iterative seed expansion (jackhmmer-style) | `--seeds --hits-faa --hmm --db` → `seeds_expanded.faa`, `profile_final.hmm` |
| 07 | `07_synteny.py` | Gene-neighbourhood tables + maps (+ clinker) | `--hits` → `synteny_table.tsv`, `synteny_map.*` |
| 08 | `08_taxonomy.py` | Host / organism / taxonomy from IDs | `--hits` → `taxonomy_table.tsv` |
| 09 | `09_phylogeny.py` | Maximum-likelihood tree (IQ-TREE) | `--aln` → `tree.treefile`, `tree.png` |
| 10 | `10_matrix.py` | Presence/absence matrix + heatmap | `--hits` → `presence_absence_matrix.tsv`, heatmap |
| 11 | `11_cluster.py` | Cluster sequences (CD-HIT / MMseqs2) | `--faa` → `cluster_*.tsv`, `cluster_reps.faa` |
| 12 | `12_motifs.py` | Motif discovery (MEME) + scanning (FIMO) | `--faa` → `meme_out/`, `fimo_hits.tsv` |
| 13 | `13_annotate.py` | Domain architecture + TM topology | `--faa --hmm --domtblout` → `annotation_summary.tsv` |
| 14 | `14_report.py` | HTML report + Methods text + export ZIP | `--proj-dir` → `report.html`, `methods.txt`, `export.zip` |
| — | `run_pipeline.py` | Run steps 01–14 end-to-end | `--seeds --db --proj-dir` → all of the above |
| — | `guide.py` | Interactive tour of the whole pipeline | *(menu-driven)* |
| — | `run_all_database_benchmark.py` | Validate against many databases | `--fasta` → benchmark report + verdict |

---

## Full flag & I/O reference

Every script also responds to `--help`. Defaults are shown in `[brackets]`.

### 01_align.py — Multiple sequence alignment
| Flag | Default | Meaning |
|------|---------|---------|
| `--seeds` | *(wizard)* | Un-aligned seed protein FASTA |
| `--out-dir` | `results/` | Output directory |
| `--tool` | `mafft` | `mafft` or `clustalo` |
| `--trim` | off | Run trimAl `--automated1` after alignment |
| `--threads` | `4` | Aligner threads |

**Outputs:** `seeds_aligned.faa` (+ `seeds_trimmed.faa` if `--trim`).
**Calls:** `run_mafft` / `run_clustalo`, `run_trimal`, `alignment_quality`.

### 02_build_hmm.py — Build profile HMM
| Flag | Default | Meaning |
|------|---------|---------|
| `--aln` | *(wizard)* | Aligned FASTA from step 01 |
| `--out-dir` | `results/` | Output directory |
| `--name` | `novel_phage_gene` | Name embedded in the HMM |

**Outputs:** `profile.hmm`. **Calls:** `run_hmmbuild`.

### 03_search.py — Search database(s)
| Flag | Default | Meaning |
|------|---------|---------|
| `--hmm` | *(wizard)* | Profile HMM from step 02 |
| `--db` | *(wizard, repeatable)* | Target FASTA; repeat for multiple DBs |
| `--evalue` | `1e-5` | E-value inclusion threshold |
| `--cpu` | `4` | hmmsearch threads |
| `--out-dir` | `results/` | Output directory |
| `--nuc` / `--sixframe` | off | DBs are nucleotide → 6-frame translate first |

**Outputs:** `search_results/<db>.tblout`, `<db>.domtblout`, `hits_combined.tsv`.
**Calls:** `run_hmmsearch_protein` / `run_hmmsearch_nucleotide`, `parse_tblout`.

### 04_score_hits.py — Confidence tiers
| Flag | Default | Meaning |
|------|---------|---------|
| `--hits` | *(wizard)* | Hits TSV from step 03 |
| `--out-dir` | `results/` | Output directory |
| `--evalue` | `1e-5` | Pre-filter E-value |
| `--bitscore` | `45.0` | Bit-score boundary for `high_confidence` |
| `--coverage` | `0.30` | Min HMM coverage for `putative` |
| `--hmm-length` | `0` | HMM length (0 = infer) |

**Outputs:** `hits_scored.tsv` (adds `confidence_tier` + QC columns).
**Calls:** `classify_hits`, `add_qc_flags`.

### 05_classify_hits.py — Canonical table + sequences
| Flag | Default | Meaning |
|------|---------|---------|
| `--hits` | *(wizard)* | Scored (or raw) hits TSV |
| `--db` | *(wizard, repeatable)* | Source protein FASTA(s) |
| `--domtblout` | — | Per-domain table for coordinates |
| `--hmm-length` | `0` | HMM length (0 = infer) |
| `--bitscore` | `45.0` | `high_confidence` boundary |
| `--out-dir` | `results/` | Output directory |

**Outputs:** `hits_main.tsv`, `hits_proteins.faa`.
**Calls:** `build_main_hits_table`, `extract_hit_sequences`, `parse_domtblout`.

### 06_iterate.py — Iterative refinement
| Flag | Default | Meaning |
|------|---------|---------|
| `--seeds` | *(wizard)* | Initial seed FASTA |
| `--hits-faa` | *(wizard)* | Candidate sequences (from step 05) |
| `--hmm` | *(wizard)* | Starting HMM |
| `--db` | *(wizard, repeatable)* | Target database(s) |
| `--out-dir` | `results/` | Output directory |
| `--iterations` | `5` | Max refinement rounds |
| `--evalue` | `1e-5` | hmmsearch E-value each round |
| `--bitscore` | `45.0` | Bit-score to admit a new seed |
| `--cpu` | `4` | Threads |

**Outputs:** `seeds_expanded.faa`, `profile_final.hmm`, `iteration_history.tsv`.
**Calls:** `run_mafft`, `run_hmmbuild`, `run_hmmsearch_protein`, `iteration_candidates`, `convergence_check`, `append_to_seeds`.

### 07_synteny.py — Gene neighbourhoods
| Flag | Default | Meaning |
|------|---------|---------|
| `--hits` | *(wizard)* | Hits TSV (step 05) |
| `--out-dir` | `results/` | Output directory |
| `--email` | `researcher@example.com` | NCBI Entrez e-mail (online fetch) |
| `--flanks` | `5` | Flanking genes each side of the hit |
| `--max-genomes` | `30` | Cap on loci fetched |
| `--local-gb` | — | Directory of local GenBank files (offline) |
| `--clinker` | off | Also build the clinker gene-link HTML |
| `--identity` | `0.3` | Min protein identity for clinker links |

**Outputs:** `synteny_table.tsv`, `synteny_neighborhoods.gff3`,
`synteny_map.{png,svg,pdf}`, `neighborhood_genbanks/`, `clinker/clinker_output.html`.
**Calls:** `build_synteny_table`, `conservation_scores`, `export_gff3`,
`export_synteny_figures`, `build_neighborhood_genbanks`, `run_clinker`.

### 08_taxonomy.py — Taxonomy from IDs
| Flag | Default | Meaning |
|------|---------|---------|
| `--hits` | *(wizard)* | Hits TSV |
| `--out-dir` | `results/` | Output directory |

**Outputs:** `taxonomy_table.tsv` (adds `host_type`, `organism_name`, taxonomy).
**Calls:** `taxonomy_table`.

### 09_phylogeny.py — IQ-TREE
| Flag | Default | Meaning |
|------|---------|---------|
| `--aln` | *(wizard)* | Aligned FASTA (step 01) |
| `--out-dir` | `results/` | Output directory |
| `--model` | `TEST` | Substitution model, or `TEST` to auto-select |
| `--bootstrap` | `1000` | Ultra-fast bootstrap replicates (`-B`) |
| `--cpu` | `4` | Threads |

**Outputs:** `iqtree.*` (incl. `.treefile`), `tree.png`.
**Calls:** `run_iqtree`, `render_tree`.

### 10_matrix.py — Presence/absence
| Flag | Default | Meaning |
|------|---------|---------|
| `--hits` | *(wizard)* | Hits TSV |
| `--out-dir` | `results/` | Output directory |
| `--tiers` | `high_confidence putative divergent` | Tiers to include |

**Outputs:** `presence_absence_matrix.tsv`, `presence_absence_heatmap.png`.
**Calls:** `build_matrix`, `matrix_stats`, `heatmap_png`.

### 11_cluster.py — Sequence clustering
| Flag | Default | Meaning |
|------|---------|---------|
| `--faa` | *(wizard)* | Protein FASTA (e.g. `hits_proteins.faa`) |
| `--out-dir` | `results/` | Output directory |
| `--tool` | `auto` | `auto` / `cd-hit` / `mmseqs2` |
| `--identity` | `0.40` | Identity threshold (0–1) |
| `--coverage` | `0.80` | Coverage threshold (0–1) |
| `--cpu` | `4` | Threads |

**Outputs:** `cluster_reps.faa`, `cluster_membership.tsv`, `cluster_summary.tsv`.
**Calls:** `cluster_dispatch`, `cluster_summary`.

### 12_motifs.py — MEME / FIMO
| Flag | Default | Meaning |
|------|---------|---------|
| `--faa` | *(wizard)* | Protein FASTA |
| `--out-dir` | `results/` | Output directory |
| `--nmotifs` | `5` | Number of motifs to find |
| `--minw` | `6` | Minimum motif width (residues) |
| `--maxw` | `50` | Maximum motif width (residues) |
| `--cpu` | `4` | MEME parallel processes |
| `--no-fimo` | off | Skip the FIMO scanning step |

**Outputs:** `meme_out/`, `fimo_hits.tsv`. **Calls:** `run_meme`, `run_fimo`, `parse_meme_txt`.

### 13_annotate.py — Functional annotation
| Flag | Default | Meaning |
|------|---------|---------|
| `--faa` | *(wizard)* | Hit protein FASTA |
| `--hmm` | *(wizard)* | Profile HMM (length context) |
| `--domtblout` | *(wizard)* | Pfam `--domtblout` for domain architecture |
| `--out-dir` | `results/` | Output directory |
| `--phobius` | off | Run Phobius (TM + signal peptide) |
| `--tmhmm` | off | Run TMHMM (TM topology) |

**Outputs:** `domain_architecture.tsv`, `annotation_summary.tsv`.
**Calls:** `domain_architecture`, `run_phobius`, `run_tmhmm`, `annotate_from_tm`.

### 14_report.py — Report & export
| Flag | Default | Meaning |
|------|---------|---------|
| `--proj-dir` | *(wizard)* | Project root (contains `results/`, `figures/`, …) |
| `--out-dir` | `<proj-dir>/reports/` | Where report files are written |

**Outputs:** `report.html`, `methods.txt`, `reproducibility.json`, `export.zip`.
**Calls:** `build_reproducibility_json`, `generate_methods_text`, `build_report_context`, `render_html_report`, `create_export_zip`.

### run_pipeline.py — Master runner
Runs 01–14 in order, wiring each output into the next.

| Flag | Default | Meaning |
|------|---------|---------|
| `--seeds` | *(wizard)* | Seed FASTA |
| `--db` | *(wizard, repeatable)* | Target database(s) |
| `--proj-dir` | *(wizard)* | Project root for all outputs |
| `--email` | `researcher@example.com` | Entrez e-mail (step 07) |
| `--cpu` | `4` | Threads |
| `--evalue` | `1e-5` | hmmsearch E-value |
| `--skip` | — | Step IDs to skip, e.g. `--skip 07 09 11` |
| `--start-at` | `01` | Begin at this step ID |
| `--trim` | off | trimAl after alignment (step 01) |
| `--nuc` | off | Nucleotide databases (step 03) |
| `--iterations` | `3` | Max iterations (step 06) |
| `--local-gb` | — | Local GenBank dir (step 07) |
| `--hmm-name` | `novel_phage_gene` | HMM name (step 02) |

Each child step is launched with `--yes` so it never prompts mid-pipeline; the
master owns all interaction.

---

## Batch, HPC & Methods extraction

**Hands-off (HPC / cron):** add `--yes` (or pipe / redirect). Nothing prompts,
nothing blocks.

```bash
python3 scripts/run_pipeline.py --seeds s.faa --db db.faa --proj-dir proj/ --yes
```

**Capture the exact commands for a Methods section.** Every script prints
`[CMD] …` lines for each tool it runs. Two ways to harvest them:

```bash
# 1. Dry run — print the explanations + commands, run nothing:
python3 scripts/03_search.py --hmm profile.hmm --db db.faa --explain-only

# 2. Grep a real run's log:
python3 scripts/run_pipeline.py ... --yes 2>&1 | tee run.log
grep '\[CMD\]' run.log
```

`14_report.py` also writes a ready-to-paste `methods.txt` and a
`reproducibility.json` audit trail (tool versions, parameters, database provenance).

**Resume / skip:**

```bash
python3 scripts/run_pipeline.py ... --start-at 07 --skip 09 11 --yes
```

**Large multi-database validation:** `run_all_database_benchmark.py` runs an
exhaustive, *resumable* benchmark across many public databases and writes a
deployment-readiness verdict. See its `--help` for the full option set.

---

## Shared flags (every script)

| Flag | Effect |
|------|--------|
| `--yes`, `-y` | Non-interactive: accept defaults, never prompt (HPC / pipes) |
| `--interactive` | Force prompts even when stdout is not a terminal |
| `--no-color` | Disable ANSI colour (also honoured via `NO_COLOR` env var) |
| `--explain-only` | Dry run: print explanations + the commands that *would* run, then stop |

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `command not found: hmmsearch` (etc.) | The tool isn't installed in the active env. `conda activate hmm-discovery`, or `bash setup_environment.sh`. |
| `0 hits` across all databases | E-value too strict, or you searched a nucleotide DB without `--nuc`. Try `--evalue 1e-3` or add `--nuc`. |
| Hits exist but all "weak" | Distant homologs — expected. Step 04 tiers them as `divergent`; consider step 06 to iterate. |
| Synteny finds no neighbours | Provide `--local-gb DIR` with GenBank files, or a valid `--email` for Entrez. |
| A script "hangs" | It's waiting at a prompt because it detected a terminal. Pass `--yes` for hands-off runs. |
| Clinker / pyGenomeViz / Phobius missing | These are optional. Install them, or omit the flag that triggers them. |

---

*These scripts wrap the same `pipeline/*` modules as the HMM Discovery web app.
For the app, see the top-level [`README.md`](../README.md).*
