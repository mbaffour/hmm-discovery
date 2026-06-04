"""
ui/step_02_msa.py — Multiple Sequence Alignment Panel (Step 2).

Runs MAFFT or Clustal Omega, optionally trims with trimAl, and reports
alignment quality metrics. A compact ASCII preview is shown inline.
"""
from __future__ import annotations

from shiny import ui

from .components import (
    info_tooltip,
    step_guidance,
    log_panel,
    section_header,
    stat_badge,
    stat_card,
    step_card,
    tool_badge,
)


# ---------------------------------------------------------------------------
# Panel UI
# ---------------------------------------------------------------------------

def panel_ui() -> ui.TagChild:
    return ui.nav_panel(
        "2. Multiple Sequence Alignment",
        ui.tags.div(
            step_guidance(
                "Align all seed sequences to reveal conserved regions — the alignment quality directly determines HMM sensitivity.",
                [
                "Trimmed multiple sequence alignment (.faa)",
                "Alignment quality stats: length, identity, gap %",
                "ASCII preview of the first 20 columns",
                ],
                "MAFFT auto mode chooses the best strategy based on dataset size. For > 500 sequences use FFT-NS-2.",
            ),
            section_header("Aligner Settings"),

            ui.layout_columns(
                # ---- aligner choice ------------------------------------------
                ui.tags.div(
                    ui.input_select(
                        "aligner",
                        "Aligner",
                        {
                            "mafft": "MAFFT (recommended)",
                            "clustalo": "Clustal Omega",
                        },
                        selected="mafft",
                    ),
                    ui.input_select(
                        "mafft_mode",
                        "MAFFT accuracy mode",
                        {
                            "auto":        "auto — chooses best mode for dataset size",
                            "localpair":   "L-INS-i — most accurate (< 200 seqs)",
                            "globalpair":  "G-INS-i — global homology (< 200 seqs)",
                            "genafpair":   "E-INS-i — many long gaps (< 200 seqs)",
                            "retree2":     "FFT-NS-2 — fast (> 500 seqs)",
                        },
                        selected="auto",
                    ),
                    ui.input_slider(
                        "msa_cpu",
                        ui.span("CPU threads", info_tooltip(
                            "Threads for MAFFT. More = faster on large seed sets.")),
                        min=1, max=32, value=4,
                    ),
                ),
                # ---- trimAl + figure format ----------------------------------
                ui.tags.div(
                    ui.input_switch(
                        "use_trimal",
                        ui.span("Apply trimAl column trimming", info_tooltip(
                            "Removes poorly-aligned, gappy columns before building "
                            "the HMM. Recommended on for most alignments.")),
                        value=True,
                    ),
                    ui.output_ui("trimal_options"),
                    ui.input_select(
                        "aln_fig_fmt",
                        "Alignment figure format",
                        {"png": "PNG (300 dpi)", "svg": "SVG (vector)", "pdf": "PDF (vector)"},
                        selected="png",
                    ),
                ),
                col_widths=[6, 6],
            ),

            # ---- tool availability badges ------------------------------------
            ui.output_ui("tool_availability"),

            # ---- run button --------------------------------------------------
            ui.tags.div(
                ui.input_action_button(
                    "run_msa",
                    "▶ Run Alignment",
                    class_="btn btn-primary mt-2",
                ),
                ui.tags.span(" ", class_="me-2"),
                ui.output_ui("msa_run_status"),
                class_="d-flex align-items-center mt-2 mb-3",
            ),

            # ---- results -----------------------------------------------------
            ui.output_ui("msa_stats"),

            section_header("Alignment Preview", "First 20 columns of the trimmed alignment"),
            ui.output_text_verbatim("msa_preview"),

            # ---- coloured alignment figure -----------------------------------
            ui.card(
                ui.card_header(
                    "Alignment Figure (ClustalX colour scheme — publication-ready)",
                ),
                ui.output_ui("alignment_figure_out"),
                class_="mt-3",
            ),
            ui.tags.div(
                ui.input_action_button(
                    "render_aln_fig", "🖼 Render Alignment Figure",
                    class_="btn btn-outline-primary btn-sm me-2",
                ),
                ui.download_button(
                    "dl_aln_figure", "⬇ Download Figure",
                    class_="btn btn-success btn-sm",
                ),
                class_="mt-2 mb-3",
            ),

            # ---- log ---------------------------------------------------------
            section_header("Run Log"),
            log_panel("msa_log", height="220px"),

            class_="container-fluid px-0",
        ),
    )


# ---------------------------------------------------------------------------
# Server-side outputs
# ---------------------------------------------------------------------------

def register_outputs(
    input,
    output,
    render,
    reactive,
    session,
    state,
    runner_dict,
    proj_dir_rv,
    **kwargs,
):
    alignment = kwargs.get("alignment", None)

    _quality      = reactive.value(None)   # dict from alignment.alignment_quality()
    _running      = reactive.value(False)
    _aln_fig_data = reactive.value(b"")    # bytes of last rendered alignment figure
    _aln_fig_fmt  = reactive.value("png")  # format of _aln_fig_data

    # ---- conditional trimAl method selector ----------------------------------
    @output
    @render.ui
    def trimal_options():
        if not input.use_trimal():
            return ui.tags.span("")
        return ui.input_select(
            "trimal_method",
            "trimAl method",
            {
                "automated1": "automated1 (recommended)",
                "strict": "strict",
                "gappyout": "gappyout",
            },
            selected="automated1",
        )

    # ---- tool availability badges --------------------------------------------
    @output
    @render.ui
    def tool_availability():
        from pipeline.utils import find_tool
        return ui.tags.div(
            tool_badge("mafft",    "MAFFT",         find_tool("mafft")    is not None),
            tool_badge("clustalo", "Clustal Omega",  find_tool("clustalo") is not None),
            tool_badge("trimal",   "trimAl",         find_tool("trimal")   is not None),
            class_="mb-2",
        )

    # ---- run status ----------------------------------------------------------
    @output
    @render.ui
    def msa_run_status():
        runner = runner_dict.get("msa")
        if runner is None:
            return ui.tags.span("")
        if runner.is_running.get():
            return ui.tags.span("🔄 Running…", class_="badge bg-warning text-dark")
        rc = runner.returncode.get()
        if rc is None:
            return ui.tags.span("")
        if rc == 0:
            return ui.tags.span("✅ Complete", class_="badge bg-success")
        return ui.tags.span(f"❌ Failed (exit {rc})", class_="badge bg-danger")

    # ---- run MSA event -------------------------------------------------------
    @reactive.effect
    @reactive.event(input.run_msa)
    async def _on_run_msa():
        from pathlib import Path as _Path

        proj_dir = proj_dir_rv.get() if proj_dir_rv is not None else None
        if proj_dir is None:
            ui.notification_show(
                "⚠️ Please load a project directory first (sidebar → Load / Create Project).",
                type="warning", duration=6,
            )
            return

        proj = _Path(proj_dir)
        input_path = ""

        # 1. Try state steps dict (set when user clicks Analyze Input)
        try:
            params = state.get_params("input") or {}
            input_path = (params or {}).get("input_path", "")
        except Exception:
            input_path = ""

        # 2. Try state project dict (alternative storage used by set_input)
        if not input_path:
            try:
                input_path = state.get_project("input_path", "") or ""
            except Exception:
                input_path = ""

        # 3. Try live Shiny inputs directly (uploaded file or folder path)
        if not input_path:
            try:
                file_info = input.seq_file()
                if file_info:
                    input_path = file_info[0]["datapath"]
            except Exception:
                pass
        if not input_path:
            try:
                fp = input.folder_path()
                if fp and fp.strip():
                    input_path = fp.strip()
            except Exception:
                pass

        if not input_path:
            ui.notification_show(
                "⚠️ No input sequences found. Go to Step 1 (Input), "
                "upload or point to your FASTA file, then click Analyze Input.",
                type="warning", duration=8,
            )
            return

        # If input_path is a directory, find the first FASTA file inside it
        _ip = _Path(input_path)
        if _ip.is_dir():
            candidates = sorted(_ip.glob("*.faa")) + sorted(_ip.glob("*.fasta")) + \
                         sorted(_ip.glob("*.fa")) + sorted(_ip.glob("*.fna"))
            if not candidates:
                return
            input_path = str(candidates[0])

        aligner = input.aligner()
        cpu = input.msa_cpu()
        out_aln = proj / "alignments" / f"seed.{aligner}.faa"
        out_aln.parent.mkdir(parents=True, exist_ok=True)

        # Build aligner command.
        # MAFFT writes alignment to stdout — use shell redirect to save to file.
        # trimAl accepts explicit -in/-out so no redirect needed.
        if aligner == "mafft":
            mode_flag = input.mafft_mode() if hasattr(input, "mafft_mode") else "auto"
            if mode_flag == "auto":
                mafft_args = f"--auto --thread {cpu}"
            else:
                mafft_args = f"--{mode_flag} --maxiterate 1000 --thread {cpu}"
            # Shell redirect captures stdout (alignment) to file; stderr (progress) goes to runner log
            cmd = ["bash", "-c",
                   f"mafft {mafft_args} '{input_path}' > '{out_aln}'"]
        else:
            cmd = [
                "clustalo",
                "-i", input_path,
                "-o", str(out_aln),
                "--threads", str(cpu),
                "--force",
            ]

        # For MAFFT + trimAl: chain both in one bash command so they run sequentially
        if aligner == "mafft" and input.use_trimal():
            trimal_out = proj / "alignments" / "seed.mafft.trimmed.faa"
            try:
                method = input.trimal_method()
            except Exception:
                method = "automated1"   # safe default if input not rendered yet
            cmd = ["bash", "-c",
                   f"mafft {mafft_args} '{input_path}' > '{out_aln}' "
                   f"&& trimal -{method} -in '{out_aln}' -out '{trimal_out}'"]

        runner = runner_dict.get("msa")
        if runner is None:
            return
        runner.start(cmd, cwd=proj)

        # Wait for completion in background (max 5 minutes)
        import asyncio as _asyncio
        for _ in range(600):          # 600 × 0.5 s = 5 min
            await _asyncio.sleep(0.5)
            if not runner.is_running.get():
                break

        if alignment is not None and state is not None:
            try:
                best = (proj / "alignments" / "seed.mafft.trimmed.faa"
                        if aligner == "mafft" and input.use_trimal()
                        else out_aln)
                if best.exists():
                    q = alignment.alignment_quality(best)
                    _quality.set(q)
                    state.mark_complete("msa", {"aligner": aligner,
                                                "use_trimal": input.use_trimal(),
                                                "aligned_path": str(best)})
            except Exception:
                pass

    # ---- msa_stats -----------------------------------------------------------
    @output
    @render.ui
    def msa_stats():
        q = _quality.get()
        if q is None:
            return ui.tags.p(
                "Run the alignment to see quality metrics.",
                class_="text-muted",
            )
        return ui.tags.div(
            section_header("Alignment Quality"),
            ui.layout_columns(
                stat_card("sequences", q.get("n_sequences", "—"), color="primary", icon="🧬"),
                stat_card("alignment length", q.get("aln_length", "—"), color="info", icon="📐"),
                stat_card("% identity (avg)", q.get("avg_pairwise_id", "—"), color="success", icon="🔗"),
                stat_card("% gaps (avg)", q.get("gap_pct", "—"), color="warning", icon="⬜"),
                col_widths=[3, 3, 3, 3],
            ),
        )

    # ---- msa_preview ---------------------------------------------------------
    @output
    @render.text
    def msa_preview():
        if alignment is not None:
            proj_dir = proj_dir_rv.get() if proj_dir_rv is not None else None
            if proj_dir is not None:
                from pathlib import Path as _Path
                proj = _Path(proj_dir)
                aln_candidates = [
                    proj / "alignments" / "seed.mafft.trimmed.faa",
                    proj / "alignments" / "seed.mafft.faa",
                    proj / "alignments" / "seed.clustalo.faa",
                ]
                aln_path = next((p for p in aln_candidates if p.exists()), None)
                if aln_path is None:
                    hits = list((proj / "alignments").glob("*.faa")) if (proj / "alignments").exists() else []
                    aln_path = hits[0] if hits else None
                if aln_path is not None:
                    try:
                        return alignment.alignment_preview(aln_path)
                    except Exception as exc:
                        return f"Preview unavailable: {exc}"
        runner = runner_dict.get("msa")
        if runner and runner.succeeded():
            return "(alignment complete — install pipeline module for preview)"
        return "No alignment yet."

    # ---- msa_log -------------------------------------------------------------
    @output
    @render.text
    def msa_log():
        lines: list[str] = []
        for key in ("msa", "trimal"):
            r = runner_dict.get(key)
            if r:
                log = r.get_log()
                if log.strip():
                    lines.append(f"=== {key.upper()} ===")
                    lines.append(log)
        return "\n".join(lines) if lines else "No log yet."

    # ---- alignment figure render & download ----------------------------------
    @reactive.effect
    @reactive.event(input.render_aln_fig)
    async def _on_render_aln_fig():
        import sys as _sys
        proj_dir = proj_dir_rv.get() if proj_dir_rv is not None else None
        if proj_dir is None:
            return
        from pathlib import Path as _Path
        proj = _Path(proj_dir)

        # Locate the best available alignment (trimmed preferred)
        aln_candidates = [
            proj / "alignments" / "seed.mafft.trimmed.faa",
            proj / "alignments" / "seed.mafft.faa",
            proj / "alignments" / "seed.clustalo.faa",
            proj / "alignments" / "seeds_trimmed.faa",
            proj / "alignments" / "seeds_aligned.faa",
        ]
        aln_path = next((p for p in aln_candidates if p.exists()), None)
        if aln_path is None:
            # Last resort: any .faa in alignments/
            hits = list((proj / "alignments").glob("*.faa")) if (proj / "alignments").exists() else []
            aln_path = hits[0] if hits else None

        if aln_path is None:
            _aln_fig_data.set(b"")
            return

        fmt = input.aln_fig_fmt() if hasattr(input, "aln_fig_fmt") else "png"
        _aln_fig_fmt.set(fmt)

        try:
            from pipeline.alignment import alignment_figure  # type: ignore
            fig_bytes = alignment_figure(
                aln_path,
                out_dir=proj / "figures",
                fmt=fmt,
                dpi=300,
                max_seqs=60,
                max_cols=300,
            )
            _aln_fig_data.set(fig_bytes)
        except Exception as exc:
            print(f"Alignment figure error: {exc}", file=_sys.stderr)
            _aln_fig_data.set(b"")

    @output
    @render.ui
    def alignment_figure_out():
        import base64
        data = _aln_fig_data.get()
        fmt  = _aln_fig_fmt.get()

        if not data:
            return ui.tags.p(
                "Click '🖼 Render Alignment Figure' above to generate the "
                "publication-ready coloured alignment.",
                class_="text-muted text-center py-4 small",
            )

        if fmt == "svg":
            try:
                return ui.tags.div(
                    ui.HTML(data.decode("utf-8", errors="replace")),
                    style="overflow:auto; max-height:500px;",
                )
            except Exception:
                pass

        if fmt in ("png", "pdf"):
            b64 = base64.b64encode(data).decode()
            mime = "image/png" if fmt == "png" else "application/pdf"
            if fmt == "png":
                return ui.tags.img(
                    src=f"data:image/png;base64,{b64}",
                    style="max-width:100%; height:auto; display:block; margin:auto;",
                )
            # PDF: show download prompt
            return ui.tags.div(
                ui.tags.p("PDF generated — use ⬇ Download Figure button.",
                          class_="text-success small text-center"),
            )

        return ui.tags.p("Unknown format.", class_="text-muted small")

    @render.download(filename=lambda: f"alignment_figure.{_aln_fig_fmt.get()}")
    def dl_aln_figure():
        data = _aln_fig_data.get()
        if data:
            yield data
