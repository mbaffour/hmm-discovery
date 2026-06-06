#!/usr/bin/env python3
"""
02_build_hmm.py — Build a profile HMM from your seed alignment.
===============================================================

WHAT THIS STEP DOES (the biology)
---------------------------------
A profile HMM (Hidden Markov Model) is a position-by-position statistical
portrait of your protein family. Where a single consensus sequence says "this
position is usually L", a profile HMM says "this position is L 60% of the time,
I 25%, V 15%, and it is almost never a gap" — for every column of the
alignment, plus the probabilities of inserting or deleting residues between
columns.

``hmmbuild`` reads the multiple sequence alignment from step 01 and distils it
into exactly this model. The resulting ``profile.hmm`` is what step 03 slides
across whole databases to find new family members, including distant homologs a
simple BLAST would miss.

WHAT THE KEY PARAMETERS MEAN
----------------------------
    --aln    The aligned FASTA from 01_align.py (aligned, not raw sequences).
    --name   A label embedded inside the HMM file. Shows up in HMMER output
             and your Methods section; purely cosmetic, but worth setting.

OUTPUTS
-------
    results/profile.hmm   the profile HMM (HMMER3 format)

INTERACTIVITY
-------------
Run it in a terminal with no/partial arguments and it becomes a guided wizard:
it interviews you for the inputs, shows the exact hmmbuild command, and asks
before running it. Pipe it, redirect it, or pass --yes and it runs straight
through in silence (safe for HPC / run_pipeline.py). See cli_common.py.

EXAMPLES
--------
    # Guided — the script will interview you:
    python3 scripts/02_build_hmm.py

    # Explicit:
    python3 scripts/02_build_hmm.py --aln results/seeds_aligned.faa --out-dir results/

    # Named model, hands-off:
    python3 scripts/02_build_hmm.py --aln seeds_trimmed.faa --name my_gene --yes
"""
import argparse
import sys
from pathlib import Path

# Make the app package importable no matter what directory we are run from,
# and make cli_common (which lives beside this script) importable too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.hmm_builder import run_hmmbuild
from pipeline.utils import ensure_tools_on_path
from cli_common import Guide, add_common_args


def parse_args():
    p = argparse.ArgumentParser(
        description="Build a HMMER3 profile HMM from an aligned FASTA file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Not required=True: a human in a terminal can supply these via the wizard.
    p.add_argument("--aln",     type=Path,
                   help="Input aligned protein FASTA (output of 01_align.py).")
    p.add_argument("--out-dir", default=Path("results"), type=Path,
                   help="Output directory; profile.hmm is written here.")
    p.add_argument("--name",    default="novel_phage_gene",
                   help="Name embedded in the HMM (passed to hmmbuild --name).")
    add_common_args(p)          # --yes / --interactive / --no-color / --explain-only
    return p.parse_args()


def main():
    args = parse_args()
    guide = Guide.from_args(args)
    ensure_tools_on_path()

    guide.header(2, "Build HMM",
                 "Distil your seed alignment into a position-specific family model.")

    # ── GUIDED WIZARD ────────────────────────────────────────────────────
    if guide.interactive and args.aln is None:
        guide.wizard_intro("Let's build your profile HMM.")
        args.aln = guide.ask_path(
            "Path to your aligned FASTA?",
            default="results/seeds_aligned.faa",
            help_text="This is the alignment produced by 01_align.py "
                      "(use seeds_trimmed.faa if you trimmed it).",
        )
        args.name = guide.ask(
            "Name to embed in the HMM?",
            default=args.name,
            help_text="A label for this family; appears in HMMER output and Methods.",
        )

    # ── Validate (works in both modes) ───────────────────────────────────
    if args.aln is None:
        guide.error("No --aln given. Provide one, or run in a terminal for the wizard.")
        sys.exit(2)

    aln = args.aln.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not aln.exists():
        guide.error(f"Alignment not found: {aln}")
        sys.exit(1)

    hmm_out = out_dir / "profile.hmm"

    guide.narrate(f"Input   : {aln.name}")
    guide.narrate(f"HMM name: {args.name}")
    guide.narrate(f"Output  : {hmm_out}")

    # ── EXPLAIN-AND-CONFIRM ──────────────────────────────────────────────
    guide.command(f"hmmbuild -n {args.name} {hmm_out} {aln}",
                  "Convert the alignment into a profile HMM that scores every "
                  "column's residue preferences.")
    if guide.confirm("Run hmmbuild now?") != "yes":
        guide.warn("HMM build skipped — nothing to do.")
        sys.exit(0)

    guide.narrate("Running hmmbuild …")
    stats = run_hmmbuild(aln, hmm_out, hmm_name=args.name)

    if not stats:
        guide.error("hmmbuild failed — no stats returned.")
        sys.exit(1)
    if not hmm_out.exists():
        guide.error(f"Expected output not found: {hmm_out}")
        sys.exit(1)

    # ── NARRATE: interpret the model ─────────────────────────────────────
    guide.header(None, "HMM statistics")
    leng = stats.get("leng", "n/a")
    nseq = stats.get("nseq", "n/a")
    guide.narrate(f"Name      : {stats.get('name', args.name)}")
    guide.narrate(f"Length    : {leng} match states")
    guide.narrate(f"Sequences : {nseq}")
    guide.narrate(f"Alphabet  : {stats.get('alph', 'n/a')}")
    guide.narrate(f"Checksum  : {stats.get('cksum', 'n/a')}")
    if stats.get("hmmbuild_version"):
        guide.narrate(f"HMMER     : {stats['hmmbuild_version']}")

    # The number of match states is roughly the family's core length.
    try:
        if int(leng) < 30:
            guide.result(f"Short model ({leng} states) — fine for small domains, "
                         "but expect less discriminating power.", good=True)
        else:
            guide.result(f"Model has {leng} match states → ready to search.", good=True)
    except (TypeError, ValueError):
        guide.result("Profile HMM built.", good=True)

    guide.done(f"Profile HMM written → {hmm_out}")
    guide.detail("Next: 03_search.py scores a database against this HMM.")
    sys.exit(0)


if __name__ == "__main__":
    main()
