#!/usr/bin/env python3
"""
01_align.py — Multiple sequence alignment of your seed sequences.
=================================================================

WHAT THIS STEP DOES (the biology)
---------------------------------
You start with a handful of "seed" proteins that you already believe belong to
the family you want to discover (e.g. a few known phage tail-fibre proteins).
Before you can build a statistical model of that family, the sequences have to
be *aligned* — laid out column-by-column so that equivalent residues (the same
position in the protein's evolutionary history) sit on top of one another.

    * MAFFT      — fast, accurate general-purpose aligner. Good default.
    * Clustal Omega — alternative aligner; sometimes cleaner on very large sets.

After aligning you can optionally TRIM the alignment with trimAl. Trimming
removes ragged, gap-heavy columns at the ends and in poorly-aligned regions so
that the model built in step 02 is driven by genuinely homologous positions
rather than alignment noise.

WHAT THE KEY PARAMETERS MEAN
----------------------------
    --tool      mafft (default) or clustalo — which aligner to run.
    --trim      Run trimAl --automated1 to clean the alignment afterwards.
    --threads   CPU threads for the aligner (faster on big seed sets).

OUTPUTS
-------
    results/seeds_aligned.faa   the multiple sequence alignment (FASTA)
    results/seeds_trimmed.faa   trimmed alignment (only if --trim)

INTERACTIVITY
-------------
Run it in a terminal with no/partial arguments and it becomes a guided wizard:
it interviews you for the inputs, explains every command before running it, and
asks before each external tool. Pipe it, redirect it, or pass --yes and it runs
straight through in silence (safe for HPC / run_pipeline.py). See cli_common.py.

EXAMPLES
--------
    # Guided — the script will interview you:
    python3 scripts/01_align.py

    # Explicit MAFFT alignment:
    python3 scripts/01_align.py --seeds seeds.faa --out-dir results/

    # Clustal Omega + trimming, 8 threads, hands-off:
    python3 scripts/01_align.py --seeds seeds.faa --tool clustalo --trim --threads 8 --yes
"""
import argparse
import sys
from pathlib import Path

# Make the app package importable no matter what directory we are run from,
# and make cli_common (which lives beside this script) importable too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.alignment import run_mafft, run_clustalo, run_trimal, alignment_quality
from pipeline.utils import ensure_tools_on_path
from cli_common import Guide, add_common_args


def parse_args():
    p = argparse.ArgumentParser(
        description="Align seed sequences with MAFFT or Clustal Omega, "
                    "optionally trim with trimAl.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Not required=True: a human in a terminal can supply these via the wizard.
    p.add_argument("--seeds",   type=Path,
                   help="Input un-aligned seed protein FASTA.")
    p.add_argument("--out-dir", default=Path("results"), type=Path,
                   help="Output directory for aligned (and trimmed) FASTA files.")
    p.add_argument("--tool",    default="mafft", choices=["mafft", "clustalo"],
                   help="Alignment tool to use.")
    p.add_argument("--trim",    action="store_true",
                   help="Run trimAl (--automated1) after alignment.")
    p.add_argument("--threads", default=4, type=int,
                   help="Number of CPU threads to pass to the aligner.")
    add_common_args(p)          # --yes / --interactive / --no-color / --explain-only
    return p.parse_args()


def main():
    args = parse_args()
    guide = Guide.from_args(args)
    ensure_tools_on_path()

    guide.header(1, "Multiple Sequence Alignment",
                 "Line up your seed proteins column-by-column so a model can be built.")

    # ── GUIDED WIZARD ────────────────────────────────────────────────────
    # If a human is present and required inputs are missing, interview them.
    # (In non-interactive mode these ask_* calls instantly return defaults,
    #  so the missing-argument validation below still fires for batch runs.)
    if guide.interactive and args.seeds is None:
        guide.wizard_intro("Let's align your seed sequences.")
        args.seeds = guide.ask_path(
            "Path to your seed protein FASTA?",
            help_text="A FASTA of un-aligned proteins you believe are in the family.",
        )
        args.tool = guide.ask_choice(
            "Which aligner?",
            [
                ("mafft",    "MAFFT — fast, accurate default (recommended)"),
                ("clustalo", "Clustal Omega — alternative, good on large sets"),
            ],
            default_index=0,
            help_text="Both produce a column-aligned FASTA.",
        )
        args.trim = guide.ask_yesno(
            "Trim ragged/gappy columns with trimAl afterwards?",
            default_yes=False,
            help_text="Trimming gives a cleaner model but discards some columns.",
        )

    # ── Validate (works in both modes) ───────────────────────────────────
    if args.seeds is None:
        guide.error("No --seeds given. Provide one, or run in a terminal for the wizard.")
        sys.exit(2)

    seeds = args.seeds.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not seeds.exists():
        guide.error(f"Seeds FASTA not found: {seeds}")
        sys.exit(1)

    guide.narrate(f"Input  : {seeds.name}")
    guide.narrate(f"Tool   : {args.tool}")
    guide.narrate(f"Threads: {args.threads}")
    guide.narrate(f"Trim   : {args.trim}")
    guide.narrate(f"Out dir: {out_dir}")

    aln_out = out_dir / "seeds_aligned.faa"

    # ── EXPLAIN-AND-CONFIRM: the alignment itself ────────────────────────
    if args.tool == "mafft":
        cmd = f"mafft --auto --thread {args.threads} {seeds} > {aln_out}"
        why = "Build the multiple sequence alignment with MAFFT's auto strategy."
    else:
        cmd = f"clustalo -i {seeds} -o {aln_out} --threads {args.threads} --force"
        why = "Build the multiple sequence alignment with Clustal Omega."
    guide.command(cmd, why)

    if guide.confirm("Run the aligner now?") != "yes":
        guide.warn("Alignment skipped — nothing to do.")
        sys.exit(0)

    guide.narrate(f"Aligning {seeds.name} with {args.tool} …")
    if args.tool == "mafft":
        result = run_mafft(seeds, aln_out, cpu=args.threads)
    else:
        result = run_clustalo(seeds, aln_out, cpu=args.threads)

    if not result or not result.exists():
        guide.error("Alignment failed — no output produced.")
        sys.exit(1)

    guide.result(f"Aligned output written → {aln_out}")

    final_aln = aln_out

    # ── EXPLAIN-AND-CONFIRM: optional trimming ───────────────────────────
    if args.trim:
        trimmed_out = out_dir / "seeds_trimmed.faa"
        guide.command(f"trimal -in {aln_out} -out {trimmed_out} -automated1",
                      "Strip ragged, gap-heavy columns so the HMM sees clean homologous positions.")
        if guide.confirm("Run trimAl now?") == "yes":
            trimmed = run_trimal(aln_out, trimmed_out)
            if not trimmed or not trimmed.exists():
                guide.warn("trimAl failed; using the untrimmed alignment.")
            else:
                guide.result(f"Trimmed output written → {trimmed_out}")
                final_aln = trimmed_out
        else:
            guide.warn("Trimming skipped; using the untrimmed alignment.")

    # ── NARRATE: interpret the alignment quality, don't just dump it ─────
    guide.header(None, "Alignment quality")
    stats = alignment_quality(final_aln)
    guide.narrate(f"Sequences       : {stats['n_sequences']}")
    guide.narrate(f"Alignment length: {stats['aln_length']} columns")
    guide.narrate(f"Gap percentage  : {stats['gap_pct']}%")
    guide.narrate(f"Conserved cols  : {stats['conserved_columns']}")
    guide.narrate(f"Avg pairwise ID : {stats['avg_pairwise_id']}%")

    # Help the user read these numbers.
    pid = stats.get("avg_pairwise_id", 0) or 0
    if pid >= 40:
        guide.result("Sequences are fairly similar → a sharp, specific HMM.", good=True)
    elif pid >= 15:
        guide.result("Moderate divergence → a usefully general HMM.", good=True)
    else:
        guide.result("Very divergent seeds → the HMM will be broad (more noise).", good=False)
        guide.detail("Consider trimming, or curating the seed set, before step 02.")

    if stats["flagged_sequences"]:
        guide.warn(f"Mostly-gap sequences (>80% gap): {', '.join(stats['flagged_sequences'])}")
        guide.detail("These add little signal and may be worth removing from the seeds.")

    guide.done(f"Alignment complete. Final alignment: {final_aln}")
    guide.detail("Next: 02_build_hmm.py turns this alignment into a profile HMM.")
    sys.exit(0)


if __name__ == "__main__":
    main()
