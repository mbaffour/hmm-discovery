#!/usr/bin/env python3
"""
02_build_hmm.py — Build a profile HMM from a multiple sequence alignment.

Runs hmmbuild on an aligned FASTA and prints key HMM statistics
(length, number of sequences, alphabet, checksum).

Example
-------
    python3 scripts/02_build_hmm.py --aln results/seeds_aligned.faa --out-dir results/
    python3 scripts/02_build_hmm.py --aln seeds_trimmed.faa --name my_gene --out-dir hmm_out/
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.hmm_builder import run_hmmbuild
from pipeline.utils import ensure_tools_on_path


def parse_args():
    p = argparse.ArgumentParser(
        description="Build a HMMER3 profile HMM from an aligned FASTA file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--aln",     required=True,  type=Path,
                   help="Input aligned protein FASTA (output of 01_align.py).")
    p.add_argument("--out-dir", default=Path("results"), type=Path,
                   help="Output directory; profile.hmm is written here.")
    p.add_argument("--name",    default="novel_phage_gene",
                   help="Name embedded in the HMM (passed to hmmbuild --name).")
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

    hmm_out = out_dir / "profile.hmm"

    print(f"\n=== Step 2: Build HMM ===")
    print(f"  Input   : {aln}")
    print(f"  HMM name: {args.name}")
    print(f"  Output  : {hmm_out}")

    print(f"\n[CMD] hmmbuild -n {args.name} {hmm_out} {aln}")
    stats = run_hmmbuild(aln, hmm_out, hmm_name=args.name)

    if not stats:
        print("ERROR: hmmbuild failed — no stats returned.", file=sys.stderr)
        sys.exit(1)

    if not hmm_out.exists():
        print(f"ERROR: Expected output not found: {hmm_out}", file=sys.stderr)
        sys.exit(1)

    print("\n--- HMM statistics ---")
    print(f"  Name      : {stats.get('name', args.name)}")
    print(f"  Length    : {stats.get('leng', 'n/a')} match states")
    print(f"  Sequences : {stats.get('nseq', 'n/a')}")
    print(f"  Alphabet  : {stats.get('alph', 'n/a')}")
    print(f"  Checksum  : {stats.get('cksum', 'n/a')}")
    if stats.get("hmmbuild_version"):
        print(f"  HMMER     : {stats['hmmbuild_version']}")

    print(f"\nDone. Profile HMM written to: {hmm_out}")
    sys.exit(0)


if __name__ == "__main__":
    main()
