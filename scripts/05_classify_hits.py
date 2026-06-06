#!/usr/bin/env python3
"""
05_classify_hits.py — Build the canonical hits table and extract hit sequences.

Reads a scored hits TSV (or a raw tblout-derived TSV), builds the full
canonical hits table with all metadata columns, and extracts the
corresponding protein sequences from the source database(s).

Example
-------
    python3 scripts/05_classify_hits.py \\
        --hits results/hits_scored.tsv \\
        --db phages.faa \\
        --out-dir results/

    python3 scripts/05_classify_hits.py \\
        --hits hits.tsv --db a.faa --db b.faa --out-dir results/
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from pipeline.hit_classifier import build_main_hits_table, extract_hit_sequences
from pipeline.searcher import parse_tblout, parse_domtblout
from pipeline.utils import ensure_tools_on_path


def parse_args():
    p = argparse.ArgumentParser(
        description="Build full hits table and extract hit sequences from DB FASTA.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--hits",       required=True,  type=Path,
                   help="Hits TSV: scored hits (04_score_hits.py output) or "
                        "raw tblout TSV from 03_search.py.")
    p.add_argument("--db",         required=True,  type=Path, action="append",
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
    return p.parse_args()


def main():
    args = parse_args()
    ensure_tools_on_path()

    hits_path = args.hits.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not hits_path.exists():
        print(f"ERROR: Hits TSV not found: {hits_path}", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== Step 5: Classify Hits ===")
    print(f"  Input hits : {hits_path}")
    print(f"  Databases  : {len(args.dbs)}")

    df = pd.read_csv(hits_path, sep="\t")
    print(f"  Loaded     : {len(df)} rows")

    # Load domtblout if provided
    dom_df = pd.DataFrame()
    if args.domtblout:
        domtblout_path = args.domtblout.resolve()
        if domtblout_path.exists():
            dom_df = parse_domtblout(domtblout_path)
            print(f"  Domain info: {len(dom_df)} domain rows loaded")
        else:
            print(f"WARNING: domtblout not found: {domtblout_path}", file=sys.stderr)

    # Determine HMM length
    hmm_length = args.hmm_length
    if hmm_length == 0 and "hmm_to" in df.columns:
        hmm_length = int(df["hmm_to"].max()) if not df["hmm_to"].isna().all() else 0

    strict = args.bitscore
    moderate = strict * 0.67

    # Determine db_name for the hits (use first DB name or existing column)
    db_name = "combined"
    if "database_source" in df.columns and df["database_source"].nunique() == 1:
        db_name = df["database_source"].iloc[0]

    print(f"\n  Building canonical hits table...")
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
    print(f"  Main hits table -> {hits_out}  ({len(main_hits)} rows)")

    # Tier summary
    if "confidence_tier" in main_hits.columns:
        print("\n--- Tier distribution ---")
        for tier, n in main_hits["confidence_tier"].value_counts().items():
            print(f"  {tier:<20} {n:>6}")

    # Extract sequences from each database
    total_extracted = 0
    all_seqs_out = out_dir / "hits_proteins.faa"

    # Collect sequences from all DBs (append mode)
    with all_seqs_out.open("w") as fout:
        for db_path in args.dbs:
            db_path = db_path.resolve()
            if not db_path.exists():
                print(f"WARNING: Database not found, skipping: {db_path}", file=sys.stderr)
                continue

            tmp_faa = out_dir / f"_tmp_{db_path.stem}.faa"
            n = extract_hit_sequences(main_hits, db_path, tmp_faa)
            total_extracted += n
            print(f"\n  Extracted {n} sequences from {db_path.name}")

            if tmp_faa.exists():
                fout.write(tmp_faa.read_text())
                tmp_faa.unlink()

    print(f"\n  All hit sequences ({total_extracted}) -> {all_seqs_out}")
    print(f"\nDone. Outputs in: {out_dir}")
    sys.exit(0)


if __name__ == "__main__":
    main()
