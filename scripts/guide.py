#!/usr/bin/env python3
"""
guide.py — An interactive tour of the HMM Discovery command-line pipeline.
==========================================================================

This is the friendly front door to the 14-step script pipeline. Instead of
remembering which script comes next and what flags it takes, you run:

    python3 scripts/guide.py

…and it interviews you about where you are in the workflow, explains each step
in plain English, shows you the EXACT command it would run, and offers to run it
for you. Nothing is hidden — every command it proposes is one you could type
yourself, so the tour doubles as a way to learn the pipeline.

WHAT IT DOES
------------
    * Asks where you are (just starting / have hits / run everything / explain
      one step / batch & HPC help).
    * Walks the relevant steps, each with: what the step does, why it matters,
      the real command, and a "Run it now?" gate.
    * Delegates to the actual step scripts (01_align.py … 14_report.py and
      run_pipeline.py) via subprocess — it never re-implements pipeline logic.

It is built on the same cli_common.Guide engine the step scripts use, so the
look and the auto-detection rules are identical: in a real terminal you get
prompts; piped / redirected / --yes you get a short pointer and a clean exit
(it never hangs waiting for input that will not come).

EXAMPLES
--------
    python3 scripts/guide.py                 # the interactive tour
    python3 scripts/guide.py --no-color      # tour without ANSI colour
"""
import argparse
import subprocess
import sys
from pathlib import Path

# Make both the app package (pipeline.*) and this scripts/ dir (cli_common)
# importable no matter what directory the tour is launched from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cli_common import Guide, add_common_args

# Directory holding the step scripts (this file's own directory).
SCRIPTS = Path(__file__).resolve().parent
PY = sys.executable or "python3"


# ---------------------------------------------------------------------------
# Step catalogue — the single source of truth the tour reads from.
# Each entry: (id, script, title, one-line purpose, example arg string).
# Keep these in sync with the per-script docstrings.
# ---------------------------------------------------------------------------
STEPS = [
    ("01", "01_align.py",        "Align seeds",
     "Line up your seed proteins column-by-column (MAFFT / Clustal Omega).",
     "--seeds seeds.faa"),
    ("02", "02_build_hmm.py",    "Build HMM",
     "Turn the alignment into a profile HMM that models the family.",
     "--aln results/seeds_aligned.faa"),
    ("03", "03_search.py",       "Search databases",
     "Score every protein in a database against the HMM (hmmsearch).",
     "--hmm results/profile.hmm --db phages.faa"),
    ("04", "04_score_hits.py",   "Score hits",
     "Sort raw hits into confidence tiers (high / putative / divergent).",
     "--hits results/hits_combined.tsv"),
    ("05", "05_classify_hits.py","Classify + extract",
     "Build the canonical hits table and pull out the hit sequences.",
     "--hits results/hits_scored.tsv --db phages.faa"),
    ("06", "06_iterate.py",      "Iterate (optional)",
     "Grow the seed set with strong new hits and rebuild — jackhmmer-style.",
     "--seeds seeds.faa --hits-faa results/hits_proteins.faa --hmm results/profile.hmm --db phages.faa"),
    ("07", "07_synteny.py",      "Synteny",
     "Fetch flanking genes and draw gene-neighbourhood maps (+ clinker).",
     "--hits results/hits_main.tsv --email you@uni.edu"),
    ("08", "08_taxonomy.py",     "Taxonomy",
     "Infer host / organism / taxonomy from each hit's sequence ID.",
     "--hits results/hits_main.tsv"),
    ("09", "09_phylogeny.py",    "Phylogeny",
     "Build a maximum-likelihood tree with IQ-TREE.",
     "--aln results/seeds_aligned.faa"),
    ("10", "10_matrix.py",       "Presence/absence",
     "Build a genome × gene matrix and a clustered heatmap.",
     "--hits results/hits_main.tsv"),
    ("11", "11_cluster.py",      "Cluster",
     "Group hit sequences with CD-HIT or MMseqs2; pick representatives.",
     "--faa results/hits_proteins.faa"),
    ("12", "12_motifs.py",       "Motifs",
     "Discover conserved motifs with MEME and scan with FIMO.",
     "--faa results/hits_proteins.faa"),
    ("13", "13_annotate.py",     "Annotate",
     "Add domain architecture and transmembrane / signal-peptide topology.",
     "--faa results/hits_proteins.faa --hmm results/profile.hmm --domtblout pfam.domtblout"),
    ("14", "14_report.py",       "Report",
     "Compile the HTML report, Methods text, and export ZIP.",
     "--proj-dir my_project/"),
]
STEPS_BY_ID = {s[0]: s for s in STEPS}


def _run_step(guide: Guide, script: str, example_args: str) -> None:
    """Show a step's command and, if the user agrees, run it as a subprocess.

    The command we display is exactly what we run (minus the example argument
    values, which the user should replace with their own paths). On "yes" we
    launch the *real* step script so the tour is doing genuine work, not a demo.
    """
    cmd_display = f"{PY} {SCRIPTS / script} {example_args}".strip()
    guide.command(cmd_display,
                  "Replace the example paths with your own files.")
    if guide.confirm(f"Run {script} now?", default_yes=False) != "yes":
        guide.detail("Skipped — copy the command above to run it yourself later.")
        return
    # Launch the real step. It will itself be interactive (it inherits this
    # terminal), so the user can fill in any details there.
    guide.narrate(f"Launching {script} …")
    proc = subprocess.run([PY, str(SCRIPTS / script)])
    if proc.returncode == 0:
        guide.result(f"{script} finished.")
    else:
        guide.warn(f"{script} exited with code {proc.returncode}.")


def _walk(guide: Guide, ids: list[str], heading: str) -> None:
    """Walk a sequence of steps, teaching and offering to run each one."""
    guide.header(None, heading)
    for sid in ids:
        sid_, script, title, purpose, example = STEPS_BY_ID[sid]
        guide.header(None, f"Step {sid_}: {title}")
        guide.explain(purpose)
        _run_step(guide, script, example)


def _explain_one(guide: Guide) -> None:
    """Path 4 — let the user pick a single step and read about it."""
    choices = [(sid, f"{sid}  {title} — {purpose}")
               for (sid, _s, title, purpose, _e) in STEPS]
    pick = guide.ask_choice("Which step would you like explained?",
                            choices, default_index=0)
    sid, script, title, purpose, example = STEPS_BY_ID[pick]
    guide.header(None, f"Step {sid}: {title}")
    guide.explain(purpose)
    guide.narrate("Example command:")
    guide.command(f"{PY} scripts/{script} {example}".strip())
    guide.detail(f"Full flags & I/O: see scripts/README.md (the '{script}' section).")


def _batch_help(guide: Guide) -> None:
    """Path 5 — explain the hands-off / HPC / Methods-extraction workflow."""
    guide.header(None, "Batch, HPC & Methods extraction")
    guide.explain(
        "Every script is interactive in a terminal but silent and non-blocking\n"
        "when piped, redirected, or given --yes. That makes them safe for HPC\n"
        "job scripts and cron. The master runner passes --yes to every child."
    )
    guide.narrate("Run the whole pipeline hands-off:")
    guide.command(
        f"{PY} scripts/run_pipeline.py --seeds seeds.faa --db phages.faa "
        f"--proj-dir my_project/ --email you@uni.edu --cpu 8 --yes")
    guide.narrate("Dry-run to capture commands for a Methods section:")
    guide.command(f"{PY} scripts/03_search.py --hmm profile.hmm --db db.faa --explain-only")
    guide.detail("Or grep the logs of a real run:  grep '\\[CMD\\]' run.log")
    guide.narrate("Resume partway / skip steps:")
    guide.command(f"{PY} scripts/run_pipeline.py ... --start-at 07 --skip 09 11 --yes")
    guide.detail("Full reference: scripts/README.md  ·  docs/CLI_INTERACTIVE_GUIDE.md")


def main():
    p = argparse.ArgumentParser(
        description="Interactive tour of the HMM Discovery CLI pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_common_args(p)   # --yes / --interactive / --no-color / --explain-only
    args = p.parse_args()
    guide = Guide.from_args(args)

    guide.header(None, "HMM Discovery — Interactive Pipeline Tour",
                 "I'll explain each step, show the command, and offer to run it.")

    # ── Non-interactive safety ───────────────────────────────────────────
    # If there is no human at a terminal, we cannot run a menu. Point the
    # reader at the written docs and exit cleanly — never hang.
    if not guide.interactive:
        guide.narrate("This tour needs an interactive terminal.")
        guide.detail("Reference:        scripts/README.md")
        guide.detail("Walkthrough:      docs/CLI_INTERACTIVE_GUIDE.md")
        guide.detail("Interactive HTML: docs/cli_interactive_guide.html "
                     "(open in a browser)")
        guide.detail("Run a step directly, e.g.:  python3 scripts/01_align.py --help")
        sys.exit(0)

    # ── Top menu ─────────────────────────────────────────────────────────
    choice = guide.ask_choice(
        "Where are you in the workflow?",
        [
            ("start",   "Just starting — I have seed sequences"),
            ("analyze", "I already have hits — I want downstream analysis"),
            ("all",     "Run everything end-to-end (the master pipeline)"),
            ("explain", "Just explain a single step to me"),
            ("batch",   "Show me the batch / HPC / Methods workflow"),
        ],
        default_index=0,
    )

    if choice == "start":
        # Core discovery path: align → build → search → score → classify → report.
        _walk(guide, ["01", "02", "03", "04", "05", "14"],
              "Discovery path — from seeds to a first hit table")
        guide.detail("Want neighbourhoods, trees, clusters? Re-run me and pick "
                     "'downstream analysis'.")

    elif choice == "analyze":
        # Downstream analysis on an existing hits table.
        _walk(guide, ["07", "08", "09", "10", "11", "12", "13", "14"],
              "Analysis path — context, taxonomy, trees, clusters, motifs")

    elif choice == "all":
        guide.header(None, "Run everything end-to-end")
        guide.explain(
            "The master runner wires every step's output into the next, from raw\n"
            "seeds to a finished HTML report. It will interview you for the seed\n"
            "file, database(s), and project directory, show the plan, then run."
        )
        guide.command(f"{PY} scripts/run_pipeline.py")
        if guide.confirm("Launch the full pipeline runner now?", default_yes=False) == "yes":
            subprocess.run([PY, str(SCRIPTS / "run_pipeline.py")])

    elif choice == "explain":
        _explain_one(guide)

    elif choice == "batch":
        _batch_help(guide)

    guide.done("End of tour.")
    guide.detail("Reference: scripts/README.md  ·  "
                 "Walkthrough: docs/CLI_INTERACTIVE_GUIDE.md")
    sys.exit(0)


if __name__ == "__main__":
    main()
