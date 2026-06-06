#!/usr/bin/env python3
"""
run_pipeline.py — Master pipeline runner: steps 01–14 in sequence.

Runs the full HMM Discovery analysis pipeline end-to-end:
  01  Align seed sequences (MAFFT)
  02  Build HMM (hmmbuild)
  03  Search databases (hmmsearch)
  04  Score hits (confidence tiers + QC flags)
  05  Classify hits + extract sequences
  06  Iterative refinement
  07  Synteny analysis
  08  Taxonomy annotation
  09  Phylogenetic tree (IQ-TREE)
  10  Presence/absence matrix + heatmap
  11  Sequence clustering (CD-HIT / MMseqs2)
  12  Motif discovery (MEME + FIMO)
  13  Functional annotation (domain architecture + TM)
  14  HTML report + methods text + export ZIP

Use --skip to omit individual steps, or --start-at to resume from a step.

Example
-------
    python3 scripts/run_pipeline.py \\
        --seeds seeds.faa --db phages.faa \\
        --proj-dir my_project/ --email user@uni.edu --cpu 8

    # Resume from step 07, skipping phylogeny and clustering:
    python3 scripts/run_pipeline.py \\
        --seeds seeds.faa --db phages.faa \\
        --proj-dir my_project/ \\
        --start-at 07 --skip 09 11
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

# Ensure pipeline/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.utils import ensure_tools_on_path

SCRIPTS_DIR = Path(__file__).resolve().parent

# Step definitions: (id, script_name, description)
STEPS = [
    ("01", "01_align.py",       "Multiple sequence alignment"),
    ("02", "02_build_hmm.py",   "Build HMM profile"),
    ("03", "03_search.py",      "Search databases"),
    ("04", "04_score_hits.py",  "Score and tier hits"),
    ("05", "05_classify_hits.py", "Classify hits + extract sequences"),
    ("06", "06_iterate.py",     "Iterative HMM refinement"),
    ("07", "07_synteny.py",     "Synteny analysis"),
    ("08", "08_taxonomy.py",    "Taxonomy annotation"),
    ("09", "09_phylogeny.py",   "Phylogenetic tree (IQ-TREE)"),
    ("10", "10_matrix.py",      "Presence/absence matrix + heatmap"),
    ("11", "11_cluster.py",     "Sequence clustering"),
    ("12", "12_motifs.py",      "Motif discovery (MEME)"),
    ("13", "13_annotate.py",    "Functional annotation"),
    ("14", "14_report.py",      "HTML report + methods + export ZIP"),
]


def parse_args():
    p = argparse.ArgumentParser(
        description="Run the complete HMM Discovery pipeline (steps 01–14).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--seeds",     required=True,  type=Path,
                   help="Un-aligned seed protein FASTA.")
    p.add_argument("--db",        required=True,  type=Path, action="append",
                   dest="dbs",   metavar="FASTA",
                   help="Target database FASTA. Repeat for multiple databases.")
    p.add_argument("--proj-dir",  required=True,  type=Path,
                   help="Project root directory. All outputs go here.")
    p.add_argument("--email",     default="researcher@example.com",
                   help="NCBI Entrez e-mail (required for synteny step 07).")
    p.add_argument("--cpu",       default=4,      type=int,
                   help="CPU threads for alignment, search, and tree inference.")
    p.add_argument("--evalue",    default=1e-5,   type=float,
                   help="E-value threshold for hmmsearch steps.")
    p.add_argument("--skip",      nargs="+",      default=[], metavar="STEP",
                   help="Step IDs to skip (e.g. --skip 07 09 11).")
    p.add_argument("--start-at",  default="01",   metavar="STEP",
                   help="Start execution at this step ID (skips earlier steps).")
    p.add_argument("--trim",      action="store_true",
                   help="Run trimAl after alignment in step 01.")
    p.add_argument("--nuc",       action="store_true",
                   help="Databases are nucleotide; 6-frame translate in step 03.")
    p.add_argument("--iterations", default=3,     type=int,
                   help="Maximum iterations for step 06 (iterative refinement).")
    p.add_argument("--local-gb",  type=Path,
                   help="Directory of local GenBank files for synteny (step 07).")
    p.add_argument("--hmm-name",  default="novel_phage_gene",
                   help="Name to embed in the HMM profile (step 02).")
    return p.parse_args()


def run_step(step_id: str, script: str, args_list: list[str], dry_run: bool = False) -> bool:
    """Run a pipeline step via subprocess; return True on success."""
    script_path = SCRIPTS_DIR / script
    cmd = [sys.executable, str(script_path)] + args_list
    print(f"\n{'='*60}")
    print(f"  Running step {step_id}: {script}")
    print(f"  CMD: {' '.join(cmd)}")
    print(f"{'='*60}")

    if dry_run:
        return True

    t0 = time.time()
    proc = subprocess.run(cmd)
    elapsed = time.time() - t0

    if proc.returncode == 0:
        print(f"\n  [DONE] Step {step_id} completed in {elapsed:.1f}s")
        return True
    else:
        print(f"\n  [FAIL] Step {step_id} exited with code {proc.returncode} "
              f"(elapsed: {elapsed:.1f}s)", file=sys.stderr)
        return False


def main():
    args = parse_args()
    ensure_tools_on_path()

    proj_dir = args.proj_dir.resolve()
    proj_dir.mkdir(parents=True, exist_ok=True)
    results_dir = proj_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    seeds = args.seeds.resolve()
    if not seeds.exists():
        print(f"ERROR: Seeds FASTA not found: {seeds}", file=sys.stderr)
        sys.exit(1)

    for db in args.dbs:
        if not db.resolve().exists():
            print(f"ERROR: Database not found: {db}", file=sys.stderr)
            sys.exit(1)

    # Normalise skip/start-at to 2-char IDs
    skip_set  = {s.lstrip("0").zfill(2) if len(s) <= 2 else s for s in args.skip}
    skip_set  = {s.zfill(2) for s in args.skip}
    start_num = int(args.start_at.lstrip("0") or "1")

    db_flags: list[str] = []
    for db in args.dbs:
        db_flags += ["--db", str(db.resolve())]

    print(f"\n{'#'*60}")
    print(f"# HMM Discovery — Full Pipeline")
    print(f"# Seeds   : {seeds}")
    print(f"# Databases: {len(args.dbs)}")
    print(f"# Proj dir : {proj_dir}")
    print(f"# Steps to skip: {sorted(skip_set) or 'none'}")
    print(f"# Start at : {args.start_at}")
    print(f"{'#'*60}")

    # Track per-step status
    status: dict[str, str] = {sid: "pending" for sid, _, _ in STEPS}

    # Paths that accumulate as steps complete
    aln_faa      = results_dir / "seeds_aligned.faa"
    trimmed_faa  = results_dir / "seeds_trimmed.faa"
    profile_hmm  = results_dir / "profile.hmm"
    hits_tsv     = results_dir / "hits_combined.tsv"
    scored_tsv   = results_dir / "hits_scored.tsv"
    main_hits    = results_dir / "hits_main.tsv"
    hits_faa     = results_dir / "hits_proteins.faa"
    seeds_exp    = results_dir / "seeds_expanded.faa"
    profile_final = results_dir / "profile_final.hmm"
    taxonomy_tsv = results_dir / "taxonomy_table.tsv"
    matrix_tsv   = results_dir / "presence_absence_matrix.tsv"

    # Decide which alignment to use for HMM build / phylogeny
    # (prefer trimmed if --trim was requested)
    final_aln = trimmed_faa if args.trim else aln_faa

    for step_id, script, desc in STEPS:
        step_num = int(step_id)

        if step_num < start_num:
            status[step_id] = "skipped (before start-at)"
            continue
        if step_id in skip_set:
            status[step_id] = "skipped (--skip)"
            continue

        print(f"\n\n{'#'*60}")
        print(f"# STEP {step_id}: {desc}")
        print(f"{'#'*60}")

        # Build step-specific argument list
        step_args: list[str] = []

        if step_id == "01":
            step_args = [
                "--seeds", str(seeds),
                "--out-dir", str(results_dir),
                "--threads", str(args.cpu),
            ]
            if args.trim:
                step_args.append("--trim")

        elif step_id == "02":
            # Use trimmed alignment if it exists, else regular alignment
            in_aln = trimmed_faa if (args.trim and trimmed_faa.exists()) else aln_faa
            if not in_aln.exists():
                in_aln = aln_faa
            step_args = [
                "--aln",     str(in_aln),
                "--out-dir", str(results_dir),
                "--name",    args.hmm_name,
            ]

        elif step_id == "03":
            step_args = [
                "--hmm",     str(profile_hmm),
                "--evalue",  str(args.evalue),
                "--cpu",     str(args.cpu),
                "--out-dir", str(results_dir),
            ] + db_flags
            if args.nuc:
                step_args.append("--nuc")

        elif step_id == "04":
            in_hits = hits_tsv if hits_tsv.exists() else results_dir / "hits_combined.tsv"
            step_args = [
                "--hits",    str(in_hits),
                "--out-dir", str(results_dir),
                "--evalue",  str(args.evalue),
            ]

        elif step_id == "05":
            in_hits = scored_tsv if scored_tsv.exists() else hits_tsv
            step_args = [
                "--hits",    str(in_hits),
                "--out-dir", str(results_dir),
            ] + db_flags

        elif step_id == "06":
            in_seeds   = seeds_exp if seeds_exp.exists() else seeds
            in_hmm     = profile_hmm
            in_hits_faa = hits_faa if hits_faa.exists() else seeds
            step_args = [
                "--seeds",      str(in_seeds),
                "--hits-faa",   str(in_hits_faa),
                "--hmm",        str(in_hmm),
                "--out-dir",    str(results_dir),
                "--iterations", str(args.iterations),
                "--evalue",     str(args.evalue),
                "--cpu",        str(args.cpu),
            ] + db_flags

        elif step_id == "07":
            in_hits = main_hits if main_hits.exists() else scored_tsv
            step_args = [
                "--hits",    str(in_hits),
                "--out-dir", str(results_dir),
                "--email",   args.email,
            ]
            if args.local_gb:
                step_args += ["--local-gb", str(args.local_gb.resolve())]

        elif step_id == "08":
            in_hits = main_hits if main_hits.exists() else scored_tsv
            step_args = [
                "--hits",    str(in_hits),
                "--out-dir", str(results_dir),
            ]

        elif step_id == "09":
            # Use final alignment; if it doesn't exist use seeds_aligned.faa
            in_aln = (profile_final.parent / "seeds_expanded.faa") \
                if seeds_exp.exists() else aln_faa
            # Actually for phylogeny, we want an alignment not a raw FASTA
            in_aln = final_aln if final_aln.exists() else aln_faa
            step_args = [
                "--aln",       str(in_aln),
                "--out-dir",   str(results_dir),
                "--cpu",       str(args.cpu),
            ]

        elif step_id == "10":
            in_hits = main_hits if main_hits.exists() else scored_tsv
            step_args = [
                "--hits",    str(in_hits),
                "--out-dir", str(results_dir),
            ]

        elif step_id == "11":
            in_faa = hits_faa if hits_faa.exists() else seeds
            step_args = [
                "--faa",     str(in_faa),
                "--out-dir", str(results_dir),
                "--cpu",     str(args.cpu),
            ]

        elif step_id == "12":
            in_faa = hits_faa if hits_faa.exists() else seeds
            step_args = [
                "--faa",     str(in_faa),
                "--out-dir", str(results_dir),
                "--cpu",     str(args.cpu),
            ]

        elif step_id == "13":
            in_faa  = hits_faa if hits_faa.exists() else seeds
            in_hmm  = profile_final if profile_final.exists() else profile_hmm
            # Domtblout from step 03
            domtbl  = results_dir / "search_results"
            # Use the first available domtblout
            domtbl_files = list(domtbl.glob("*.domtblout")) if domtbl.exists() else []
            if not domtbl_files:
                print(f"WARNING: No domtblout files found; skipping step 13.",
                      file=sys.stderr)
                status[step_id] = "skipped (no domtblout)"
                continue
            step_args = [
                "--faa",       str(in_faa),
                "--hmm",       str(in_hmm),
                "--domtblout", str(domtbl_files[0]),
                "--out-dir",   str(results_dir),
            ]

        elif step_id == "14":
            step_args = [
                "--proj-dir", str(proj_dir),
                "--out-dir",  str(proj_dir / "reports"),
            ]

        ok = run_step(step_id, script, step_args)
        status[step_id] = "OK" if ok else "FAILED"

        if not ok:
            print(f"\nERROR: Step {step_id} failed. Aborting pipeline.", file=sys.stderr)
            # Print summary of what completed so far then exit
            _print_summary(status)
            sys.exit(1)

    _print_summary(status)
    sys.exit(0)


def _print_summary(status: dict) -> None:
    """Print a summary table of step outcomes."""
    print(f"\n\n{'='*60}")
    print(f"  Pipeline Summary")
    print(f"{'='*60}")
    print(f"  {'Step':<6} {'Description':<38} {'Status'}")
    print(f"  {'-'*6} {'-'*38} {'-'*20}")
    for step_id, script, desc in STEPS:
        st = status.get(step_id, "pending")
        flag = "OK" if st == "OK" else ("SKIP" if "skip" in st.lower() else "FAIL")
        print(f"  {step_id:<6} {desc:<38} {st}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
