"""
ui/step_05_validate.py — Validation & Score Calibration Panel (Step 5).

Two sub-sections:
  A. Custom calibration — user uploads known positives + negatives, runs
     hmmsearch against both, views score distribution, tunes thresholds.
  B. Built-in controls  — runs the bundled positive/negative control sets
     appropriate for the current biology mode and reports sensitivity /
     specificity / FPR.
"""
from __future__ import annotations

import os
from pathlib import Path

from shiny import ui

from .components import info_tooltip, log_panel, section_header, stat_card, step_card, step_guidance


# ---------------------------------------------------------------------------
# Panel UI
# ---------------------------------------------------------------------------

def panel_ui() -> ui.TagChild:
    return ui.nav_panel(
        "5. Score Calibration",
        ui.tags.div(
            step_guidance(
                "Calibrate bit-score thresholds against known positives and negatives to tune sensitivity and specificity.",
                [
                "Score distribution chart comparing positive and negative sets",
                "Recommended strict and moderate thresholds",
                "Built-in taxon-level control results",
                ],
                "Use your seed sequences as positives. For negatives, use unrelated proteins from a different protein family.",
            ),
            ui.tags.p(
                "Calibrate bit-score thresholds against known positives/negatives "
                "and run built-in taxon-level controls to measure sensitivity and "
                "specificity for the current biology mode.",
                class_="text-muted mb-3",
            ),

            # ================================================================
            # SECTION A: Custom calibration
            # ================================================================
            ui.card(
                ui.card_header(ui.tags.strong("A. Custom Calibration Sets")),
                ui.layout_columns(
                    ui.tags.div(
                        ui.input_file(
                            "pos_faa",
                            "Known positives FASTA",
                            accept=[".faa", ".fasta", ".fa"],
                            placeholder="Upload FASTA file…",
                        ),
                        ui.input_checkbox(
                            "use_seeds_as_pos",
                            "Use seed sequences as positives",
                            value=True,
                        ),
                        ui.tags.small(
                            "If checked and no file is uploaded, the seed alignment "
                            "sequences will be used as the positive set.",
                            class_="text-muted d-block mt-1",
                        ),
                    ),
                    ui.tags.div(
                        ui.input_file(
                            "neg_faa",
                            "Known negatives FASTA",
                            accept=[".faa", ".fasta", ".fa"],
                            placeholder="Upload FASTA file…",
                        ),
                        ui.tags.small(
                            "Tip: use a random sample of SwissProt non-phage proteins, "
                            "or use the built-in controls below.",
                            class_="text-muted d-block mt-1",
                        ),
                    ),
                    col_widths=[6, 6],
                ),
                ui.tags.div(
                    ui.input_action_button(
                        "run_calibration",
                        "▶ Run Calibration",
                        class_="btn btn-primary",
                    ),
                    class_="mt-2",
                ),
                class_="mb-3",
            ),

            # Score distribution + threshold tuning (custom)
            ui.card(
                ui.card_header(ui.tags.strong("Score Distribution (Custom Sets)")),
                ui.output_ui("score_dist_plot"),
                section_header("Threshold Tuning", "Drag sliders to adjust cutoffs"),
                ui.layout_columns(
                    ui.input_slider(
                        "strict_thresh",
                        "Strict threshold (bits)",
                        min=10, max=200, value=45, step=1,
                    ),
                    ui.input_slider(
                        "moderate_thresh",
                        "Moderate threshold (bits)",
                        min=5, max=150, value=30, step=1,
                    ),
                    col_widths=[6, 6],
                ),
                section_header("Threshold Statistics"),
                ui.output_ui("threshold_stats"),
                class_="mb-3",
            ),

            section_header("Calibration Log"),
            log_panel("calibration_log"),

            # ================================================================
            # SECTION B: Built-in controls
            # ================================================================
            ui.tags.hr(class_="my-4"),
            ui.tags.h5("B. Built-in Taxon Controls", class_="mb-1"),
            ui.tags.p(
                "Runs the bundled control FASTA files for the current biology mode. "
                "Phage mode uses fungi, mammalian and archaeal proteins as negatives; "
                "bacterial mode uses eukaryotic viral and plant proteins; "
                "generic mode uses shuffled seeds plus plant and archaeal proteins.",
                class_="text-muted mb-3",
            ),

            ui.card(
                ui.card_header(ui.tags.strong("Control Settings")),
                ui.layout_columns(
                    ui.input_numeric(
                        "ctrl_strict",
                        ui.span("Strict threshold (bits)", info_tooltip(
                            "Bit score for a high-confidence call. ≥45 is a "
                            "reliable match for most families.")),
                        value=45, min=5, max=300, step=1,
                    ),
                    ui.input_numeric(
                        "ctrl_moderate",
                        ui.span("Moderate threshold (bits)", info_tooltip(
                            "Bit score for a putative call. Hits between moderate "
                            "and strict are worth manual review.")),
                        value=30, min=5, max=200, step=1,
                    ),
                    ui.input_numeric(
                        "ctrl_cpu",
                        "CPU threads",
                        value=4, min=1, max=64, step=1,
                    ),
                    col_widths=[4, 4, 4],
                ),
                ui.tags.div(
                    ui.input_action_button(
                        "run_controls",
                        "▶ Run Built-in Controls",
                        class_="btn btn-outline-secondary",
                    ),
                    class_="mt-2",
                ),
                class_="mb-3",
            ),

            # Summary stats
            ui.output_ui("controls_summary_cards"),

            # Per-control detail table
            ui.output_ui("controls_detail_table"),

            # Score distribution comparing positives vs controls
            ui.output_ui("controls_score_dist"),

            section_header("Controls Log"),
            log_panel("controls_log"),

            class_="container-fluid px-0",
        ),
    )


# ---------------------------------------------------------------------------
# Server outputs
# ---------------------------------------------------------------------------

def register_outputs(input, output, render, reactive, session, **kwargs):
    state        = kwargs.get("state", {})
    proj_dir_rv  = kwargs.get("proj_dir_rv", None)
    biology_mode = kwargs.get("biology_mode", lambda: "generic")

    # ---- Shared helpers ----
    def _proj_dir() -> Path | None:
        if proj_dir_rv is not None:
            v = proj_dir_rv.get()
            return Path(v) if v else None
        return None

    def _hmm_path() -> Path | None:
        pd_ = _proj_dir()
        if pd_ is None:
            return None
        candidates = sorted(pd_.glob("hmm/*.hmm"))
        return candidates[-1] if candidates else None

    def _app_dir() -> Path:
        return Path(__file__).parent.parent

    # ---- hmmsearch helper that uses augmented PATH ----
    def _run_hmmsearch_get_scores(hmm: Path, fasta: Path, cpu: int = 4) -> list[float]:
        """Run hmmsearch and return per-sequence bit scores."""
        from pipeline.utils import find_tool, run_cmd  # type: ignore
        hmmsearch_bin = find_tool("hmmsearch") or "hmmsearch"
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".tbl", delete=False) as tmp:
            tbl = Path(tmp.name)
        try:
            run_cmd([
                hmmsearch_bin,
                "--cpu", str(cpu),
                "--noali",
                "--tblout", str(tbl),
                str(hmm),
                str(fasta),
            ])
            scores: list[float] = []
            if tbl.exists():
                with tbl.open() as fh:
                    for line in fh:
                        if line.startswith("#") or not line.strip():
                            continue
                        parts = line.split()
                        if len(parts) >= 6:
                            try:
                                scores.append(float(parts[5]))
                            except ValueError:
                                pass
            return scores
        finally:
            tbl.unlink(missing_ok=True)

    # ===========================================================================
    # SECTION A: Custom calibration
    # ===========================================================================

    _pos_scores: reactive.Value[list] = reactive.value([])
    _neg_scores: reactive.Value[list] = reactive.value([])
    _log_lines:  reactive.Value[list] = reactive.value([])

    def _log(msg: str):
        lines = _log_lines.get()
        lines.append(msg)
        _log_lines.set(lines[-500:])

    @reactive.effect
    @reactive.event(input.run_calibration)
    async def _on_run_calibration():
        _log_lines.set([])
        _log("=== Starting calibration ===")

        hmm = _hmm_path()
        if hmm is None:
            _log("ERROR: No HMM profile found. Build HMM in step 3 first.")
            return

        _log(f"Using HMM: {hmm}")
        pd_ = _proj_dir()

        # --- Positives ---
        pos_fasta: Path | None = None
        pos_info = input.pos_faa()
        if pos_info and len(pos_info) > 0:
            pos_fasta = Path(pos_info[0]["datapath"])
            _log(f"Positive set: {pos_info[0]['name']} ({os.path.getsize(pos_fasta)} bytes)")
        elif input.use_seeds_as_pos():
            if pd_ is not None:
                for seed_dir in ["data", "seeds", "input"]:
                    seed_candidates = sorted((pd_ / seed_dir).glob("*.faa")) + sorted((pd_ / seed_dir).glob("*.fasta"))
                    if seed_candidates:
                        pos_fasta = seed_candidates[0]
                        _log(f"Using seed file as positives: {pos_fasta.name}")
                        break
            if pos_fasta is None:
                _log("WARNING: No seed file found in data/, seeds/, or input/; skipping positives.")
        else:
            _log("WARNING: No positive set provided.")

        # --- Negatives ---
        neg_fasta: Path | None = None
        neg_info = input.neg_faa()
        if neg_info and len(neg_info) > 0:
            neg_fasta = Path(neg_info[0]["datapath"])
            _log(f"Negative set: {neg_info[0]['name']} ({os.path.getsize(neg_fasta)} bytes)")
        else:
            _log("WARNING: No negative set provided.")

        try:
            if pos_fasta is not None and pos_fasta.exists():
                _log("Running hmmsearch on positives…")
                pos_sc = _run_hmmsearch_get_scores(hmm, pos_fasta)
                _pos_scores.set(pos_sc)
                _log(f"  → {len(pos_sc)} positive hits scored")
            else:
                _pos_scores.set([])

            if neg_fasta is not None and neg_fasta.exists():
                _log("Running hmmsearch on negatives…")
                neg_sc = _run_hmmsearch_get_scores(hmm, neg_fasta)
                _neg_scores.set(neg_sc)
                _log(f"  → {len(neg_sc)} negative hits scored")
            else:
                _neg_scores.set([])

            _log("=== Calibration complete ===")
        except FileNotFoundError:
            _log("ERROR: hmmsearch not found. Check HMMER installation.")
        except Exception as exc:
            _log(f"ERROR: {exc}")

    @output
    @render.ui
    def score_dist_plot():
        pos_sc = _pos_scores.get()
        neg_sc = _neg_scores.get()
        strict   = input.strict_thresh()
        moderate = input.moderate_thresh()

        if not pos_sc and not neg_sc:
            return ui.tags.p(
                "Run calibration to see score distribution.",
                class_="text-muted text-center py-4",
            )

        return _render_score_dist_plot(
            pos_sc, neg_sc, strict, moderate,
            title="Custom Set Score Distribution",
        )

    @output
    @render.ui
    def threshold_stats():
        pos_sc = _pos_scores.get()
        neg_sc = _neg_scores.get()
        if not pos_sc and not neg_sc:
            return ui.tags.span("")
        return _render_threshold_stats(
            pos_sc, neg_sc,
            input.strict_thresh(),
            input.moderate_thresh(),
        )

    @output
    @render.text
    def calibration_log():
        lines = _log_lines.get()
        return "\n".join(lines) if lines else "Waiting for calibration run…"

    # ===========================================================================
    # SECTION B: Built-in controls
    # ===========================================================================

    _ctrl_report:   reactive.Value[object] = reactive.value(None)
    _ctrl_pos_sc:   reactive.Value[list]   = reactive.value([])
    _ctrl_neg_sc:   reactive.Value[dict]   = reactive.value({})  # name → scores
    _ctrl_log:      reactive.Value[list]   = reactive.value([])

    def _clog(msg: str):
        lines = _ctrl_log.get()
        lines.append(msg)
        _ctrl_log.set(lines[-500:])

    @reactive.effect
    @reactive.event(input.run_controls)
    async def _on_run_controls():
        _ctrl_log.set([])
        _clog("=== Starting built-in controls ===")

        hmm = _hmm_path()
        if hmm is None:
            _clog("ERROR: No HMM profile found. Build HMM in step 3 first.")
            return

        pd_ = _proj_dir()
        if pd_ is None:
            _clog("ERROR: No project directory. Open a project first.")
            return

        mode       = biology_mode() if callable(biology_mode) else biology_mode
        strict     = float(input.ctrl_strict())
        moderate   = float(input.ctrl_moderate())
        cpu        = int(input.ctrl_cpu())
        out_dir    = pd_ / "results" / "controls"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Seed sequences as positive control — check multiple locations
        seed_faa = None
        for seed_dir in ["data", "seeds", "input"]:
            seed_candidates = sorted((pd_ / seed_dir).glob("*.faa")) + sorted((pd_ / seed_dir).glob("*.fasta"))
            if seed_candidates:
                seed_faa = seed_candidates[0]
                break
        if seed_faa is None:
            # Also check project root
            root_candidates = sorted(pd_.glob("*.faa")) + sorted(pd_.glob("*.fasta"))
            seed_faa = root_candidates[0] if root_candidates else None

        _clog(f"Biology mode: {mode}")
        _clog(f"Strict threshold: {strict} bits")
        _clog(f"Moderate threshold: {moderate} bits")

        if seed_faa is None or not Path(seed_faa).exists():
            _clog(f"ERROR: No seed FASTA found in project. Upload sequences in Step 1 first.")
            _clog(f"  Searched: data/, seeds/, input/ under {pd_}")
            return

        _clog(f"Seed file: {seed_faa} ({Path(seed_faa).stat().st_size} bytes)")

        try:
            from pipeline.controls import run_all_controls, available_controls  # type: ignore

            # Show which controls will run
            avail = available_controls(mode=mode, app_dir=_app_dir())
            _clog(f"Controls for mode '{mode}': {len(avail)} sets")
            for c in avail:
                status = "✅ ready" if c.get("available") else "❌ missing"
                _clog(f"  {c['name']} ({c['role']}) — {status}")

            _clog("Running controls pipeline…")
            report = run_all_controls(
                hmm_path=hmm,
                seed_faa=seed_faa,
                out_dir=out_dir,
                mode=mode,
                strict_threshold=strict,
                moderate_threshold=moderate,
                cpu=cpu,
                app_dir=_app_dir(),
            )
            _ctrl_report.set(report)

            # Collect pos/neg scores for the plot
            pos_scores_all: list[float] = []
            neg_scores_dict: dict[str, list[float]] = {}
            for res in report.results:
                if res.get("role") == "positive":
                    pos_scores_all.extend(res.get("scores", []))
                else:
                    neg_scores_dict[res.get("name", "unknown")] = res.get("scores", [])
            _ctrl_pos_sc.set(pos_scores_all)
            _ctrl_neg_sc.set(neg_scores_dict)

            summary = report.summary()
            _clog(f"\n=== Results ===")
            _clog(f"Sensitivity : {summary.get('sensitivity', 0):.1%}")
            _clog(f"Specificity : {summary.get('specificity', 0):.1%}")
            _clog(f"FPR         : {summary.get('false_positive_rate', 0):.1%}")
            _clog(f"Total neg.  : {summary.get('total_negatives', 0)}")
            _clog(f"False pos.  : {summary.get('false_positives', 0)}")
            _clog("=== Controls complete ===")

        except Exception as exc:
            _clog(f"ERROR running controls: {exc}")
            import traceback
            _clog(traceback.format_exc())

    @output
    @render.ui
    def controls_summary_cards():
        report = _ctrl_report.get()
        if report is None:
            return ui.tags.p(
                "Run built-in controls to see results.",
                class_="text-muted py-3",
            )
        summary = report.summary()
        sens    = summary.get("sensitivity", 0)
        spec    = summary.get("specificity", 0)
        fpr     = summary.get("false_positive_rate", 0)
        n_neg   = summary.get("total_negatives", 0)
        n_fp    = summary.get("false_positives", 0)
        n_pos   = summary.get("total_positives", 0)
        n_tp    = summary.get("true_positives", 0)

        def _colour(val, reverse=False):
            good = val >= 0.95 if not reverse else val <= 0.02
            bad  = val < 0.80  if not reverse else val > 0.10
            return "success" if good else ("danger" if bad else "warning")

        return ui.layout_columns(
            stat_card("Sensitivity",   f"{sens:.1%}",  color=_colour(sens)),
            stat_card("Specificity",   f"{spec:.1%}",  color=_colour(spec)),
            stat_card("FPR",           f"{fpr:.2%}",   color=_colour(fpr, reverse=True)),
            stat_card("TP / Pos",      f"{n_tp} / {n_pos}",  color="info"),
            stat_card("FP / Neg",      f"{n_fp} / {n_neg}",  color="info"),
            col_widths=[2, 2, 2, 3, 3],
        )

    @output
    @render.ui
    def controls_detail_table():
        report = _ctrl_report.get()
        if report is None:
            return ui.tags.span("")
        try:
            df = report.to_dataframe()
        except Exception:
            return ui.tags.span("")
        if df.empty:
            return ui.tags.p("No control results available.", class_="text-muted")

        rows = []
        for _, row in df.iterrows():
            role_badge = (
                ui.tags.span("Positive", class_="badge bg-success")
                if row.get("role") == "positive"
                else ui.tags.span("Negative", class_="badge bg-danger")
            )
            n_seqs = row.get("n_sequences", 0)
            n_hits = row.get("n_hits_strict", 0)
            rate   = n_hits / n_seqs if n_seqs > 0 else 0
            rows.append(
                ui.tags.tr(
                    ui.tags.td(row.get("name", "")),
                    ui.tags.td(role_badge),
                    ui.tags.td(str(n_seqs)),
                    ui.tags.td(str(n_hits)),
                    ui.tags.td(f"{rate:.1%}"),
                    ui.tags.td(
                        f"{row.get('min_score', 0):.1f} – {row.get('max_score', 0):.1f}"
                        if n_hits > 0 else "—"
                    ),
                )
            )

        return ui.tags.div(
            ui.tags.h6("Per-Control Results", class_="mt-3 mb-2"),
            ui.tags.table(
                ui.tags.thead(
                    ui.tags.tr(
                        ui.tags.th("Control set"),
                        ui.tags.th("Role"),
                        ui.tags.th("Sequences"),
                        ui.tags.th("Hits (strict)"),
                        ui.tags.th("Hit rate"),
                        ui.tags.th("Score range"),
                    )
                ),
                ui.tags.tbody(*rows),
                class_="table table-sm table-bordered table-hover mt-2",
            ),
        )

    @output
    @render.ui
    def controls_score_dist():
        pos_sc       = _ctrl_pos_sc.get()
        neg_sc_dict  = _ctrl_neg_sc.get()
        strict       = float(input.ctrl_strict())
        moderate     = float(input.ctrl_moderate())

        if not pos_sc and not neg_sc_dict:
            return ui.tags.span("")

        # Flatten all negative scores for the plot
        neg_sc = [s for scores in neg_sc_dict.values() for s in scores]
        return _render_score_dist_plot(
            pos_sc, neg_sc, strict, moderate,
            title="Controls Score Distribution (Positives vs All Negatives)",
        )

    @output
    @render.text
    def controls_log():
        lines = _ctrl_log.get()
        return "\n".join(lines) if lines else "Waiting for controls run…"


# ---------------------------------------------------------------------------
# Shared rendering helpers
# ---------------------------------------------------------------------------

def _render_score_dist_plot(
    pos_sc: list,
    neg_sc: list,
    strict: float,
    moderate: float,
    title: str = "Score Distribution",
) -> ui.TagChild:
    """Return a plotly (or matplotlib fallback) score distribution HTML element."""
    try:
        import plotly.graph_objects as go
        fig = go.Figure()
        if pos_sc:
            fig.add_trace(go.Histogram(
                x=pos_sc, name="Positives",
                marker_color="rgba(40,167,69,0.7)",
                nbinsx=40, opacity=0.75,
            ))
        if neg_sc:
            fig.add_trace(go.Histogram(
                x=neg_sc, name="Negatives",
                marker_color="rgba(220,53,69,0.7)",
                nbinsx=40, opacity=0.75,
            ))
        fig.add_vline(
            x=strict, line_dash="dash", line_color="#0d6efd",
            annotation_text=f"Strict ({strict})",
            annotation_position="top right",
        )
        fig.add_vline(
            x=moderate, line_dash="dot", line_color="#fd7e14",
            annotation_text=f"Moderate ({moderate})",
            annotation_position="top left",
        )
        fig.update_layout(
            title_text=title,
            barmode="overlay",
            xaxis_title="Bit Score",
            yaxis_title="Count",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=20, t=60, b=40),
            height=350,
            template="plotly_white",
        )
        _html = fig.to_html(full_html=True, include_plotlyjs="cdn")
        _esc = _html.replace("&", "&amp;").replace('"', "&quot;")
        return ui.HTML(f'<iframe srcdoc="{_esc}" style="width:100%; height:380px; border:none;" sandbox="allow-scripts allow-same-origin"></iframe>')
    except ImportError:
        import io, base64
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 3.5))
        if pos_sc:
            ax.hist(pos_sc, bins=40, alpha=0.7, color="#28a745", label="Positives")
        if neg_sc:
            ax.hist(neg_sc, bins=40, alpha=0.7, color="#dc3545", label="Negatives")
        ax.axvline(strict,   color="#0d6efd", linestyle="--", label=f"Strict ({strict})")
        ax.axvline(moderate, color="#fd7e14", linestyle=":",  label=f"Moderate ({moderate})")
        ax.set_xlabel("Bit Score")
        ax.set_ylabel("Count")
        ax.set_title(title)
        ax.legend()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return ui.HTML(f'<img src="data:image/png;base64,{b64}" style="width:100%">')


def _render_threshold_stats(
    pos_sc: list,
    neg_sc: list,
    strict: float,
    moderate: float,
) -> ui.TagChild:
    def _compute(thresh):
        tp = sum(1 for s in pos_sc if s >= thresh)
        fn = sum(1 for s in pos_sc if s < thresh)
        fp = sum(1 for s in neg_sc if s >= thresh)
        tn = sum(1 for s in neg_sc if s < thresh)
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        fdr = fp / (fp + tp) if (fp + tp) > 0 else 0.0
        return tp, fp, fn, tn, sensitivity, specificity, fdr

    rows = []
    for thresh_val, label in [(strict, "Strict"), (moderate, "Moderate")]:
        tp, fp, fn, tn, sens, spec, fdr = _compute(thresh_val)
        rows.append(
            ui.tags.tr(
                ui.tags.td(ui.tags.strong(label)),
                ui.tags.td(f"{thresh_val} bits"),
                ui.tags.td(str(tp)),
                ui.tags.td(str(fp)),
                ui.tags.td(str(fn)),
                ui.tags.td(str(tn)),
                ui.tags.td(f"{sens:.1%}"),
                ui.tags.td(f"{spec:.1%}"),
                ui.tags.td(f"{fdr:.1%}", class_="text-danger" if fdr > 0.1 else ""),
            )
        )

    return ui.tags.div(
        ui.tags.table(
            ui.tags.thead(
                ui.tags.tr(
                    ui.tags.th("Threshold"),
                    ui.tags.th("Bits"),
                    ui.tags.th("TP"),
                    ui.tags.th("FP"),
                    ui.tags.th("FN"),
                    ui.tags.th("TN"),
                    ui.tags.th("Sensitivity"),
                    ui.tags.th("Specificity"),
                    ui.tags.th("FDR"),
                )
            ),
            ui.tags.tbody(*rows),
            class_="table table-sm table-bordered",
        ),
        class_="mt-2",
    )
