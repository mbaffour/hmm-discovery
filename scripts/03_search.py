#!/usr/bin/env python3
"""
03_search.py — Search one or more sequence databases with your profile HMM.
===========================================================================

WHAT THIS STEP DOES (the biology)
---------------------------------
A profile HMM is a position-by-position statistical model of your protein
family, built in step 02 from the seed alignment. ``hmmsearch`` slides that
model across every protein in a target database and scores how well each one
matches. Proteins that score well are candidate family members ("hits").

    * Protein database (.faa)  → searched directly.
    * Nucleotide database (.fna) → there are no proteins to score yet, so we
      first translate the DNA in all six reading frames (3 forward + 3 reverse)
      into hypothetical proteins, then search those. This is how the app finds
      genes in raw genomes/contigs that were never formally annotated.

Two numbers control the result:

    --evalue   Expectation value: how many hits this good you'd expect BY
               CHANCE in a database this size. 1e-5 = fewer than 1 in 100,000.
               Lower is stricter (fewer, more confident hits).
    --cpu      Threads. Higher = faster on large databases.

OUTPUTS
-------
    search_results/<db>.tblout     raw HMMER per-sequence table (one per DB)
    search_results/<db>.domtblout  raw HMMER per-domain table
    hits_combined.tsv              all DBs merged into one tidy table

INTERACTIVITY
-------------
Run it in a terminal with no/partial arguments and it becomes a guided wizard,
explains each command before running it, and asks before searching each
database. Pipe it, redirect it, or pass --yes and it runs straight through in
silence (safe for HPC / run_pipeline.py). See cli_common.py for the details.

EXAMPLES
--------
    # Guided — the script will interview you:
    python3 scripts/03_search.py

    # Explicit protein search:
    python3 scripts/03_search.py --hmm results/profile.hmm --db phages.faa

    # Nucleotide genomes, 8 threads, hands-off:
    python3 scripts/03_search.py --hmm profile.hmm --db genomes.fna --nuc --cpu 8 --yes
"""
import argparse
import sys
from pathlib import Path

# Make the app package importable no matter what directory we are run from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from pipeline.searcher import (
    run_hmmsearch_protein,
    run_hmmsearch_nucleotide,
    parse_tblout,
)
from pipeline.utils import ensure_tools_on_path
from cli_common import Guide, add_common_args


def parse_args():
    p = argparse.ArgumentParser(
        description="Search FASTA database(s) with a profile HMM (hmmsearch).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Not required=True: a human in a terminal can supply these via the wizard.
    p.add_argument("--hmm", type=Path,
                   help="Profile HMM (output of 02_build_hmm.py).")
    p.add_argument("--db", type=Path, action="append", dest="dbs", metavar="FASTA",
                   help="Target database FASTA. Repeat to search multiple DBs.")
    p.add_argument("--evalue", default=1e-5, type=float,
                   help="E-value inclusion threshold passed to hmmsearch.")
    p.add_argument("--cpu", default=4, type=int,
                   help="Number of CPU threads for hmmsearch.")
    p.add_argument("--out-dir", default=Path("results"), type=Path,
                   help="Output directory.")
    p.add_argument("--nuc", action="store_true",
                   help="Databases are nucleotide FASTA; 6-frame translate first.")
    p.add_argument("--sixframe", action="store_true",
                   help="Alias for --nuc.")
    add_common_args(p)          # --yes / --interactive / --no-color / --explain-only
    return p.parse_args()


def main():
    args = parse_args()
    guide = Guide.from_args(args)
    ensure_tools_on_path()

    guide.header(3, "HMM Search",
                 "Score every sequence in a database against your profile HMM.")

    # ── GUIDED WIZARD ────────────────────────────────────────────────────
    # If a human is present and required inputs are missing, interview them.
    # (In non-interactive mode these ask_* calls instantly return defaults,
    #  so the missing-argument errors below still fire cleanly for batch runs.)
    nucleotide_mode = args.nuc or args.sixframe

    if guide.interactive and args.hmm is None:
        guide.wizard_intro("Let's set up your database search.")
        args.hmm = guide.ask_path(
            "Path to your profile HMM?",
            default="results/profile.hmm",
            help_text="This is the .hmm file produced by 02_build_hmm.py.",
        )

    if guide.interactive and not args.dbs:
        first = guide.ask_path(
            "Database FASTA to search?",
            help_text="Protein (.faa) or nucleotide (.fna/.fasta) sequences.",
        )
        args.dbs = [first]
        # Offer to add more databases one at a time.
        while guide.ask_yesno("Add another database?", default_yes=False):
            args.dbs.append(guide.ask_path("Next database FASTA?"))

        # Ask whether these are nucleotide sequences (changes the whole search).
        nucleotide_mode = guide.ask_yesno(
            "Are these NUCLEOTIDE databases (raw DNA / genomes)?",
            default_yes=False,
            help_text="Yes → translate DNA in 6 frames before searching. "
                      "No → they are already protein sequences.",
        )

        # Let the user pick strictness with explanations.
        args.evalue = float(guide.ask_choice(
            "How strict should the search be?",
            [
                ("1e-5",  "standard — recommended for most families"),
                ("1e-3",  "permissive — catches more distant homologs (more noise)"),
                ("1e-10", "strict — only strong, unambiguous matches"),
            ],
            default_index=0,
            help_text="This is the hmmsearch E-value threshold.",
        ))

    # ── Validate (works in both modes) ───────────────────────────────────
    if args.hmm is None:
        guide.error("No --hmm given. Provide one, or run in a terminal for the wizard.")
        sys.exit(2)
    if not args.dbs:
        guide.error("No --db given. Provide at least one database FASTA.")
        sys.exit(2)

    hmm = args.hmm.resolve()
    out_dir = args.out_dir.resolve()
    search_dir = out_dir / "search_results"
    search_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir = Path(__file__).resolve().parent

    if not hmm.exists():
        guide.error(f"HMM not found: {hmm}")
        sys.exit(1)

    guide.narrate(f"HMM        : {hmm.name}")
    guide.narrate(f"Mode       : {'nucleotide (6-frame translation)' if nucleotide_mode else 'protein'}")
    guide.narrate(f"E-value    : {args.evalue}")
    guide.narrate(f"CPU threads: {args.cpu}")
    guide.narrate(f"Databases  : {len(args.dbs)}")

    all_hits: list[pd.DataFrame] = []
    summary_rows = []

    for db_path in args.dbs:
        db_path = db_path.resolve()
        db_name = db_path.stem
        if not db_path.exists():
            guide.warn(f"Database not found, skipping: {db_path}")
            continue

        guide.header(None, f"Searching: {db_name}")

        # Build the human-readable command + a one-line "why".
        if nucleotide_mode:
            cmd = (f"[6-frame translate {db_path.name}] | "
                   f"hmmsearch --tblout {db_name}.tblout -E {args.evalue} "
                   f"--cpu {args.cpu} {hmm.name} <translated.faa>")
            why = ("Translate the DNA in all six frames, then score every "
                   "candidate ORF against the HMM.")
        else:
            cmd = (f"hmmsearch --tblout {search_dir}/{db_name}.tblout "
                   f"--domtblout {search_dir}/{db_name}.domtblout "
                   f"-E {args.evalue} --cpu {args.cpu} {hmm} {db_path}")
            why = (f"Score every protein in {db_name} against the HMM; keep "
                   f"matches with E ≤ {args.evalue}.")

        guide.command(cmd, why)

        # EXPLAIN-AND-CONFIRM gate. Returns 'yes' instantly when non-interactive.
        if guide.confirm(f"Search {db_name} now?") != "yes":
            guide.warn(f"Skipped {db_name}.")
            continue

        guide.narrate(f"Running hmmsearch on {db_name} …")
        if nucleotide_mode:
            res = run_hmmsearch_nucleotide(
                hmm_path=hmm, db_fna=db_path, out_dir=search_dir / db_name,
                db_name=db_name, scripts_dir=scripts_dir,
                evalue=args.evalue, cpu=args.cpu,
            )
        else:
            res = run_hmmsearch_protein(
                hmm_path=hmm, db_faa=db_path, out_dir=search_dir,
                db_name=db_name, evalue=args.evalue, cpu=args.cpu,
            )

        hit_count = res.get("hit_count", 0)
        strict_count = res.get("strict_count", 0)

        # NARRATE: interpret the numbers, don't just dump them.
        guide.result(f"{hit_count} hits total · {strict_count} strong (bit ≥ 45)",
                     good=hit_count > 0)
        if hit_count == 0:
            guide.detail("No matches — try a higher --evalue, or check the DB type "
                         "(protein vs nucleotide).")
        elif strict_count == 0:
            guide.detail("Hits exist but all are weak — likely distant homologs; "
                         "step 04 will tier them as 'divergent'.")
        else:
            guide.detail(f"{strict_count} strong matches → probable true family members.")

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

    # ── Merge + save ─────────────────────────────────────────────────────
    combined_out = out_dir / "hits_combined.tsv"
    if all_hits:
        combined = pd.concat(all_hits, ignore_index=True)
        combined.to_csv(combined_out, sep="\t", index=False)
        guide.result(f"Combined {len(combined)} hits → {combined_out}")
    else:
        pd.DataFrame().to_csv(combined_out, sep="\t", index=False)
        guide.warn("No hits found across any database. Wrote an empty table.")

    # ── Summary table ────────────────────────────────────────────────────
    if summary_rows:
        print()
        print(f"  {'Database':<30} {'Total':>8} {'Strong(bit≥45)':>16}")
        print(f"  {'-' * 30} {'-' * 8} {'-' * 16}")
        for row in summary_rows:
            print(f"  {row['database']:<30} {row['total_hits']:>8} "
                  f"{row['strict_hits_bit45']:>16}")

    guide.done(f"Search complete. Results in: {out_dir}")
    guide.detail("Next: 04_score_hits.py assigns confidence tiers to these hits.")
    sys.exit(0)


if __name__ == "__main__":
    main()
