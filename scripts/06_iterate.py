#!/usr/bin/env python3
"""
06_iterate.py — Iterative HMM refinement (jackhmmer-style seed expansion).
==========================================================================

WHAT THIS STEP DOES (the biology)
---------------------------------
A profile HMM built from a small seed set only "knows" the diversity of those
seeds. If the true family is broader, you can grow the model by bootstrapping:
search with the current HMM, fold the strongest new hits back into the seed
set, rebuild, and search again. Each round the model gets a little wider and
catches relatives the previous round missed — until it stops finding anything
new (convergence). This is the same idea as jackhmmer / PSI-BLAST iteration.

Each iteration runs:
    1. Align the current seed set            (MAFFT)
    2. Build an HMM from that alignment       (hmmbuild)
    3. Search the database(s) with it         (hmmsearch)
    4. Add high-confidence NEW hits to seeds  (auto-approved if bit ≥ strict)
    5. Check convergence and repeat

Convergence (BOTH must hold) stops the loop early:
    * Hit count changed < 5% versus the previous iteration, AND
    * HMM length changed < 3 match states.

WHAT THE KEY PARAMETERS MEAN
----------------------------
    --iterations  Maximum rounds (the loop may stop earlier at convergence).
    --evalue      hmmsearch E-value threshold used every round.
    --bitscore    A new hit must score at least this to be promoted to a seed.

OUTPUTS
-------
    results/seeds_expanded.faa      the final, grown seed set
    results/profile_final.hmm       the final refined HMM
    results/iteration_history.tsv   per-round hit counts, HMM length, new seeds
    results/iteration_NN/...        per-iteration working files

INTERACTIVITY
-------------
Run it in a terminal with no/partial arguments and it becomes a guided wizard,
explains the loop, and confirms once before the (potentially long) run. Pipe it
or pass --yes for hands-off operation (safe for HPC / run_pipeline.py).

EXAMPLES
--------
    # Guided — the script will interview you:
    python3 scripts/06_iterate.py

    # Explicit:
    python3 scripts/06_iterate.py \\
        --seeds seeds.faa --hits-faa results/hits_proteins.faa \\
        --hmm results/profile.hmm --db phages.faa --out-dir results/ --iterations 5

    # Multiple DBs, hands-off:
    python3 scripts/06_iterate.py --seeds seeds.faa --hits-faa hits.faa \\
        --hmm profile.hmm --db a.faa --db b.faa --iterations 10 --cpu 8 --yes
"""
import argparse
import shutil
import sys
from pathlib import Path

# Make the app package importable no matter what directory we are run from,
# and make cli_common (which lives beside this script) importable too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from pipeline.alignment import run_mafft
from pipeline.hmm_builder import run_hmmbuild
from pipeline.searcher import run_hmmsearch_protein, parse_tblout
from pipeline.hit_classifier import build_main_hits_table, extract_hit_sequences
from pipeline.iterative import iteration_candidates, convergence_check, append_to_seeds
from pipeline.utils import ensure_tools_on_path
from cli_common import Guide, add_common_args


def parse_args():
    p = argparse.ArgumentParser(
        description="Iteratively refine an HMM by expanding seeds with high-confidence hits.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Not required=True: a human in a terminal can supply these via the wizard.
    p.add_argument("--seeds",      type=Path,
                   help="Initial un-aligned seed protein FASTA.")
    p.add_argument("--hits-faa",   type=Path,
                   help="Protein FASTA containing candidate sequences from 05_classify_hits.py.")
    p.add_argument("--hmm",        type=Path,
                   help="Starting HMM profile (output of 02_build_hmm.py).")
    p.add_argument("--db",         type=Path, action="append",
                   dest="dbs",    metavar="FASTA",
                   help="Target protein database FASTA. Repeat for multiple DBs.")
    p.add_argument("--out-dir",    default=Path("results"), type=Path,
                   help="Output directory.")
    p.add_argument("--iterations", default=5,      type=int,
                   help="Maximum number of refinement iterations.")
    p.add_argument("--evalue",     default=1e-5,   type=float,
                   help="E-value threshold for hmmsearch at each iteration.")
    p.add_argument("--bitscore",   default=45.0,   type=float,
                   help="Strict bit-score threshold for selecting new seeds.")
    p.add_argument("--cpu",        default=4,      type=int,
                   help="Number of CPU threads for alignment and search.")
    add_common_args(p)          # --yes / --interactive / --no-color / --explain-only
    return p.parse_args()


def main():
    args = parse_args()
    guide = Guide.from_args(args)
    ensure_tools_on_path()

    guide.header(6, "Iterative HMM Refinement",
                 "Grow the seed set with strong new hits, round by round, until convergence.")

    # ── GUIDED WIZARD ────────────────────────────────────────────────────
    if guide.interactive and (args.seeds is None or args.hits_faa is None
                              or args.hmm is None or not args.dbs):
        guide.wizard_intro("Let's set up iterative refinement.")
        if args.seeds is None:
            args.seeds = guide.ask_path(
                "Path to your seed FASTA?",
                default="results/seeds_expanded.faa",
                help_text="The current seed set to grow (often the original seeds).",
            )
        if args.hits_faa is None:
            args.hits_faa = guide.ask_path(
                "Path to the candidate hit sequences FASTA?",
                default="results/hits_proteins.faa",
                help_text="hits_proteins.faa from 05_classify_hits.py.",
            )
        if args.hmm is None:
            args.hmm = guide.ask_path(
                "Path to the starting HMM?",
                default="results/profile.hmm",
                help_text="The profile.hmm from 02_build_hmm.py.",
            )
        if not args.dbs:
            first = guide.ask_path(
                "Database FASTA to search each round?",
                help_text="Protein database to re-search as the model widens.",
            )
            args.dbs = [first]
            while guide.ask_yesno("Add another database?", default_yes=False):
                args.dbs.append(guide.ask_path("Next database FASTA?"))
        args.iterations = int(guide.ask(
            "Maximum number of iterations?",
            default=str(args.iterations),
            help_text="The loop stops earlier if it converges.",
        ))

    # ── Validate (works in both modes) ───────────────────────────────────
    missing = [n for n, v in [("--seeds", args.seeds), ("--hits-faa", args.hits_faa),
                              ("--hmm", args.hmm)] if v is None]
    if missing:
        guide.error(f"Missing required input(s): {', '.join(missing)}. "
                    "Provide them, or run in a terminal for the wizard.")
        sys.exit(2)
    if not args.dbs:
        guide.error("No --db given. Provide at least one database FASTA.")
        sys.exit(2)

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    seeds = args.seeds.resolve()
    hits_faa = args.hits_faa.resolve()
    start_hmm = args.hmm.resolve()

    for pth in [seeds, hits_faa, start_hmm]:
        if not pth.exists():
            guide.error(f"File not found: {pth}")
            sys.exit(1)
    for db in args.dbs:
        if not db.resolve().exists():
            guide.error(f"Database not found: {db}")
            sys.exit(1)

    guide.narrate(f"Seeds        : {seeds.name}")
    guide.narrate(f"Starting HMM : {start_hmm.name}")
    guide.narrate(f"Databases    : {len(args.dbs)}")
    guide.narrate(f"Max iterations: {args.iterations}")
    guide.narrate(f"E-value      : {args.evalue}")
    guide.narrate(f"Bit threshold: {args.bitscore}")

    # ── EXPLAIN-AND-CONFIRM: gate the whole (potentially long) loop once ──
    guide.command(
        f"loop ×{args.iterations}: mafft → hmmbuild → hmmsearch (-E {args.evalue}, "
        f"--cpu {args.cpu}) → promote hits with bit ≥ {args.bitscore}",
        "Each round re-aligns, rebuilds, re-searches, and folds strong new hits "
        "back into the seeds until convergence.")
    if guide.confirm("Start the refinement loop now?") != "yes":
        guide.warn("Iterative refinement skipped — nothing written.")
        sys.exit(0)

    # Working copies for this run.
    current_seeds = out_dir / "iter_seeds_0.faa"
    shutil.copy(seeds, current_seeds)
    current_hmm = out_dir / "iter_hmm_0.hmm"
    shutil.copy(start_hmm, current_hmm)

    history = []
    prev_count = 0
    prev_leng = 0

    strict = args.bitscore
    moderate = strict * 0.67

    for it in range(1, args.iterations + 1):
        iter_dir = out_dir / f"iteration_{it:02d}"
        iter_dir.mkdir(parents=True, exist_ok=True)

        guide.header(None, f"Iteration {it}")

        # 1) Align current seeds.
        aln_out = iter_dir / "seeds_aligned.faa"
        guide.command(f"mafft --auto --thread {args.cpu} {current_seeds} > {aln_out}",
                      "Re-align the (possibly grown) seed set.")
        aln_result = run_mafft(current_seeds, aln_out, cpu=args.cpu)
        if not aln_result or not aln_result.exists():
            guide.error(f"Alignment failed at iteration {it}.")
            sys.exit(1)

        # 2) Build HMM.
        hmm_out = iter_dir / "profile.hmm"
        guide.command(f"hmmbuild -n iter_{it} {hmm_out} {aln_out}",
                      "Rebuild the profile from the re-aligned seeds.")
        hmm_stats = run_hmmbuild(aln_out, hmm_out, hmm_name=f"iter_{it}")
        if not hmm_stats:
            guide.error(f"hmmbuild failed at iteration {it}.")
            sys.exit(1)
        curr_leng = hmm_stats.get("leng", 0)

        # 3) Search all databases.
        all_hits: list[pd.DataFrame] = []
        for db_path in args.dbs:
            db_path = db_path.resolve()
            db_name = db_path.stem
            guide.command(f"hmmsearch --tblout {iter_dir}/{db_name}.tblout "
                          f"-E {args.evalue} --cpu {args.cpu} {hmm_out} {db_path}",
                          f"Re-search {db_name} with the refined HMM.")
            res = run_hmmsearch_protein(
                hmm_path=hmm_out,
                db_faa=db_path,
                out_dir=iter_dir,
                db_name=db_name,
                evalue=args.evalue,
                cpu=args.cpu,
            )
            tblout_path = res.get("tblout")
            if tblout_path and Path(tblout_path).exists():
                df = parse_tblout(tblout_path)
                if not df.empty:
                    df["database_source"] = db_name
                    all_hits.append(df)

        combined = pd.concat(all_hits, ignore_index=True) if all_hits else pd.DataFrame()
        curr_count = len(combined)
        guide.result(f"Iteration {it}: {curr_count} hits  |  HMM length: {curr_leng}")

        # 4) Build main hits table and find new candidates.
        hits_table = pd.DataFrame()
        if not combined.empty:
            hits_table = build_main_hits_table(
                tblout_df=combined,
                domtblout_df=pd.DataFrame(),
                hmm_length=curr_leng,
                db_name="combined",
                strict=strict,
                moderate=moderate,
                iteration=it,
            )

        candidates = iteration_candidates(hits_table, current_seeds, strict=strict)
        guide.detail(f"New candidates (bit ≥ {strict}): {len(candidates)}")

        history.append({
            "iteration": it,
            "hit_count": curr_count,
            "hmm_leng": curr_leng,
            "new_candidates": len(candidates),
        })

        # 5) Check convergence.
        converged = convergence_check(prev_count, curr_count, prev_leng, curr_leng)
        if converged and it > 1:
            guide.result(f"Converged at iteration {it} — hit count and model length stable.")
            break

        # 6) Append candidates to seed set (auto-approve all with bit ≥ strict).
        if not candidates.empty:
            approved_ids = candidates["protein_id"].dropna().tolist()
            new_seeds = iter_dir / "seeds_expanded.faa"
            shutil.copy(current_seeds, new_seeds)
            n_added = append_to_seeds(
                existing_faa=current_seeds,
                new_seqs_faa=hits_faa,
                approved_ids=approved_ids,
                out_faa=new_seeds,
            )
            guide.detail(f"Added {n_added} sequences to the seed set.")
            current_seeds = new_seeds
        else:
            guide.detail("No new candidates to add; seed set unchanged.")

        current_hmm = hmm_out
        prev_count = curr_count
        prev_leng = curr_leng

    # Write final outputs.
    seeds_expanded = out_dir / "seeds_expanded.faa"
    shutil.copy(current_seeds, seeds_expanded)

    profile_final = out_dir / "profile_final.hmm"
    shutil.copy(current_hmm, profile_final)

    history_df = pd.DataFrame(history)
    history_out = out_dir / "iteration_history.tsv"
    history_df.to_csv(history_out, sep="\t", index=False)

    guide.header(None, "Iteration history")
    if not history_df.empty:
        for line in history_df.to_string(index=False).splitlines():
            guide.narrate(line)

    guide.result(f"Final seeds → {seeds_expanded}")
    guide.result(f"Final HMM   → {profile_final}")
    guide.result(f"History     → {history_out}")
    guide.done("Iterative refinement complete.")
    guide.detail("Next: re-run 03_search.py with profile_final.hmm, or proceed to 07–13.")
    sys.exit(0)


if __name__ == "__main__":
    main()
