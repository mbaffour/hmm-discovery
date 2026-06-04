# Release Notes

## v1.0.0 — GitHub-Ready Deployable Build

This release bundle is prepared for public repository upload and shared
research use. It contains application code, synthetic/demo data, documentation,
environment files, citation metadata, and deployment guidance. It does not
include private research FASTA files, downloaded public database caches, logs,
or benchmark result tables.

## Highlights

- End-to-end HMM discovery workflow in a Python Shiny app.
- Profile HMM construction with MAFFT, trimAl, and HMMER.
- Public database search against INPHARED, RefSeq, Swiss-Prot, GPD, GVD-AVrC,
  Pfam, and VOGDB.
- Exhaustive six-frame ORF nucleotide discovery mode for short, overlapping,
  noncanonical, or annotation-missed genes.
- Prodigal baseline mode for faster conventional gene prediction.
- Five-upstream / five-downstream synteny recovery where context is available.
- Run summary, reproducibility JSON, methods text, report HTML, and export ZIP.
- User-selected output/export destinations and storage cleanup guidance.
- VOGDB VFAM is the supported viral ortholog/family annotation layer.

## Validation Status

- Python compile checks pass across app, core, UI, pipeline, database, and
  script modules.
- Database registry dry-run expands all built-in databases.
- RefSeq bacterial proteins dry-run expansion currently resolves 973 files.
- VOGDB is the supported viral annotation layer; required core discovery
  databases are the deployment gate.
- `ACKNOWLEDGEMENTS.md` and `CITATION.cff` are included for citation hygiene.
- `docs/METHODOLOGY.md` and `docs/DOCUMENTATION_INDEX.md` are included for
  manuscript/reviewer documentation and repository navigation.

## Known Caveats

- Large database runs require substantial time, CPU, disk, and stable internet.
- Six-frame ORF discovery is intentionally sensitive and can produce more
  borderline candidates than conventional gene-calling workflows.
- Public database snapshots can change; run exports record URLs, access times,
  sizes, and checksums when available.

## Before Publishing

1. ~~Replace placeholder repository URLs in `README.md` and `CITATION.cff`.~~ Done — URLs now point to `https://github.com/mbaffour/hmm-discovery`.
2. Confirm `git status` does not include private project folders, downloaded
   databases, logs, benchmark outputs, or unpublished sequence files.
3. Run the demo project once from a clean folder.
4. Generate a Run Summary and export ZIP from the app.
5. Follow `docs/DEPLOYMENT_CHECKLIST.md`.
