# Deployment Checklist

Use this checklist before publishing a release or deploying for shared use.

## Repository hygiene

- Confirm no private input FASTA, project directories, downloaded databases, result tables, or logs are committed.
- Keep only synthetic or public demo data in `example_data/`.
- Confirm `ACKNOWLEDGEMENTS.md` and `CITATION.cff` are present and linked from `README.md`.
- Confirm `docs/METHODOLOGY.md` and `docs/DOCUMENTATION_INDEX.md` are present and linked from `README.md`.
- Run `python -m compileall -q app.py core ui pipeline`.
- Run the demo project once from a clean directory.
- Confirm `core.env_setup.check_environment()` reports `all_full_run_ok: True`.
- Confirm database relevance text appears in Step 0 and Step 4 so users understand why each database might be selected.
- Confirm Step 4 explains six-frame ORF scanning: three forward frames, three reverse-complement frames, stop-to-stop peptide extraction, minimum ORF length, HMMER search, coordinate retention, and the sensitivity/noise tradeoff.
- Confirm Step 4 recommends VOGDB VFAM for viral ortholog/family annotation.
- Confirm the registered database list does not include seed/input FASTA as a searchable database unless the user explicitly registered a separate custom target.
- Confirm no-code app readiness: ordinary users can complete setup checks, project creation, input upload, HMM build, database selection, single-genome scans, six-frame ORF mode, summary generation, cache cleanup, and export from the app UI without writing code.
- Confirm `www/presentation/` contains current workflow diagrams for presentations and onboarding.

## Local deployment

- Create the environment with `conda env create -f environment.yml`.
- Activate it with `conda activate hmm-discovery`.
- Launch with `./run_app.sh`.
- Open `http://127.0.0.1:8081`.

## Docker deployment

- Build with `docker build -t hmm-discovery .`.
- Run with `docker run --rm -p 8081:8081 hmm-discovery`.
- Open `http://127.0.0.1:8081`.

## Shared server notes

- Use a persistent volume for project directories and cached databases.
- Set reasonable storage quotas; public viral databases can be hundreds of MB to several GB.
- Put the app behind institutional authentication if users will upload unpublished data.
- Back up only project outputs that users explicitly want retained.
- Run each user/project in an isolated project folder and keep output paths outside the clean application repository.
- Prefer sequential cache cleanup for very large database runs; keep final tables, logs, reports, HMMs, and reproducibility metadata, not raw downloaded databases.

## Database provenance

- For every downloaded database file, preserve source URL, access date, file size, and SHA256 checksum in the benchmark manifest or run summary.
- Confirm selected tools/databases are acknowledged in `ACKNOWLEDGEMENTS.md` and that run-specific citations are recoverable from `reports/reproducibility.json`.
- Confirm `reports/reproducibility.json` contains `database_provenance` for benchmark runs.
- Confirm `results/all_database_summary.tsv` includes source URL count, source size, access window, and SHA256 prefixes for future benchmark runs.
- Record nucleotide search mode (`sixframe` or `prodigal`) for each nucleotide database. Use six-frame discovery mode for short, overlapping, noncanonical, or annotation-missed ORFs.
- Treat external database names, versions, URLs, and access dates as part of the scientific record; reviewers may ask what exact database snapshot was searched.
- Record VOGDB release and source URLs when VOGDB is selected: VOGDB release 230 / RefSeq release 230, `vfam.hmm.tar.gz`, and `vfam.annotations.tsv.gz`.

## Release test

- Load `example_data/demo_protein_family.fasta`.
- Run alignment, HMM build, self-search validation, and export.
- Register a single nucleotide FASTA under `Database Setup -> Add Custom Database / Single Genome Target`, run Step 4 with `Exhaustive six-frame ORFs`, and confirm hit coordinates are preserved in the output headers/tables.
- Confirm Step 9 can save the export ZIP to a user-selected folder outside the repository.
- Confirm Step 9 Run Summary creates `reports/RUN_SUMMARY.md` and `reports/run_summary.json`, and that active benchmark summaries reflect `nt_orf_mode: sixframe`.
- Confirm Step 9 Storage Cleanup previews before deletion and blocks cleanup while a benchmark PID is alive.
- Confirm Step 9 Deployment Readiness reminds users about self-search recovery, database status, nucleotide ORF mode, provenance, exports, and Git hygiene.
- For full research validation, run a phage search with INPHARED proteins first, then add nucleotide databases once storage and runtime expectations are clear.
- For exhaustive deployment validation, use the app's `Database Setup -> All-Database Research Validation` panel with nucleotide ORF mode set to `Exhaustive six-frame ORFs`: run `Dry-Run Expansion`, then `Smoke test`, then `Real partial`, and only then `All registered databases`.
- Treat `Prodigal predicted genes` as a fast annotation baseline only; do not use Prodigal-only nucleotide results as evidence that weird/annotation-missed genes are absent.
- Treat the app as core-discovery deployment-ready when required discovery databases pass and every optional database is recorded as `complete`, `failed`, `skipped`, or `partial` with a clear reason.
- Keep exhaustive benchmark outputs outside the Git repository because they may contain private sequences, hits, reports, and logs.
