#!/usr/bin/env python3
"""
08_taxonomy.py — Attach taxonomy and host information to each hit.
==================================================================

WHAT THIS STEP DOES (the biology)
---------------------------------
Once you have a list of hits, the natural next question is "what organisms are
these from, and what do they infect?" Many sequence databases (especially
INPHARED-style phage sets) encode that information directly in the sequence ID —
as accession prefixes and pipe-delimited fields. This step parses those IDs to
infer, per hit:

    * host_type      — the kind of host (e.g. a bacterial genus, "environmental")
    * organism_name  — the source organism / phage name where available
    * taxonomy        — a lineage string

This is pure string/metadata parsing — no external tools or network — so it is
fast and deterministic. The annotated table feeds the report and matrix steps.

WHAT THE KEY PARAMETERS MEAN
----------------------------
    --hits   The canonical hits table (05) or any hits TSV with sequence IDs.

OUTPUTS
-------
    results/taxonomy_table.tsv   the hits table plus host/organism/taxonomy columns

INTERACTIVITY
-------------
Run it in a terminal with no arguments and it becomes a guided wizard, then
narrates the host-type breakdown. Pipe it or pass --yes for hands-off operation
(safe for HPC / run_pipeline.py). See cli_common.py.

EXAMPLES
--------
    # Guided — the script will interview you:
    python3 scripts/08_taxonomy.py

    # Explicit / hands-off:
    python3 scripts/08_taxonomy.py --hits results/hits_main.tsv --out-dir results/ --yes
"""
import argparse
import sys
from pathlib import Path

# Make the app package importable no matter what directory we are run from,
# and make cli_common (which lives beside this script) importable too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from pipeline.taxonomy import taxonomy_table
from pipeline.utils import ensure_tools_on_path
from cli_common import Guide, add_common_args


def parse_args():
    p = argparse.ArgumentParser(
        description="Annotate hits with taxonomy information from sequence IDs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Not required=True: a human in a terminal can supply this via the wizard.
    p.add_argument("--hits",    type=Path,
                   help="Hits TSV (output of 05_classify_hits.py or similar).")
    p.add_argument("--out-dir", default=Path("results"), type=Path,
                   help="Output directory.")
    add_common_args(p)          # --yes / --interactive / --no-color / --explain-only
    return p.parse_args()


def main():
    args = parse_args()
    guide = Guide.from_args(args)
    ensure_tools_on_path()

    guide.header(8, "Taxonomy Annotation",
                 "Parse sequence IDs to infer host type, organism, and lineage per hit.")

    # ── GUIDED WIZARD ────────────────────────────────────────────────────
    if guide.interactive and args.hits is None:
        guide.wizard_intro("Let's annotate taxonomy.")
        args.hits = guide.ask_path(
            "Path to your hits TSV?",
            default="results/hits_main.tsv",
            help_text="The canonical hits table from 05_classify_hits.py.",
        )

    # ── Validate (works in both modes) ───────────────────────────────────
    if args.hits is None:
        guide.error("No --hits given. Provide one, or run in a terminal for the wizard.")
        sys.exit(2)

    hits_path = args.hits.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not hits_path.exists():
        guide.error(f"Hits TSV not found: {hits_path}")
        sys.exit(1)

    guide.narrate(f"Input  : {hits_path.name}")
    guide.narrate(f"Out dir: {out_dir}")

    hits_df = pd.read_csv(hits_path, sep="\t")
    guide.detail(f"Loaded {len(hits_df)} rows.")

    if hits_df.empty:
        guide.warn("Input is empty. Writing an empty taxonomy table.")
        out_path = out_dir / "taxonomy_table.tsv"
        hits_df.to_csv(out_path, sep="\t", index=False)
        guide.done(f"Nothing to annotate. Output: {out_path}")
        sys.exit(0)

    # ── EXPLAIN-AND-CONFIRM ──────────────────────────────────────────────
    guide.command("taxonomy_table(hits) — parse accession prefixes & INPHARED IDs",
                  "Derive host_type, organism_name, and taxonomy from each sequence ID.")
    if guide.confirm("Annotate taxonomy now?") != "yes":
        guide.warn("Taxonomy annotation skipped — nothing written.")
        sys.exit(0)

    guide.narrate("Parsing sequence IDs …")
    annotated = taxonomy_table(hits_df)

    out_path = out_dir / "taxonomy_table.tsv"
    annotated.to_csv(out_path, sep="\t", index=False)

    # ── NARRATE: interpret the breakdown ─────────────────────────────────
    if "host_type" in annotated.columns:
        guide.header(None, "Host type distribution")
        for ht, n in annotated["host_type"].value_counts().items():
            guide.narrate(f"{str(ht):<25} {n:>6}")

    if "organism_name" in annotated.columns:
        named = annotated["organism_name"].dropna()
        named = named[named.str.strip() != ""]
        guide.result(f"Named organisms: {len(named)} / {len(annotated)} rows.")
        if len(named) == 0:
            guide.detail("No organism names parsed — the DB IDs may not encode taxonomy.")

    guide.done(f"Taxonomy table → {out_path}")
    guide.detail("Next: 09_phylogeny.py / 10_matrix.py / 14_report.py use this annotation.")
    sys.exit(0)


if __name__ == "__main__":
    main()
