"""
ui/step_09_export.py — Export Panel (Step 9).

Download all outputs, view reproducibility report, browse audit trail,
and preview the auto-generated HTML summary report.
"""
from __future__ import annotations

import io
import json
import shutil
import zipfile
from pathlib import Path

from shiny import ui

from .components import click_go_strip, guidance_callout, learning_card, step_guidance, section_header, stat_card


# ---------------------------------------------------------------------------
# Panel UI
# ---------------------------------------------------------------------------

def panel_ui() -> ui.TagChild:
    return ui.nav_panel(
        "9. Export",
        ui.tags.div(
            step_guidance(
                "Download all results in publication-ready formats or as a single ZIP archive for reproducibility.",
                [
                "TSV tables (hits, synteny, taxonomy, clusters)",
                "Protein FASTA sequences",
                "Figures in PNG (300 dpi), SVG (vector), and PDF",
                "Methods paragraph for your paper",
                "Full reproducibility JSON with tool versions",
                ],
                "The ZIP includes everything needed to reproduce the analysis from scratch.",
            ),
            ui.tags.p(
                "Download individual result files or the full export ZIP. "
                "Review reproducibility metadata and the auto-generated Methods paragraph.",
                class_="text-muted mb-3",
            ),
            click_go_strip([
                ("Summarize", "Create RUN_SUMMARY files"),
                ("Clean", "Preview removable cache safely"),
                ("Choose folder", "Pick where the final ZIP goes"),
                ("Export", "Package reviewer-ready evidence"),
            ]),
            ui.layout_columns(
                learning_card(
                    "Keep for publication",
                    [
                        "hits_main.tsv, hits_best_per_genome.tsv, synteny tables, and placement report.",
                        "METHODS_TEXT.txt, reproducibility.json, RUN_SUMMARY.md.",
                        "Figures and final export ZIP stored outside the Git repository when data are private.",
                    ],
                    tone="success",
                ),
                learning_card(
                    "Safe to clear after export",
                    [
                        "Runtime chunk folders, translated temporary ORFs, domtblout scratch files, and stream caches.",
                        "Downloaded database caches when you can re-download or re-stream them later.",
                        "Never clear while a run is active; the app blocks this automatically.",
                    ],
                    tone="warning",
                ),
                col_widths=[6, 6],
                class_="mb-3",
            ),

            # ---- Card: Run Summary ------------------------------------------
            ui.card(
                ui.card_header(ui.tags.strong("Run Summary")),
                ui.tags.p(
                    "Generate a compact factual summary of what was run, which databases were searched, "
                    "how many hits were found, confidence tiers, synteny status, and the key output files.",
                    class_="text-muted small mb-2",
                ),
                ui.tags.div(
                    ui.input_action_button(
                        "btn_generate_run_summary",
                        "Generate Run Summary",
                        class_="btn btn-outline-info btn-sm me-2",
                    ),
                    ui.download_button("dl_run_summary_md", "RUN_SUMMARY.md", class_="btn btn-outline-info btn-sm me-1"),
                    ui.download_button("dl_run_summary_json", "run_summary.json", class_="btn btn-outline-info btn-sm"),
                    class_="mb-2",
                ),
                ui.output_ui("run_summary_status"),
                ui.output_ui("run_summary_cards"),
                ui.output_ui("run_summary_preview"),
                class_="mb-3",
            ),

            # ---- Card: Storage Cleanup --------------------------------------
            ui.card(
                ui.card_header(ui.tags.strong("Storage Cleanup")),
                ui.tags.p(
                    "Clear bulky regenerable intermediates after analysis while keeping final tables, reports, figures, logs, HMMs, alignments, and inputs.",
                    class_="text-muted small mb-2",
                ),
                guidance_callout(
                    "Cleanup rule",
                    "Preview first. Cleanup removes files that can be regenerated, but keeps the scientific record of the run. If a benchmark PID is alive, cleanup is blocked to avoid corrupting active chunk processing.",
                    "warning",
                ),
                ui.tags.div(
                    ui.input_switch(
                        "cleanup_include_cache",
                        "Also remove downloaded database cache files",
                        value=True,
                    ),
                    ui.tags.small(
                        "Cleanup is blocked while a benchmark is running in this project folder.",
                        class_="text-muted d-block mb-2",
                    ),
                ),
                ui.tags.div(
                    ui.input_action_button(
                        "btn_preview_cleanup",
                        "Preview Cleanup",
                        class_="btn btn-outline-warning btn-sm me-2",
                    ),
                    ui.input_action_button(
                        "btn_run_cleanup",
                        "Clear Bulky Intermediates",
                        class_="btn btn-warning btn-sm",
                    ),
                    class_="mb-2",
                ),
                ui.output_ui("cleanup_status"),
                ui.output_ui("cleanup_preview"),
                class_="mb-3",
            ),

            # ---- Card: Deployment Readiness ---------------------------------
            ui.card(
                ui.card_header(ui.tags.strong("Deployment Readiness")),
                ui.tags.p(
                    "Before sharing a run or publishing a release, confirm the app can explain exactly what was searched, how it was searched, and what files are safe to retain.",
                    class_="text-muted small mb-2",
                ),
                ui.layout_columns(
                    learning_card(
                        "Research run",
                        [
                            "Self-search recovered the seed set before database scanning.",
                            "Each selected database is marked complete, failed, skipped, or partial with a reason.",
                            "Nucleotide databases record whether six-frame discovery or Prodigal baseline mode was used.",
                        ],
                        tone="info",
                    ),
                    learning_card(
                        "Database provenance",
                        [
                            "Run Summary and reproducibility JSON include source URLs, access dates, source sizes, and SHA256 checksums when available.",
                            "Extreme databases should be processed sequentially with disk guards and cache cleanup.",
                            "Do not mix private outputs into the clean Git repository.",
                        ],
                        tone="success",
                    ),
                    learning_card(
                        "Public release",
                        [
                            "Run the smoke test from a clean folder after every meaningful code change.",
                            "Confirm export ZIP, METHODS_TEXT, reproducibility JSON, and RUN_SUMMARY files are generated.",
                            "Review docs/DEPLOYMENT_CHECKLIST.md before uploading to GitHub.",
                        ],
                        tone="warning",
                    ),
                    col_widths=[4, 4, 4],
                ),
                class_="mb-3",
            ),

            # ---- Card: Download Results -------------------------------------
            ui.card(
                ui.card_header(ui.tags.strong("Download Results")),

                # Tables
                section_header("Tables"),
                ui.tags.div(
                    ui.download_button("dl_hits_main_tsv", "hits_main.tsv", class_="btn btn-outline-primary btn-sm me-1 mb-1"),
                    ui.download_button("dl_hits_best_tsv", "hits_best_per_genome.tsv", class_="btn btn-outline-primary btn-sm me-1 mb-1"),
                    ui.download_button("dl_synteny_tsv", "synteny_table.tsv", class_="btn btn-outline-primary btn-sm me-1 mb-1"),
                    ui.download_button("dl_pam_tsv", "presence_absence_matrix.tsv", class_="btn btn-outline-primary btn-sm me-1 mb-1"),
                    ui.download_button("dl_taxonomy_tsv", "taxonomy_table.tsv", class_="btn btn-outline-primary btn-sm me-1 mb-1"),
                    class_="mb-2",
                ),

                # Sequences
                section_header("Sequences"),
                ui.tags.div(
                    ui.download_button("dl_hits_proteins_faa", "hits_proteins.faa", class_="btn btn-outline-success btn-sm me-1 mb-1"),
                    ui.download_button("dl_hits_aligned_faa", "hits_aligned.faa", class_="btn btn-outline-success btn-sm me-1 mb-1"),
                    ui.download_button("dl_cluster_reps_faa", "cluster_reps.faa", class_="btn btn-outline-success btn-sm me-1 mb-1"),
                    class_="mb-2",
                ),

                # Figures
                section_header("Figures", "PNG (300 dpi) · SVG (vector) · PDF (print)"),
                ui.tags.div(
                    # Synteny map
                    ui.tags.small("Synteny map:", class_="text-muted d-block mb-1"),
                    ui.download_button("dl_synteny_png_exp", "🖼 PNG", class_="btn btn-outline-secondary btn-sm me-1 mb-1"),
                    ui.download_button("dl_synteny_svg_exp", "📐 SVG", class_="btn btn-outline-secondary btn-sm me-1 mb-1"),
                    ui.download_button("dl_synteny_pdf_exp", "📄 PDF", class_="btn btn-outline-secondary btn-sm me-1 mb-2"),
                    # Tree
                    ui.tags.small("Phylogenetic tree:", class_="text-muted d-block mb-1"),
                    ui.download_button("dl_tree_png_exp", "🖼 PNG", class_="btn btn-outline-secondary btn-sm me-1 mb-1"),
                    ui.download_button("dl_tree_svg_exp", "📐 SVG", class_="btn btn-outline-secondary btn-sm me-1 mb-2"),
                    # Heatmap
                    ui.tags.small("Presence/absence heatmap:", class_="text-muted d-block mb-1"),
                    ui.download_button("dl_heatmap_png", "🖼 PNG", class_="btn btn-outline-secondary btn-sm me-1 mb-1"),
                    ui.download_button("dl_heatmap_svg_exp", "📐 SVG", class_="btn btn-outline-secondary btn-sm me-1 mb-2"),
                    # HMM logo
                    ui.tags.small("HMM logo:", class_="text-muted d-block mb-1"),
                    ui.download_button("dl_hmm_logo_png", "🖼 PNG", class_="btn btn-outline-secondary btn-sm me-1 mb-1"),
                    ui.download_button("dl_hmm_logo_svg_exp", "📐 SVG", class_="btn btn-outline-secondary btn-sm me-1 mb-2"),
                    # Taxonomy Sankey
                    ui.tags.small("Taxonomy Sankey:", class_="text-muted d-block mb-1"),
                    ui.download_button("dl_taxonomy_sankey_svg", "📐 SVG", class_="btn btn-outline-secondary btn-sm me-1 mb-1"),
                    ui.download_button("dl_taxonomy_sankey_png_exp", "🖼 PNG", class_="btn btn-outline-secondary btn-sm me-1 mb-1"),
                    class_="mb-2",
                ),

                # Reports
                section_header("Reports"),
                ui.tags.div(
                    ui.download_button("dl_summary_report_html", "summary_report.html", class_="btn btn-outline-info btn-sm me-1 mb-1"),
                    ui.download_button("dl_repro_json", "reproducibility.json", class_="btn btn-outline-info btn-sm me-1 mb-1"),
                    ui.download_button("dl_methods_txt", "METHODS_TEXT.txt", class_="btn btn-outline-info btn-sm me-1 mb-1"),
                    class_="mb-2",
                ),

                ui.tags.hr(),
                ui.layout_columns(
                    ui.input_text(
                        "export_dest_dir",
                        "Save export ZIP to folder",
                        value=str(Path.home() / "Documents" / "HMM-Discovery-Exports"),
                        placeholder="/path/to/save/final/export",
                    ),
                    ui.tags.div(
                        ui.input_action_button(
                            "btn_save_zip_to_folder",
                            "Save ZIP to Folder",
                            class_="btn btn-outline-success mt-4",
                        ),
                        ui.output_ui("zip_save_status"),
                    ),
                    col_widths=[8, 4],
                ),
                ui.tags.small(
                    "Choose a folder outside the app repository for sharable exports. "
                    "Do not save unpublished FASTA, logs, or benchmark outputs into a public Git folder.",
                    class_="text-muted d-block mb-2",
                ),
                ui.tags.div(
                    ui.input_action_button(
                        "btn_export_zip",
                        "📦 Export All (ZIP)",
                        class_="btn btn-primary",
                    ),
                    ui.output_ui("zip_download_ui"),
                    class_="d-flex align-items-center gap-3 mt-2",
                ),

                class_="mb-3",
            ),

            # ---- Card: Reproducibility --------------------------------------
            ui.card(
                ui.card_header(ui.tags.strong("Reproducibility")),
                section_header("Tool Versions & Parameters"),
                ui.output_ui("repro_summary"),
                section_header("Methods Paragraph"),
                ui.output_ui("methods_text_display"),
                section_header("Audit Trail"),
                ui.output_data_frame("audit_trail_table"),
                class_="mb-3",
            ),

            # ---- Card: HTML Report Preview ----------------------------------
            ui.card(
                ui.card_header(ui.tags.strong("HTML Report Preview")),
                ui.output_ui("report_preview"),
                class_="mb-3",
            ),

            class_="container-fluid px-0",
        ),
    )


# ---------------------------------------------------------------------------
# Server outputs
# ---------------------------------------------------------------------------

def register_outputs(input, output, render, reactive, session, **kwargs):
    proj_dir_rv = kwargs.get("proj_dir_rv", None)
    reporter = kwargs.get("reporter", None)

    def _proj_dir() -> Path | None:
        if proj_dir_rv is not None:
            v = proj_dir_rv.get()
            return Path(v) if v else None
        return None

    def _results_dir() -> Path | None:
        pd_ = _proj_dir()
        if pd_ is None:
            return None
        for cand in [pd_ / "results", pd_ / "output", pd_]:
            if cand.is_dir():
                return cand
        return pd_

    def _reports_dir() -> Path | None:
        pd_ = _proj_dir()
        if pd_ is None:
            return None
        rd = pd_ / "reports"
        if rd.is_dir():
            return rd
        return _results_dir()

    def _logs_dir() -> Path | None:
        pd_ = _proj_dir()
        if pd_ is None:
            return None
        ld = pd_ / "logs"
        return ld if ld.is_dir() else pd_

    def _serve_file(rel_dirs: list[str], filename: str):
        """Locate a file in one of several possible directories and yield its bytes."""
        pd_ = _proj_dir()
        if pd_ is None:
            return
        for d in rel_dirs:
            f = pd_ / d / filename
            if f.exists():
                yield f.read_bytes()
                return
        # Try directly in proj_dir
        f = pd_ / filename
        if f.exists():
            yield f.read_bytes()

    _run_summary_message: reactive.Value[str] = reactive.value("")
    _run_summary_data: reactive.Value[dict | None] = reactive.value(None)
    _run_summary_md: reactive.Value[str] = reactive.value("")
    _cleanup_message: reactive.Value[str] = reactive.value("")
    _cleanup_data: reactive.Value[dict | None] = reactive.value(None)

    def _load_or_generate_run_summary(write: bool = False) -> dict:
        pd_ = _proj_dir()
        if pd_ is None:
            return {"summary": None, "markdown": "", "error": "Load a project before generating a summary."}
        try:
            from core.run_summary import render_summary_markdown, summarize_project, write_run_summary

            if write:
                result = write_run_summary(pd_)
                return {
                    "summary": result["summary"],
                    "markdown": result["markdown"],
                    "markdown_path": result["markdown_path"],
                    "json_path": result["json_path"],
                }
            summary = summarize_project(pd_)
            return {"summary": summary, "markdown": render_summary_markdown(summary)}
        except Exception as exc:
            return {"summary": None, "markdown": "", "error": str(exc)}

    @reactive.effect
    @reactive.event(input.btn_generate_run_summary)
    async def _on_generate_run_summary():
        result = _load_or_generate_run_summary(write=True)
        if result.get("error"):
            _run_summary_message.set(f"Could not generate summary: {result['error']}")
            _run_summary_data.set(None)
            _run_summary_md.set("")
            return
        _run_summary_data.set(result.get("summary"))
        _run_summary_md.set(result.get("markdown", ""))
        _run_summary_message.set(
            f"Saved: {result.get('markdown_path')} and {result.get('json_path')}"
        )

    @output
    @render.ui
    def run_summary_status():
        msg = _run_summary_message.get()
        if not msg:
            return ui.tags.p(
                "Summary files are generated on demand from the current project outputs.",
                class_="text-muted small",
            )
        cls = "text-success" if msg.startswith("Saved:") else "text-warning"
        return ui.tags.p(msg, class_=f"{cls} small")

    @output
    @render.ui
    def run_summary_cards():
        data = _run_summary_data.get()
        if data is None:
            result = _load_or_generate_run_summary(write=False)
            data = result.get("summary")
        if not data:
            return ui.tags.span("")
        hs = data.get("hit_summary", {}) or {}
        db_rows = data.get("database_summary", []) or []
        db_complete = sum(1 for row in db_rows if row.get("status") == "complete")
        db_running = sum(1 for row in db_rows if row.get("status") == "running")
        nt_mode = (data.get("active_command", {}) or {}).get("nt_orf_mode", "")
        return ui.layout_columns(
            stat_card("Total hits", hs.get("total_hits", 0), "primary"),
            stat_card("High confidence", (hs.get("confidence_tiers", {}) or {}).get("high_confidence", 0), "success"),
            stat_card("Databases complete", f"{db_complete}/{len(db_rows)}", "info"),
            stat_card("Running", db_running, "warning" if db_running else "secondary"),
            stat_card("NT ORF mode", nt_mode or "project", "secondary"),
            col_widths=[2, 2, 3, 2, 3],
        )

    @output
    @render.ui
    def run_summary_preview():
        md = _run_summary_md.get()
        if not md:
            result = _load_or_generate_run_summary(write=False)
            md = result.get("markdown", "")
        if not md:
            return ui.tags.span("")
        preview = "\n".join(md.splitlines()[:80])
        return ui.tags.pre(
            preview,
            class_="small bg-dark text-light border rounded p-3",
            style="max-height:360px; overflow:auto; white-space:pre-wrap;",
        )

    @render.download(filename="RUN_SUMMARY.md")
    def dl_run_summary_md():
        pd_ = _proj_dir()
        if pd_ is None:
            yield b""
            return
        from core.run_summary import write_run_summary

        result = write_run_summary(pd_)
        yield Path(result["markdown_path"]).read_bytes()

    @render.download(filename="run_summary.json")
    def dl_run_summary_json():
        pd_ = _proj_dir()
        if pd_ is None:
            yield b"{}"
            return
        from core.run_summary import write_run_summary

        result = write_run_summary(pd_)
        yield Path(result["json_path"]).read_bytes()

    def _cleanup_preview_or_run(dry_run: bool) -> dict:
        pd_ = _proj_dir()
        if pd_ is None:
            return {"status": "no_project", "message": "Load a project before cleanup.", "items": [], "total_bytes": 0}
        try:
            from core.storage_cleanup import cleanup_project

            return cleanup_project(
                pd_,
                include_download_cache=bool(input.cleanup_include_cache()),
                dry_run=dry_run,
            )
        except Exception as exc:
            return {"status": "error", "message": str(exc), "items": [], "total_bytes": 0}

    @reactive.effect
    @reactive.event(input.btn_preview_cleanup)
    async def _on_preview_cleanup():
        result = _cleanup_preview_or_run(dry_run=True)
        _cleanup_data.set(result)
        if result.get("status") == "blocked_running":
            _cleanup_message.set(result.get("message", "Cleanup is blocked while this project is running."))
        else:
            from core.storage_cleanup import format_bytes

            _cleanup_message.set(f"Preview: {format_bytes(result.get('total_bytes', 0))} can be cleared.")

    @reactive.effect
    @reactive.event(input.btn_run_cleanup)
    async def _on_run_cleanup():
        preview = _cleanup_data.get()
        if not preview or preview.get("status") == "no_project":
            _cleanup_message.set("Click 'Preview Cleanup' first to see what will be removed.")
            return
        result = _cleanup_preview_or_run(dry_run=False)
        _cleanup_data.set(result)
        if result.get("status") == "blocked_running":
            _cleanup_message.set(result.get("message", "Cleanup is blocked while this project is running."))
        elif result.get("status") == "cleaned":
            from core.storage_cleanup import format_bytes

            _cleanup_message.set(f"Cleaned: {format_bytes(result.get('freed_bytes', 0))} freed.")
        else:
            _cleanup_message.set(result.get("message", f"Cleanup status: {result.get('status', 'unknown')}"))

    @output
    @render.ui
    def cleanup_status():
        msg = _cleanup_message.get()
        if not msg:
            return ui.tags.p(
                "Preview first to see removable intermediate files and caches.",
                class_="text-muted small",
            )
        cls = "text-success" if msg.startswith("Cleaned:") else "text-warning" if "blocked" in msg.lower() else "text-info"
        return ui.tags.p(msg, class_=f"{cls} small")

    @output
    @render.ui
    def cleanup_preview():
        data = _cleanup_data.get()
        if not data:
            return ui.tags.span("")
        from core.storage_cleanup import format_bytes

        items = data.get("items", [])[:20]
        rows = [
            ui.tags.tr(
                ui.tags.td(ui.tags.code(item.get("path", ""))),
                ui.tags.td(format_bytes(item.get("bytes", 0))),
                ui.tags.td(item.get("kind", "")),
            )
            for item in items
        ]
        if not rows:
            rows = [ui.tags.tr(ui.tags.td("No bulky cleanup candidates found.", colspan="3"))]
        return ui.tags.div(
            ui.layout_columns(
                stat_card("Can clear", format_bytes(data.get("total_bytes", 0)), "warning"),
                stat_card("Items", len(data.get("items", [])), "secondary"),
                stat_card("Benchmark", "running" if data.get("running") else "not running", "danger" if data.get("running") else "success"),
                col_widths=[4, 4, 4],
            ),
            ui.tags.table(
                ui.tags.thead(ui.tags.tr(ui.tags.th("Path"), ui.tags.th("Size"), ui.tags.th("Type"))),
                ui.tags.tbody(*rows),
                class_="table table-sm table-striped mt-2",
            ),
        )

    # ==========================================================================
    # TABLE DOWNLOADS
    # ==========================================================================

    @render.download(filename="hits_main.tsv")
    def dl_hits_main_tsv():
        yield from _serve_file(["results", "output", ""], "hits_main.tsv")

    @render.download(filename="hits_best_per_genome.tsv")
    def dl_hits_best_tsv():
        yield from _serve_file(["results", "output", ""], "hits_best_per_genome.tsv")

    @render.download(filename="synteny_table.tsv")
    def dl_synteny_tsv():
        yield from _serve_file(["results", "output", ""], "synteny_table.tsv")

    @render.download(filename="presence_absence_matrix.tsv")
    def dl_pam_tsv():
        yield from _serve_file(["results", "output", ""], "presence_absence_matrix.tsv")

    @render.download(filename="taxonomy_table.tsv")
    def dl_taxonomy_tsv():
        yield from _serve_file(["results", "output", ""], "taxonomy_table.tsv")

    # ==========================================================================
    # SEQUENCE DOWNLOADS
    # ==========================================================================

    @render.download(filename="hits_proteins.faa")
    def dl_hits_proteins_faa():
        yield from _serve_file(["results", "output", ""], "hits_proteins.faa")

    @render.download(filename="hits_aligned.faa")
    def dl_hits_aligned_faa():
        yield from _serve_file(["results", "alignments", "output", ""], "hits_aligned.faa")

    @render.download(filename="cluster_reps.faa")
    def dl_cluster_reps_faa():
        yield from _serve_file(["results", "output", ""], "cluster_reps.faa")

    # ==========================================================================
    # FIGURE DOWNLOADS
    # ==========================================================================

    # ── Synteny map (PNG / SVG / PDF) ──────────────────────────────────
    @render.download(filename="synteny_map.png")
    def dl_synteny_png_exp():
        yield from _serve_file(["figures", "results", ""], "synteny_map.png")

    @render.download(filename="synteny_map.svg")
    def dl_synteny_svg_exp():
        yield from _serve_file(["figures", "results", ""], "synteny_map.svg")

    @render.download(filename="synteny_map.pdf")
    def dl_synteny_pdf_exp():
        yield from _serve_file(["figures", "results", ""], "synteny_map.pdf")

    # ── Phylogenetic tree (PNG / SVG) ───────────────────────────────────
    @render.download(filename="tree.png")
    def dl_tree_png_exp():
        yield from _serve_file(["figures", "results", ""], "tree.png")

    @render.download(filename="tree.svg")
    def dl_tree_svg_exp():
        yield from _serve_file(["figures", "results", ""], "tree.svg")

    # ── Heatmap (PNG / SVG) ─────────────────────────────────────────────
    @render.download(filename="heatmap.png")
    def dl_heatmap_png():
        yield from _serve_file(["figures", "results", ""], "heatmap.png")

    @render.download(filename="heatmap.svg")
    def dl_heatmap_svg_exp():
        yield from _serve_file(["figures", "results", ""], "heatmap.svg")

    # ── HMM logo (PNG / SVG) ────────────────────────────────────────────
    @render.download(filename="hmm_logo.png")
    def dl_hmm_logo_png():
        yield from _serve_file(["figures", "hmm", "results", ""], "hmm_logo.png")

    @render.download(filename="hmm_logo.svg")
    def dl_hmm_logo_svg_exp():
        yield from _serve_file(["figures", "hmm", "results", ""], "hmm_logo.svg")

    # ── Taxonomy Sankey (SVG / PNG) ─────────────────────────────────────
    @render.download(filename="taxonomy_sankey.svg")
    def dl_taxonomy_sankey_svg():
        yield from _serve_file(["figures", "results", ""], "taxonomy_sankey.svg")

    @render.download(filename="taxonomy_sankey.png")
    def dl_taxonomy_sankey_png_exp():
        yield from _serve_file(["figures", "results", ""], "taxonomy_sankey.png")

    # ==========================================================================
    # REPORT DOWNLOADS
    # ==========================================================================

    @render.download(filename="summary_report.html")
    def dl_summary_report_html():
        yield from _serve_file(["reports", "results", ""], "summary_report.html")

    @render.download(filename="reproducibility.json")
    def dl_repro_json():
        yield from _serve_file(["reports", "results", ""], "reproducibility.json")

    @render.download(filename="METHODS_TEXT.txt")
    def dl_methods_txt():
        yield from _serve_file(["reports", "results", ""], "METHODS_TEXT.txt")

    # ==========================================================================
    # ZIP EXPORT
    # ==========================================================================

    _zip_ready: reactive.Value[bytes | None] = reactive.value(None)
    _zip_saved_message: reactive.Value[str] = reactive.value("")

    def _build_export_zip_bytes(pd_: Path) -> bytes:
        """Build and return the full export ZIP as bytes."""
        # Generate reproducibility files before ZIP creation
        if reporter is not None:
            try:
                hits_file = pd_ / "results" / "hits_main.tsv"
                hits_df = None
                if hits_file.exists():
                    import pandas as _pd
                    hits_df = _pd.read_csv(hits_file, sep="\t")

                state_file = pd_ / ".pipeline_state.json"
                state_dict = {}
                if state_file.exists():
                    state_dict = json.loads(state_file.read_text())

                tools_file = pd_ / "reports" / "tools.json"
                tools_dict = {}
                if tools_file.exists():
                    tools_dict = json.loads(tools_file.read_text())

                if hasattr(reporter, "build_reproducibility_json"):
                    repro = reporter.build_reproducibility_json(pd_, hits_df, state_dict, tools_dict)
                    if hasattr(reporter, "generate_methods_text"):
                        reporter.generate_methods_text(pd_, repro)
                    if hasattr(reporter, "render_html_report"):
                        try:
                            ctx = reporter.build_report_context(pd_, repro) if hasattr(reporter, "build_report_context") else repro
                            reporter.render_html_report(pd_, ctx)
                        except Exception:
                            pass
            except Exception:
                pass

        if reporter is not None and hasattr(reporter, "create_export_zip"):
            try:
                zip_path = reporter.create_export_zip(pd_)
                return Path(zip_path).read_bytes()
            except Exception:
                pass

        file_map = {
            # Tables
            "tables/hits_main.tsv":              ["results/hits_main.tsv", "hits_main.tsv"],
            "tables/hits_best_per_genome.tsv":   ["results/hits_best_per_genome.tsv"],
            "tables/synteny_table.tsv":          ["results/synteny_table.tsv"],
            "tables/presence_absence_matrix.tsv":["results/presence_absence_matrix.tsv"],
            "tables/taxonomy_table.tsv":         ["results/taxonomy_table.tsv"],
            "tables/taxonomy_outliers.tsv":      ["results/taxonomy_outliers.tsv"],
            "tables/cluster_summary.tsv":        ["results/cluster_summary.tsv"],
            "tables/controls_results.tsv":       ["results/controls_results.tsv"],
            # Sequences
            "sequences/hits_proteins.faa":       ["results/hits_proteins.faa"],
            "sequences/hits_aligned.faa":        ["results/hits_aligned.faa", "alignments/hits_aligned.faa"],
            "sequences/cluster_reps.faa":        ["results/cluster_reps.faa"],
            "sequences/iter_profile.hmm":        ["hmm/iter_profile.hmm"],
            # Figures
            "figures/synteny_map.png":           ["figures/synteny_map.png", "results/synteny_map.png"],
            "figures/synteny_map.svg":           ["figures/synteny_map.svg", "results/synteny_map.svg"],
            "figures/synteny_map.pdf":           ["figures/synteny_map.pdf", "results/synteny_map.pdf"],
            "figures/tree.png":                  ["figures/tree.png", "results/tree.png"],
            "figures/tree.svg":                  ["figures/tree.svg", "results/tree.svg"],
            "figures/heatmap.png":               ["figures/heatmap.png", "results/heatmap.png"],
            "figures/heatmap.svg":               ["figures/heatmap.svg", "results/heatmap.svg"],
            "figures/hmm_logo.png":              ["figures/hmm_logo.png", "hmm/hmm_logo.png", "results/hmm_logo.png"],
            "figures/hmm_logo.svg":              ["figures/hmm_logo.svg", "hmm/hmm_logo.svg"],
            "figures/taxonomy_sankey.svg":       ["figures/taxonomy_sankey.svg", "results/taxonomy_sankey.svg"],
            "figures/taxonomy_sankey.png":       ["figures/taxonomy_sankey.png", "results/taxonomy_sankey.png"],
            # Reports
            "reports/summary_report.html":       ["reports/summary_report.html"],
            "reports/reproducibility.json":      ["reports/reproducibility.json"],
            "reports/METHODS_TEXT.txt":          ["reports/METHODS_TEXT.txt"],
            "reports/RUN_SUMMARY.md":            ["reports/RUN_SUMMARY.md"],
            "reports/run_summary.json":          ["reports/run_summary.json"],
        }

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for zip_path, candidates in file_map.items():
                for rel in candidates:
                    f = pd_ / rel
                    if f.exists():
                        zf.write(f, zip_path)
                        break
            for meme_cand in [pd_ / "results" / "meme_out", pd_ / "meme_out"]:
                if meme_cand.is_dir():
                    for meme_file in meme_cand.rglob("*"):
                        if meme_file.is_file():
                            zf.write(meme_file, f"motifs/{meme_file.relative_to(meme_cand)}")
                    break
        return buf.getvalue()

    @reactive.effect
    @reactive.event(input.btn_export_zip)
    async def _on_export_zip():
        _zip_ready.set(None)
        pd_ = _proj_dir()
        if pd_ is None:
            return
        _zip_ready.set(_build_export_zip_bytes(pd_))

    @reactive.effect
    @reactive.event(input.btn_save_zip_to_folder)
    async def _on_save_zip_to_folder():
        _zip_saved_message.set("")
        pd_ = _proj_dir()
        if pd_ is None:
            _zip_saved_message.set("Load a project before exporting.")
            return
        try:
            dest = Path((input.export_dest_dir() or "").strip()).expanduser()
            if not dest:
                _zip_saved_message.set("Enter a destination folder.")
                return
            dest.mkdir(parents=True, exist_ok=True)
            data = _zip_ready.get() or _build_export_zip_bytes(pd_)
            project_name = pd_.name or "hmm_discovery_project"
            zip_path = dest / f"{project_name}_hmm_discovery_export.zip"
            zip_path.write_bytes(data)
            _zip_ready.set(data)
            _zip_saved_message.set(f"Saved: {zip_path}")
        except Exception as exc:
            _zip_saved_message.set(f"Could not save ZIP: {exc}")

    @output
    @render.ui
    def zip_download_ui():
        data = _zip_ready.get()
        if data is None:
            return ui.tags.span("")
        import base64
        b64 = base64.b64encode(data).decode()
        return ui.HTML(
            f'<a href="data:application/zip;base64,{b64}" '
            f'download="hmm_discovery_export.zip" '
            f'class="btn btn-success btn-sm">⬇ Download ZIP ({len(data)//1024} KB)</a>'
        )

    @output
    @render.ui
    def zip_save_status():
        msg = _zip_saved_message.get()
        if not msg:
            return ui.tags.span("")
        cls = "text-success" if msg.startswith("Saved:") else "text-warning"
        return ui.tags.div(ui.tags.small(msg, class_=cls), class_="mt-2")

    # ==========================================================================
    # REPRODUCIBILITY CARD
    # ==========================================================================

    @output
    @render.ui
    def repro_summary():
        rpd = _reports_dir()
        if rpd is None:
            return ui.tags.p("Project directory not set.", class_="text-muted small")
        repro_file = rpd / "reproducibility.json"
        if not repro_file.exists():
            return ui.tags.p("reproducibility.json not found — complete the pipeline first.", class_="text-muted small")

        try:
            data = json.loads(repro_file.read_text())
        except Exception as exc:
            return ui.tags.p(f"Could not parse reproducibility.json: {exc}", class_="text-danger small")

        # Tool versions table
        tools = data.get("tool_versions", {})
        tool_rows = [
            ui.tags.tr(ui.tags.td(t), ui.tags.td(v))
            for t, v in tools.items()
        ]
        tool_table = ui.tags.table(
            ui.tags.thead(ui.tags.tr(ui.tags.th("Tool"), ui.tags.th("Version"))),
            ui.tags.tbody(*tool_rows) if tool_rows else ui.tags.tbody(
                ui.tags.tr(ui.tags.td("—", colspan="2"))
            ),
            class_="table table-sm table-bordered w-auto",
        )

        # Parameters summary
        params = data.get("parameters", {})
        param_rows = [
            ui.tags.tr(ui.tags.td(k, class_="text-muted"), ui.tags.td(str(v)))
            for k, v in params.items()
        ]
        param_table = ui.tags.table(
            ui.tags.thead(ui.tags.tr(ui.tags.th("Parameter"), ui.tags.th("Value"))),
            ui.tags.tbody(*param_rows) if param_rows else ui.tags.tbody(
                ui.tags.tr(ui.tags.td("—", colspan="2"))
            ),
            class_="table table-sm table-bordered w-auto",
        ) if params else ui.tags.span("")

        run_date = data.get("generated_at", data.get("run_date", data.get("timestamp", "unknown")))
        proj_name = Path(data.get("project_dir", "")).name or "—"

        return ui.tags.div(
            ui.layout_columns(
                stat_card("Project", proj_name, "primary"),
                stat_card("Run date", run_date, "secondary"),
                stat_card("Tools logged", len(tools), "info"),
                col_widths=[4, 4, 4],
            ),
            ui.tags.div(
                ui.tags.h6("Tool Versions", class_="mt-3"),
                tool_table,
                ui.tags.h6("Parameters", class_="mt-3") if params else "",
                param_table,
                class_="mt-2",
            ),
        )

    @output
    @render.ui
    def methods_text_display():
        rpd = _reports_dir()
        if rpd is None:
            return ui.tags.span("")
        f = rpd / "METHODS_TEXT.txt"
        if not f.exists():
            return ui.tags.p("METHODS_TEXT.txt not found.", class_="text-muted small")
        try:
            text = f.read_text()
        except Exception as exc:
            return ui.tags.p(f"Error reading file: {exc}", class_="text-danger small")
        return ui.tags.blockquote(
            ui.tags.p(text, style="white-space:pre-wrap; font-style:italic;"),
            class_="blockquote border-start border-4 border-primary ps-3 bg-light p-3 rounded",
        )

    @output
    @render.data_frame
    def audit_trail_table():
        import pandas as pd

        ld = _logs_dir()
        if ld is None:
            return render.DataGrid(pd.DataFrame(), height="200px")
        audit_file = ld / "audit_trail.jsonl"
        if not audit_file.exists():
            return render.DataGrid(
                pd.DataFrame(columns=["timestamp", "step", "event", "details"]),
                height="200px",
            )
        try:
            records = []
            for line in audit_file.read_text().splitlines():
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        records.append({"raw": line})
            df = pd.DataFrame(records)
            # Ensure useful columns come first
            priority = ["timestamp", "step", "event", "details"]
            other = [c for c in df.columns if c not in priority]
            ordered = [c for c in priority if c in df.columns] + other
            df = df[ordered]
            return render.DataGrid(df, height="400px", filters=True)
        except Exception as exc:
            return render.DataGrid(
                pd.DataFrame({"error": [str(exc)]}),
                height="100px",
            )

    @output
    @render.ui
    def report_preview():
        rpd = _reports_dir()
        if rpd is None:
            return ui.tags.p("Project directory not set.", class_="text-muted small")
        f = rpd / "summary_report.html"
        if not f.exists():
            return ui.tags.div(
                ui.tags.p(
                    "summary_report.html not found. Complete the pipeline to generate the report.",
                    class_="text-muted text-center py-4",
                ),
                class_="border rounded p-3",
            )
        try:
            html_content = f.read_text()
        except Exception as exc:
            return ui.tags.p(f"Error reading report: {exc}", class_="text-danger small")

        # Embed in a sandboxed, scrollable container
        return ui.tags.div(
            ui.HTML(
                f'<iframe srcdoc="{_escape_html_attr(html_content)}" '
                f'style="width:100%; height:600px; border:1px solid #dee2e6; border-radius:4px;" '
                f'sandbox="allow-same-origin"></iframe>'
            ),
        )


def _escape_html_attr(s: str) -> str:
    """Escape a string for embedding in an HTML attribute (srcdoc)."""
    return (
        s.replace("&", "&amp;")
         .replace('"', "&quot;")
         .replace("'", "&#39;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )
