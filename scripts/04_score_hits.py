#!/usr/bin/env python3
"""
04_score_hits.py — Score and classify raw hmmsearch hits into confidence tiers.

Reads a TSV of hits (output of 03_search.py) and applies multi-evidence
confidence scoring:
  high_confidence — strong bit score + good HMM coverage
  putative        — moderate evidence
  divergent       — weak or partial hits
  likely_fp       — likely false positives

QC flags are also appended (high_bias, short_alignment, low_complexity,
contig_edge).

Example
-------
    python3 scripts/04_score_hits.py --hits results/hits_combined.tsv --out-dir results/
    python3 scripts/04_score_hits.py --hits hits.tsv --bitscore 50 --coverage 0.7
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from pipeline.confidence import classify_hits, add_qc_flags
from pipeline.utils import ensure_tools_on_path


def parse_args():
    p = argparse.ArgumentParser(
        description="Score hmmsearch hits into confidence tiers with QC flags.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--hits",     required=True,  type=Path,
                   help="Input hits TSV (output of 03_search.py or similar).")
    p.add_argument("--out-dir",  default=Path("results"), type=Path,
                   help="Output directory.")
    p.add_argument("--evalue",   default=1e-5,   type=float,
                   help="E-value filter applied before scoring (pre-filter).")
    p.add_argument("--bitscore", default=45.0,   type=float,
                   help="Strict bit-score threshold for high_confidence tier.")
    p.add_argument("--coverage", default=0.30,   type=float,
                   help="Minimum HMM coverage fraction for putative tier (0–1).")
    p.add_argument("--hmm-length", default=0,    type=int,
                   help="HMM profile length in match states. 0 = infer from data.")
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

    print(f"\n=== Step 4: Score Hits ===")
    print(f"  Input    : {hits_path}")
    print(f"  E-value  : {args.evalue}")
    print(f"  Bit score: {args.bitscore}")
    print(f"  Coverage : {args.coverage}")

    df = pd.read_csv(hits_path, sep="\t")
    print(f"  Loaded   : {len(df)} rows")

    if df.empty:
        print("WARNING: Input is empty. Writing empty output.", file=sys.stderr)
        out_path = out_dir / "hits_scored.tsv"
        df.to_csv(out_path, sep="\t", index=False)
        print(f"\nDone (empty). Output: {out_path}")
        sys.exit(0)

    # Pre-filter on e-value if the column exists
    if "evalue" in df.columns:
        before = len(df)
        df = df[pd.to_numeric(df["evalue"], errors="coerce") <= args.evalue].copy()
        print(f"  After e-value filter: {len(df)} / {before} rows")

    # Determine HMM length: from argument, or from hmm_to column max, or 0
    hmm_length = args.hmm_length
    if hmm_length == 0 and "hmm_to" in df.columns:
        hmm_length = int(df["hmm_to"].max()) if not df["hmm_to"].isna().all() else 0
    if hmm_length == 0:
        print("WARNING: HMM length unknown; using 0 (all hits scored as full coverage).",
              file=sys.stderr)

    strict = args.bitscore
    moderate = strict * 0.67  # ~30 if strict=45

    print(f"  HMM length: {hmm_length}")
    print(f"  Thresholds: strict={strict}, moderate={moderate:.1f}")

    # Classify
    scored = classify_hits(df, hmm_length=hmm_length, strict=strict,
                           moderate=moderate, hmm_cov_floor=args.coverage)

    # Add QC flags
    scored = add_qc_flags(scored)

    out_path = out_dir / "hits_scored.tsv"
    scored.to_csv(out_path, sep="\t", index=False)

    # Summary
    print("\n--- Tier distribution ---")
    if "confidence_tier" in scored.columns:
        counts = scored["confidence_tier"].value_counts()
        for tier, n in counts.items():
            print(f"  {tier:<20} {n:>6}")
    print(f"\nDone. Scored hits -> {out_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
