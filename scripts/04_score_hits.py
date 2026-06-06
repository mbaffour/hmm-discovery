#!/usr/bin/env python3
"""
04_score_hits.py — Sort raw hmmsearch hits into confidence tiers.
=================================================================

WHAT THIS STEP DOES (the biology)
---------------------------------
Step 03 returns every sequence that scored above an E-value cutoff — but a raw
hit list mixes confident family members with borderline and spurious matches.
This step weighs MULTIPLE lines of evidence (bit score, how much of the HMM the
hit covers, alignment length, composition bias) and assigns each hit to a tier:

    high_confidence — strong bit score AND good HMM coverage → almost certainly real
    putative        — moderate evidence → probably real, worth follow-up
    divergent       — weak or partial → possible distant homolog, treat with care
    likely_fp       — likely false positive → background noise

It also appends QC flags (high_bias, short_alignment, low_complexity,
contig_edge) so you can see *why* a hit landed where it did.

WHAT THE KEY PARAMETERS MEAN
----------------------------
    --evalue     Pre-filter: drop hits worse than this before scoring.
    --bitscore   The strict bit-score boundary for the high_confidence tier.
    --coverage   Minimum fraction of the HMM a hit must span to be "putative".
    --hmm-length HMM length in match states; 0 = infer it from the data.

OUTPUTS
-------
    results/hits_scored.tsv   the input hits plus confidence_tier and QC columns

INTERACTIVITY
-------------
Run it in a terminal with no/partial arguments and it becomes a guided wizard:
it interviews you for the inputs and thresholds, then narrates the tier
breakdown. Pipe it, redirect it, or pass --yes for hands-off operation (safe
for HPC / run_pipeline.py). See cli_common.py.

EXAMPLES
--------
    # Guided — the script will interview you:
    python3 scripts/04_score_hits.py

    # Explicit:
    python3 scripts/04_score_hits.py --hits results/hits_combined.tsv --out-dir results/

    # Custom thresholds, hands-off:
    python3 scripts/04_score_hits.py --hits hits.tsv --bitscore 50 --coverage 0.7 --yes
"""
import argparse
import sys
from pathlib import Path

# Make the app package importable no matter what directory we are run from,
# and make cli_common (which lives beside this script) importable too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from pipeline.confidence import classify_hits, add_qc_flags
from pipeline.utils import ensure_tools_on_path
from cli_common import Guide, add_common_args


def parse_args():
    p = argparse.ArgumentParser(
        description="Score hmmsearch hits into confidence tiers with QC flags.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Not required=True: a human in a terminal can supply these via the wizard.
    p.add_argument("--hits",     type=Path,
                   help="Input hits TSV (output of 03_search.py or similar).")
    p.add_argument("--hmm",      type=Path,
                   help="Profile HMM (02_build_hmm.py). Read to get the true HMM "
                        "length — strongly recommended, otherwise every hit is "
                        "flagged likely_fp when the length can't be inferred.")
    p.add_argument("--out-dir",  default=Path("results"), type=Path,
                   help="Output directory.")
    p.add_argument("--evalue",   default=1e-5,   type=float,
                   help="E-value filter applied before scoring (pre-filter).")
    p.add_argument("--bitscore", default=45.0,   type=float,
                   help="Strict bit-score threshold for high_confidence tier.")
    p.add_argument("--coverage", default=0.30,   type=float,
                   help="Minimum HMM coverage fraction for putative tier (0–1).")
    p.add_argument("--hmm-length", default=0,    type=int,
                   help="HMM profile length in match states. 0 = infer from data.")
    add_common_args(p)          # --yes / --interactive / --no-color / --explain-only
    return p.parse_args()


def main():
    args = parse_args()
    guide = Guide.from_args(args)
    ensure_tools_on_path()

    guide.header(4, "Score Hits",
                 "Sort raw matches into high-confidence, putative, divergent, and likely-FP tiers.")

    # ── GUIDED WIZARD ────────────────────────────────────────────────────
    if guide.interactive and args.hits is None:
        guide.wizard_intro("Let's score your search hits.")
        args.hits = guide.ask_path(
            "Path to your hits TSV?",
            default="results/hits_combined.tsv",
            help_text="The combined hits table written by 03_search.py.",
        )
        if args.hmm is None:
            args.hmm = guide.ask_path(
                "Path to your profile HMM?",
                default="results/profile.hmm",
                help_text="Read to get the HMM length so coverage can be judged. "
                          "Without it, every hit is flagged likely_fp.",
            )
        args.bitscore = float(guide.ask_choice(
            "Strict bit-score cutoff for the high-confidence tier?",
            [
                ("45", "45 — standard (recommended)"),
                ("30", "30 — permissive (keeps weaker hits as high-conf)"),
                ("60", "60 — strict (only very strong hits are high-conf)"),
            ],
            default_index=0,
            help_text="Hits at or above this bit score can reach high_confidence.",
        ))

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

    guide.narrate(f"Input    : {hits_path.name}")
    guide.narrate(f"E-value  : {args.evalue}")
    guide.narrate(f"Bit score: {args.bitscore}")
    guide.narrate(f"Coverage : {args.coverage}")

    df = pd.read_csv(hits_path, sep="\t")
    guide.detail(f"Loaded {len(df)} rows.")

    if df.empty:
        guide.warn("Input is empty. Writing an empty scored table.")
        out_path = out_dir / "hits_scored.tsv"
        df.to_csv(out_path, sep="\t", index=False)
        guide.done(f"Nothing to score. Output: {out_path}")
        sys.exit(0)

    # Pre-filter on e-value if the column exists.
    if "evalue" in df.columns:
        before = len(df)
        df = df[pd.to_numeric(df["evalue"], errors="coerce") <= args.evalue].copy()
        guide.detail(f"After e-value filter (≤ {args.evalue}): {len(df)} / {before} rows.")

    # Determine HMM length, in priority order:
    #   1. explicit --hmm-length
    #   2. read it from the profile HMM (--hmm)  ← the accurate source
    #   3. infer from the hmm_to column (only present when a domtblout was merged)
    # This matters a lot: score_hit() flags EVERY hit as likely_fp when the HMM
    # length is 0 (it cannot judge coverage), so we work hard to find a real one.
    hmm_length = args.hmm_length
    if hmm_length == 0 and args.hmm is not None:
        hmm_file = args.hmm.resolve()
        if hmm_file.exists():
            try:
                from pipeline.hmm_builder import parse_hmm_file
                hmm_length = int(parse_hmm_file(hmm_file).get("LENG", 0) or 0)
                guide.detail(f"HMM length read from {hmm_file.name}: {hmm_length}")
            except Exception as exc:
                guide.warn(f"Could not read HMM length from {hmm_file.name}: {exc}")
        else:
            guide.warn(f"--hmm not found: {hmm_file}")
    if hmm_length == 0 and "hmm_to" in df.columns and not df["hmm_to"].isna().all():
        hmm_length = int(df["hmm_to"].max())
        guide.detail(f"HMM length inferred from hmm_to column: {hmm_length}")
    if hmm_length == 0:
        guide.warn("HMM length unknown — every hit would be flagged likely_fp. "
                   "Pass --hmm results/profile.hmm so coverage can be judged.")

    strict = args.bitscore
    moderate = strict * 0.67  # ~30 if strict=45 — the putative/divergent boundary.

    guide.narrate(f"HMM length: {hmm_length}")
    guide.narrate(f"Thresholds: strict={strict}, moderate={moderate:.1f}")

    # ── EXPLAIN-AND-CONFIRM ──────────────────────────────────────────────
    guide.command(
        f"classify_hits(bitscore≥{strict}, moderate≥{moderate:.1f}, "
        f"hmm_cov≥{args.coverage}) → add_qc_flags()",
        "Apply the multi-evidence tiering rules and append QC flags to every hit.")
    if guide.confirm("Score the hits now?") != "yes":
        guide.warn("Scoring skipped — nothing written.")
        sys.exit(0)

    guide.narrate("Classifying hits and adding QC flags …")
    scored = classify_hits(df, hmm_length=hmm_length, strict=strict,
                           moderate=moderate, hmm_cov_floor=args.coverage)
    # add_qc_flags() returns a Series of pipe-separated flag strings, one per
    # row — assign it to the qc_flags column (do NOT rebind `scored`, which
    # would replace the whole DataFrame with a Series and corrupt the output).
    scored["qc_flags"] = add_qc_flags(scored)

    out_path = out_dir / "hits_scored.tsv"
    scored.to_csv(out_path, sep="\t", index=False)

    # ── NARRATE: interpret the tier distribution ─────────────────────────
    guide.header(None, "Tier distribution")
    if "confidence_tier" in scored.columns:
        counts = scored["confidence_tier"].value_counts()
        for tier, n in counts.items():
            guide.narrate(f"{tier:<20} {n:>6}")
        high = int(counts.get("high_confidence", 0))
        fp = int(counts.get("likely_fp", 0))
        if high > 0:
            guide.result(f"{high} high-confidence hits → probable true family members.")
        elif counts.get("putative", 0) or counts.get("divergent", 0):
            guide.result("No high-confidence hits, but putative/divergent ones exist — "
                         "likely distant homologs.", good=False)
            guide.detail("Consider a more permissive --bitscore, or iterate (step 06).")
        else:
            guide.result("All hits look like false positives.", good=False)
            guide.detail("Re-check the input DB type and the search E-value in step 03.")
        if fp:
            guide.detail(f"{fp} hits flagged likely_fp — these are filtered out downstream.")

    guide.done(f"Scored hits written → {out_path}")
    guide.detail("Next: 05_classify_hits.py builds the canonical table and extracts sequences.")
    sys.exit(0)


if __name__ == "__main__":
    main()
