# HMM Discovery

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Who This Is For

HMM Discovery is built for researchers, graduate students, and bioinformatics core facility staff who need to find distant homologs of a protein family across large public databases. If you study phage tail fibers, depolymerases, receptor-binding proteins, or any protein family where BLAST alone misses divergent members, this app provides a guided, reproducible workflow without requiring command-line expertise.

## Table of Contents

- [What The App Does](#what-the-app-does)
- [Repository Contents](#repository-contents)
- [Quick Start With Conda Or Mamba](#quick-start-with-conda-or-mamba)
- [Quick Start With Docker](#quick-start-with-docker)
- [Comprehensive Startup Guide](docs/STARTUP_GUIDE.md)
- [First Demo Run](#first-demo-run)
- [No-Code App Runs](#no-code-app-runs)
- [Local File And Folder Picking](#local-file-and-folder-picking)
- [Full Research Run](#full-research-run)
- [Command-Line Pipeline](#command-line-pipeline)
- [Exhaustive All-Database Benchmark](#exhaustive-all-database-benchmark)
- [Database Behavior](#database-behavior)
- [Synteny Outputs](#synteny-outputs)
- [Exported Results](#exported-results)
- [Troubleshooting](#troubleshooting)
- [Privacy And Data Handling](#privacy-and-data-handling)
- [Citation](#citation)

---

HMM Discovery is a Python Shiny application for discovering and analyzing distant homologs of a protein family. It guides users from seed sequences to profile HMM construction, public database search, hit classification, synteny recovery, phylogeny, motif analysis, and exportable research reports.

This deployment bundle is sanitized for public release. It contains no private research project data, no downloaded databases, and no prior run outputs. The included FASTA in `example_data/demo_protein_family.fasta` is synthetic demonstration data.

Project website and interactive guide: <https://mbaffour.github.io/hmm-discovery/>

GitHub repository: <https://github.com/mbaffour/hmm-discovery>

## What The App Does

- Accepts protein FASTA, nucleotide FASTA, GenBank, or folders of sequence files.
- Builds multiple sequence alignments with MAFFT and trims them with trimAl.
- Builds HMMER3 profile HMMs and validates seed recovery.
- Searches protein and nucleotide databases with HMMER.
- Supports INPHARED and RefSeq viral genome/protein searches.
- Annotates hits with Pfam domains and VOGDB VFAM viral ortholog/family HMMs.
- Caches public database downloads resumably for large remote files.
- Uses Prodigal plus `seqkit` chunking for faster nucleotide database searches when available.
- Recovers five upstream and five downstream genes for synteny analysis when sequence context is available.
- Exports TSV, GFF3, figures, reports, methods text, and reproducibility metadata.

## Repository Contents

```text
app.py                    Shiny app entry point
core/                     Environment checks, state, logging, job runners
databases/                Built-in database registry and download helpers
pipeline/                 Alignment, HMM, search, synteny, motifs, tree, reports
scripts/                  Command-line version of the whole pipeline (see scripts/README.md)
ui/                       Shiny UI step modules
www/                      Static assets and app guide
www/index.html            Website-style landing page for the app
www/presentation/         Presentation-ready workflow diagrams
example_data/             Synthetic demo data only
docs/                     Interactive guide, blog post, deployment checklist
scripts/README.md         Command-line pipeline reference (flags, I/O, batch/HPC, Methods)
docs/CLI_INTERACTIVE_GUIDE.md  Walkthrough of the interactive command-line scripts
docs/cli_interactive_guide.html  Self-contained interactive CLI guide (open in a browser)
docs/STARTUP_GUIDE.md     Comprehensive startup guide for Conda, Docker, demo runs, and long runs
docs/METHODOLOGY.md       Scientific workflow and manuscript-facing methodology
docs/DOCUMENTATION_INDEX.md  Map of user, reviewer, deployment, and citation docs
ACKNOWLEDGEMENTS.md       Tool/database citation guidance
CITATION.cff              GitHub citation metadata
RELEASE_NOTES.md          Release highlights and publication caveats
environment.yml           Conda/mamba environment
requirements.txt          Python dependencies
Dockerfile                Container deployment
run_app.sh                Local launcher
```

## Quick Start With Conda Or Mamba

```bash
git clone https://github.com/mbaffour/hmm-discovery.git hmm-discovery
cd hmm-discovery
conda env create -f environment.yml
conda activate hmm-discovery
./run_app.sh
```

Open `http://127.0.0.1:8081`.

If you prefer to use the setup script:

```bash
bash setup_environment.sh
./run_app.sh
```

## Quick Start With Docker

```bash
docker build -t hmm-discovery .
docker run --rm -p 8081:8081 hmm-discovery
```

Open `http://127.0.0.1:8081`.

For shared deployments, mount a persistent project directory:

```bash
docker run --rm -p 8081:8081 \
  -v "$PWD/projects:/app/projects" \
  hmm-discovery
```

## First Demo Run

1. Launch the app.
2. Create a new project directory.
3. Load `example_data/demo_protein_family.fasta`.
4. Run Step 2: Multiple Sequence Alignment.
5. Run Step 3: Build Profile HMM.
6. Run Step 5: Score Calibration to confirm seed recovery.
7. Run Step 9: Export to create a reproducible ZIP.

The demo FASTA is synthetic and only intended to confirm installation.

## No-Code App Runs

Normal research runs are designed to happen entirely inside the app. Users do
not need to write Python, R, shell commands, or workflow scripts to create a
project, check/install required tools, upload FASTA files, build an HMM, choose
databases, run single-genome scans, use exhaustive six-frame ORFs, generate
summaries, clear cache files, or export results. Command-line examples in this
README are optional conveniences for administrators, shared servers, and
advanced automation.

## Local File And Folder Picking

Every app field that needs a local file or folder has a Browse-style chooser.
On local desktop installs, **Choose File...** and **Choose Folder...** open the
native operating-system picker and fill the app field automatically. The app
also keeps an in-page navigator as a fallback, where users can browse from Home,
Documents, Desktop, the current project folder, or parent folders; open
subfolders; select files; choose the current folder; and create folders where
that makes sense. Manual path typing remains available as a fallback.

Covered paths include the project folder, Step 1 input FASTA/GenBank/folder,
custom database or single-genome FASTA/GenBank path, benchmark FASTA, benchmark
output folder, synteny local GenBank folder, and Step 9 final export folder.

## Full Research Run

For a phage protein family discovery run:

1. Load your curated protein seed FASTA.
2. Build and inspect the alignment.
3. Build the HMM and verify strong self-recovery.
4. Search INPHARED proteins first for a fast check.
5. Add INPHARED genomes and RefSeq viral genomes/proteins for discovery-scale analysis.
6. Run confidence classification and synteny analysis.
7. Export all outputs.

Nucleotide database searches can take substantial CPU time. The deployment build caches compressed public databases first, then translates/searches locally so network interruptions do not destroy long runs.

For a manuscript-facing explanation of the full workflow, see [docs/METHODOLOGY.md](docs/METHODOLOGY.md). For a map of all release documents, see [docs/DOCUMENTATION_INDEX.md](docs/DOCUMENTATION_INDEX.md).

Presentation diagrams are in [www/presentation](www/presentation). They include
a workflow overview, no-code user journey, database strategy, and reproducible
output package diagram for slides and lab meetings.

## Command-Line Pipeline

Every step the app performs is also available as a standalone command-line
script in `scripts/`, driving the same `pipeline/` code. Use the scripts for HPC
clusters, automation, headless servers, or to produce an exact, copy-pasteable
Methods section for a paper.

The scripts are interactive in a terminal (they interview you for missing
inputs, explain each command before running it, and interpret the results) and
silent/non-blocking when piped or given `--yes` — so the same script is safe to
run by hand or inside a cluster job.

```bash
python3 scripts/guide.py                  # interactive tour of the whole pipeline
python3 scripts/run_pipeline.py           # run all 14 steps (wizard)
python3 scripts/01_align.py --help        # any single step
```

Documentation:

- [`scripts/README.md`](scripts/README.md) — full flag and input/output reference,
  data-flow diagram, and the batch/HPC/Methods workflow.
- [`docs/CLI_INTERACTIVE_GUIDE.md`](docs/CLI_INTERACTIVE_GUIDE.md) — friendly
  walkthrough of the interactive experience.
- [`docs/cli_interactive_guide.html`](docs/cli_interactive_guide.html) — a
  self-contained interactive guide with a clickable step explorer and a live
  command builder (open in any browser).

## Exhaustive All-Database Benchmark

For no-code deployment validation, open the app and go to **Database Setup -> All-Database Research Validation**.

1. Choose the input FASTA. Use **Use Current Project Input** after completing Step 1, or use the FASTA picker.
2. Choose an output folder outside the Git repository using the output folder picker.
3. Click **Dry-Run Expansion** to verify the registered database list and remote file counts.
4. Click **Start / Resume** to run the selected preset. The app shows the manifest, PID, per-database status, and live log.

The same workflow is also available as a standalone runner for advanced users or servers:

```bash
python scripts/run_all_database_benchmark.py \
  --fasta "/path/to/your_seed_family.fasta" \
  --out "/path/to/HMM-Discovery-AllDB-Benchmark" \
  --preset all \
  --cpu 4
```

Useful modes:

```bash
# Expand database URLs without downloading data
python scripts/run_all_database_benchmark.py --dry-run --out /tmp/hmm_benchmark_dryrun

# Small synthetic smoke test
python scripts/run_all_database_benchmark.py \
  --preset smoke \
  --fasta example_data/demo_protein_family.fasta \
  --out /tmp/hmm_benchmark_smoke

# Fast real-data partial validation
python scripts/run_all_database_benchmark.py \
  --preset partial \
  --fasta "/path/to/your_seed_family.fasta" \
  --out "/path/to/HMM-Discovery-AllDB-Benchmark" \
  --nt-orf-mode sixframe
```

The app and runner both write `benchmark_manifest.json`, `per_database_metrics.tsv`, `all_database_summary.tsv`, `hits_main.tsv`, reports, logs, synteny outputs, run summaries, and a final export ZIP. Runs are resumable: click **Start / Resume** again, or re-run the same command, and completed databases are skipped. By default the benchmark removes raw downloaded cache files after each searchable DB chunk so machines with limited disk can still process large registries sequentially.

For nucleotide databases, the benchmark defaults to `--nt-orf-mode sixframe`. This is the research-discovery mode for short, overlapping, noncanonical, or annotation-missed genes. `--nt-orf-mode prodigal` is available only as a faster conventional annotation baseline and should not be treated as exhaustive gene discovery.

VOGDB VFAM is the supported viral ortholog/family annotation layer. It uses the same HMMER `hmmscan` path as Pfam, which keeps annotation reproducible across local laptops, workstations, and containers.

## Database Behavior

The app ships with registry entries for public databases, but it does not include downloaded database files. This keeps the repository small and avoids redistributing third-party data.

Seed/input FASTA files are never auto-registered as searchable databases. Use self-search validation for seed recovery, and use the registry only for public databases or custom databases that a user explicitly adds.

For remote databases:

- Compressed public files are downloaded into the project cache when needed.
- Downloads use resume support and completion markers.
- Nucleotide FASTA files can be translated with exhaustive six-frame ORF scanning or Prodigal.
- `seqkit` is used to split large nucleotide FASTA files for parallel translation.
- HMMER searches translated ORFs, predicted proteins, or protein FASTA records.

Annotation databases:

- **VOGDB VFAM (annotation)** downloads VOGDB release 230 VFAM HMMs from `https://fileshare.csb.univie.ac.at/vog/vog230/vfam.hmm.tar.gz`, downloads annotations from `https://fileshare.csb.univie.ac.at/vog/vog230/vfam.annotations.tsv.gz`, indexes the HMMs with `hmmpress`, and scans current hit proteins with `hmmscan`. The release is VOGDB 230 / RefSeq 230 with 39,585 VFAMs. MD5 checksums are not bundled unless the upstream release provides them; the benchmark records SHA256 provenance for downloaded files.
- **Pfam (domain scan)** is broad conserved-domain annotation for discovered proteins.

`results/vogdb_vfam_annotation.tsv` contains `query_protein_id`, `vfam_id`, `evalue`, `bit_score`, `query_coverage` when available, and annotation/function/category fields from the VOGDB annotation table.

For a single genome run, register the genome FASTA in **Database Setup -> Add Custom Database / Single Genome Target**, set molecule type to `Nucleotide`, then search that one database in Step 4. Step 4 offers two nucleotide modes:

- **Exhaustive six-frame ORFs** translates every stop-to-stop ORF above the length cutoff and is best for unusual, short, overlapping, or noncanonical genes.
- **Prodigal predicted genes** is faster and cleaner for conventional gene prediction, especially on large database-scale scans.

Both modes search translated proteins with HMMER and write the same tblout/search outputs. Six-frame ORF headers include strand and coordinate ranges for follow-up.

How six-frame ORF scanning works:

1. The nucleotide sequence is read in three forward reading frames and three reverse-complement reading frames.
2. Each frame is split at stop codons (`TAA`, `TAG`, `TGA`).
3. Every stop-to-stop peptide above the selected minimum amino-acid length is retained as a candidate ORF.
4. HMMER searches those translated candidate peptides with the profile HMM.
5. Hits keep their source contig, strand, frame, nucleotide start/end, and amino-acid length when available, so they can be inspected and used for synteny.

This mode is intentionally more sensitive than a conventional gene caller because it does not require Prodigal or another annotation tool to predict the gene first. The cost is more candidates, more runtime, and more borderline hits that should be reviewed with bit score, HMM coverage, reciprocal/self-search behavior, and genomic context.

## Synteny Outputs

Synteny analysis attempts to recover five genes upstream and five genes downstream of each placed hit. Outputs include:

- `results/synteny_table.tsv`
- `results/synteny_placement_report.tsv`
- `results/synteny_neighborhoods.gff3`
- synteny map figures in `figures/`
- optional GenBank-style neighborhood exports

The TSV and GFF3 files are suitable for importing into other synteny or genome-visualization tools.

## Exported Results

Typical export files include:

- `hits_main.tsv`
- `hits_best_per_genome.tsv`
- `presence_absence_matrix.tsv`
- `taxonomy_table.tsv`
- `synteny_table.tsv`
- `synteny_neighborhoods.gff3`
- `summary_report.html`
- `RUN_SUMMARY.md`
- `run_summary.json`
- `METHODS_TEXT.txt`
- `reproducibility.json`
- `export_YYYYMMDD_HHMMSS.zip`

Use **Step 9 -> Run Summary -> Generate Run Summary** to create `reports/RUN_SUMMARY.md` and `reports/run_summary.json`. The summary reports input statistics, command/settings metadata, database status, database source URLs, access dates/checksums when available, hit counts, confidence tiers, top hits, synteny status, and key output files.

For nucleotide databases or single-genome scans, use **Exhaustive six-frame ORFs** when the target may be short, overlapping, noncanonical, or absent from conventional gene calls. **Prodigal predicted genes** is included as a faster annotation baseline, but a Prodigal-only run should not be interpreted as exhaustive evidence that a weird ORF is absent.

Before public release or shared deployment, follow [docs/DEPLOYMENT_CHECKLIST.md](docs/DEPLOYMENT_CHECKLIST.md). Keep private FASTA files, downloaded databases, logs, and result tables outside the clean Git repository.

## Troubleshooting

Run this check from the repository root:

```bash
python - <<'PY'
from core.env_setup import check_environment
r = check_environment()
print("all_required_ok:", r["all_required_ok"])
print("all_python_ok:", r["all_python_ok"])
print("all_full_run_ok:", r["all_full_run_ok"])
print("missing tools:", [t["name"] for t in r.get("missing_full_run_tools", [])])
print("missing python:", [p["pkg"] for p in r.get("missing_full_run_python", [])])
PY
```

Common fixes:

- Re-run `conda env update -f environment.yml`.
- Confirm `conda activate hmm-discovery` before launching.
- Use Docker if local bioinformatics tooling is inconsistent.
- Start with protein databases before very large nucleotide databases.
- Make sure project directories have enough disk space for cached public databases.

## Privacy And Data Handling

Do not commit project directories, downloaded databases, logs, or unpublished FASTA/GenBank files. `.gitignore` and `.dockerignore` are configured to exclude common outputs, but users remain responsible for checking `git status` before publishing.

## Citation

If this app supports your work, cite the repository and the underlying tools used in your analysis, including HMMER, MAFFT, trimAl, Prodigal, seqkit, IQ-TREE, MEME Suite, CD-HIT/MMseqs2, INPHARED, UniProt/Swiss-Prot, RefSeq, GPD, GVD-AVrC, Pfam, VOGDB, and any other databases selected during the run.

See [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md) for the complete tool/database acknowledgement checklist and [CITATION.cff](CITATION.cff) for GitHub citation metadata.
