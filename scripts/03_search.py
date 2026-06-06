#!/usr/bin/env python3
"""
03_search.py — Run hmmsearch against one or more databases.

For protein databases (default): runs hmmsearch directly.
For nucleotide databases (--nuc / --sixframe): translates via 6-frame ORF
prediction first, then runs hmmsearch on the translated proteins.

Results from all databases are merged into a single hits_combined.tsv.

Example
-------
    python3 scripts/03_search.py --hmm results/profile.hmm --db phages.faa --out-dir results/
    python3 scripts/03_search.py --hmm profile.hmm --db genomes.fna --nuc --cpu 8 --evalue 1e-3
    python3 scripts/03_search.py --hmm profile.hmm --db a.faa --db b.faa --out-dir results/
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from pipeline.searcher import (
    run_hmmsearch_protein,
    run_hmmsearch_nucleotide,
    parse_tblout,
)
from pipeline.utils import ensure_tools_on_path


def parse_args():
    p = argparse.ArgumentParser(
        description="Run hmmsearch against one or more FASTA databases.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--hmm",     required=True,  type=Path,
                   help="Profile HMM (output of 02_build_hmm.py).")
    p.add_argument("--db",      required=True,  type=Path, action="append",
                   dest="dbs",  metavar="FASTA",
                   help="Target database FASTA. Repeat to search multiple DBs.")
    p.add_argument("--evalue",  default=1e-5,   type=float,
                   help="E-value inclusion threshold passed to hmmsearch.")
    p.add_argument("--cpu",     default=4,       type=int,
                   help="Number of CPU threads for hmmsearch.")
    p.add_argument("--out-dir", default=Path("results"), type=Path,
                   help="Output directory.")
    p.add_argument("--nuc",     action="store_true",
                   help="Databases are nucleotide FASTA; 6-frame translate before searching.")
    p.add_argument("--sixframe", action="store_true",
                   help="Alias for --nuc (6-frame translate nucleotide input).")
    return p.parse_args()


def main():
    args = parse_args()
    ensure_tools_on_path()

    hmm = args.hmm.resolve()
    out_dir = args.out_dir.resolve()
    search_dir = out_dir / "search_results"
    search_dir.mkdir(parents=True, exist_ok=True)
    nucleotide_mode = args.nuc or args.sixframe

    if not hmm.exists():
        print(f"ERROR: HMM not found: {hmm}", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== Step 3: HMM Search ===")
    print(f"  HMM    : {hmm}")
    print(f"  Mode   : {'nucleotide (6-frame)' if nucleotide_mode else 'protein'}")
    print(f"  E-value: {args.evalue}")
    print(f"  CPU    : {args.cpu}")
    print(f"  DBs    : {len(args.dbs)}")

    # Scripts dir for nucleotide translation helper
    scripts_dir = Path(__file__).resolve().parent

    all_hits: list[pd.DataFrame] = []
    summary_rows = []

    for db_path in args.dbs:
        db_path = db_path.resolve()
        db_name = db_path.stem
        if not db_path.exists():
            print(f"WARNING: Database not found, skipping: {db_path}", file=sys.stderr)
            continue

        print(f"\n  Searching: {db_name}  ({db_path})")

        if nucleotide_mode:
            print(f"[CMD] [6-frame translate] {db_path} -> hmmsearch --tblout ... "
                  f"-E {args.evalue} --cpu {args.cpu} {hmm} <translated.faa>")
            res = run_hmmsearch_nucleotide(
                hmm_path=hmm,
                db_fna=db_path,
                out_dir=search_dir / db_name,
                db_name=db_name,
                scripts_dir=scripts_dir,
                evalue=args.evalue,
                cpu=args.cpu,
            )
        else:
            print(f"[CMD] hmmsearch --tblout {search_dir}/{db_name}.tblout "
                  f"--domtblout {search_dir}/{db_name}.domtblout "
                  f"-E {args.evalue} --cpu {args.cpu} {hmm} {db_path}")
            res = run_hmmsearch_protein(
                hmm_path=hmm,
                db_faa=db_path,
                out_dir=search_dir,
                db_name=db_name,
                evalue=args.evalue,
                cpu=args.cpu,
            )

        hit_count  = res.get("hit_count", 0)
        strict_count = res.get("strict_count", 0)
        print(f"    Hits: {hit_count} total  |  {strict_count} with bit >= 45")
        summary_rows.append({
            "database": db_name,
            "total_hits": hit_count,
            "strict_hits_bit45": strict_count,
        })

        tblout_path = res.get("tblout")
        if tblout_path and Path(tblout_path).exists():
            df = parse_tblout(tblout_path)
            if not df.empty:
                df["database_source"] = db_name
                all_hits.append(df)

    # Merge and save combined hits
    if all_hits:
        combined = pd.concat(all_hits, ignore_index=True)
        combined_out = out_dir / "hits_combined.tsv"
        combined.to_csv(combined_out, sep="\t", index=False)
        print(f"\n  Combined hits ({len(combined)} rows) -> {combined_out}")
    else:
        print("\n  No hits found across all databases.", file=sys.stderr)
        combined_out = out_dir / "hits_combined.tsv"
        pd.DataFrame().to_csv(combined_out, sep="\t", index=False)

    # Print summary table
    print("\n--- Search summary ---")
    print(f"  {'Database':<30} {'Total hits':>12} {'Bit>=45 hits':>14}")
    print(f"  {'-'*30} {'-'*12} {'-'*14}")
    for row in summary_rows:
        print(f"  {row['database']:<30} {row['total_hits']:>12} {row['strict_hits_bit45']:>14}")

    print(f"\nDone. Results in: {out_dir}")
    sys.exit(0)


if __name__ == "__main__":
    main()
