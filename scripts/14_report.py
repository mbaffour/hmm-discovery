#!/usr/bin/env python3
"""
14_report.py — Compile the HTML report, methods text, and export ZIP.
=====================================================================

WHAT THIS STEP DOES (the science of reproducibility)
----------------------------------------------------
A discovery is only useful if someone else can reproduce it. This final step
walks the whole project directory and pulls everything together into a single,
shareable record:

    * report.html          — a readable summary: hit counts, tier breakdown,
      figures (heatmap, tree, synteny), and key tables.
    * methods.txt          — a manuscript-ready Methods paragraph, with the exact
      tools, versions, and parameters that were used.
    * reproducibility.json — a full audit trail: tool versions, commands,
      database provenance, and per-step state.
    * export.zip           — every result, figure, and report archived for
      hand-off or supplementary material.

It reads from the subdirectories earlier steps wrote (results/, figures/,
reports/, trees/, logs/), so the more steps you ran, the richer the report.

WHAT THE KEY PARAMETERS MEAN
----------------------------
    --proj-dir  The project root containing results/, figures/, etc.
    --out-dir   Where the report files go (defaults to <proj-dir>/reports/).

OUTPUTS
-------
    <out-dir>/report.html
    <out-dir>/methods.txt
    <out-dir>/reproducibility.json
    <out-dir>/export.zip

INTERACTIVITY
-------------
Run it in a terminal with no/partial arguments and it becomes a guided wizard,
then narrates each artefact as it is produced. Pipe it or pass --yes for
hands-off operation (safe for HPC / run_pipeline.py). See cli_common.py.

EXAMPLES
--------
    # Guided — the script will interview you:
    python3 scripts/14_report.py

    # Explicit / hands-off:
    python3 scripts/14_report.py --proj-dir my_project/ --yes
"""
import argparse
import sys
from pathlib import Path

# Make the app package importable no matter what directory we are run from,
# and make cli_common (which lives beside this script) importable too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from pipeline.reporter import (
    build_reproducibility_json,
    build_report_context,
    generate_methods_text,
    render_html_report,
    create_export_zip,
)
from pipeline.utils import ensure_tools_on_path
from cli_common import Guide, add_common_args


def parse_args():
    p = argparse.ArgumentParser(
        description="Generate HTML report, methods text, and export ZIP for a completed run.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Not required=True: a human in a terminal can supply this via the wizard.
    p.add_argument("--proj-dir", type=Path,
                   help="Project root directory containing results/, figures/, reports/, etc.")
    p.add_argument("--out-dir",  type=Path,
                   help="Output directory for report files. Defaults to <proj-dir>/reports/.")
    add_common_args(p)          # --yes / --interactive / --no-color / --explain-only
    return p.parse_args()


def _collect_tool_versions() -> dict:
    """Return a dict of tool_name -> version string for common tools."""
    import subprocess
    versions = {}
    tool_cmds = {
        "hmmbuild":  ["hmmbuild", "--version"],
        "mafft":     ["mafft", "--version"],
        "iqtree2":   ["iqtree2", "--version"],
        "trimal":    ["trimal", "--version"],
        "clustalo":  ["clustalo", "--version"],
        "meme":      ["meme", "--version"],
        "cd-hit":    ["cd-hit", "-h"],
    }
    for tool, cmd in tool_cmds.items():
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            out = (proc.stdout + proc.stderr).strip().splitlines()
            versions[tool] = out[0] if out else "installed"
        except Exception:
            pass
    return versions


def main():
    args = parse_args()
    guide = Guide.from_args(args)
    ensure_tools_on_path()

    guide.header(14, "Generate Report",
                 "Compile the HTML report, methods text, audit JSON, and export ZIP.")

    # ── GUIDED WIZARD ────────────────────────────────────────────────────
    if guide.interactive and args.proj_dir is None:
        guide.wizard_intro("Let's compile the final report.")
        args.proj_dir = guide.ask_path(
            "Path to your project directory?",
            default=".",
            help_text="The root folder containing results/, figures/, reports/, etc.",
        )

    # ── Validate (works in both modes) ───────────────────────────────────
    if args.proj_dir is None:
        guide.error("No --proj-dir given. Provide one, or run in a terminal for the wizard.")
        sys.exit(2)

    proj_dir = args.proj_dir.resolve()
    out_dir = (args.out_dir or proj_dir / "reports").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not proj_dir.exists():
        guide.error(f"Project directory not found: {proj_dir}")
        sys.exit(1)

    guide.narrate(f"Project dir: {proj_dir}")
    guide.narrate(f"Output dir : {out_dir}")

    # ── EXPLAIN-AND-CONFIRM ──────────────────────────────────────────────
    guide.command(f"build report from {proj_dir} → report.html, methods.txt, "
                  "reproducibility.json, export.zip",
                  "Gather every result, figure, and tool version into a shareable record.")
    if guide.confirm("Generate the report now?") != "yes":
        guide.warn("Report generation skipped — nothing written.")
        sys.exit(0)

    # Load hits table if available (try the richest first).
    hits_df = None
    for hits_candidate in [
        proj_dir / "results" / "hits_main.tsv",
        proj_dir / "results" / "hits_scored.tsv",
        proj_dir / "results" / "hits_combined.tsv",
    ]:
        if hits_candidate.exists():
            try:
                hits_df = pd.read_csv(hits_candidate, sep="\t")
                guide.detail(f"Hits loaded: {len(hits_df)} rows from {hits_candidate.name}.")
            except Exception as exc:
                guide.warn(f"Could not load {hits_candidate}: {exc}")
            break
    if hits_df is None:
        guide.detail("No hits table found — report will be generated without hit stats.")

    # Collect tool versions for the audit record.
    tools = _collect_tool_versions()

    # ── Reproducibility record ───────────────────────────────────────────
    guide.narrate("Building reproducibility record …")
    repro = build_reproducibility_json(
        proj_dir=proj_dir,
        hits_df=hits_df,
        state={},
        tools=tools,
    )
    repro_path = out_dir / "reproducibility.json"
    import json
    repro_path.write_text(json.dumps(repro, indent=2, default=str))
    guide.result(f"Reproducibility JSON → {repro_path}")

    # ── Methods text ─────────────────────────────────────────────────────
    guide.narrate("Generating methods text …")
    methods_text = generate_methods_text(proj_dir=proj_dir, repro=repro)
    methods_out = out_dir / "methods.txt"
    methods_out.write_text(methods_text)
    guide.result(f"Methods text → {methods_out}")

    # Build report context.
    context = build_report_context(
        proj_dir=proj_dir,
        hits_df=hits_df,
        repro=repro,
        methods_text=methods_text,
        tools=tools,
    )

    # ── HTML report ──────────────────────────────────────────────────────
    guide.narrate("Rendering HTML report …")
    html_path = render_html_report(proj_dir=proj_dir, context=context)
    report_out = out_dir / "report.html"
    if html_path and Path(html_path).exists() and Path(html_path) != report_out:
        import shutil
        shutil.copy(html_path, report_out)
        html_path = report_out
    elif not html_path or not Path(html_path).exists():
        # Fallback: write a minimal HTML directly so there is always a report.
        report_out.write_text(f"<html><body><h1>HMM Discovery Report</h1>"
                              f"<p>Generated from: {proj_dir}</p>"
                              f"<pre>{methods_text}</pre></body></html>")
        html_path = report_out
    guide.result(f"HTML report → {html_path}")

    # ── Export ZIP ───────────────────────────────────────────────────────
    guide.narrate("Creating export ZIP …")
    try:
        zip_path = create_export_zip(proj_dir=proj_dir)
        export_out = out_dir / "export.zip"
        if zip_path and Path(zip_path).exists() and Path(zip_path) != export_out:
            import shutil
            shutil.copy(zip_path, export_out)
            guide.result(f"Export ZIP → {export_out}")
        else:
            guide.result(f"Export ZIP → {zip_path}")
    except Exception as exc:
        guide.warn(f"Export ZIP failed: {exc}")

    guide.done(f"Report complete. Reports in: {out_dir}")
    guide.detail(f"Open {out_dir / 'report.html'} in a browser to review the run.")
    sys.exit(0)


if __name__ == "__main__":
    main()
