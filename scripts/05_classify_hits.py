#!/usr/bin/env python3
"""
05_classify_hits.py — Build the canonical hits table and pull out the sequences.
================================================================================

WHAT THIS STEP DOES (the biology)
---------------------------------
By now you have a scored list of hits, but it is still mostly raw HMMER output.
This step does two things that the rest of the pipeline depends on:

    1. Builds the *canonical* hits table — one tidy row per hit with every
       metadata column the downstream steps expect (coordinates, coverage,
       confidence tier, domain spans, source database, and so on). Optional
       domtblout data is merged in to pin down per-domain coordinates.

    2. Extracts the actual PROTEIN SEQUENCES of those hits out of the source
       database FASTA(s) and writes them to one file. Everything after this —
       phylogeny, clustering, motifs, annotation — operates on these sequences.

WHAT THE KEY PARAMETERS MEAN
----------------------------
    --hits       Scored hits (04) or a raw tblout-derived TSV (03).
    --db         Source FASTA(s) the sequences are pulled from. Repeatable.
    --domtblout  Optional per-domain table to supplement coordinates.
    --bitscore   Strict bit-score boundary (high_confidence) — kept consistent
                 with step 04 so tiers don't shift between steps.

OUTPUTS
-------
    results/hits_main.tsv       the canonical, fully-annotated hits table
    results/hits_proteins.faa   the protein sequences of all hits

INTERACTIVITY
-------------
Run it in a terminal with no/partial arguments and it becomes a guided wizard:
it interviews you for the hits table and database(s), then narrates the tier
breakdown and extraction counts. Pipe it or pass --yes for hands-off operation
(safe for HPC / run_pipeline.py). See cli_common.py.

EXAMPLES
--------
    # Guided — the script will interview you:
    python3 scripts/05_classify_hits.py

    # Explicit:
    python3 scripts/05_classify_hits.py \\
        --hits results/hits_scored.tsv --db phages.faa --out-dir results/

    # Multiple databases, hands-off:
    python3 scripts/05_classify_hits.py --hits hits.tsv --db a.faa --db b.faa --yes
"""
import argparse
import sys
from pathlib import Path

# Make the app package importable no matter what directory we are run from,
# and make cli_common (which lives beside this script) importable too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from pipeline.hit_classifier import build_main_hits_table, extract_hit_sequences
from pipeline.searcher import parse_tblout, parse_domtblout
from pipeline.utils import ensure_tools_on_path
from cli_common import Guide, add_common_args


def parse_args():
    p = argparse.ArgumentParser(
        description="Build full hits table and extract hit sequences from DB FASTA.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Not required=True: a human in a terminal can supply these via the wizard.
    p.add_argument("--hits",       type=Path,
                   help="Hits TSV: scored hits (04_score_hits.py output) or "
                        "raw tblout TSV from 03_search.py.")
    p.add_argument("--db",         type=Path, action="append",
                   dest="dbs",    metavar="FASTA",
                   help="Source protein FASTA database(s) to extract sequences from. "
                        "Repeat for multiple databases.")
    p.add_argument("--domtblout",  type=Path,
                   help="Optional: domtblout file to supplement domain coordinates.")
    p.add_argument("--hmm-length", default=0,      type=int,
                   help="HMM profile length (match states). 0 = infer from data.")
    p.add_argument("--bitscore",   default=45.0,   type=float,
                   help="Strict bit-score threshold (high_confidence boundary).")
    p.add_argument("--out-dir",    default=Path("results"), type=Path,
                   help="Output directory.")
    add_common_args(p)          # --yes / --interactive / --no-color / --explain-only
    return p.parse_args()


def main():
    args = parse_args()
    guide = Guide.from_args(args)
    ensure_tools_on_path()

    guide.header(5, "Classify Hits",
                 "Build the canonical hits table and extract the hit protein sequences.")

    # ── GUIDED WIZARD ────────────────────────────────────────────────────
    if guide.interactive and (args.hits is None or not args.dbs):
        guide.wizard_intro("Let's build the canonical hits table.")
        if args.hits is None:
            args.hits = guide.ask_path(
                "Path to your hits TSV?",
                default="results/hits_scored.tsv",
                help_text="Scored hits from 04_score_hits.py (or a raw 03 table).",
            )
        if not args.dbs:
            first = guide.ask_path(
                "Source database FASTA to extract sequences from?",
                help_text="The same protein FASTA you searched in step 03.",
            )
            args.dbs = [first]
            while guide.ask_yesno("Add another source database?", default_yes=False):
                args.dbs.append(guide.ask_path("Next database FASTA?"))

    # ── Validate (works in both modes) ───────────────────────────────────
    if args.hits is None:
        guide.error("No --hits given. Provide one, or run in a terminal for the wizard.")
        sys.exit(2)
    if not args.dbs:
        guide.error("No --db given. Provide at least one source database FASTA.")
        sys.exit(2)

    hits_path = args.hits.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not hits_path.exists():
        guide.error(f"Hits TSV not found: {hits_path}")
        sys.exit(1)

    guide.narrate(f"Input hits : {hits_path.name}")
    guide.narrate(f"Databases  : {len(args.dbs)}")

    df = pd.read_csv(hits_path, sep="\t")
    guide.detail(f"Loaded {len(df)} rows.")

    # Load domtblout if provided (gives precise per-domain coordinates).
    dom_df = pd.DataFrame()
    if args.domtblout:
        domtblout_path = args.domtblout.resolve()
        if domtblout_path.exists():
            dom_df = parse_domtblout(domtblout_path)
            guide.detail(f"Domain info: {len(dom_df)} domain rows loaded.")
        else:
            guide.warn(f"domtblout not found: {domtblout_path}")

    # Determine HMM length.
    hmm_length = args.hmm_length
    if hmm_length == 0 and "hmm_to" in df.columns:
        hmm_length = int(df["hmm_to"].max()) if not df["hmm_to"].isna().all() else 0

    strict = args.bitscore
    moderate = strict * 0.67

    # Determine db_name for the hits (use first DB name or existing column).
    db_name = "combined"
    if "database_source" in df.columns and df["database_source"].nunique() == 1:
        db_name = df["database_source"].iloc[0]

    # ── EXPLAIN-AND-CONFIRM: build the canonical table ───────────────────
    guide.command(
        f"build_main_hits_table(hmm_length={hmm_length}, strict={strict}, "
        f"moderate={moderate:.1f})",
        "Assemble one tidy, fully-annotated row per hit (the table every later step reads).")
    if guide.confirm("Build the canonical hits table now?") != "yes":
        guide.warn("Skipped — nothing written.")
        sys.exit(0)

    guide.narrate("Building canonical hits table …")
    main_hits = build_main_hits_table(
        tblout_df=df,
        domtblout_df=dom_df,
        hmm_length=hmm_length,
        db_name=db_name,
        strict=strict,
        moderate=moderate,
    )

    hits_out = out_dir / "hits_main.tsv"
    main_hits.to_csv(hits_out, sep="\t", index=False)
    guide.result(f"Main hits table → {hits_out}  ({len(main_hits)} rows)")

    # Tier summary.
    if "confidence_tier" in main_hits.columns:
        guide.header(None, "Tier distribution")
        for tier, n in main_hits["confidence_tier"].value_counts().items():
            guide.narrate(f"{tier:<20} {n:>6}")

    # ── EXTRACT sequences from each database ─────────────────────────────
    guide.header(None, "Extract hit sequences")
    total_extracted = 0
    all_seqs_out = out_dir / "hits_proteins.faa"

    # Collect sequences from all DBs into one FASTA (concatenated).
    with all_seqs_out.open("w") as fout:
        for db_path in args.dbs:
            db_path = db_path.resolve()
            if not db_path.exists():
                guide.warn(f"Database not found, skipping: {db_path}")
                continue

            tmp_faa = out_dir / f"_tmp_{db_path.stem}.faa"
            n = extract_hit_sequences(main_hits, db_path, tmp_faa)
            total_extracted += n
            guide.detail(f"Extracted {n} sequences from {db_path.name}.")

            if tmp_faa.exists():
                fout.write(tmp_faa.read_text())
                tmp_faa.unlink()

    if total_extracted > 0:
        guide.result(f"All hit sequences ({total_extracted}) → {all_seqs_out}")
    else:
        guide.warn("No sequences extracted — check that the hit IDs match the database FASTA.")

    guide.done(f"Classification complete. Outputs in: {out_dir}")
    guide.detail("Next: 06_iterate.py (refine) or 07–13 downstream analyses on these sequences.")
    sys.exit(0)


if __name__ == "__main__":
    main()
