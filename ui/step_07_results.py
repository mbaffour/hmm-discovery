"""
ui/step_07_results.py — Results Table Panel (Step 7).

Main interactive hits table with filtering by tier, E-value, bit score,
database, and QC status.  Accompanied by score histogram, database bar chart,
and confidence-tier pie.
"""
from __future__ import annotations

from pathlib import Path

from shiny import ui

from .components import (
    step_guidance,
    section_header,
    stat_card,
    tier_badge,
    qc_flag_badges,
)


# ---------------------------------------------------------------------------
# Panel UI
# ---------------------------------------------------------------------------

def panel_ui() -> ui.TagChild:
    return ui.nav_panel(
        "7. Results",
        ui.tags.div(
            step_guidance(
                "Browse and filter all hits across all searched databases.",
                [
                "Interactive sortable table with all hits",
                "Bit score distribution histogram",
                "Hits per database bar chart",
                "Confidence tier pie chart",
                ],
                "High-confidence hits have bit score ≥ 45 and HMM coverage ≥ 60%. Putative hits are worth manual review.",
            ),
            ui.tags.p(
                "Browse all HMM hits across searched databases. "
                "Use the filters below to focus on specific confidence tiers or score ranges.",
                class_="text-muted mb-3",
            ),

            # ---- Summary stat row -------------------------------------------
            section_header("Summary"),
            ui.layout_columns(
                ui.output_ui("stat_total"),
                ui.output_ui("stat_high"),
                ui.output_ui("stat_putative"),
                ui.output_ui("stat_divergent"),
                ui.output_ui("stat_likely_fp"),
                ui.output_ui("stat_databases"),
                col_widths=[2, 2, 2, 2, 2, 2],
            ),

            # ---- Filters accordion ------------------------------------------
            ui.tags.div(
                ui.accordion(
                    ui.accordion_panel(
                        "🔍 Filters",
                        ui.layout_columns(
                            ui.tags.div(
                                ui.tags.label("Confidence Tier", class_="form-label fw-semibold"),
                                ui.input_checkbox_group(
                                    "filter_tier",
                                    None,
                                    choices={
                                        "high_confidence": "High Confidence",
                                        "putative": "Putative",
                                        "divergent": "Divergent",
                                        "likely_fp": "Likely FP",
                                    },
                                    selected=["high_confidence", "putative", "divergent", "likely_fp"],
                                    inline=False,
                                ),
                            ),
                            ui.tags.div(
                                ui.input_text(
                                    "filter_evalue",
                                    "Max E-value",
                                    value="1e-3",
                                    placeholder="e.g. 1e-5",
                                ),
                                ui.input_slider(
                                    "filter_bitscore",
                                    "Min bit score",
                                    min=0, max=500, value=0, step=5,
                                ),
                            ),
                            ui.tags.div(
                                ui.input_select(
                                    "filter_database",
                                    "Database",
                                    choices={"__all__": "All databases"},
                                ),
                                ui.input_switch(
                                    "filter_qc_clean",
                                    "Show only QC-clean hits",
                                    value=False,
                                ),
                            ),
                            col_widths=[4, 4, 4],
                        ),
                    ),
                    id="results_filter_accordion",
                    open=False,
                ),
                class_="mb-3",
            ),

            # ---- Main hits table --------------------------------------------
            ui.card(
                ui.card_header(
                    ui.tags.div(
                        ui.tags.strong("Hits Table"),
                        ui.output_ui("hits_table_count"),
                        class_="d-flex align-items-center gap-2",
                    )
                ),
                ui.output_data_frame("hits_table"),
                class_="mb-3",
            ),

            # ---- Charts row -------------------------------------------------
            ui.layout_columns(
                ui.card(
                    ui.card_header(ui.tags.strong("Bit Score Distribution")),
                    ui.output_ui("score_hist"),
                ),
                ui.card(
                    ui.card_header(ui.tags.strong("Hits per Database")),
                    ui.output_ui("db_bar"),
                ),
                col_widths=[6, 6],
            ),

            # ---- Tier pie ---------------------------------------------------
            ui.card(
                ui.card_header(ui.tags.strong("Confidence Tier Distribution")),
                ui.output_ui("tier_pie"),
                class_="mt-3",
            ),

            class_="container-fluid px-0",
        ),
    )


# ---------------------------------------------------------------------------
# Server outputs
# ---------------------------------------------------------------------------

def _plotly_iframe(fig, height: str = "300px"):
    """Render a Plotly figure inside a sandboxed iframe so scripts execute."""
    from shiny import ui as _ui
    html = fig.to_html(full_html=True, include_plotlyjs="cdn")
    escaped = html.replace("&", "&amp;").replace('"', "&quot;")
    return _ui.HTML(
        f'<iframe srcdoc="{escaped}" style="width:100%; height:{height}; border:none;" '
        f'sandbox="allow-scripts allow-same-origin"></iframe>'
    )


def register_outputs(input, output, render, reactive, session, **kwargs):
    proj_dir_rv = kwargs.get("proj_dir_rv", None)
    state = kwargs.get("state", None)

    TIER_COLORS = {
        "high_confidence": "#28a745",
        "putative": "#0d6efd",
        "divergent": "#fd7e14",
        "likely_fp": "#dc3545",
    }

    def _proj_dir() -> Path | None:
        if proj_dir_rv is not None:
            v = proj_dir_rv.get()
            return Path(v) if v else None
        return None

    @reactive.calc
    def _raw_hits_df():
        import pandas as pd

        pd_ = _proj_dir()
        if pd_ is None:
            return pd.DataFrame()
        hits_file = pd_ / "results" / "hits_main.tsv"
        if not hits_file.exists():
            # Try alternate locations
            for alt in [pd_ / "hits_main.tsv", pd_ / "output" / "hits_main.tsv"]:
                if alt.exists():
                    hits_file = alt
                    break
            else:
                return pd.DataFrame()
        try:
            df = pd.read_csv(hits_file, sep="\t")
            if not df.empty and state is not None:
                try:
                    state.mark_complete("classify", {"hits_count": len(df)})
                except Exception:
                    pass
            return df
        except Exception:
            return pd.DataFrame()

    @reactive.calc
    def _filtered_df():
        import pandas as pd

        df = _raw_hits_df()
        if df.empty:
            return df

        # Tier filter
        selected_tiers = list(input.filter_tier())
        if selected_tiers and "confidence_tier" in df.columns:
            df = df[df["confidence_tier"].isin(selected_tiers)]

        # E-value filter
        evalue_str = input.filter_evalue().strip()
        evalue_col = "evalue" if "evalue" in df.columns else "e_value" if "e_value" in df.columns else None
        if evalue_str and evalue_col:
            try:
                ev = float(evalue_str)
                df = df[df[evalue_col] <= ev]
            except ValueError:
                pass

        # Bit score filter
        min_bs = input.filter_bitscore()
        if min_bs > 0 and "bit_score" in df.columns:
            df = df[df["bit_score"] >= min_bs]

        # Database filter
        db_sel = input.filter_database()
        if db_sel and db_sel != "__all__" and "database_source" in df.columns:
            df = df[df["database_source"] == db_sel]

        # QC clean filter
        if input.filter_qc_clean() and "qc_flags" in df.columns:
            df = df[df["qc_flags"].isna() | (df["qc_flags"] == "")]

        return df

    # Update database choices when raw data loads
    @reactive.effect
    def _update_db_choices():
        df = _raw_hits_df()
        if df.empty or "database_source" not in df.columns:
            return
        dbs = sorted(df["database_source"].dropna().unique().tolist())
        choices = {"__all__": "All databases"}
        choices.update({d: d for d in dbs})
        ui.update_select("filter_database", choices=choices, session=session)

    # ---- Stat cards ---------------------------------------------------------
    def _make_stat_output(output_id, tier_key=None, label="", color="primary", icon=""):
        @output(id=output_id)
        @render.ui
        def _stat():
            df = _filtered_df()
            if tier_key is None:
                val = len(df)
            elif tier_key == "__databases__":
                val = df["database_source"].nunique() if "database_source" in df.columns else 0
            else:
                val = (df["confidence_tier"] == tier_key).sum() if "confidence_tier" in df.columns else 0
            return stat_card(label, val, color=color, icon=icon)

    _make_stat_output("stat_total", None, "Total Hits", "secondary", "🔎")
    _make_stat_output("stat_high", "high_confidence", "High Confidence", "success", "✅")
    _make_stat_output("stat_putative", "putative", "Putative", "primary", "🔵")
    _make_stat_output("stat_divergent", "divergent", "Divergent", "warning", "🟡")
    _make_stat_output("stat_likely_fp", "likely_fp", "Likely FP", "danger", "❌")
    _make_stat_output("stat_databases", "__databases__", "Databases", "info", "🗄️")

    # ---- hits_table_count ---------------------------------------------------
    @output
    @render.ui
    def hits_table_count():
        n = len(_filtered_df())
        return ui.tags.span(f"({n} rows)", class_="text-muted small")

    # ---- hits_table ---------------------------------------------------------
    @output
    @render.data_frame
    def hits_table():
        import pandas as pd

        df = _filtered_df()
        if df.empty:
            return render.DataGrid(
                pd.DataFrame(columns=[
                    "protein_id", "confidence_tier", "bit_score",
                    "hmm_coverage_pct", "database_source", "description",
                ]),
                height="400px",
            )

        # Define preferred column order (keep columns that exist)
        priority_cols = [
            "protein_id", "confidence_tier", "bit_score", "e_value",
            "hmm_coverage_pct", "database_source", "description",
        ]
        other_cols = [c for c in df.columns if c not in priority_cols]
        ordered_cols = [c for c in priority_cols if c in df.columns] + other_cols
        df = df[ordered_cols]

        return render.DataGrid(
            df,
            selection_mode="rows",
            height="450px",
            filters=True,
        )

    # ---- score_hist ---------------------------------------------------------
    @output
    @render.ui
    def score_hist():
        df = _filtered_df()
        if df.empty or "bit_score" not in df.columns:
            return ui.tags.p("No data.", class_="text-muted text-center py-3")
        try:
            import plotly.graph_objects as go

            fig = go.Figure()
            if "confidence_tier" in df.columns:
                for tier, grp in df.groupby("confidence_tier"):
                    fig.add_trace(go.Histogram(
                        x=grp["bit_score"],
                        name=tier.replace("_", " ").title(),
                        marker_color=TIER_COLORS.get(tier, "#6c757d"),
                        opacity=0.75,
                        nbinsx=40,
                    ))
            else:
                fig.add_trace(go.Histogram(x=df["bit_score"], nbinsx=40, name="All"))

            fig.update_layout(
                barmode="overlay",
                xaxis_title="Bit Score",
                yaxis_title="Count",
                height=280,
                margin=dict(l=40, r=10, t=20, b=40),
                template="plotly_white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            return _plotly_iframe(fig)
        except ImportError:
            return ui.tags.p("plotly not installed.", class_="text-warning small")

    # ---- db_bar -------------------------------------------------------------
    @output
    @render.ui
    def db_bar():
        df = _filtered_df()
        if df.empty or "database_source" not in df.columns:
            return ui.tags.p("No data.", class_="text-muted text-center py-3")
        try:
            import plotly.graph_objects as go

            counts = df["database_source"].value_counts()
            fig = go.Figure(go.Bar(
                x=counts.index.tolist(),
                y=counts.values.tolist(),
                marker_color="#0d6efd",
            ))
            fig.update_layout(
                xaxis_title="Database",
                yaxis_title="Hits",
                height=280,
                margin=dict(l=40, r=10, t=20, b=80),
                template="plotly_white",
            )
            return _plotly_iframe(fig)
        except ImportError:
            return ui.tags.p("plotly not installed.", class_="text-warning small")

    # ---- tier_pie -----------------------------------------------------------
    @output
    @render.ui
    def tier_pie():
        df = _filtered_df()
        if df.empty or "confidence_tier" not in df.columns:
            return ui.tags.p("No data.", class_="text-muted text-center py-3")
        try:
            import plotly.graph_objects as go

            counts = df["confidence_tier"].value_counts()
            labels = [t.replace("_", " ").title() for t in counts.index]
            colors = [TIER_COLORS.get(t, "#6c757d") for t in counts.index]

            fig = go.Figure(go.Pie(
                labels=labels,
                values=counts.values.tolist(),
                marker=dict(colors=colors),
                hole=0.35,
            ))
            fig.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=20, b=20),
                template="plotly_white",
            )
            return _plotly_iframe(fig)
        except ImportError:
            return ui.tags.p("plotly not installed.", class_="text-warning small")
