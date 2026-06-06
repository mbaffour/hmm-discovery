#!/usr/bin/env python3
"""
11_cluster.py — Group hit sequences into clusters with CD-HIT or MMseqs2.
=========================================================================

WHAT THIS STEP DOES (the biology)
---------------------------------
A search can return hundreds of hits, but many are near-identical copies of the
same protein. Clustering collapses that redundancy: it groups sequences that are
similar above an identity threshold and picks one REPRESENTATIVE per group. This
gives you (a) a non-redundant sequence set for downstream analyses, and (b) a
sense of how many genuinely distinct variants of the family exist.

    * CD-HIT   — very fast greedy clustering; the usual first choice.
    * MMseqs2  — sensitive, scales to very large sets.
    * auto     — try CD-HIT, fall back to MMseqs2 if it is not installed.

WHAT THE KEY PARAMETERS MEAN
----------------------------
    --identity  Sequences this similar (or more) join the same cluster. Lower =
                broader clusters (e.g. 0.4 groups distant relatives together).
    --coverage  Minimum alignment coverage of the shorter sequence — stops short
                fragments from being merged with long proteins by accident.
    --tool      auto / cd-hit / mmseqs2.

OUTPUTS
-------
    results/cluster_reps.faa        one representative sequence per cluster
    results/cluster_membership.tsv  which sequence belongs to which cluster
    results/cluster_summary.tsv     per-cluster size and representative

INTERACTIVITY
-------------
Run it in a terminal with no/partial arguments and it becomes a guided wizard,
shows the exact tool command, and confirms before running. Pipe it or pass --yes
for hands-off operation (safe for HPC / run_pipeline.py). See cli_common.py.

EXAMPLES
--------
    # Guided — the script will interview you:
    python3 scripts/11_cluster.py

    # Explicit / hands-off:
    python3 scripts/11_cluster.py --faa results/hits_proteins.faa --out-dir results/ --yes

    # MMseqs2 at 30% identity:
    python3 scripts/11_cluster.py --faa hits.faa --tool mmseqs2 --identity 0.3 --coverage 0.8
"""
import argparse
import shutil
import sys
from pathlib import Path

# Make the app package importable no matter what directory we are run from,
# and make cli_common (which lives beside this script) importable too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.clustering import cluster_dispatch, cluster_cdhit, cluster_mmseqs, cluster_summary
from pipeline.utils import ensure_tools_on_path, find_tool
from cli_common import Guide, add_common_args


def parse_args():
    p = argparse.ArgumentParser(
        description="Cluster protein sequences with CD-HIT or MMseqs2.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Not required=True: a human in a terminal can supply this via the wizard.
    p.add_argument("--faa",      type=Path,
                   help="Input protein FASTA (e.g. hits_proteins.faa from 05_classify_hits.py).")
    p.add_argument("--out-dir",  default=Path("results"), type=Path,
                   help="Output directory.")
    p.add_argument("--tool",     default="auto", choices=["auto", "cd-hit", "mmseqs2"],
                   help="Clustering tool. 'auto' tries cd-hit then mmseqs2.")
    p.add_argument("--identity", default=0.40,   type=float,
                   help="Sequence identity threshold (0–1).")
    p.add_argument("--coverage", default=0.80,   type=float,
                   help="Alignment coverage threshold for the shorter sequence (0–1).")
    p.add_argument("--cpu",      default=4,      type=int,
                   help="Number of CPU threads.")
    add_common_args(p)          # --yes / --interactive / --no-color / --explain-only
    return p.parse_args()


def main():
    args = parse_args()
    guide = Guide.from_args(args)
    ensure_tools_on_path()

    guide.header(11, "Sequence Clustering",
                 "Collapse redundant hits into clusters and pick a representative each.")

    # ── GUIDED WIZARD ────────────────────────────────────────────────────
    if guide.interactive and args.faa is None:
        guide.wizard_intro("Let's cluster the hit sequences.")
        args.faa = guide.ask_path(
            "Path to your protein FASTA?",
            default="results/hits_proteins.faa",
            help_text="hits_proteins.faa from 05_classify_hits.py.",
        )
        args.tool = guide.ask_choice(
            "Which clustering tool?",
            [
                ("auto",    "auto — CD-HIT if available, else MMseqs2 (recommended)"),
                ("cd-hit",  "cd-hit — fast greedy clustering"),
                ("mmseqs2", "mmseqs2 — sensitive, scales to huge sets"),
            ],
            default_index=0,
        )
        args.identity = float(guide.ask_choice(
            "Identity threshold?",
            [
                ("0.40", "0.40 — broad clusters, group distant relatives (default)"),
                ("0.70", "0.70 — tighter clusters"),
                ("0.90", "0.90 — near-duplicates only"),
            ],
            default_index=0,
            help_text="Sequences this similar or more join the same cluster.",
        ))

    # ── Validate (works in both modes) ───────────────────────────────────
    if args.faa is None:
        guide.error("No --faa given. Provide one, or run in a terminal for the wizard.")
        sys.exit(2)

    faa = args.faa.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not faa.exists():
        guide.error(f"FASTA not found: {faa}")
        sys.exit(1)

    guide.narrate(f"Input    : {faa.name}")
    guide.narrate(f"Tool     : {args.tool}")
    guide.narrate(f"Identity : {args.identity}")
    guide.narrate(f"Coverage : {args.coverage}")
    guide.narrate(f"CPU      : {args.cpu}")

    kwargs = dict(identity=args.identity, coverage=args.coverage, threads=args.cpu)

    # ── EXPLAIN-AND-CONFIRM + dispatch to the requested tool ─────────────
    if args.tool == "cd-hit":
        if not find_tool("cd-hit"):
            guide.error("cd-hit not found on PATH.")
            sys.exit(1)
        guide.command(f"cd-hit -i {faa} -o {out_dir}/cdhit_clusters "
                      f"-c {args.identity} -aL {args.coverage} -T {args.cpu}",
                      "Greedy clustering at the chosen identity/coverage.")
    elif args.tool == "mmseqs2":
        if not find_tool("mmseqs"):
            guide.error("mmseqs not found on PATH.")
            sys.exit(1)
        guide.command(f"mmseqs easy-cluster {faa} {out_dir}/mmseqs_clusters "
                      f"{out_dir}/mmseqs_tmp --min-seq-id {args.identity} -c {args.coverage} "
                      f"--threads {args.cpu}",
                      "Sensitive clustering at the chosen identity/coverage.")
    else:
        guide.command(f"cd-hit / mmseqs (auto) identity={args.identity} "
                      f"coverage={args.coverage} threads={args.cpu}",
                      "Try CD-HIT first; fall back to MMseqs2 if it is not installed.")

    if guide.confirm("Run clustering now?") != "yes":
        guide.warn("Clustering skipped — nothing written.")
        sys.exit(0)

    guide.narrate("Clustering …")
    if args.tool == "cd-hit":
        result = cluster_cdhit(faa, out_dir, **kwargs)
    elif args.tool == "mmseqs2":
        result = cluster_mmseqs(faa, out_dir, **kwargs)
    else:
        result = cluster_dispatch(faa, out_dir, **kwargs)

    if result.get("error"):
        guide.error(f"Clustering failed: {result['error']}")
        sys.exit(1)

    n_clusters = result.get("n_clusters", 0)
    membership_df = result.get("membership_df")
    rep_faa = result.get("rep_faa")

    # ── NARRATE: interpret the result ────────────────────────────────────
    n_in = membership_df is not None and len(membership_df) or 0
    guide.result(f"Clusters formed: {n_clusters}")
    if membership_df is not None and not membership_df.empty and n_clusters:
        ratio = len(membership_df) / n_clusters
        guide.detail(f"{len(membership_df)} sequences → {n_clusters} clusters "
                     f"(~{ratio:.1f} sequences per cluster).")
        if ratio > 3:
            guide.detail("High redundancy — many near-duplicate hits collapsed.")
        elif ratio < 1.2:
            guide.detail("Low redundancy — most hits are distinct variants.")

    # Save membership table.
    membership_out = out_dir / "cluster_membership.tsv"
    if membership_df is not None and not membership_df.empty:
        membership_df.to_csv(membership_out, sep="\t", index=False)
        guide.result(f"Membership table → {membership_out}  ({len(membership_df)} rows)")

    # Save cluster summary.
    summary_df = cluster_summary(membership_df) if membership_df is not None else None
    summary_out = out_dir / "cluster_summary.tsv"
    if summary_df is not None and not summary_df.empty:
        summary_df.to_csv(summary_out, sep="\t", index=False)
        guide.result(f"Cluster summary → {summary_out}")

    # Copy representative FASTA to the standard output name.
    reps_out = out_dir / "cluster_reps.faa"
    if rep_faa:
        rep_path = Path(rep_faa)
        # CD-HIT writes rep sequences to a path without extension; check both.
        for candidate in [rep_path, Path(str(rep_path) + ".faa")]:
            if candidate.exists():
                shutil.copy(candidate, reps_out)
                guide.result(f"Representatives → {reps_out}")
                break

    guide.done(f"Clustering complete. Outputs in: {out_dir}")
    guide.detail("Next: 12_motifs.py / 13_annotate.py can run on cluster_reps.faa.")
    sys.exit(0)


if __name__ == "__main__":
    main()
