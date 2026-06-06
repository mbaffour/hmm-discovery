#!/usr/bin/env python3
"""
08_taxonomy.py — Add taxonomy annotations to the hits table.

Parses accession prefixes and INPHARED-style pipe-delimited sequence IDs
to infer host type, organism name, and taxonomy string for each hit.

Example
-------
    python3 scripts/08_taxonomy.py --hits results/hits_main.tsv --out-dir results/
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from pipeline.taxonomy import taxonomy_table
from pipeline.utils import ensure_tools_on_path


def parse_args():
    p = argparse.ArgumentParser(
        description="Annotate hits with taxonomy information from sequence IDs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--hits",    required=True,  type=Path,
                   help="Hits TSV (output of 05_classify_hits.py or similar).")
    p.add_argument("--out-dir", default=Path("results"), type=Path,
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

    print(f"\n=== Step 8: Taxonomy Annotation ===")
    print(f"  Input  : {hits_path}")
    print(f"  Out dir: {out_dir}")

    hits_df = pd.read_csv(hits_path, sep="\t")
    print(f"  Loaded : {len(hits_df)} rows")

    if hits_df.empty:
        print("WARNING: Input is empty.", file=sys.stderr)
        out_path = out_dir / "taxonomy_table.tsv"
        hits_df.to_csv(out_path, sep="\t", index=False)
        print(f"\nDone (empty). Output: {out_path}")
        sys.exit(0)

    annotated = taxonomy_table(hits_df)

    out_path = out_dir / "taxonomy_table.tsv"
    annotated.to_csv(out_path, sep="\t", index=False)

    # Summary
    if "host_type" in annotated.columns:
        print("\n--- Host type distribution ---")
        for ht, n in annotated["host_type"].value_counts().items():
            print(f"  {ht:<25} {n:>6}")

    if "organism_name" in annotated.columns:
        named = annotated["organism_name"].dropna()
        named = named[named.str.strip() != ""]
        print(f"\n  Named organisms  : {len(named)}")
        print(f"  Total rows       : {len(annotated)}")

    print(f"\nDone. Taxonomy table -> {out_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
