#!/usr/bin/env python3
"""
13_annotate.py — Functional annotation: domain architecture, TM topology, signal peptides.

Uses a Pfam domtblout file (from hmmsearch against Pfam-A) to build domain
architecture strings. Optionally runs Phobius (TM + signal peptide) and/or
TMHMM (TM topology prediction) on the hit sequences.

Example
-------
    python3 scripts/13_annotate.py \\
        --faa results/hits_proteins.faa \\
        --hmm profile.hmm \\
        --domtblout pfam_hits.domtblout \\
        --out-dir results/

    # With Phobius and TMHMM:
    python3 scripts/13_annotate.py \\
        --faa hits.faa --hmm profile.hmm --domtblout pfam.domtblout \\
        --phobius --tmhmm --out-dir results/
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from pipeline.annotation import domain_architecture, run_phobius, run_tmhmm, annotate_from_tm
from pipeline.hmm_builder import parse_hmm_file
from pipeline.utils import ensure_tools_on_path


def parse_args():
    p = argparse.ArgumentParser(
        description="Annotate hit sequences: domain architecture, TM topology, signal peptides.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--faa",       required=True,  type=Path,
                   help="Hit protein FASTA (output of 05_classify_hits.py).")
    p.add_argument("--hmm",       required=True,  type=Path,
                   help="Profile HMM used to build the domain tblout.")
    p.add_argument("--domtblout", required=True,  type=Path,
                   help="Pfam hmmsearch --domtblout file for domain architecture.")
    p.add_argument("--out-dir",   default=Path("results"), type=Path,
                   help="Output directory.")
    p.add_argument("--phobius",   action="store_true",
                   help="Run Phobius for TM topology + signal peptide prediction.")
    p.add_argument("--tmhmm",     action="store_true",
                   help="Run TMHMM for transmembrane topology prediction.")
    return p.parse_args()


def main():
    args = parse_args()
    ensure_tools_on_path()

    faa = args.faa.resolve()
    hmm = args.hmm.resolve()
    domtblout = args.domtblout.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    for p, name in [(faa, "--faa"), (hmm, "--hmm"), (domtblout, "--domtblout")]:
        if not p.exists():
            print(f"ERROR: {name} file not found: {p}", file=sys.stderr)
            sys.exit(1)

    print(f"\n=== Step 13: Functional Annotation ===")
    print(f"  FASTA       : {faa}")
    print(f"  HMM         : {hmm}")
    print(f"  domtblout   : {domtblout}")
    print(f"  Phobius     : {args.phobius}")
    print(f"  TMHMM       : {args.tmhmm}")

    # Parse HMM length for context
    hmm_meta = parse_hmm_file(hmm)
    hmm_length = hmm_meta.get("LENG", 0)

    # Domain architecture from Pfam domtblout
    print(f"\n  Building domain architecture table from {domtblout}...")
    dom_arch_df = domain_architecture(domtblout, hmm_length=hmm_length)
    dom_out = out_dir / "domain_architecture.tsv"
    dom_arch_df.to_csv(dom_out, sep="\t", index=False)
    print(f"  Domain architecture ({len(dom_arch_df)} proteins) -> {dom_out}")

    if not dom_arch_df.empty:
        top_archs = dom_arch_df["domain_architecture"].value_counts().head(5)
        print("\n--- Top domain architectures ---")
        for arch, count in top_archs.items():
            print(f"  {arch:<50} {count:>5}")

    # Phobius
    phobius_df = pd.DataFrame()
    if args.phobius:
        print(f"\n[CMD] phobius.pl -short < {faa}")
        phobius_df = run_phobius(faa, out_dir)
        if phobius_df.empty:
            print("WARNING: Phobius returned no results (not installed or no TM hits).",
                  file=sys.stderr)
        else:
            print(f"  Phobius: {len(phobius_df)} proteins annotated")

    # TMHMM
    tmhmm_df = pd.DataFrame()
    if args.tmhmm:
        print(f"\n[CMD] tmhmm --short < {faa}")
        tmhmm_df = run_tmhmm(faa, out_dir)
        if tmhmm_df.empty:
            print("WARNING: TMHMM returned no results (not installed or no TM hits).",
                  file=sys.stderr)
        else:
            print(f"  TMHMM: {len(tmhmm_df)} proteins annotated")

    # Combine TM annotations with domain architecture
    combined_tm = pd.concat([phobius_df, tmhmm_df], ignore_index=True) \
        if (not phobius_df.empty or not tmhmm_df.empty) else pd.DataFrame()

    # Merge all annotation into summary table
    summary_df = dom_arch_df.copy()
    if not combined_tm.empty and "protein_id" in combined_tm.columns:
        # Add TM count and topology if available
        tm_cols = [c for c in combined_tm.columns if c != "protein_id"]
        summary_df = summary_df.merge(
            combined_tm[["protein_id"] + tm_cols],
            on="protein_id",
            how="left",
        )

    summary_out = out_dir / "annotation_summary.tsv"
    summary_df.to_csv(summary_out, sep="\t", index=False)
    print(f"\n  Annotation summary ({len(summary_df)} rows) -> {summary_out}")

    print(f"\nDone. Outputs in: {out_dir}")
    sys.exit(0)


if __name__ == "__main__":
    main()
