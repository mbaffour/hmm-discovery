#!/usr/bin/env python3
"""
run_pipeline.py — Master runner: drive steps 01–14 end-to-end.
==============================================================

WHAT THIS DOES
--------------
This is the conductor. It runs every step script in order, wiring each step's
outputs into the next step's inputs, so a single command takes you from raw seed
sequences all the way to a finished HTML report:

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

Each step is launched as its own subprocess. The master ALWAYS passes --yes to
every child so the children never stop to prompt mid-pipeline — any interaction
(collecting inputs, confirming the run) happens once, here, at the top level.

Use --skip to omit steps and --start-at to resume a partial run.

INTERACTIVITY
-------------
Run it in a terminal with no/partial arguments and it becomes a guided wizard:
it collects the seeds, database(s), and project directory, shows you the full
plan (which steps will run vs. skip), and asks for one confirmation before
launching. Pipe it or pass --yes to run the whole thing hands-off (HPC/cron).

EXAMPLES
--------
    # Guided — the runner will interview you, show the plan, and confirm:
    python3 scripts/run_pipeline.py

    # Explicit, hands-off:
    python3 scripts/run_pipeline.py \\
        --seeds seeds.faa --db phages.faa --proj-dir my_project/ \\
        --email you@uni.edu --cpu 8 --yes

    # Resume from step 07, skipping phylogeny and clustering:
    python3 scripts/run_pipeline.py --seeds seeds.faa --db phages.faa \\
        --proj-dir my_project/ --start-at 07 --skip 09 11 --yes
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

# Ensure pipeline/ is importable, and cli_common (beside this script) too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.utils import ensure_tools_on_path
from cli_common import Guide, add_common_args

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
    # Not required=True: a human in a terminal can supply these via the wizard.
    p.add_argument("--seeds",     type=Path,
                   help="Un-aligned seed protein FASTA.")
    p.add_argument("--db",        type=Path, action="append",
                   dest="dbs",   metavar="FASTA",
                   help="Target database FASTA. Repeat for multiple databases.")
    p.add_argument("--proj-dir",  type=Path,
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
    add_common_args(p)          # --yes / --interactive / --no-color / --explain-only
    return p.parse_args()


def run_step(guide: Guide, step_id: str, script: str, args_list: list[str]) -> bool:
    """Run a pipeline step via subprocess; return True on success.

    The child is always invoked with --yes (already present in args_list) so it
    never tries to prompt — the master owns all interaction.
    """
    script_path = SCRIPTS_DIR / script
    cmd = [sys.executable, str(script_path)] + args_list

    guide.command(" ".join(cmd), f"Run step {step_id} ({script}) as a subprocess.")

    t0 = time.time()
    proc = subprocess.run(cmd)
    elapsed = time.time() - t0

    if proc.returncode == 0:
        guide.result(f"Step {step_id} completed in {elapsed:.1f}s")
        return True
    else:
        guide.error(f"Step {step_id} exited with code {proc.returncode} "
                    f"(elapsed: {elapsed:.1f}s)")
        return False


def main():
    args = parse_args()
    guide = Guide.from_args(args)
    ensure_tools_on_path()

    guide.header(None, "HMM Discovery — Full Pipeline",
                 "Drive steps 01–14 end-to-end, wiring each step's output into the next.")

    # ── TOP-LEVEL WIZARD ─────────────────────────────────────────────────
    # Collect the few required inputs once; children inherit them via flags.
    if guide.interactive and (args.seeds is None or not args.dbs or args.proj_dir is None):
        guide.wizard_intro("Let's set up the full pipeline run.")
        if args.seeds is None:
            args.seeds = guide.ask_path(
                "Path to your seed protein FASTA?",
                help_text="Un-aligned seed proteins to start from (step 01 input).",
            )
        if not args.dbs:
            first = guide.ask_path(
                "Database FASTA to search?",
                help_text="Protein (.faa) or nucleotide (.fna) sequences to scan.",
            )
            args.dbs = [first]
            while guide.ask_yesno("Add another database?", default_yes=False):
                args.dbs.append(guide.ask_path("Next database FASTA?"))
            args.nuc = guide.ask_yesno(
                "Are these NUCLEOTIDE databases (raw DNA / genomes)?",
                default_yes=False,
                help_text="Yes → step 03 translates DNA in 6 frames before searching.",
            )
        if args.proj_dir is None:
            args.proj_dir = guide.ask_path(
                "Project directory for all outputs?",
                default="hmm_project",
                must_exist=False,
                help_text="Created if it does not exist; results land in <proj-dir>/results/.",
            )
        args.email = guide.ask(
            "NCBI Entrez e-mail (for synteny step 07)?",
            default=args.email,
            help_text="Used only if step 07 fetches neighbourhoods from NCBI.",
        )

    # ── Validate (works in both modes) ───────────────────────────────────
    if args.seeds is None:
        guide.error("No --seeds given. Provide one, or run in a terminal for the wizard.")
        sys.exit(2)
    if not args.dbs:
        guide.error("No --db given. Provide at least one database FASTA.")
        sys.exit(2)
    if args.proj_dir is None:
        guide.error("No --proj-dir given. Provide one, or run in a terminal for the wizard.")
        sys.exit(2)

    proj_dir = args.proj_dir.resolve()
    proj_dir.mkdir(parents=True, exist_ok=True)
    results_dir = proj_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    seeds = args.seeds.resolve()
    if not seeds.exists():
        guide.error(f"Seeds FASTA not found: {seeds}")
        sys.exit(1)

    for db in args.dbs:
        if not db.resolve().exists():
            guide.error(f"Database not found: {db}")
            sys.exit(1)

    # Normalise skip/start-at to 2-char IDs.
    skip_set  = {s.zfill(2) for s in args.skip}
    start_num = int(args.start_at.lstrip("0") or "1")

    db_flags: list[str] = []
    for db in args.dbs:
        db_flags += ["--db", str(db.resolve())]

    # ── SHOW THE PLAN and confirm once ───────────────────────────────────
    guide.narrate(f"Seeds     : {seeds}")
    guide.narrate(f"Databases : {len(args.dbs)} ({'nucleotide' if args.nuc else 'protein'})")
    guide.narrate(f"Project   : {proj_dir}")
    guide.narrate(f"CPU       : {args.cpu}   E-value: {args.evalue}")

    guide.header(None, "Plan")
    will_run = []
    for step_id, script, desc in STEPS:
        step_num = int(step_id)
        if step_num < start_num:
            mark, note = "skip", "before --start-at"
        elif step_id in skip_set:
            mark, note = "skip", "--skip"
        else:
            mark, note = "RUN ", ""
            will_run.append(step_id)
        line = f"[{mark}] {step_id}  {desc}"
        if note:
            line += f"   ({note})"
        guide.narrate(line)

    if not will_run:
        guide.warn("No steps selected to run (check --skip / --start-at).")
        sys.exit(0)

    if guide.confirm(f"Run the full pipeline now ({len(will_run)} steps)?") != "yes":
        guide.warn("Pipeline run cancelled.")
        sys.exit(0)

    # Track per-step status.
    status: dict[str, str] = {sid: "pending" for sid, _, _ in STEPS}

    # Paths that accumulate as steps complete.
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

    # Prefer the trimmed alignment for HMM build / phylogeny if --trim was set.
    final_aln = trimmed_faa if args.trim else aln_faa

    # Every child runs hands-off so it never prompts mid-pipeline.
    CHILD_YES = ["--yes"]

    for step_id, script, desc in STEPS:
        step_num = int(step_id)

        if step_num < start_num:
            status[step_id] = "skipped (before start-at)"
            continue
        if step_id in skip_set:
            status[step_id] = "skipped (--skip)"
            continue

        guide.header(None, f"STEP {step_id}: {desc}")

        # Build step-specific argument list.
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
            # Use trimmed alignment if it exists, else regular alignment.
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
            # Use the final alignment; fall back to seeds_aligned.faa.
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
            # Domtblout from step 03.
            domtbl  = results_dir / "search_results"
            domtbl_files = list(domtbl.glob("*.domtblout")) if domtbl.exists() else []
            if not domtbl_files:
                guide.warn("No domtblout files found; skipping step 13.")
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

        # Append --yes so the child never prompts.
        ok = run_step(guide, step_id, script, step_args + CHILD_YES)
        status[step_id] = "OK" if ok else "FAILED"

        if not ok:
            guide.error(f"Step {step_id} failed. Aborting pipeline.")
            _print_summary(guide, status)
            sys.exit(1)

    _print_summary(guide, status)
    guide.done(f"Pipeline complete. Project: {proj_dir}")
    guide.detail(f"Open {proj_dir / 'reports' / 'report.html'} to review the run.")
    sys.exit(0)


def _print_summary(guide: Guide, status: dict) -> None:
    """Print a summary table of step outcomes."""
    guide.header(None, "Pipeline Summary")
    for step_id, script, desc in STEPS:
        st = status.get(step_id, "pending")
        good = (st == "OK")
        if st == "OK" or "skip" in st.lower():
            guide.result(f"{step_id}  {desc:<38} {st}", good=good or "skip" in st.lower())
        else:
            guide.result(f"{step_id}  {desc:<38} {st}", good=False)


if __name__ == "__main__":
    main()
