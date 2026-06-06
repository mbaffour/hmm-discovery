#!/usr/bin/env python3
"""
09_phylogeny.py — Maximum-likelihood phylogenetic tree with IQ-TREE.
====================================================================

WHAT THIS STEP DOES (the biology)
---------------------------------
A phylogenetic tree shows how your sequences are related by descent — which hits
are close cousins, which form their own deep-branching clade, and whether your
seeds and new hits intermingle (good: they are one family) or split apart (a
warning: you may have lumped two families together). IQ-TREE infers a
maximum-likelihood tree: it searches for the tree topology and branch lengths
that make the observed alignment most probable under a model of amino-acid
substitution.

Ultra-fast bootstrap (UFBoot, the -B option) repeats the inference on resampled
columns to put confidence values on each branch — high values mean the split is
well supported by the data.

WHAT THE KEY PARAMETERS MEAN
----------------------------
    --aln        An ALIGNED protein FASTA (the tree is inferred from columns).
    --model      Substitution model, or TEST to let IQ-TREE pick the best fit.
    --bootstrap  Number of UFBoot replicates (branch support).
    --cpu        Threads for the (CPU-heavy) tree search.

OUTPUTS
-------
    results/iqtree.*   IQ-TREE files (.treefile, .iqtree log, etc.)
    results/tree.png   rendered tree figure (matplotlib + Bio.Phylo)
    results/tree.svg   vector tree figure for manuscripts

INTERACTIVITY
-------------
Run it in a terminal with no/partial arguments and it becomes a guided wizard,
shows the exact iqtree2 command, and confirms before the (slow) inference. Pipe
it or pass --yes for hands-off operation (safe for HPC / run_pipeline.py).

EXAMPLES
--------
    # Guided — the script will interview you:
    python3 scripts/09_phylogeny.py

    # Explicit:
    python3 scripts/09_phylogeny.py --aln results/seeds_aligned.faa --out-dir results/

    # Fixed model, more bootstraps, hands-off:
    python3 scripts/09_phylogeny.py --aln hits_aligned.faa --model LG+G4 --bootstrap 1000 --cpu 8 --yes
"""
import argparse
import sys
from pathlib import Path

# Make the app package importable no matter what directory we are run from,
# and make cli_common (which lives beside this script) importable too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.phylo import run_iqtree, render_tree
from pipeline.utils import ensure_tools_on_path
from cli_common import Guide, add_common_args


def parse_args():
    p = argparse.ArgumentParser(
        description="Build a maximum-likelihood phylogenetic tree with IQ-TREE.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Not required=True: a human in a terminal can supply these via the wizard.
    p.add_argument("--aln",       type=Path,
                   help="Aligned protein FASTA (output of 01_align.py).")
    p.add_argument("--out-dir",   default=Path("results"), type=Path,
                   help="Output directory.")
    p.add_argument("--model",     default="TEST",
                   help="Substitution model, or TEST for automatic selection.")
    p.add_argument("--bootstrap", default=1000,   type=int,
                   help="Number of ultra-fast bootstrap replicates (UFBoot, -B).")
    p.add_argument("--cpu",       default=4,      type=int,
                   help="Number of CPU threads.")
    add_common_args(p)          # --yes / --interactive / --no-color / --explain-only
    return p.parse_args()


def main():
    args = parse_args()
    guide = Guide.from_args(args)
    ensure_tools_on_path()

    guide.header(9, "Phylogenetic Tree",
                 "Infer how your sequences are related with a maximum-likelihood tree.")

    # ── GUIDED WIZARD ────────────────────────────────────────────────────
    if guide.interactive and args.aln is None:
        guide.wizard_intro("Let's build a phylogenetic tree.")
        args.aln = guide.ask_path(
            "Path to your aligned FASTA?",
            default="results/seeds_aligned.faa",
            help_text="Must be ALIGNED (e.g. from 01_align.py).",
        )
        args.model = guide.ask_choice(
            "Substitution model?",
            [
                ("TEST",  "TEST — let IQ-TREE pick the best-fit model (recommended)"),
                ("LG+G4", "LG+G4 — common protein model, skips model selection"),
                ("WAG",   "WAG — older protein model"),
            ],
            default_index=0,
            help_text="TEST is safest but a little slower.",
        )
        args.bootstrap = int(guide.ask(
            "Number of ultra-fast bootstrap replicates?",
            default=str(args.bootstrap),
            help_text="1000 is standard; more = steadier support values, slower.",
        ))

    # ── Validate (works in both modes) ───────────────────────────────────
    if args.aln is None:
        guide.error("No --aln given. Provide one, or run in a terminal for the wizard.")
        sys.exit(2)

    aln = args.aln.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not aln.exists():
        guide.error(f"Alignment not found: {aln}")
        sys.exit(1)

    guide.narrate(f"Input    : {aln.name}")
    guide.narrate(f"Model    : {args.model}")
    guide.narrate(f"Bootstrap: {args.bootstrap}")
    guide.narrate(f"CPU      : {args.cpu}")

    iqtree_prefix = out_dir / "iqtree"

    # ── EXPLAIN-AND-CONFIRM ──────────────────────────────────────────────
    guide.command(
        f"iqtree2 -s {aln} -m {args.model} -T {args.cpu} "
        f"-B {args.bootstrap} --prefix {iqtree_prefix} -redo",
        "Infer the ML tree and branch support. This can be slow on large alignments.")
    if guide.confirm("Run IQ-TREE now?") != "yes":
        guide.warn("Tree inference skipped — nothing written.")
        sys.exit(0)

    guide.narrate("Running IQ-TREE …")
    result = run_iqtree(
        aln_path=aln,
        out_dir=out_dir,
        model=args.model,
        bootstrap=args.bootstrap,
        cpu=args.cpu,
    )

    if not result.get("success"):
        guide.error(f"IQ-TREE failed: {result.get('error', 'unknown error')}")
        sys.exit(1)

    treefile = result.get("treefile")
    guide.result(f"Tree file → {treefile}")
    guide.detail(f"Log file  : {result.get('logfile')}")
    guide.detail(f"Model used: {result.get('model_used', 'unknown')}")

    # ── Render tree image (best-effort; missing libs are non-fatal) ──────
    tree_png = out_dir / "tree.png"
    guide.narrate(f"Rendering tree image → {tree_png}")
    # Load a hits table if one exists so tip labels can be coloured by
    # confidence tier (and the legend populated). Optional — None is fine.
    hits_for_tree = None
    for cand in (out_dir / "hits_main.tsv", out_dir / "hits_scored.tsv"):
        if cand.exists():
            try:
                import pandas as _pd
                hits_for_tree = _pd.read_csv(cand, sep="\t")
                break
            except Exception:
                pass
    try:
        render_result = render_tree(
            treefile=treefile,
            hits_df=hits_for_tree,
            out_dir=out_dir,
        )
        if render_result.get("success"):
            guide.result(f"Tree PNG → {render_result.get('png_path')}")
            if render_result.get("svg_path"):
                guide.detail(f"Tree SVG → {render_result.get('svg_path')}")
        else:
            guide.warn(f"Tree rendering: {render_result.get('error', 'failed')}")
    except Exception as exc:
        guide.warn(f"Tree rendering skipped: {exc}")

    guide.done(f"Phylogeny complete. Outputs in: {out_dir}")
    guide.detail("Next: 10_matrix.py / 14_report.py incorporate the tree and hits.")
    sys.exit(0)


if __name__ == "__main__":
    main()
