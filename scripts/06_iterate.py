#!/usr/bin/env python3
"""
06_iterate.py — Iterative HMM refinement (jackhmmer-style).

Expands the seed set through successive rounds of:
  1. Align current seeds
  2. Build HMM from alignment
  3. Search database(s) with HMM
  4. Add high-confidence novel hits to seeds
  5. Repeat until convergence

Convergence criteria (both required):
  - Hit count change < 5% relative to previous iteration
  - HMM length change < 3 match states

Example
-------
    python3 scripts/06_iterate.py \\
        --seeds seeds.faa --hits-faa hits_proteins.faa \\
        --hmm results/profile.hmm --db phages.faa \\
        --out-dir results/ --iterations 5

    python3 scripts/06_iterate.py \\
        --seeds seeds.faa --hits-faa hits.faa \\
        --hmm profile.hmm --db a.faa --db b.faa \\
        --iterations 10 --evalue 1e-5 --cpu 8
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from pipeline.alignment import run_mafft
from pipeline.hmm_builder import run_hmmbuild
from pipeline.searcher import run_hmmsearch_protein, parse_tblout
from pipeline.hit_classifier import build_main_hits_table, extract_hit_sequences
from pipeline.iterative import iteration_candidates, convergence_check, append_to_seeds
from pipeline.utils import ensure_tools_on_path


def parse_args():
    p = argparse.ArgumentParser(
        description="Iteratively refine an HMM by expanding seeds with high-confidence hits.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--seeds",      required=True,  type=Path,
                   help="Initial un-aligned seed protein FASTA.")
    p.add_argument("--hits-faa",   required=True,  type=Path,
                   help="Protein FASTA containing candidate sequences from 05_classify_hits.py.")
    p.add_argument("--hmm",        required=True,  type=Path,
                   help="Starting HMM profile (output of 02_build_hmm.py).")
    p.add_argument("--db",         required=True,  type=Path, action="append",
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
    return p.parse_args()


def main():
    args = parse_args()
    ensure_tools_on_path()

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    seeds = args.seeds.resolve()
    hits_faa = args.hits_faa.resolve()
    start_hmm = args.hmm.resolve()

    for p in [seeds, hits_faa, start_hmm]:
        if not p.exists():
            print(f"ERROR: File not found: {p}", file=sys.stderr)
            sys.exit(1)
    for db in args.dbs:
        if not db.resolve().exists():
            print(f"ERROR: Database not found: {db}", file=sys.stderr)
            sys.exit(1)

    print(f"\n=== Step 6: Iterative HMM Refinement ===")
    print(f"  Seeds       : {seeds}")
    print(f"  Starting HMM: {start_hmm}")
    print(f"  Databases   : {len(args.dbs)}")
    print(f"  Max iterations: {args.iterations}")
    print(f"  E-value     : {args.evalue}")
    print(f"  Bit threshold: {args.bitscore}")

    # Working copies for this run
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

        print(f"\n--- Iteration {it} ---")

        # 1) Align current seeds
        aln_out = iter_dir / "seeds_aligned.faa"
        print(f"[CMD] mafft --auto --thread {args.cpu} {current_seeds} > {aln_out}")
        aln_result = run_mafft(current_seeds, aln_out, cpu=args.cpu)
        if not aln_result or not aln_result.exists():
            print(f"ERROR: Alignment failed at iteration {it}.", file=sys.stderr)
            sys.exit(1)

        # 2) Build HMM
        hmm_out = iter_dir / "profile.hmm"
        print(f"[CMD] hmmbuild -n iter_{it} {hmm_out} {aln_out}")
        hmm_stats = run_hmmbuild(aln_out, hmm_out, hmm_name=f"iter_{it}")
        if not hmm_stats:
            print(f"ERROR: hmmbuild failed at iteration {it}.", file=sys.stderr)
            sys.exit(1)
        curr_leng = hmm_stats.get("leng", 0)

        # 3) Search all databases
        all_hits: list[pd.DataFrame] = []
        for db_path in args.dbs:
            db_path = db_path.resolve()
            db_name = db_path.stem
            print(f"[CMD] hmmsearch --tblout {iter_dir}/{db_name}.tblout "
                  f"-E {args.evalue} --cpu {args.cpu} {hmm_out} {db_path}")
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
        print(f"  Iteration {it}: {curr_count} hits  |  HMM length: {curr_leng}")

        # 4) Build main hits table and find new candidates
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
        print(f"  New candidates: {len(candidates)}")

        history.append({
            "iteration": it,
            "hit_count": curr_count,
            "hmm_leng": curr_leng,
            "new_candidates": len(candidates),
        })

        # 5) Check convergence
        converged = convergence_check(prev_count, curr_count, prev_leng, curr_leng)
        if converged and it > 1:
            print(f"  Converged at iteration {it}.")
            break

        # 6) Append candidates to seed set (auto-approve all with bit >= strict)
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
            print(f"  Added {n_added} sequences to seed set.")
            current_seeds = new_seeds
        else:
            print("  No new candidates to add; seed set unchanged.")

        current_hmm = hmm_out
        prev_count = curr_count
        prev_leng = curr_leng

    # Write final outputs
    seeds_expanded = out_dir / "seeds_expanded.faa"
    shutil.copy(current_seeds, seeds_expanded)

    profile_final = out_dir / "profile_final.hmm"
    shutil.copy(current_hmm, profile_final)

    history_df = pd.DataFrame(history)
    history_out = out_dir / "iteration_history.tsv"
    history_df.to_csv(history_out, sep="\t", index=False)

    print(f"\n--- Iteration history ---")
    if not history_df.empty:
        print(history_df.to_string(index=False))

    print(f"\n  Final seeds    -> {seeds_expanded}")
    print(f"  Final HMM      -> {profile_final}")
    print(f"  History        -> {history_out}")
    print(f"\nDone.")
    sys.exit(0)


if __name__ == "__main__":
    main()
