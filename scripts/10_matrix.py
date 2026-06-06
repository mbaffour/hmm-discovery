#!/usr/bin/env python3
"""
10_matrix.py — Build a genome presence/absence matrix and heatmap.

Constructs a binary genome × gene presence/absence matrix from the hits
table, computes summary statistics (core genes, accessory genes), and
exports both the matrix TSV and a publication-quality PNG heatmap.

Example
-------
    python3 scripts/10_matrix.py --hits results/hits_main.tsv --out-dir results/
    python3 scripts/10_matrix.py --hits hits.tsv --tiers high_confidence putative
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from pipeline.matrix import build_matrix, matrix_stats, heatmap_png
from pipeline.utils import ensure_tools_on_path


def parse_args():
    p = argparse.ArgumentParser(
        description="Build genome presence/absence matrix and heatmap PNG.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--hits",    required=True,  type=Path,
                   help="Hits TSV (output of 05_classify_hits.py or 04_score_hits.py).")
    p.add_argument("--out-dir", default=Path("results"), type=Path,
                   help="Output directory.")
    p.add_argument("--tiers",   nargs="+",
                   default=["high_confidence", "putative", "divergent"],
                   metavar="TIER",
                   help="Confidence tiers to include in the matrix. "
                        "Options: high_confidence putative divergent likely_fp.")
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

    print(f"\n=== Step 10: Presence/Absence Matrix ===")
    print(f"  Input : {hits_path}")
    print(f"  Tiers : {', '.join(args.tiers)}")

    hits_df = pd.read_csv(hits_path, sep="\t")
    print(f"  Loaded: {len(hits_df)} rows")

    if hits_df.empty:
        print("WARNING: Input is empty.", file=sys.stderr)
        sys.exit(0)

    matrix = build_matrix(hits_df, confidence_tiers=args.tiers)

    if matrix.empty:
        print("WARNING: Matrix is empty — no matching data.", file=sys.stderr)
        sys.exit(0)

    matrix_out = out_dir / "presence_absence_matrix.tsv"
    matrix.to_csv(matrix_out, sep="\t")
    print(f"\n  Matrix ({matrix.shape[0]} genomes × {matrix.shape[1]} genes) -> {matrix_out}")

    stats = matrix_stats(matrix)
    print("\n--- Matrix statistics ---")
    print(f"  Genomes            : {stats['n_genomes']}")
    print(f"  Genes              : {stats['n_genes']}")
    print(f"  Avg genes/genome   : {stats['avg_genes_per_genome']}")
    print(f"  Avg genomes/gene   : {stats['avg_genomes_per_gene']}")
    if stats["core_genes"]:
        print(f"  Core genes (>90%) : {', '.join(stats['core_genes'][:10])}"
              + ("..." if len(stats["core_genes"]) > 10 else ""))
    if stats["accessory_genes"]:
        print(f"  Accessory (<10%)  : {len(stats['accessory_genes'])} genes")

    heatmap_out = out_dir / "presence_absence_heatmap.png"
    print(f"\n  Rendering heatmap -> {heatmap_out}")
    png_bytes = heatmap_png(matrix, out_path=heatmap_out)
    if png_bytes:
        heatmap_out.write_bytes(png_bytes)
        print(f"  Heatmap PNG -> {heatmap_out}  ({len(png_bytes):,} bytes)")
    else:
        print("WARNING: heatmap_png returned empty bytes.", file=sys.stderr)

    print(f"\nDone. Outputs in: {out_dir}")
    sys.exit(0)


if __name__ == "__main__":
    main()
