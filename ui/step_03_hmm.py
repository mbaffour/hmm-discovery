"""
ui/step_03_hmm.py — Build Profile HMM Panel (Step 3).

Runs hmmbuild on the trimmed MSA, then self-searches the seed sequences to
confirm recovery. Renders an interactive HMM logo plot via matplotlib.
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
        "3. Build Profile HMM",
        ui.tags.div(
            step_guidance(
                "Build a statistical profile of your protein family from the alignment — this is the core model used for all searches.",
                [
                ".hmm profile file (saved in hmm/)",
                "Profile statistics: length, sequences, checksum",
                "HMM position logo showing information content per column",
                ],
                "The LENG value should roughly match your protein length. A self-test (hmmsearch against seeds) should recover 100% of inputs.",
            ),
            section_header("HMM Build Settings"),

            ui.layout_columns(
                ui.tags.div(
                    ui.input_text(
                        "hmm_name",
                        ui.span("HMM name", info_tooltip(
                            "Sets the NAME field in the .hmm file. Use a short, "
                            "descriptive slug (e.g. phage_tail_fiber). This name appears in "
                            "hmmsearch output and is how databases label your profile."
                        )),
                        value="novel_gene",
                        placeholder="e.g. phage_tail_fiber",
                    ),
                    ui.tags.small(
                        "Used as the NAME field in the .hmm file.",
                        class_="text-muted",
                    ),
                ),
                ui.tags.div(
                    ui.output_ui("hmmbuild_tool_badge"),
                ),
                col_widths=[6, 6],
            ),

            # ---- run button --------------------------------------------------
            ui.tags.div(
                ui.input_action_button(
                    "run_hmmbuild",
                    "▶ Build HMM",
                    class_="btn btn-primary mt-2",
                ),
                ui.tags.span(" ", class_="me-1"),
                ui.output_ui("hmm_run_status"),
                class_="d-flex align-items-center mt-2 mb-3",
            ),

            # ---- build stats -------------------------------------------------
            ui.output_ui("hmm_stats"),

            # ---- self-search recovery ----------------------------------------
            ui.output_ui("self_search_stats"),

            # ---- HMM logo ----------------------------------------------------
            section_header("HMM Logo", "Information content per position (bits)"),
            ui.output_plot("hmm_logo_plot", height="300px"),

            # ---- log ---------------------------------------------------------
            section_header("Run Log"),
            log_panel("hmm_log", height="200px"),

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
    hmm_builder = kwargs.get("hmm_builder", None)

    _hmm_meta = reactive.value(None)         # dict from hmm_builder.parse_hmm_file()
    _self_search = reactive.value(None)       # dict from hmm_builder.self_search_recovery()
    _logo_data = reactive.value(None)         # list[dict] from hmm_builder.logo_data()
    _hmm_run_status = reactive.value("")     # "" | "complete" | "ERROR: ..."

    # ---- tool badge ----------------------------------------------------------
    @output
    @render.ui
    def hmmbuild_tool_badge():
        from pipeline.utils import find_tool
        return ui.tags.div(
            tool_badge("hmmbuild",  "HMMER hmmbuild",  find_tool("hmmbuild")  is not None),
            tool_badge("hmmsearch", "HMMER hmmsearch", find_tool("hmmsearch") is not None),
        )

    # ---- run status ----------------------------------------------------------
    @output
    @render.ui
    def hmm_run_status():
        runner = runner_dict.get("hmm")
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

    # ---- run hmmbuild event --------------------------------------------------
    @reactive.effect
    @reactive.event(input.run_hmmbuild)
    async def _on_run_hmmbuild():
        import traceback as _tb, sys as _sys
        try:
            await _run_hmmbuild_inner()
        except Exception as _exc:
            _tb.print_exc(file=_sys.stderr)
            _hmm_run_status.set(f"ERROR: {_exc}")

    async def _run_hmmbuild_inner():
        import asyncio as _asyncio
        from pathlib import Path as _Path

        proj_dir = proj_dir_rv.get() if proj_dir_rv is not None else None
        # Fall back to reading from state file on disk if reactive value is default cwd
        if proj_dir is None or not (_Path(proj_dir) / "alignments").exists():
            if state is not None:
                ip = state.get_project("input_path", "")
                if ip:
                    # input_path is e.g. /Users/.../project_name/seeds — go up one level
                    candidate = _Path(ip)
                    proj_dir = str(candidate.parent) if (candidate.parent / "alignments").exists() else str(candidate)
            if proj_dir is None:
                return

        proj = _Path(proj_dir)
        aln_dir = proj / "alignments"

        # Prefer trimmed alignment; fall back to raw mafft or any .faa in alignments/
        candidates = [
            aln_dir / "seed.mafft.trimmed.faa",
            aln_dir / "seed_nr90.mafft.trimmed.faa",
            aln_dir / "seed.mafft.faa",
            aln_dir / "seed_nr90.mafft.faa",
        ]
        aln_file = next((f for f in candidates if f.exists()), None)
        if aln_file is None:
            # Try any .faa in alignments/
            hits = list(aln_dir.glob("*.faa")) if aln_dir.exists() else []
            aln_file = hits[0] if hits else None
        if aln_file is None:
            _hmm_run_status.set("No alignment file found — run Step 2 first.")
            return

        try:
            hmm_name = (input.hmm_name() or "protein_family").strip() or "protein_family"
        except Exception:
            hmm_name = "protein_family"

        hmm_out = proj / "hmm" / f"{hmm_name}.hmm"
        hmm_out.parent.mkdir(parents=True, exist_ok=True)

        cmd = ["-n", hmm_name, str(hmm_out), str(aln_file)]

        runner = runner_dict.get("hmm")
        if runner is None:
            return
        runner.start(["hmmbuild"] + cmd, cwd=proj)

        # Wait for hmmbuild to finish (fast — typically < 1 s)
        for _ in range(60):
            await _asyncio.sleep(0.5)
            if not runner.is_running.get():
                break

        # Parse results once file is written
        if hmm_out.exists():
            _meta: dict = {}
            if hmm_builder is not None:
                try:
                    _meta = hmm_builder.parse_hmm_file(hmm_out)
                    _hmm_meta.set(_meta)
                except Exception:
                    pass
                try:
                    logo = hmm_builder.logo_data(hmm_out)
                    _logo_data.set(logo)
                except Exception:
                    pass
                # Self-search recovery
                try:
                    seeds_faa = proj / "data" / "seeds.faa"
                    if not seeds_faa.exists():
                        seeds_faa = aln_file  # fall back to alignment file
                    ss = hmm_builder.self_search_recovery(hmm_out, seeds_faa)
                    _self_search.set(ss)
                except Exception:
                    pass
            if state is not None:
                state.mark_complete("hmm_build", {
                    "hmm_name": hmm_name,
                    "hmm_path": str(hmm_out),
                    "profile_length": _meta.get("LENG", 0),
                })
                _hmm_run_status.set("complete")

    # ---- hmm_stats -----------------------------------------------------------
    @output
    @render.ui
    def hmm_stats():
        meta = _hmm_meta.get()
        if meta is None:
            return ui.tags.p(
                "Build the HMM to see profile statistics.",
                class_="text-muted",
            )
        return ui.tags.div(
            section_header("Profile Statistics"),
            ui.layout_columns(
                stat_card("LENG", meta.get("LENG", "—"), color="primary", icon="📏"),
                stat_card("NSEQ", meta.get("NSEQ", "—"), color="info", icon="🧬"),
                stat_card("ALPH", meta.get("ALPH", "amino"), color="secondary", icon="🔤"),
                stat_card("checksum", meta.get("CKSUM", "—"), color="light", icon="🔑"),
                col_widths=[3, 3, 3, 3],
            ),
        )

    # ---- self_search_stats ---------------------------------------------------
    @output
    @render.ui
    def self_search_stats():
        ss = _self_search.get()
        if ss is None:
            return ui.tags.span("")
        n_rec = ss.get("recovered", 0)
        n_total = ss.get("total", 0)
        min_score = ss.get("min_score", "—")
        max_score = ss.get("max_score", "—")
        pct = int(100 * n_rec / max(n_total, 1))
        color = "success" if pct >= 90 else ("warning" if pct >= 70 else "danger")
        return ui.tags.div(
            section_header("Seed Self-Search Recovery"),
            ui.layout_columns(
                stat_card("recovered", f"{n_rec} / {n_total}", color=color, icon="🎯"),
                stat_card("% recovery", f"{pct}%", color=color, icon="📊"),
                stat_card("min score", f"{min_score:.1f}" if isinstance(min_score, float) else str(min_score),
                          color="info", icon="⬇️"),
                stat_card("max score", f"{max_score:.1f}" if isinstance(max_score, float) else str(max_score),
                          color="info", icon="⬆️"),
                col_widths=[3, 3, 3, 3],
            ),
        )

    # ---- hmm_logo_plot -------------------------------------------------------
    @output
    @render.plot
    def hmm_logo_plot():
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        logo = _logo_data.get()
        if logo is None:
            fig, ax = plt.subplots(figsize=(8, 2))
            ax.text(0.5, 0.5, "Build the HMM to see logo",
                    ha="center", va="center", transform=ax.transAxes,
                    color="gray", fontsize=12)
            ax.axis("off")
            return fig

        # logo is a list of dicts:
        #   {"pos": int, "top_aa": [{"aa": str, "prob": float}]}
        import math as _math
        positions = [d["pos"] for d in logo]

        def _compute_ic(top_aa_list: list) -> float:
            """Compute information content from residue probabilities."""
            probs = [r.get("prob", 0.0) for r in top_aa_list]
            total = sum(probs)
            if total <= 0:
                return 0.0
            probs = [p / total for p in probs]
            entropy = -sum(p * _math.log2(p) for p in probs if p > 0)
            return max(0.0, _math.log2(20) - entropy)

        ics = [_compute_ic(d.get("top_aa", [])) for d in logo]

        # Color scheme for amino acids
        def _aa_color(aa: str) -> str:
            hydrophobic = set("AVILMFYW")
            charged = set("RKHDE")
            polar = set("STNQ")
            if aa in hydrophobic:
                return "#4878CF"   # blue
            if aa in charged:
                return "#D65F5F"   # red
            if aa in polar:
                return "#6ACC65"   # green
            return "#B8B8B8"       # gray (Cys, Pro, Gly, etc.)

        fig, ax = plt.subplots(figsize=(max(10, len(positions) * 0.3), 4))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("#fafafa")

        bottom = [0.0] * len(positions)
        for rank in range(3):
            heights = []
            colors = []
            for d, ic_val in zip(logo, ics):
                residues = sorted(
                    d.get("top_aa", []), key=lambda r: r.get("prob", 0), reverse=True
                )
                if rank < len(residues):
                    r = residues[rank]
                    frac = r.get("prob", 0.0)
                    heights.append(ic_val * frac)
                    colors.append(_aa_color(r.get("aa", "X")))
                else:
                    heights.append(0.0)
                    colors.append("#B8B8B8")
            ax.bar(positions, heights, bottom=bottom, color=colors, width=0.85, linewidth=0)
            bottom = [b + h for b, h in zip(bottom, heights)]

        ax.set_xlabel("HMM Position", fontsize=14, fontweight="bold", labelpad=8)
        ax.set_ylabel("Information Content (bits)", fontsize=14, fontweight="bold", labelpad=8)
        ax.set_title("HMM Position-Specific Information Content",
                     fontsize=16, fontweight="bold", pad=12)
        ax.set_xlim(min(positions) - 0.5, max(positions) + 0.5)
        ax.set_ylim(0, 4.3)
        ax.tick_params(labelsize=11, width=1.2)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["bottom", "left"]].set_linewidth(1.2)
        ax.yaxis.grid(True, color="#e0e0e0", alpha=0.5, linewidth=0.5)

        legend_patches = [
            mpatches.Patch(color="#4878CF", label="Hydrophobic"),
            mpatches.Patch(color="#D65F5F", label="Charged"),
            mpatches.Patch(color="#6ACC65", label="Polar"),
            mpatches.Patch(color="#B8B8B8", label="Other"),
        ]
        ax.legend(handles=legend_patches, loc="upper right", fontsize=11,
                  framealpha=0.9, ncol=4, edgecolor="#cccccc")

        fig.tight_layout()
        return fig

    # ---- hmm_log -------------------------------------------------------------
    @output
    @render.text
    def hmm_log():
        runner = runner_dict.get("hmm")
        if runner is None:
            return "No log yet."
        return runner.get_log()
