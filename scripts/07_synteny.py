#!/usr/bin/env python3
"""
07_synteny.py — Build synteny neighbourhood tables and figures.

Fetches genomic neighbourhood context for each hit (from local GenBank files
or NCBI Entrez), computes conservation scores across genomes, exports a
synteny table, GFF3 file, neighbourhood GenBanks, and synteny map figures.
Optionally runs clinker for gene-link comparison.

Example
-------
    python3 scripts/07_synteny.py \\
        --hits results/hits_main.tsv --out-dir results/ --email user@uni.edu

    python3 scripts/07_synteny.py \\
        --hits hits.tsv --local-gb genbanks/ --clinker --flanks 8 --max-genomes 50
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from pipeline.synteny import (
    build_synteny_table,
    conservation_scores,
    export_synteny_figures,
    export_gff3,
    build_neighborhood_genbanks,
    run_clinker,
)
from pipeline.utils import ensure_tools_on_path


def parse_args():
    p = argparse.ArgumentParser(
        description="Build synteny neighbourhoods and generate synteny figures.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--hits",        required=True,  type=Path,
                   help="Hits TSV (output of 05_classify_hits.py or 04_score_hits.py).")
    p.add_argument("--out-dir",     default=Path("results"), type=Path,
                   help="Output directory.")
    p.add_argument("--email",       default="researcher@example.com",
                   help="NCBI Entrez e-mail address (required for Entrez fetch mode).")
    p.add_argument("--flanks",      default=5,      type=int,
                   help="Number of flanking genes each side of the hit gene.")
    p.add_argument("--max-genomes", default=30,     type=int,
                   help="Maximum number of genomic loci to fetch.")
    p.add_argument("--local-gb",    type=Path,
                   help="Directory containing local GenBank (.gb/.gbk/.gbff) files.")
    p.add_argument("--clinker",     action="store_true",
                   help="Run clinker for gene-link HTML comparison plot.")
    p.add_argument("--identity",    default=0.3,    type=float,
                   help="Minimum protein identity for clinker links (0–1).")
    return p.parse_args()


def main():
    args = parse_args()
    ensure_tools_on_path()

    hits_path = args.hits.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not hits_path.exists():
        print(f"ERROR: Hits TSV not found: {hits_path}", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== Step 7: Synteny Analysis ===")
    print(f"  Input   : {hits_path}")
    print(f"  Email   : {args.email}")
    print(f"  Flanks  : {args.flanks}")
    print(f"  Max genomes: {args.max_genomes}")
    if args.local_gb:
        print(f"  Local GB: {args.local_gb}")
    print(f"  Clinker : {args.clinker}")

    hits_df = pd.read_csv(hits_path, sep="\t")
    print(f"  Loaded  : {len(hits_df)} hits")

    if hits_df.empty:
        print("WARNING: No hits to analyse.", file=sys.stderr)
        sys.exit(0)

    # Build local genbank dir list
    local_gb_dirs = []
    if args.local_gb:
        gb_dir = args.local_gb.resolve()
        if not gb_dir.exists():
            print(f"WARNING: --local-gb directory not found: {gb_dir}", file=sys.stderr)
        else:
            local_gb_dirs.append(gb_dir)

    scripts_dir = Path(__file__).resolve().parent

    print("\n  Building synteny table...")
    syn_df, placement_df = build_synteny_table(
        hits_df=hits_df,
        email=args.email,
        flanks=args.flanks,
        max_genomes=args.max_genomes,
        local_genbank_dirs=local_gb_dirs,
        scripts_dir=scripts_dir,
        log_callback=lambda msg: print(f"    {msg}"),
    )

    if syn_df is None or (hasattr(syn_df, "empty") and syn_df.empty):
        print("WARNING: Synteny table is empty — no neighbourhood data retrieved.",
              file=sys.stderr)
        syn_df = pd.DataFrame()

    # Save synteny table
    synteny_out = out_dir / "synteny_table.tsv"
    if not (hasattr(syn_df, "empty") and syn_df.empty):
        syn_df.to_csv(synteny_out, sep="\t", index=False)
        print(f"  Synteny table ({len(syn_df)} rows) -> {synteny_out}")
    else:
        pd.DataFrame().to_csv(synteny_out, sep="\t", index=False)
        print(f"  Synteny table (empty) -> {synteny_out}")

    # Conservation scores
    if not (hasattr(syn_df, "empty") and syn_df.empty):
        cons_df = conservation_scores(syn_df)
        cons_out = out_dir / "conservation_scores.tsv"
        cons_df.to_csv(cons_out, sep="\t", index=False)
        print(f"  Conservation scores -> {cons_out}")

    # GFF3 export
    gff_out = out_dir / "synteny_neighborhoods.gff3"
    if not (hasattr(syn_df, "empty") and syn_df.empty):
        export_gff3(syn_df, gff_out)
        print(f"  GFF3 -> {gff_out}")

    # Export synteny figures (PNG/SVG/PDF)
    if not (hasattr(syn_df, "empty") and syn_df.empty):
        print("\n  Exporting synteny figures...")
        export_synteny_figures(syn_df, out_dir)
        print(f"  Figures -> {out_dir}/synteny_map.*")

    # Build neighbourhood GenBanks
    nb_dir = out_dir / "neighborhood_genbanks"
    nb_dir.mkdir(parents=True, exist_ok=True)
    if not (hasattr(syn_df, "empty") and syn_df.empty):
        print("\n  Building neighbourhood GenBanks...")
        build_neighborhood_genbanks(syn_df, nb_dir)
        print(f"  GenBanks -> {nb_dir}/")

    # Run clinker
    if args.clinker:
        clinker_dir = out_dir / "clinker"
        clinker_dir.mkdir(parents=True, exist_ok=True)
        clinker_html = clinker_dir / "clinker_output.html"
        print(f"\n[CMD] clinker {nb_dir}/*.gb -p {clinker_html} --identity {args.identity}")
        gb_files = list(nb_dir.glob("*.gb")) + list(nb_dir.glob("*.gbk"))
        if gb_files:
            run_clinker(
                genbank_dir=nb_dir,
                out_html=clinker_html,
                identity=args.identity,
            )
            print(f"  Clinker HTML -> {clinker_html}")
        else:
            print("WARNING: No GenBank files found for clinker.", file=sys.stderr)

    print(f"\nDone. Outputs in: {out_dir}")
    sys.exit(0)


if __name__ == "__main__":
    main()
