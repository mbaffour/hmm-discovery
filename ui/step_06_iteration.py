"""
ui/step_06_iteration.py — Iterative Refinement Panel (Step 6).

Shows candidate diff table, convergence plot, and controls for running
the next alignment→HMM-build→search iteration.
"""
from __future__ import annotations

from pathlib import Path

from shiny import ui

from .components import info_tooltip, step_guidance, log_panel, section_header, stat_card, step_card


# ---------------------------------------------------------------------------
# Panel UI
# ---------------------------------------------------------------------------

def panel_ui() -> ui.TagChild:
    return ui.nav_panel(
        "6. Iterative Refinement",
        ui.tags.div(
            step_guidance(
                "Expand the seed set with high-confidence hits, rebuild the HMM, and repeat until the hit count stabilises.",
                [
                "Updated HMM profile",
                "New search results against the same databases",
                "Iteration history table tracking hit count and profile length per round",
                ],
                "Stop iterating when the hit count changes by < 5% between rounds. Too many iterations can broaden the family definition.",
            ),
            ui.tags.p(
                "Each iteration re-aligns accepted candidates, rebuilds the HMM, and re-searches databases. "
                "Continue until the hit count and profile length converge.",
                class_="text-muted mb-3",
            ),

            # ---- Status cards --------------------------------------------------
            section_header("Iteration Status"),
            ui.layout_columns(
                ui.output_ui("iter_status_cards"),
                col_widths=[12],
            ),

            # ---- Remote homology toggle ----------------------------------------
            ui.card(
                ui.card_header(ui.tags.strong("Search Settings")),
                ui.layout_columns(
                    ui.tags.div(
                        ui.input_switch(
                            "remote_homology",
                            ui.span("Remote homology mode (sensitive search)", info_tooltip(
                                "Lowers the E-value threshold to 1e-2 and clusters weak "
                                "hits by sequence similarity. Finds distantly related "
                                "sequences but may introduce more false positives — use "
                                "calibration thresholds to filter."
                            )),
                            value=False,
                        ),
                    ),
                    col_widths=[12],
                ),
                class_="mb-3",
            ),

            # ---- Candidate diff table ------------------------------------------
            ui.card(
                ui.card_header(
                    ui.tags.div(
                        ui.tags.strong("Candidate Diff"),
                        ui.tags.small(
                            " — Sequences that would be added in the next iteration",
                            class_="text-muted",
                        ),
                        class_="d-flex align-items-center gap-1",
                    )
                ),
                ui.output_data_frame("candidate_diff"),
                ui.tags.div(
                    ui.input_action_button(
                        "accept_selected",
                        "✔ Accept Selected & Run Iteration",
                        class_="btn btn-primary me-2",
                    ),
                    ui.input_action_button(
                        "accept_all",
                        "✔✔ Accept All & Run Iteration",
                        class_="btn btn-outline-primary",
                    ),
                    class_="mt-2 d-flex gap-2",
                ),
                class_="mb-3",
            ),

            # ---- Convergence plot ----------------------------------------------
            ui.card(
                ui.card_header(ui.tags.strong("Convergence")),
                ui.output_ui("convergence_plot"),
                class_="mb-3",
            ),

            # ---- Iteration history accordion -----------------------------------
            section_header("Iteration History"),
            ui.output_ui("iteration_history_accordion"),

            # ---- Log panel -----------------------------------------------------
            section_header("Iteration Log"),
            log_panel("iteration_log"),

            class_="container-fluid px-0",
        ),
    )


# ---------------------------------------------------------------------------
# Server outputs
# ---------------------------------------------------------------------------

def register_outputs(input, output, render, reactive, session, **kwargs):
    state = kwargs.get("state", {})
    proj_dir_rv = kwargs.get("proj_dir_rv", None)
    iterative = kwargs.get("iterative", None)  # iterative module/object injected by app.py
    runner_dict = kwargs.get("runner_dict", {})

    _log_lines: reactive.Value[list] = reactive.value([])

    def _log(msg: str):
        lines = _log_lines.get()
        lines.append(msg)
        _log_lines.set(lines[-500:])

    def _proj_dir() -> Path | None:
        if proj_dir_rv is not None:
            v = proj_dir_rv.get()
            return Path(v) if v else None
        return None

    def _iteration_meta() -> dict:
        """Read iteration metadata from project dir."""
        pd = _proj_dir()
        if pd is None:
            return {}
        meta_file = pd / "hmm" / "iteration_meta.json"
        if meta_file.exists():
            import json
            try:
                return json.loads(meta_file.read_text())
            except Exception:
                pass
        return {}

    # ---- iter_status_cards -----------------------------------------------------
    @output
    @render.ui
    def iter_status_cards():
        meta = _iteration_meta()
        n_iter = meta.get("iteration", 0)
        hit_count = meta.get("hit_count", "—")
        profile_leng = meta.get("profile_leng", "—")
        return ui.layout_columns(
            stat_card("Current Iteration", n_iter, color="primary", icon="🔁"),
            stat_card("Hit Count", hit_count, color="success", icon="🎯"),
            stat_card("Profile LENG", profile_leng, color="info", icon="📏"),
            col_widths=[4, 4, 4],
        )

    # ---- candidate_diff --------------------------------------------------------
    @output
    @render.data_frame
    def candidate_diff():
        import pandas as pd

        pd2 = _proj_dir()

        # First try reading pre-computed candidates from disk (preferred — no side effects)
        if pd2 is not None:
            cand_file = pd2 / "hmm" / "iteration_candidates.tsv"
            if cand_file.exists():
                try:
                    df = pd.read_csv(cand_file, sep="\t")
                    return render.DataGrid(df, selection_mode="rows", height="300px")
                except Exception:
                    pass

        # Fallback: compute live from hits_main.tsv via the iterative module
        if iterative is not None and hasattr(iterative, "iteration_candidates") and pd2 is not None:
            try:
                hits_file = pd2 / "results" / "hits_main.tsv"
                seeds_faa = pd2 / "data" / "seeds.faa"
                if hits_file.exists() and seeds_faa.exists():
                    hits_df = pd.read_csv(hits_file, sep="\t")
                    df = iterative.iteration_candidates(hits_df, seeds_faa, 45.0)
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        return render.DataGrid(df, selection_mode="rows", height="300px")
            except Exception:
                pass  # silent — no reactive mutations inside render

        return render.DataGrid(
            pd.DataFrame(columns=["protein_id", "bit_score", "evalue", "description"]),
            height="200px",
        )

    # ---- Accept All button -----------------------------------------------------
    @reactive.effect
    @reactive.event(input.accept_all)
    async def _on_accept_all():
        _log("Accepting all candidates…")
        pd_ = _proj_dir()
        if pd_ is None:
            _log("ERROR: Project dir not set.")
            return
        cand_file = pd_ / "hmm" / "iteration_candidates.tsv"
        if iterative is not None and hasattr(iterative, "append_to_seeds"):
            try:
                import pandas as _pd
                if cand_file.exists():
                    cand_df = _pd.read_csv(cand_file, sep="\t")
                    all_ids = list(cand_df["protein_id"]) if "protein_id" in cand_df.columns else []
                    seeds_faa = pd_ / "data" / "seeds.faa"
                    cands_faa = pd_ / "hmm" / "iteration_candidates.faa"
                    if seeds_faa.exists() and cands_faa.exists():
                        iterative.append_to_seeds(seeds_faa, cands_faa, all_ids, seeds_faa)
                        _log(f"All {len(all_ids)} candidates appended to seed set.")
                    else:
                        _log("WARNING: seeds.faa or iteration_candidates.faa not found.")
            except Exception as exc:
                _log(f"ERROR: {exc}")
                return
        else:
            _log("WARNING: iterative module not available; using disk-based workflow.")
            if not cand_file.exists():
                _log("No candidates file found.")
                return
        await _run_iteration_pipeline()

    # ---- Accept Selected button ------------------------------------------------
    @reactive.effect
    @reactive.event(input.accept_selected)
    async def _on_accept_selected():
        selected_rows = input.candidate_diff_selected_rows() if hasattr(input, "candidate_diff_selected_rows") else []
        _log(f"Accepting {len(selected_rows)} selected candidates…")
        pd_ = _proj_dir()
        if iterative is not None and hasattr(iterative, "append_to_seeds") and pd_ is not None:
            try:
                import pandas as _pd
                cand_file = pd_ / "hmm" / "iteration_candidates.tsv"
                if cand_file.exists():
                    cand_df = _pd.read_csv(cand_file, sep="\t")
                    all_ids = list(cand_df["protein_id"]) if "protein_id" in cand_df.columns else []
                    selected_ids = [all_ids[i] for i in selected_rows if i < len(all_ids)]
                    seeds_faa = pd_ / "data" / "seeds.faa"
                    cands_faa = pd_ / "hmm" / "iteration_candidates.faa"
                    if seeds_faa.exists() and cands_faa.exists():
                        iterative.append_to_seeds(seeds_faa, cands_faa, selected_ids, seeds_faa)
                        _log(f"{len(selected_ids)} candidates appended.")
                    else:
                        _log("WARNING: seeds.faa or iteration_candidates.faa not found.")
            except Exception as exc:
                _log(f"ERROR: {exc}")
                return
        await _run_iteration_pipeline()

    async def _run_iteration_pipeline():
        import asyncio, subprocess

        pd_ = _proj_dir()
        if pd_ is None:
            _log("ERROR: Project directory not set.")
            return

        remote_mode = input.remote_homology()
        _log(f"Running iteration (remote_homology={remote_mode})…")

        # Run iteration inline using the pipeline modules (no external script needed)
        try:
            from pipeline import alignment as _aln, hmm_builder as _hmm_b, searcher as _srch
            import shutil as _shutil

            seeds_faa  = pd_ / "data" / "seeds.faa"
            # Fallback seed locations
            if not seeds_faa.exists():
                for cand in [pd_ / "input" / "seed.faa", pd_ / "input" / "seeds.faa"]:
                    if cand.exists():
                        seeds_faa = cand
                        break
            if not seeds_faa.exists():
                _log("ERROR: seeds.faa not found — upload input sequences in Step 1 first.")
                return

            aln_dir = pd_ / "alignments"
            hmm_dir = pd_ / "hmm"
            hmm_dir.mkdir(parents=True, exist_ok=True)

            _log("Re-aligning seed sequences with MAFFT…")
            aln_raw = _aln.run_mafft(seeds_faa, aln_dir / "iter_aligned.faa", cpu=4)
            if not aln_raw or not aln_raw.exists():
                _log("ERROR: MAFFT alignment failed."); return

            aln_trimmed = _aln.run_trimal(aln_raw, aln_dir / "iter_aligned.trimmed.faa")
            if not aln_trimmed or not aln_trimmed.exists():
                _log("WARNING: trimAl failed — using raw alignment.")
                aln_trimmed = aln_raw

            _log("Rebuilding profile HMM with hmmbuild…")
            hmm_path = hmm_dir / "iter_profile.hmm"
            info = _hmm_b.run_hmmbuild(aln_trimmed, hmm_path, hmm_name="iter_profile")
            if not info:
                _log("ERROR: hmmbuild failed."); return
            _log(f"  → LENG={info['leng']}, NSEQ={info['nseq']}")

            _log("Re-searching against seed set with hmmsearch…")
            sr = _srch.run_hmmsearch_protein(
                hmm_path=hmm_path, db_faa=seeds_faa,
                out_dir=pd_ / "search_results" / "iteration",
                db_name="iter_seeds", evalue=1e-5,
            )
            _log(f"  → {sr['hit_count']} hits ({sr['strict_count']} strict ≥45 bits)")
            _log("Iteration complete.")

        except Exception as exc:
            import traceback as _tb
            _log(f"ERROR during iteration: {exc}")
            _log(_tb.format_exc()[:400])

    # ---- convergence_plot ------------------------------------------------------
    @output
    @render.ui
    def convergence_plot():
        conv_data: list[dict] = []

        if iterative is not None and hasattr(iterative, "convergence_data"):
            try:
                import json as _json
                pd_tmp = _proj_dir()
                if pd_tmp is not None:
                    hist_path = pd_tmp / "hmm" / "convergence.json"
                    history = _json.loads(hist_path.read_text()) if hist_path.exists() else []
                    result = iterative.convergence_data(history)
                    # convergence_data returns a dict of lists; convert to list of dicts
                    iters = result.get("iterations", [])
                    conv_data = [
                        {
                            "iteration": iters[i],
                            "hit_count": result["hit_counts"][i],
                            "profile_leng": result["leng_values"][i],
                        }
                        for i in range(len(iters))
                    ]
            except Exception:
                pass

        if not conv_data:
            pd_ = _proj_dir()
            if pd_ is not None:
                import json
                conv_file = pd_ / "hmm" / "convergence.json"
                if conv_file.exists():
                    try:
                        conv_data = json.loads(conv_file.read_text())
                    except Exception:
                        pass

        if not conv_data:
            return ui.tags.p("No convergence data yet.", class_="text-muted text-center py-3")

        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots

            iters = [d.get("iteration", i) for i, d in enumerate(conv_data)]
            hits = [d.get("hit_count", 0) for d in conv_data]
            lengs = [d.get("profile_leng", 0) for d in conv_data]

            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(
                go.Scatter(x=iters, y=hits, name="Hit Count",
                           mode="lines+markers", line=dict(color="#0d6efd")),
                secondary_y=False,
            )
            fig.add_trace(
                go.Scatter(x=iters, y=lengs, name="Profile LENG",
                           mode="lines+markers", line=dict(color="#fd7e14", dash="dash")),
                secondary_y=True,
            )
            fig.update_xaxes(title_text="Iteration", dtick=1)
            fig.update_yaxes(title_text="Hit Count", secondary_y=False)
            fig.update_yaxes(title_text="Profile LENG", secondary_y=True)
            fig.update_layout(
                height=300,
                margin=dict(l=50, r=50, t=30, b=40),
                template="plotly_white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            _html = fig.to_html(full_html=True, include_plotlyjs="cdn")
            _esc = _html.replace("&", "&amp;").replace('"', "&quot;")
            return ui.HTML(f'<iframe srcdoc="{_esc}" style="width:100%; height:340px; border:none;" sandbox="allow-scripts allow-same-origin"></iframe>')
        except ImportError:
            return ui.tags.p("plotly not installed; cannot render convergence plot.", class_="text-warning")

    # ---- iteration_history_accordion -------------------------------------------
    @output
    @render.ui
    def iteration_history_accordion():
        pd_ = _proj_dir()
        if pd_ is None:
            return ui.tags.span("")

        import json
        hist_file = pd_ / "hmm" / "convergence.json"
        if not hist_file.exists():
            return ui.tags.p("No iteration history.", class_="text-muted small")

        try:
            history = json.loads(hist_file.read_text())
        except Exception:
            return ui.tags.p("Could not parse iteration history.", class_="text-muted small")

        panels = []
        for entry in reversed(history):
            n = entry.get("iteration", "?")
            panels.append(
                ui.accordion_panel(
                    f"Iteration {n}",
                    ui.layout_columns(
                        stat_card("Hits", entry.get("hit_count", "—"), "primary"),
                        stat_card("Profile LENG", entry.get("profile_leng", "—"), "info"),
                        stat_card("Seeds", entry.get("seed_count", "—"), "success"),
                        col_widths=[4, 4, 4],
                    ),
                    ui.tags.small(
                        entry.get("timestamp", ""),
                        class_="text-muted d-block mt-1",
                    ),
                )
            )

        if not panels:
            return ui.tags.p("No history entries.", class_="text-muted small")

        return ui.accordion(*panels, id="iter_hist_accordion", open=False)

    # ---- iteration_log ---------------------------------------------------------
    @output
    @render.text
    def iteration_log():
        lines = _log_lines.get()
        # Merge runner output only when the runner has actually started/completed
        runner = runner_dict.get("iteration")
        runner_output = ""
        if runner is not None and runner.returncode.get() is not None:
            runner_output = runner.get_log()
        combined = "\n".join(lines)
        if runner_output:
            combined = (combined + "\n" + runner_output).strip()
        return combined if combined else "Waiting for iteration run…"
