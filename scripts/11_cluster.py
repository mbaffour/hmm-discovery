#!/usr/bin/env python3
"""
11_cluster.py — Cluster hit sequences with CD-HIT or MMseqs2.

Dispatches to CD-HIT first (if available), then MMseqs2. Produces cluster
representative sequences, a full membership table, and a per-cluster summary.

Example
-------
    python3 scripts/11_cluster.py --faa results/hits_proteins.faa --out-dir results/
    python3 scripts/11_cluster.py --faa hits.faa --tool cd-hit --identity 0.5 --cpu 8
    python3 scripts/11_cluster.py --faa hits.faa --tool mmseqs2 --identity 0.3 --coverage 0.8
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.clustering import cluster_dispatch, cluster_cdhit, cluster_mmseqs, cluster_summary
from pipeline.utils import ensure_tools_on_path, find_tool


def parse_args():
    p = argparse.ArgumentParser(
        description="Cluster protein sequences with CD-HIT or MMseqs2.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--faa",      required=True,  type=Path,
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
    return p.parse_args()


def main():
    args = parse_args()
    ensure_tools_on_path()

    faa = args.faa.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not faa.exists():
        print(f"ERROR: FASTA not found: {faa}", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== Step 11: Sequence Clustering ===")
    print(f"  Input    : {faa}")
    print(f"  Tool     : {args.tool}")
    print(f"  Identity : {args.identity}")
    print(f"  Coverage : {args.coverage}")
    print(f"  CPU      : {args.cpu}")

    kwargs = dict(identity=args.identity, coverage=args.coverage, threads=args.cpu)

    if args.tool == "cd-hit":
        if not find_tool("cd-hit"):
            print("ERROR: cd-hit not found on PATH.", file=sys.stderr)
            sys.exit(1)
        print(f"\n[CMD] cd-hit -i {faa} -o {out_dir}/cdhit_clusters "
              f"-c {args.identity} -aL {args.coverage} -T {args.cpu}")
        result = cluster_cdhit(faa, out_dir, **kwargs)
    elif args.tool == "mmseqs2":
        if not find_tool("mmseqs"):
            print("ERROR: mmseqs not found on PATH.", file=sys.stderr)
            sys.exit(1)
        print(f"\n[CMD] mmseqs easy-cluster {faa} {out_dir}/mmseqs_clusters "
              f"{out_dir}/mmseqs_tmp --min-seq-id {args.identity} -c {args.coverage} "
              f"--threads {args.cpu}")
        result = cluster_mmseqs(faa, out_dir, **kwargs)
    else:
        print(f"\n[CMD] cd-hit / mmseqs (auto-selected) with identity={args.identity} "
              f"coverage={args.coverage} threads={args.cpu}")
        result = cluster_dispatch(faa, out_dir, **kwargs)

    if result.get("error"):
        print(f"ERROR: Clustering failed: {result['error']}", file=sys.stderr)
        sys.exit(1)

    n_clusters = result.get("n_clusters", 0)
    membership_df = result.get("membership_df")
    rep_faa = result.get("rep_faa")

    print(f"\n  Clusters formed: {n_clusters}")

    # Save membership table
    membership_out = out_dir / "cluster_membership.tsv"
    if membership_df is not None and not membership_df.empty:
        membership_df.to_csv(membership_out, sep="\t", index=False)
        print(f"  Membership table -> {membership_out}  ({len(membership_df)} rows)")

    # Save cluster summary
    summary_df = cluster_summary(membership_df) if membership_df is not None else None
    summary_out = out_dir / "cluster_summary.tsv"
    if summary_df is not None and not summary_df.empty:
        summary_df.to_csv(summary_out, sep="\t", index=False)
        print(f"  Cluster summary  -> {summary_out}")

    # Copy representative FASTA to standard output name
    reps_out = out_dir / "cluster_reps.faa"
    if rep_faa:
        rep_path = Path(rep_faa)
        # CD-HIT writes rep sequences to path without extension; check both
        for candidate in [rep_path, Path(str(rep_path) + ".faa")]:
            if candidate.exists():
                shutil.copy(candidate, reps_out)
                print(f"  Representatives  -> {reps_out}")
                break

    print(f"\nDone. Outputs in: {out_dir}")
    sys.exit(0)


if __name__ == "__main__":
    main()
