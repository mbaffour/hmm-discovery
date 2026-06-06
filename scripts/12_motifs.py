#!/usr/bin/env python3
"""
12_motifs.py — De-novo motif discovery with MEME and scanning with FIMO.

Runs MEME on a protein FASTA to find conserved motifs, then optionally
uses FIMO to scan those motifs against the same or a different FASTA.
Requires the MEME Suite (https://meme-suite.org/).

Example
-------
    python3 scripts/12_motifs.py --faa results/hits_proteins.faa --out-dir results/
    python3 scripts/12_motifs.py --faa hits.faa --nmotifs 10 --minw 8 --maxw 40 --cpu 8
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.motifs import run_meme, run_fimo, parse_meme_txt
from pipeline.utils import ensure_tools_on_path


def parse_args():
    p = argparse.ArgumentParser(
        description="Discover protein sequence motifs with MEME and scan with FIMO.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--faa",     required=True,  type=Path,
                   help="Input protein FASTA.")
    p.add_argument("--out-dir", default=Path("results"), type=Path,
                   help="Output directory.")
    p.add_argument("--nmotifs", default=5,    type=int,
                   help="Number of motifs to find (MEME -nmotifs).")
    p.add_argument("--minw",    default=6,    type=int,
                   help="Minimum motif width in residues (MEME -minw).")
    p.add_argument("--maxw",    default=50,   type=int,
                   help="Maximum motif width in residues (MEME -maxw).")
    p.add_argument("--cpu",     default=4,    type=int,
                   help="Number of parallel processes (MEME -p).")
    p.add_argument("--no-fimo", action="store_true",
                   help="Skip FIMO scanning step.")
    return p.parse_args()


def main():
    args = parse_args()
    ensure_tools_on_path()

    faa = args.faa.resolve()
    out_dir = args.out_dir.resolve()
    meme_dir = out_dir / "meme_out"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not faa.exists():
        print(f"ERROR: FASTA not found: {faa}", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== Step 12: Motif Discovery ===")
    print(f"  Input   : {faa}")
    print(f"  Motifs  : {args.nmotifs}")
    print(f"  Width   : {args.minw}–{args.maxw}")
    print(f"  CPU     : {args.cpu}")

    print(f"\n[CMD] meme {faa} -oc {meme_dir} -protein "
          f"-nmotifs {args.nmotifs} -minw {args.minw} -maxw {args.maxw} "
          f"-p {args.cpu} -mod zoops")

    meme_result = run_meme(
        faa_path=faa,
        out_dir=meme_dir,
        n_motifs=args.nmotifs,
        min_width=args.minw,
        max_width=args.maxw,
        cpu=args.cpu,
    )

    if not meme_result.get("success"):
        print(f"ERROR: MEME failed: {meme_result.get('error', 'unknown')}", file=sys.stderr)
        sys.exit(1)

    n_found = meme_result.get("n_motifs_found", 0)
    print(f"\n  MEME output -> {meme_dir}")
    print(f"  Motifs found: {n_found}")

    if n_found > 0:
        print("\n--- Discovered motifs ---")
        for m in meme_result.get("motifs", []):
            mid       = m.get("id", "?")
            consensus = m.get("consensus", "")
            evalue    = m.get("evalue", "")
            width     = m.get("width", "")
            nsites    = m.get("nsites", "")
            print(f"  {mid:<10} width={width:<4} nsites={nsites:<5} "
                  f"evalue={evalue:<12} consensus={consensus}")

    # FIMO scanning
    if not args.no_fimo:
        meme_txt = meme_result.get("meme_txt")
        if meme_txt and Path(meme_txt).exists():
            fimo_dir = out_dir / "fimo_out"
            fimo_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n[CMD] fimo --oc {fimo_dir} {meme_txt} {faa}")
            fimo_df = run_fimo(
                meme_txt=Path(meme_txt),
                faa_path=faa,
                out_dir=fimo_dir,
            )
            fimo_out = out_dir / "fimo_hits.tsv"
            if fimo_df is not None and not fimo_df.empty:
                fimo_df.to_csv(fimo_out, sep="\t", index=False)
                print(f"  FIMO hits ({len(fimo_df)} rows) -> {fimo_out}")
            else:
                print("  FIMO: no hits returned.")
        else:
            print("WARNING: meme.txt not found; skipping FIMO.", file=sys.stderr)

    print(f"\nDone. MEME output in: {meme_dir}")
    sys.exit(0)


if __name__ == "__main__":
    main()
