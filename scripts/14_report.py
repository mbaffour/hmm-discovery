#!/usr/bin/env python3
"""
14_report.py — Generate HTML report, methods text, and export ZIP.

Builds a reproducibility record and summary report from a completed
project directory. Produces:
  - report.html          — HTML summary with figures and hit statistics
  - methods.txt          — Manuscript-ready methods paragraph
  - export.zip           — All results, figures, and reports archived
  - reproducibility.json — Full audit record (tool versions, commands, DB provenance)

The project directory should contain subdirectories produced by earlier
pipeline steps: results/, figures/, reports/, trees/, logs/.

Example
-------
    python3 scripts/14_report.py --proj-dir /path/to/project --out-dir /path/to/project/reports
    python3 scripts/14_report.py --proj-dir .
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from pipeline.reporter import (
    build_reproducibility_json,
    build_report_context,
    generate_methods_text,
    render_html_report,
    create_export_zip,
)
from pipeline.utils import ensure_tools_on_path


def parse_args():
    p = argparse.ArgumentParser(
        description="Generate HTML report, methods text, and export ZIP for a completed run.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--proj-dir", required=True, type=Path,
                   help="Project root directory containing results/, figures/, reports/, etc.")
    p.add_argument("--out-dir",  type=Path,
                   help="Output directory for report files. Defaults to <proj-dir>/reports/.")
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
    ensure_tools_on_path()

    proj_dir = args.proj_dir.resolve()
    out_dir = (args.out_dir or proj_dir / "reports").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not proj_dir.exists():
        print(f"ERROR: Project directory not found: {proj_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== Step 14: Generate Report ===")
    print(f"  Project dir: {proj_dir}")
    print(f"  Output dir : {out_dir}")

    # Load hits table if available
    hits_df = None
    for hits_candidate in [
        proj_dir / "results" / "hits_main.tsv",
        proj_dir / "results" / "hits_scored.tsv",
        proj_dir / "results" / "hits_combined.tsv",
    ]:
        if hits_candidate.exists():
            try:
                hits_df = pd.read_csv(hits_candidate, sep="\t")
                print(f"  Hits loaded: {len(hits_df)} rows from {hits_candidate.name}")
            except Exception as exc:
                print(f"WARNING: Could not load {hits_candidate}: {exc}", file=sys.stderr)
            break

    # Collect tool versions
    tools = _collect_tool_versions()

    # Build reproducibility record
    print("\n  Building reproducibility record...")
    repro = build_reproducibility_json(
        proj_dir=proj_dir,
        hits_df=hits_df,
        state={},
        tools=tools,
    )
    repro_path = out_dir / "reproducibility.json"
    import json
    repro_path.write_text(json.dumps(repro, indent=2, default=str))
    print(f"  Reproducibility JSON -> {repro_path}")

    # Generate methods text
    print("\n  Generating methods text...")
    methods_text = generate_methods_text(proj_dir=proj_dir, repro=repro)
    methods_out = out_dir / "methods.txt"
    methods_out.write_text(methods_text)
    print(f"  Methods text -> {methods_out}")

    # Build report context
    context = build_report_context(
        proj_dir=proj_dir,
        hits_df=hits_df,
        repro=repro,
        methods_text=methods_text,
        tools=tools,
    )

    # Render HTML report
    print("\n  Rendering HTML report...")
    html_path = render_html_report(proj_dir=proj_dir, context=context)
    # Copy to out_dir / report.html if not already there
    report_out = out_dir / "report.html"
    if html_path and Path(html_path).exists() and Path(html_path) != report_out:
        import shutil
        shutil.copy(html_path, report_out)
        html_path = report_out
    elif not html_path or not Path(html_path).exists():
        # Fallback: write the minimal HTML directly
        report_out.write_text(f"<html><body><h1>HMM Discovery Report</h1>"
                              f"<p>Generated from: {proj_dir}</p>"
                              f"<pre>{methods_text}</pre></body></html>")
        html_path = report_out
    print(f"  HTML report -> {html_path}")

    # Create export ZIP
    print("\n  Creating export ZIP...")
    try:
        zip_path = create_export_zip(proj_dir=proj_dir)
        # Also copy to out_dir
        export_out = out_dir / "export.zip"
        if zip_path and Path(zip_path).exists() and Path(zip_path) != export_out:
            import shutil
            shutil.copy(zip_path, export_out)
            print(f"  Export ZIP -> {export_out}")
        else:
            print(f"  Export ZIP -> {zip_path}")
    except Exception as exc:
        print(f"WARNING: Export ZIP failed: {exc}", file=sys.stderr)

    print(f"\nDone. Reports in: {out_dir}")
    sys.exit(0)


if __name__ == "__main__":
    main()
