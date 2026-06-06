#!/usr/bin/env python3
"""
09_phylogeny.py — Maximum-likelihood phylogenetic tree with IQ-TREE.

Runs IQ-TREE2 (or iqtree) on an aligned protein FASTA and optionally
renders a labelled tree figure with toytree/toyplot.

Example
-------
    python3 scripts/09_phylogeny.py --aln results/seeds_aligned.faa --out-dir results/
    python3 scripts/09_phylogeny.py --aln hits_aligned.faa --model LG+G4 --bootstrap 1000 --cpu 8
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.phylo import run_iqtree, render_tree
from pipeline.utils import ensure_tools_on_path


def parse_args():
    p = argparse.ArgumentParser(
        description="Build a maximum-likelihood phylogenetic tree with IQ-TREE.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--aln",       required=True,  type=Path,
                   help="Aligned protein FASTA (output of 01_align.py).")
    p.add_argument("--out-dir",   default=Path("results"), type=Path,
                   help="Output directory.")
    p.add_argument("--model",     default="TEST",
                   help="Substitution model, or TEST for automatic selection.")
    p.add_argument("--bootstrap", default=1000,   type=int,
                   help="Number of ultra-fast bootstrap replicates (UFBoot, -B).")
    p.add_argument("--cpu",       default=4,      type=int,
                   help="Number of CPU threads.")
    return p.parse_args()


def main():
    args = parse_args()
    ensure_tools_on_path()

    aln = args.aln.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not aln.exists():
        print(f"ERROR: Alignment not found: {aln}", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== Step 9: Phylogenetic Tree ===")
    print(f"  Input    : {aln}")
    print(f"  Model    : {args.model}")
    print(f"  Bootstrap: {args.bootstrap}")
    print(f"  CPU      : {args.cpu}")

    iqtree_prefix = out_dir / "iqtree"
    print(f"\n[CMD] iqtree2 -s {aln} -m {args.model} -T {args.cpu} "
          f"-B {args.bootstrap} --prefix {iqtree_prefix} -redo")

    result = run_iqtree(
        aln_path=aln,
        out_dir=out_dir,
        model=args.model,
        bootstrap=args.bootstrap,
        cpu=args.cpu,
    )

    if not result.get("success"):
        print(f"ERROR: IQ-TREE failed: {result.get('error', 'unknown error')}", file=sys.stderr)
        sys.exit(1)

    treefile = result.get("treefile")
    print(f"\n  Tree file : {treefile}")
    print(f"  Log file  : {result.get('logfile')}")
    print(f"  Model used: {result.get('model_used', 'unknown')}")

    # Render tree image
    tree_png = out_dir / "tree.png"
    print(f"\n  Rendering tree image -> {tree_png}")
    try:
        render_result = render_tree(
            treefile=treefile,
            hits_df=None,
            out_dir=out_dir,
        )
        if render_result.get("success"):
            print(f"  Tree PNG  : {render_result.get('figure_path')}")
        else:
            print(f"  Tree rendering: {render_result.get('error', 'failed')} "
                  f"(toytree/toyplot may not be installed)", file=sys.stderr)
    except Exception as exc:
        print(f"  Tree rendering skipped: {exc}", file=sys.stderr)

    print(f"\nDone. Outputs in: {out_dir}")
    sys.exit(0)


if __name__ == "__main__":
    main()
