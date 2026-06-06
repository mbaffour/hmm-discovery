# Documentation Index

Use this index to decide which document belongs in which context.

## For New Users

- `README.md`: quick start, installation, first demo run, database behavior,
  output overview, no-code app-running expectations, troubleshooting, and
  privacy notes.
- `docs/STARTUP_GUIDE.md`: comprehensive startup path for Conda, Docker,
  demo runs, single-genome scans, long runs, and common launch problems.
- `www/guide.html`: interactive browser guide bundled with the app.
- `www/index.html`: website-style landing page introducing the app and linking
  the main guide.
- `www/presentation/`: presentation-ready workflow diagrams for talks, posters,
  lab meetings, and onboarding.
- `docs/METHODOLOGY.md`: scientific workflow and interpretation guidance.

## For Command-Line And Pipeline Users

- `scripts/README.md`: complete reference for the command-line pipeline — quick
  start, a pipeline data-flow diagram, a per-step table, the full flag and
  input/output reference for every script, and the batch/HPC/Methods workflow.
- `docs/CLI_INTERACTIVE_GUIDE.md`: friendly walkthrough of the interactive
  scripts — the guided wizard, explain-and-confirm gate, narration, and how
  prompts auto-disable for HPC/batch runs.
- `docs/cli_interactive_guide.html`: self-contained interactive browser guide
  with a clickable step explorer and a live command builder (open by
  double-clicking; no internet required).
- `scripts/guide.py`: runnable interactive tour — `python3 scripts/guide.py`
  explains each step, shows the command, and offers to run it.

## For Research Methods And Reviewers

- `docs/METHODOLOGY.md`: detailed method logic, ORF modes, discovery versus
  annotation, synteny, limitations, and recommended manuscript package.
- `reports/METHODS_TEXT.txt`: generated methods paragraph for a specific run.
- `reports/reproducibility.json`: generated run metadata, tool versions,
  database provenance, and citation guidance.
- `reports/RUN_SUMMARY.md`: generated human-readable run summary.
- `ACKNOWLEDGEMENTS.md`: complete tool and database acknowledgement checklist.
- `CITATION.cff`: GitHub citation metadata for the software.

## For Deployment

- `DEPLOYMENT.md`: local/Docker deployment notes.
- `docs/DEPLOYMENT_CHECKLIST.md`: release and shared-server checklist,
  including no-code UI readiness checks.
- `RELEASE_NOTES.md`: release highlights, validation status, caveats, and
  before-publishing tasks.
- `Dockerfile`, `environment.yml`, `requirements.txt`, `setup_environment.sh`,
  and `run_app.sh`: installation/runtime files.

## For Outreach

- `docs/BLOG_POST.md`: public-facing project overview.
- `README.html`: static HTML companion to the app guide.
- `www/presentation/*.svg` and `www/presentation/*.png`: reusable visual
  workflow assets.

## For Legal And Citation Hygiene

- `LICENSE`: software license.
- `CITATION.cff`: citation metadata.
- `ACKNOWLEDGEMENTS.md`: external tool/database citation checklist.

## Not Included In The GitHub Release

The clean deployable repository should not include private FASTA/GenBank files,
downloaded public database caches, benchmark outputs, project folders, logs,
raw result tables from unpublished analyses, or export ZIPs containing private
data.
