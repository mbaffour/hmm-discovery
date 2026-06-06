#!/usr/bin/env python3
"""
10_matrix.py — Build a genome × gene presence/absence matrix and heatmap.
=========================================================================

WHAT THIS STEP DOES (the biology)
---------------------------------
A presence/absence matrix turns your hit list into a comparative-genomics view:
rows are genomes, columns are genes (or gene clusters), and each cell is 1 if
that genome carries that gene and 0 if it doesn't. From this you can read off
the pan-genome structure at a glance:

    * CORE genes      — present in almost every genome (>90%): the conserved
      backbone of the family.
    * ACCESSORY genes — present in only a few (<10%): variable, often lineage-
      specific or recently acquired.

The matrix is exported as a TSV and as a clustered heatmap PNG suitable for a
figure. You choose which confidence tiers to include so noise (likely_fp) can be
excluded.

WHAT THE KEY PARAMETERS MEAN
----------------------------
    --hits   The canonical hits table (05) or scored hits (04).
    --tiers  Which confidence tiers to count as "present" (default excludes
             likely_fp). Options: high_confidence putative divergent likely_fp.

OUTPUTS
-------
    results/presence_absence_matrix.tsv   the binary genome × gene matrix
    results/presence_absence_heatmap.png  clustered heatmap figure

INTERACTIVITY
-------------
Run it in a terminal with no/partial arguments and it becomes a guided wizard,
then narrates core/accessory statistics. Pipe it or pass --yes for hands-off
operation (safe for HPC / run_pipeline.py). See cli_common.py.

EXAMPLES
--------
    # Guided — the script will interview you:
    python3 scripts/10_matrix.py

    # Explicit / hands-off:
    python3 scripts/10_matrix.py --hits results/hits_main.tsv --out-dir results/ --yes

    # Only the strongest tiers:
    python3 scripts/10_matrix.py --hits hits.tsv --tiers high_confidence putative
"""
import argparse
import sys
from pathlib import Path

# Make the app package importable no matter what directory we are run from,
# and make cli_common (which lives beside this script) importable too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from pipeline.matrix import build_matrix, matrix_stats, heatmap_png
from pipeline.utils import ensure_tools_on_path
from cli_common import Guide, add_common_args


def parse_args():
    p = argparse.ArgumentParser(
        description="Build genome presence/absence matrix and heatmap PNG.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Not required=True: a human in a terminal can supply this via the wizard.
    p.add_argument("--hits",    type=Path,
                   help="Hits TSV (output of 05_classify_hits.py or 04_score_hits.py).")
    p.add_argument("--out-dir", default=Path("results"), type=Path,
                   help="Output directory.")
    p.add_argument("--tiers",   nargs="+",
                   default=["high_confidence", "putative", "divergent"],
                   metavar="TIER",
                   help="Confidence tiers to include in the matrix. "
                        "Options: high_confidence putative divergent likely_fp.")
    add_common_args(p)          # --yes / --interactive / --no-color / --explain-only
    return p.parse_args()


def main():
    args = parse_args()
    guide = Guide.from_args(args)
    ensure_tools_on_path()

    guide.header(10, "Presence/Absence Matrix",
                 "Turn the hit list into a genome × gene matrix and a heatmap figure.")

    # ── GUIDED WIZARD ────────────────────────────────────────────────────
    if guide.interactive and args.hits is None:
        guide.wizard_intro("Let's build the presence/absence matrix.")
        args.hits = guide.ask_path(
            "Path to your hits TSV?",
            default="results/hits_main.tsv",
            help_text="The canonical hits table from 05_classify_hits.py.",
        )
        include_weak = guide.ask_yesno(
            "Include divergent hits in the matrix?",
            default_yes=True,
            help_text="No → only high_confidence + putative (cleaner, fewer genes).",
        )
        if not include_weak:
            args.tiers = ["high_confidence", "putative"]

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

    guide.narrate(f"Input : {hits_path.name}")
    guide.narrate(f"Tiers : {', '.join(args.tiers)}")

    hits_df = pd.read_csv(hits_path, sep="\t")
    guide.detail(f"Loaded {len(hits_df)} rows.")

    if hits_df.empty:
        guide.warn("Input is empty — nothing to build.")
        sys.exit(0)

    # ── EXPLAIN-AND-CONFIRM ──────────────────────────────────────────────
    guide.command(f"build_matrix(tiers={args.tiers}) → heatmap_png()",
                  "Pivot the hits into a binary genome × gene matrix and render a heatmap.")
    if guide.confirm("Build the matrix now?") != "yes":
        guide.warn("Matrix build skipped — nothing written.")
        sys.exit(0)

    guide.narrate("Building presence/absence matrix …")
    matrix = build_matrix(hits_df, confidence_tiers=args.tiers)

    if matrix.empty:
        guide.warn("Matrix is empty — no rows matched the chosen tiers.")
        guide.detail("Try including more tiers (e.g. add 'divergent').")
        sys.exit(0)

    matrix_out = out_dir / "presence_absence_matrix.tsv"
    matrix.to_csv(matrix_out, sep="\t")
    guide.result(f"Matrix ({matrix.shape[0]} genomes × {matrix.shape[1]} genes) → {matrix_out}")

    # ── NARRATE: interpret the pan-genome structure ──────────────────────
    stats = matrix_stats(matrix)
    guide.header(None, "Matrix statistics")
    guide.narrate(f"Genomes          : {stats['n_genomes']}")
    guide.narrate(f"Genes            : {stats['n_genes']}")
    guide.narrate(f"Avg genes/genome : {stats['avg_genes_per_genome']}")
    guide.narrate(f"Avg genomes/gene : {stats['avg_genomes_per_gene']}")
    if stats["core_genes"]:
        shown = ', '.join(stats['core_genes'][:10]) + ("…" if len(stats["core_genes"]) > 10 else "")
        guide.result(f"Core genes (>90% of genomes): {shown}")
    else:
        guide.detail("No core genes — the family is patchily distributed across genomes.")
    if stats["accessory_genes"]:
        guide.detail(f"Accessory genes (<10% of genomes): {len(stats['accessory_genes'])}")

    # ── Heatmap figure ───────────────────────────────────────────────────
    heatmap_out = out_dir / "presence_absence_heatmap.png"
    guide.narrate(f"Rendering heatmap → {heatmap_out}")
    png_bytes = heatmap_png(matrix, out_path=heatmap_out)
    if png_bytes:
        heatmap_out.write_bytes(png_bytes)
        guide.result(f"Heatmap PNG → {heatmap_out}  ({len(png_bytes):,} bytes)")
    else:
        guide.warn("heatmap_png returned empty bytes (plotting backend may be missing).")

    guide.done(f"Matrix complete. Outputs in: {out_dir}")
    guide.detail("Next: 11_cluster.py groups the hit sequences, or 14_report.py compiles results.")
    sys.exit(0)


if __name__ == "__main__":
    main()
