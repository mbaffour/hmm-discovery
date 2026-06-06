#!/usr/bin/env python3
"""
01_align.py — Multiple sequence alignment of seed sequences.

Runs MAFFT or Clustal Omega on an input FASTA and optionally trims
the alignment with trimAl. Prints alignment quality statistics on
completion.

Example
-------
    python3 scripts/01_align.py --seeds seeds.faa --out-dir results/
    python3 scripts/01_align.py --seeds seeds.faa --tool clustalo --trim --threads 8
"""
import argparse
import sys
from pathlib import Path

# Allow imports from the app root (pipeline/, core/, etc.)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.alignment import run_mafft, run_clustalo, run_trimal, alignment_quality
from pipeline.utils import ensure_tools_on_path


def parse_args():
    p = argparse.ArgumentParser(
        description="Align seed sequences with MAFFT or Clustal Omega, "
                    "optionally trim with trimAl.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--seeds",   required=True,  type=Path,
                   help="Input un-aligned seed protein FASTA.")
    p.add_argument("--out-dir", default=Path("results"), type=Path,
                   help="Output directory for aligned (and trimmed) FASTA files.")
    p.add_argument("--tool",    default="mafft", choices=["mafft", "clustalo"],
                   help="Alignment tool to use.")
    p.add_argument("--trim",    action="store_true",
                   help="Run trimAl (--automated1) after alignment.")
    p.add_argument("--threads", default=4, type=int,
                   help="Number of CPU threads to pass to the aligner.")
    return p.parse_args()


def main():
    args = parse_args()
    ensure_tools_on_path()

    seeds = args.seeds.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not seeds.exists():
        print(f"ERROR: Seeds FASTA not found: {seeds}", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== Step 1: Multiple Sequence Alignment ===")
    print(f"  Input  : {seeds}")
    print(f"  Tool   : {args.tool}")
    print(f"  Threads: {args.threads}")
    print(f"  Trim   : {args.trim}")
    print(f"  Out dir: {out_dir}")

    aln_out = out_dir / "seeds_aligned.faa"

    if args.tool == "mafft":
        print(f"\n[CMD] mafft --auto --thread {args.threads} {seeds} > {aln_out}")
        result = run_mafft(seeds, aln_out, cpu=args.threads)
    else:
        print(f"\n[CMD] clustalo -i {seeds} -o {aln_out} --threads {args.threads} --force")
        result = run_clustalo(seeds, aln_out, cpu=args.threads)

    if not result or not result.exists():
        print("ERROR: Alignment failed — no output produced.", file=sys.stderr)
        sys.exit(1)

    print(f"  Aligned output: {aln_out}")

    final_aln = aln_out

    if args.trim:
        trimmed_out = out_dir / "seeds_trimmed.faa"
        print(f"\n[CMD] trimal -in {aln_out} -out {trimmed_out} -automated1")
        trimmed = run_trimal(aln_out, trimmed_out)
        if not trimmed or not trimmed.exists():
            print("WARNING: trimAl failed; using untrimmed alignment.", file=sys.stderr)
        else:
            print(f"  Trimmed output: {trimmed_out}")
            final_aln = trimmed_out

    print("\n--- Alignment quality ---")
    stats = alignment_quality(final_aln)
    print(f"  Sequences      : {stats['n_sequences']}")
    print(f"  Alignment length: {stats['aln_length']} columns")
    print(f"  Gap percentage : {stats['gap_pct']}%")
    print(f"  Conserved cols : {stats['conserved_columns']}")
    print(f"  Avg pairwise ID: {stats['avg_pairwise_id']}%")
    if stats["flagged_sequences"]:
        print(f"  Flagged (>80% gap): {', '.join(stats['flagged_sequences'])}")

    print(f"\nDone. Final alignment: {final_aln}")
    sys.exit(0)


if __name__ == "__main__":
    main()
