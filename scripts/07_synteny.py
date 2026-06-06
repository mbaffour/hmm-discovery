#!/usr/bin/env python3
"""
07_synteny.py — Build synteny (gene-neighbourhood) tables and figures.
======================================================================

WHAT THIS STEP DOES (the biology)
---------------------------------
A gene rarely acts alone — its function is often hinted at by its NEIGHBOURS on
the genome. "Synteny" is the conservation of gene order across genomes. For each
hit, this step pulls the surrounding genes (its genomic neighbourhood), lines
those neighbourhoods up across many genomes, and asks: which flanking genes
recur? Conserved gene order is strong evidence that your hit sits in a real,
functional operon or gene cassette rather than being an isolated fluke.

Neighbourhood context comes from either local GenBank files (offline, fast) or
NCBI Entrez (online, needs an e-mail). The step then scores conservation,
exports a synteny table, a GFF3, per-locus GenBanks, and synteny map figures.
Optionally it runs clinker to draw gene-link comparison plots.

WHAT THE KEY PARAMETERS MEAN
----------------------------
    --email        NCBI Entrez contact e-mail (required for online fetch).
    --flanks       How many genes to show on each side of the hit gene.
    --max-genomes  Cap on how many loci to fetch (keeps figures readable).
    --local-gb     Directory of local GenBank files (use instead of Entrez).
    --clinker      Also run clinker for an interactive gene-link HTML plot.

OUTPUTS
-------
    results/synteny_table.tsv          one row per neighbourhood gene
    results/conservation_scores.tsv    per-gene conservation across loci
    results/synteny_neighborhoods.gff3 neighbourhoods in GFF3
    results/synteny_map.*              synteny map figures (PNG/SVG/PDF)
    results/neighborhood_genbanks/     per-locus GenBank files
    results/clinker/clinker_output.html (only with --clinker)

INTERACTIVITY
-------------
Run it in a terminal with no/partial arguments and it becomes a guided wizard,
explains the fetch, and confirms before the (network-heavy) neighbourhood build.
Pipe it or pass --yes for hands-off operation (safe for HPC / run_pipeline.py).

EXAMPLES
--------
    # Guided — the script will interview you:
    python3 scripts/07_synteny.py

    # Explicit, Entrez fetch:
    python3 scripts/07_synteny.py --hits results/hits_main.tsv --email you@uni.edu

    # Local GenBanks + clinker, hands-off:
    python3 scripts/07_synteny.py --hits hits.tsv --local-gb genbanks/ --clinker --yes
"""
import argparse
import sys
from pathlib import Path

# Make the app package importable no matter what directory we are run from,
# and make cli_common (which lives beside this script) importable too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

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
from cli_common import Guide, add_common_args


def parse_args():
    p = argparse.ArgumentParser(
        description="Build synteny neighbourhoods and generate synteny figures.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Not required=True: a human in a terminal can supply these via the wizard.
    p.add_argument("--hits",        type=Path,
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
    add_common_args(p)          # --yes / --interactive / --no-color / --explain-only
    return p.parse_args()


def main():
    args = parse_args()
    guide = Guide.from_args(args)
    ensure_tools_on_path()

    guide.header(7, "Synteny Analysis",
                 "Compare each hit's gene neighbourhood across genomes to spot conserved context.")

    # ── GUIDED WIZARD ────────────────────────────────────────────────────
    if guide.interactive and args.hits is None:
        guide.wizard_intro("Let's analyse gene neighbourhoods.")
        args.hits = guide.ask_path(
            "Path to your hits TSV?",
            default="results/hits_main.tsv",
            help_text="The canonical hits table from 05_classify_hits.py.",
        )
        use_local = guide.ask_yesno(
            "Do you have local GenBank files to use (instead of fetching from NCBI)?",
            default_yes=False,
            help_text="Local files are faster and need no network/e-mail.",
        )
        if use_local:
            args.local_gb = guide.ask_path(
                "Directory of GenBank (.gb/.gbk/.gbff) files?",
                help_text="All matching files in this folder are scanned.",
            )
        else:
            args.email = guide.ask(
                "NCBI Entrez e-mail address?",
                default=args.email,
                help_text="NCBI requires a contact e-mail for Entrez fetches.",
            )
        args.flanks = int(guide.ask(
            "How many flanking genes each side of the hit?",
            default=str(args.flanks),
            help_text="More flanks = wider context but busier figures.",
        ))
        args.clinker = guide.ask_yesno(
            "Also run clinker for an interactive gene-link plot?",
            default_yes=False,
            help_text="Requires clinker to be installed.",
        )

    # ── Validate (works in both modes) ───────────────────────────────────
    if args.hits is None:
        guide.error("No --hits given. Provide one, or run in a terminal for the wizard.")
        sys.exit(2)

    hits_path = args.hits.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not hits_path.exists():
        guide.error(f"Hits TSV not found: {hits_path}")
        sys.exit(1)

    guide.narrate(f"Input      : {hits_path.name}")
    guide.narrate(f"Email      : {args.email}")
    guide.narrate(f"Flanks     : {args.flanks}")
    guide.narrate(f"Max genomes: {args.max_genomes}")
    if args.local_gb:
        guide.narrate(f"Local GB   : {args.local_gb}")
    guide.narrate(f"Clinker    : {args.clinker}")

    hits_df = pd.read_csv(hits_path, sep="\t")
    guide.detail(f"Loaded {len(hits_df)} hits.")

    if hits_df.empty:
        guide.warn("No hits to analyse.")
        sys.exit(0)

    # Build local genbank dir list.
    local_gb_dirs = []
    if args.local_gb:
        gb_dir = args.local_gb.resolve()
        if not gb_dir.exists():
            guide.warn(f"--local-gb directory not found: {gb_dir}")
        else:
            local_gb_dirs.append(gb_dir)

    scripts_dir = Path(__file__).resolve().parent

    # ── EXPLAIN-AND-CONFIRM: the neighbourhood build (network-heavy) ─────
    src = f"local GenBanks in {local_gb_dirs[0]}" if local_gb_dirs \
        else f"NCBI Entrez (as {args.email})"
    guide.command(
        f"build_synteny_table(flanks={args.flanks}, max_genomes={args.max_genomes}) "
        f"from {src}",
        "Fetch each hit's genomic neighbourhood and assemble the synteny table. "
        "Entrez fetches can be slow and require network access.")
    if guide.confirm("Build the synteny table now?") != "yes":
        guide.warn("Synteny build skipped — nothing written.")
        sys.exit(0)

    guide.narrate("Building synteny table …")
    syn_df, placement_df = build_synteny_table(
        hits_df=hits_df,
        email=args.email,
        flanks=args.flanks,
        max_genomes=args.max_genomes,
        local_genbank_dirs=local_gb_dirs,
        scripts_dir=scripts_dir,
        log_callback=lambda msg: guide.detail(str(msg)),
    )

    if syn_df is None or (hasattr(syn_df, "empty") and syn_df.empty):
        guide.warn("Synteny table is empty — no neighbourhood data retrieved.")
        guide.detail("Check your e-mail/network for Entrez, or that local GenBanks "
                     "contain the hit loci.")
        syn_df = pd.DataFrame()

    # Save synteny table.
    synteny_out = out_dir / "synteny_table.tsv"
    has_data = not (hasattr(syn_df, "empty") and syn_df.empty)
    if has_data:
        syn_df.to_csv(synteny_out, sep="\t", index=False)
        guide.result(f"Synteny table ({len(syn_df)} rows) → {synteny_out}")
    else:
        pd.DataFrame().to_csv(synteny_out, sep="\t", index=False)
        guide.warn(f"Synteny table (empty) → {synteny_out}")

    # Conservation scores.
    if has_data:
        cons_df = conservation_scores(syn_df)
        cons_out = out_dir / "conservation_scores.tsv"
        cons_df.to_csv(cons_out, sep="\t", index=False)
        guide.result(f"Conservation scores → {cons_out}")

    # GFF3 export.
    gff_out = out_dir / "synteny_neighborhoods.gff3"
    if has_data:
        export_gff3(syn_df, gff_out)
        guide.result(f"GFF3 → {gff_out}")

    # Export synteny figures (PNG/SVG/PDF).
    if has_data:
        guide.narrate("Exporting synteny figures …")
        export_synteny_figures(syn_df, out_dir)
        guide.result(f"Figures → {out_dir}/synteny_map.*")

    # Build neighbourhood GenBanks.
    nb_dir = out_dir / "neighborhood_genbanks"
    nb_dir.mkdir(parents=True, exist_ok=True)
    if has_data:
        guide.narrate("Building neighbourhood GenBanks …")
        build_neighborhood_genbanks(syn_df, nb_dir)
        guide.result(f"GenBanks → {nb_dir}/")

    # Run clinker.
    if args.clinker:
        clinker_dir = out_dir / "clinker"
        clinker_dir.mkdir(parents=True, exist_ok=True)
        clinker_html = clinker_dir / "clinker_output.html"
        gb_files = list(nb_dir.glob("*.gb")) + list(nb_dir.glob("*.gbk"))
        guide.command(f"clinker {nb_dir}/*.gb -p {clinker_html} --identity {args.identity}",
                      "Draw gene-link comparisons between the neighbourhood loci.")
        if not gb_files:
            guide.warn("No GenBank files found for clinker.")
        elif guide.confirm("Run clinker now?") == "yes":
            run_clinker(
                genbank_dir=nb_dir,
                out_html=clinker_html,
                identity=args.identity,
            )
            guide.result(f"Clinker HTML → {clinker_html}")
        else:
            guide.warn("clinker skipped.")

    guide.done(f"Synteny analysis complete. Outputs in: {out_dir}")
    guide.detail("Next: 08_taxonomy.py annotates hosts/organisms for these hits.")
    sys.exit(0)


if __name__ == "__main__":
    main()
