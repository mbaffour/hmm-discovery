"""
ui/step_08_analysis.py — Analysis Panel (Step 8).

Seven sub-tabs: Synteny, Taxonomy, Phylogenetic Tree,
Presence/Absence Matrix, Sequence Clusters, Motif Discovery, Structure.
Heavy computations use AsyncJobRunner via kwargs["runner_dict"].
"""
from __future__ import annotations

import shutil
from pathlib import Path

from shiny import ui

from .components import (
    filesystem_picker_ui,
    guidance_callout,
    info_tooltip,
    learning_card,
    step_guidance,
    log_panel,
    register_filesystem_picker,
    section_header,
    stat_card,
    step_card,
    tier_badge,
)

# ---------------------------------------------------------------------------
# Helper: check tool availability
# ---------------------------------------------------------------------------

def _tool_available(name: str) -> bool:
    try:
        from pipeline.utils import find_tool
        return find_tool(name) is not None
    except ImportError:
        return shutil.which(name) is not None


def _avail_badge(tool: str, label: str) -> ui.TagChild:
    # For pygenomeviz: check Python import since it has no simple CLI command
    if tool == "pygenomeviz":
        try:
            import importlib
            found = importlib.util.find_spec("pygenomeviz") is not None
        except Exception:
            found = False
    elif tool == "iqtree2":
        # Accept any IQ-TREE binary (iqtree2, iqtree v2/v3) — the run handler
        # falls back across all of them.
        found = any(_tool_available(t) for t in ("iqtree2", "iqtree", "iqtree3"))
    else:
        found = _tool_available(tool)
    cls   = "bg-success" if found else "bg-warning text-dark"
    icon  = "✅" if found else "⚠️"
    title = f"{tool} available" if found else f"{tool} not found — install to enable"
    return ui.tags.span(f"{icon} {label}", class_=f"badge {cls} ms-2", title=title)


# ---------------------------------------------------------------------------
# Panel UI
# ---------------------------------------------------------------------------

def panel_ui() -> ui.TagChild:
    return ui.nav_panel(
        "8. Analysis",
        ui.tags.div(
            step_guidance(
                "Deep-dive analysis: genomic context, taxonomy, phylogeny, sequence clusters, motifs, and predicted structure.",
                [
                "Synteny maps showing gene neighbourhood context",
                "Taxonomy Sankey and treemap",
                "Phylogenetic tree (IQ-TREE)",
                "Presence/absence matrix heatmap",
                "Sequence cluster bubble chart (CD-HIT)",
                "Motif logos (MEME)",
                ],
                "Synteny requires internet access to fetch GenBank records from NCBI. Use the Entrez mode with your email address.",
            ),
            ui.tags.p(
                "Post-discovery analysis: genomic context, taxonomy, phylogeny, "
                "sequence clusters, motifs, and structure.",
                class_="text-muted mb-3",
            ),

            ui.navset_tab(

                # ---- Tab 1: Synteny -----------------------------------------
                ui.nav_panel(
                    "Synteny",
                    ui.tags.div(
                        section_header(
                            "Genomic Neighbourhood Analysis",
                            "Pick up flanking genes via local GenBank files, "
                            "NCBI Entrez, or the built-in project scripts (18 + 24)",
                        ),

                        # ── Tool availability badges ────────────────────────────
                        ui.tags.div(
                            ui.tags.small("Visualization tools: ", class_="text-muted me-1"),
                            _avail_badge("clinker",    "clinker"),
                            _avail_badge("pygenomeviz","pyGenomeViz"),
                            _avail_badge("easyfig",    "EasyFig"),
                            class_="mb-3",
                        ),
                        ui.layout_columns(
                            learning_card(
                                "What synteny can prove",
                                [
                                    "Placed hits show upstream and downstream genes when source context is available.",
                                    "Conserved neighbours support biology, but missing context is not proof of absence.",
                                    "The placement report explains which hits could not be mapped and why.",
                                ],
                                tone="info",
                            ),
                            learning_card(
                                "Using other synteny programs",
                                [
                                    "Download TSV/GFF3 for downstream parsing.",
                                    "Download clinker HTML for an interactive gene-cluster view.",
                                    "Use local GenBank files when you need the most reliable flanking-gene coordinates.",
                                ],
                                tone="success",
                            ),
                            col_widths=[6, 6],
                            class_="mb-3",
                        ),

                        # ── Source mode + viz tool ─────────────────────────────
                        ui.layout_columns(
                            ui.tags.div(
                                ui.input_radio_buttons(
                                    "synteny_mode",
                                    "Neighbourhood source",
                                    choices={
                                        "auto":    "Auto (local GenBank → NCBI Entrez)",
                                        "scripts": "Use project scripts 18 + 24",
                                        "entrez":  "NCBI Entrez only",
                                    },
                                    selected="auto",
                                ),
                            ),
                            ui.tags.div(
                                ui.input_select(
                                    "synteny_viz_tool",
                                    "Visualization tool",
                                    choices={
                                        "matplotlib":  "Built-in matplotlib (always available)",
                                        "clinker":     "clinker — interactive HTML",
                                        "pygenomeviz": "pyGenomeViz — publication PNG",
                                        "easyfig":     "EasyFig — SVG/PNG",
                                    },
                                    selected="matplotlib",
                                ),
                                ui.input_text(
                                    "synteny_email", "NCBI email",
                                    placeholder="you@example.com",
                                ),
                                ui.input_text(
                                    "synteny_local_gb_dir",
                                    "Local GenBank folder (optional)",
                                    placeholder="/path/to/genbank_files/",
                                ),
                                filesystem_picker_ui(
                                    "synteny_gb_dir_picker",
                                    "Local GenBank Folder Picker",
                                    "Navigate to the folder containing GenBank files, then click Use Current Folder.",
                                    allow_create_dir=True,
                                ),
                            ),
                            col_widths=[5, 7],
                        ),

                        ui.layout_columns(
                            ui.input_slider("synteny_flanks",
                                            ui.span("Flanking genes each side", info_tooltip(
                                                "Number of genes upstream and downstream of the hit to include in the "
                                                "neighbourhood. 5 is standard; increase for large operons."
                                            )),
                                            min=1, max=10, value=5, step=1),
                            ui.input_slider("synteny_max_genomes",
                                            ui.span("Max genomes", info_tooltip(
                                                "Cap on genomes shown in the synteny figure. Higher values give a "
                                                "more complete picture but can make figures unreadable."
                                            )),
                                            min=5, max=100, value=20, step=5),
                            ui.input_slider("synteny_clinker_id",
                                            ui.span("clinker identity threshold", info_tooltip(
                                                "Minimum amino-acid identity for clinker to draw a link between genes. "
                                                "Lower = more connections; 0.3 is a good default for distant families."
                                            )),
                                            min=0.1, max=0.9, value=0.3, step=0.05),
                            col_widths=[4, 4, 4],
                        ),
                        guidance_callout(
                            "Why five upstream and five downstream genes?",
                            "Five genes per side is a compact neighbourhood window: large enough to see local genome architecture, small enough to compare many genomes without turning the plot unreadable. Increase it for broad operons; decrease it for dense figures.",
                            "secondary",
                        ),

                        ui.tags.div(
                            ui.input_action_button(
                                "run_synteny", "▶ Run Synteny Analysis",
                                class_="btn btn-primary me-2",
                            ),
                            ui.output_ui("synteny_source_note"),
                            class_="mb-3",
                        ),

                        # ── Interactive plotly map ──────────────────────────────
                        ui.card(
                            ui.card_header("Synteny Map — Interactive (built-in)"),
                            ui.output_ui("synteny_interactive"),
                        ),

                        # ── clinker interactive HTML ─────────────────────────────
                        ui.card(
                            ui.card_header(
                                ui.tags.span("clinker — Interactive Gene Cluster Comparison"),
                                ui.tags.small(
                                    " (requires clinker on PATH — pip install clinker)",
                                    class_="text-muted",
                                ),
                            ),
                            ui.output_ui("clinker_figure"),
                            class_="mt-3",
                        ),

                        # ── Static gene-map figure (matplotlib / pyGenomeViz / script 24) ──
                        ui.card(
                            ui.card_header("Gene-Map Figure (matplotlib / pyGenomeViz / script 24)"),
                            ui.output_ui("synteny_genemap_figure"),
                            class_="mt-3",
                        ),

                        # ── Frequency chart (script 24) ─────────────────────────
                        ui.card(
                            ui.card_header("Neighbour Frequency Chart (script 24)"),
                            ui.output_ui("synteny_freq_figure"),
                            class_="mt-3",
                        ),

                        # ── Conservation table ──────────────────────────────────
                        ui.card(
                            ui.card_header("Neighbourhood Conservation"),
                            ui.output_ui("neighborhood_conservation"),
                            class_="mt-3",
                        ),

                        # ── Placement Report ───────────────────────────────────
                        ui.card(
                            ui.card_header(
                                ui.tags.span("Placement Report"),
                                ui.tags.small(
                                    " — which hits were placed in synteny context, and why others were not",
                                    class_="text-muted",
                                ),
                            ),
                            ui.output_ui("synteny_placement_report"),
                            class_="mt-3",
                        ),

                        # ── Downloads ──────────────────────────────────────────
                        ui.tags.div(
                            ui.tags.strong("Publication figures: ", class_="me-1 small"),
                            ui.download_button("dl_synteny_png_8",    "⬇ PNG (300dpi)",
                                               class_="btn btn-success btn-sm me-1"),
                            ui.download_button("dl_synteny_svg_8",    "⬇ SVG (vector)",
                                               class_="btn btn-success btn-sm me-1"),
                            ui.download_button("dl_synteny_pdf_8",    "⬇ PDF (vector)",
                                               class_="btn btn-success btn-sm me-1"),
                            ui.tags.span("  |  ", class_="text-muted"),
                            ui.download_button("dl_synteny_pgv_png",  "⬇ pyGenomeViz PNG",
                                               class_="btn btn-outline-secondary btn-sm me-1"),
                            ui.download_button("dl_synteny_clinker",  "⬇ clinker HTML",
                                               class_="btn btn-outline-secondary btn-sm me-1"),
                            ui.download_button("dl_synteny_freq",     "⬇ Freq PNG",
                                               class_="btn btn-outline-secondary btn-sm me-1"),
                            ui.download_button("dl_synteny_tsv_8",    "⬇ TSV",
                                               class_="btn btn-outline-secondary btn-sm me-1"),
                            ui.download_button("dl_synteny_gff3_8",   "⬇ GFF3",
                                               class_="btn btn-outline-secondary btn-sm me-1"),
                            ui.download_button("dl_placement_report", "⬇ Placement Report",
                                               class_="btn btn-outline-secondary btn-sm"),
                            class_="mt-2",
                        ),

                        section_header("Log"),
                        log_panel("synteny_log"),
                        class_="container-fluid px-0 py-2",
                    ),
                ),

                # ---- Tab 2: Taxonomy ----------------------------------------
                ui.nav_panel(
                    "Taxonomy",
                    ui.tags.div(
                        section_header("Taxonomic Distribution"),
                        ui.input_action_button("run_taxonomy", "▶ Build Taxonomy", class_="btn btn-primary mb-3"),
                        ui.layout_columns(
                            ui.card(
                                ui.card_header("Taxonomy Sankey"),
                                ui.output_ui("taxonomy_sankey"),
                            ),
                            ui.card(
                                ui.card_header("Taxonomy Treemap"),
                                ui.output_ui("taxonomy_treemap"),
                            ),
                            col_widths=[6, 6],
                        ),
                        ui.card(
                            ui.card_header("Taxonomic Outliers"),
                            ui.output_data_frame("taxonomy_outliers"),
                            class_="mt-3",
                        ),
                        ui.tags.div(
                            ui.download_button("dl_taxonomy_tsv_8", "⬇️ taxonomy_table.tsv",
                                               class_="btn btn-outline-primary btn-sm me-1 mb-1"),
                            ui.download_button("dl_taxonomy_outliers_8", "⬇️ taxonomy_outliers.tsv",
                                               class_="btn btn-outline-primary btn-sm me-1 mb-1"),
                            class_="mt-2",
                        ),
                        class_="container-fluid px-0 py-2",
                    ),
                ),

                # ---- Tab 3: Phylogenetic Tree --------------------------------
                ui.nav_panel(
                    ui.tags.span(
                        "Phylogenetic Tree",
                        _avail_badge("iqtree2", "IQ-TREE"),
                    ),
                    ui.tags.div(
                        section_header("Phylogenetic Tree (IQ-TREE)"),
                        ui.layout_columns(
                            ui.input_select(
                                "tree_model",
                                "Substitution model",
                                choices={"TEST": "ModelTest (auto)", "LG": "LG", "WAG": "WAG", "JTT": "JTT"},
                                selected="TEST",
                            ),
                            ui.input_numeric("tree_bootstrap",
                                            ui.span("Bootstrap replicates", info_tooltip(
                                                "Number of ultrafast bootstrap (UFBoot) replicates. IQ-TREE requires "
                                                "at least 1000 when UFBoot is enabled."
                                            )),
                                            value=1000, min=1000, max=10000, step=100),
                            ui.input_slider("tree_cpu",
                                            ui.span("Threads", info_tooltip(
                                                "CPU threads for IQ-TREE. More threads = faster, but set to ≤ "
                                                "your physical core count for best performance."
                                            )),
                                            min=1, max=32, value=4, step=1),
                            col_widths=[4, 4, 4],
                        ),
                        ui.input_action_button("run_iqtree", "▶ Run IQ-TREE", class_="btn btn-primary mb-3"),
                        ui.card(
                            ui.card_header("Tree Figure"),
                            ui.output_ui("tree_figure"),
                        ),
                        ui.tags.div(
                            ui.download_button("dl_treefile", "⬇ .treefile", class_="btn btn-outline-secondary btn-sm me-1"),
                            ui.download_button("dl_tree_png", "⬇ PNG", class_="btn btn-outline-secondary btn-sm me-1"),
                            ui.download_button("dl_tree_svg", "⬇ SVG", class_="btn btn-outline-secondary btn-sm"),
                            class_="mt-2",
                        ),
                        section_header("IQ-TREE Log"),
                        log_panel("iqtree_log"),
                        class_="container-fluid px-0 py-2",
                    ),
                ),

                # ---- Tab 4: Presence/Absence Matrix -------------------------
                ui.nav_panel(
                    "Presence/Absence Matrix",
                    ui.tags.div(
                        section_header("Presence/Absence Matrix"),
                        ui.layout_columns(
                            ui.input_checkbox_group(
                                "matrix_tiers",
                                "Include confidence tiers",
                                choices={
                                    "high_confidence": "High Confidence",
                                    "putative": "Putative",
                                    "divergent": "Divergent",
                                },
                                selected=["high_confidence", "putative"],
                                inline=True,
                            ),
                            ui.input_action_button("run_matrix", "▶ Build Matrix", class_="btn btn-primary"),
                            col_widths=[8, 4],
                        ),
                        ui.card(
                            ui.card_header("Heatmap"),
                            ui.output_ui("heatmap_figure"),
                            class_="mt-3",
                        ),
                        ui.card(
                            ui.card_header("Matrix Statistics"),
                            ui.output_ui("matrix_stats"),
                            class_="mt-3",
                        ),
                        class_="container-fluid px-0 py-2",
                    ),
                ),

                # ---- Tab 5: Sequence Clusters --------------------------------
                ui.nav_panel(
                    ui.tags.span(
                        "Sequence Clusters",
                        _avail_badge("cd-hit", "CD-HIT"),
                        _avail_badge("mmseqs", "MMseqs2"),
                    ),
                    ui.tags.div(
                        section_header("Sequence Clustering"),
                        ui.layout_columns(
                            ui.input_slider("cluster_identity",
                                            ui.span("Identity threshold", info_tooltip(
                                                "Minimum sequence identity to group proteins into the same cluster. "
                                                "0.7 (70%) finds subfamily-level groups; 0.4 catches remote homologs."
                                            )),
                                            min=0.3, max=0.95, value=0.7, step=0.05),
                            ui.input_slider("cluster_coverage",
                                            ui.span("Coverage threshold", info_tooltip(
                                                "Minimum alignment coverage (fraction of the shorter sequence). "
                                                "0.8 is strict; lower to 0.5 if sequences vary in length or have "
                                                "domain truncations."
                                            )),
                                            min=0.3, max=1.0, value=0.8, step=0.05),
                            ui.input_select(
                                "cluster_tool",
                                "Clustering tool",
                                choices={"cd-hit": "CD-HIT", "mmseqs2": "MMseqs2"},
                            ),
                            col_widths=[4, 4, 4],
                        ),
                        ui.input_action_button("run_clustering", "▶ Cluster Sequences", class_="btn btn-primary mb-3"),
                        log_panel("cluster_log"),
                        ui.card(
                            ui.card_header("Cluster Bubble Chart"),
                            ui.output_ui("cluster_treemap"),
                        ),
                        ui.card(
                            ui.card_header("Cluster Table"),
                            ui.output_data_frame("cluster_table"),
                            class_="mt-3",
                        ),
                        class_="container-fluid px-0 py-2",
                    ),
                ),

                # ---- Tab 6: Motif Discovery ----------------------------------
                ui.nav_panel(
                    ui.tags.span(
                        "Motif Discovery",
                        _avail_badge("meme", "MEME"),
                        _avail_badge("fimo", "FIMO"),
                    ),
                    ui.tags.div(
                        section_header("Motif Discovery (MEME / FIMO)"),
                        ui.layout_columns(
                            ui.input_slider("motif_n",
                                            ui.span("Number of motifs", info_tooltip(
                                                "How many distinct motifs MEME should find. 3–5 is typical; "
                                                "increase if your family has many conserved regions."
                                            )),
                                            min=1, max=20, value=5, step=1),
                            ui.input_slider("motif_min_width",
                                            ui.span("Min motif width", info_tooltip(
                                                "Shortest motif MEME will report (amino acids). "
                                                "6 is standard; lower to 4 for short binding motifs."
                                            )),
                                            min=4, max=20, value=6, step=1),
                            ui.input_slider("motif_max_width",
                                            ui.span("Max motif width", info_tooltip(
                                                "Longest motif MEME will report (amino acids). "
                                                "20 is standard; increase to 50 for large conserved domains."
                                            )),
                                            min=8, max=50, value=20, step=1),
                            col_widths=[4, 4, 4],
                        ),
                        ui.input_action_button("run_meme", "▶ Discover Motifs", class_="btn btn-primary mb-3"),
                        log_panel("meme_log"),
                        ui.card(
                            ui.card_header("Motif Logos"),
                            ui.output_ui("motif_logos"),
                        ),
                        ui.card(
                            ui.card_header("FIMO Hits Table"),
                            ui.output_data_frame("fimo_table"),
                            class_="mt-3",
                        ),
                        class_="container-fluid px-0 py-2",
                    ),
                ),

                # ---- Tab 7: Structure ---------------------------------------
                ui.nav_panel(
                    ui.tags.span(
                        "Structure",
                        _avail_badge("foldseek", "Foldseek"),
                    ),
                    ui.tags.div(
                        section_header("Structure Prediction & Comparison"),
                        ui.input_action_button(
                            "run_structure",
                            "▶ Run Structure Prediction",
                            class_="btn btn-primary mb-3",
                        ),
                        ui.tags.small(
                            "Calls script 20 (ColabFold / ESMFold + Foldseek). "
                            "Requires GPU or remote API credentials.",
                            class_="text-muted d-block mb-3",
                        ),
                        ui.card(
                            ui.card_header("Structure Results"),
                            ui.output_data_frame("structure_table"),
                        ),
                        ui.card(
                            ui.card_header("Structure Log"),
                            ui.output_text_verbatim("structure_log"),
                            class_="mt-3",
                        ),
                        class_="container-fluid px-0 py-2",
                    ),
                ),

                id="analysis_tabs",
            ),

            class_="container-fluid px-0",
        ),
    )


# ---------------------------------------------------------------------------
# Server outputs
# ---------------------------------------------------------------------------

def register_outputs(input, output, render, reactive, session, **kwargs):
    import asyncio
    import base64
    import json
    import subprocess

    proj_dir_rv = kwargs.get("proj_dir_rv", None)
    runner_dict = kwargs.get("runner_dict", {})

    # Per-tab log lines
    _logs: dict[str, reactive.Value] = {
        tab: reactive.value([]) for tab in
        ["synteny", "iqtree", "clustering", "meme", "structure"]
    }

    def _log(tab: str, msg: str):
        lines = _logs[tab].get()
        lines.append(msg)
        _logs[tab].set(lines[-500:])

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
            if cand.exists():
                return cand
        return pd_

    register_filesystem_picker(
        input,
        output,
        render,
        reactive,
        session,
        picker_id="synteny_gb_dir_picker",
        target_input_id="synteny_local_gb_dir",
        mode="dir",
        initial_dir=Path.home() / "Documents",
        project_dir_getter=_proj_dir,
        allow_create_dir=True,
    )

    async def _run_script(tab: str, cmd: list[str]):
        _log(tab, f"Running: {' '.join(cmd)}")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert proc.stdout is not None
            async for line in proc.stdout:
                _log(tab, line.decode().rstrip())
            await proc.wait()
            _log(tab, f"Done (exit {proc.returncode}).")
        except FileNotFoundError:
            _log(tab, f"ERROR: command not found: {cmd[0]}")
        except Exception as exc:
            _log(tab, f"ERROR: {exc}")

    def _plotly_html(fig, height: str = "400px") -> ui.TagChild:
        try:
            html = fig.to_html(full_html=True, include_plotlyjs="cdn")
            escaped = html.replace("&", "&amp;").replace('"', "&quot;")
            return ui.HTML(
                f'<iframe srcdoc="{escaped}" style="width:100%; height:{height}; border:none;" '
                f'sandbox="allow-scripts allow-same-origin"></iframe>'
            )
        except Exception as exc:
            return ui.tags.p(f"Render error: {exc}", class_="text-danger small")

    # ==========================================================================
    # TAB 1: SYNTENY
    # ==========================================================================

    _syn_df:            reactive.Value        = reactive.value(None)   # long-format table
    _syn_cons_df:       reactive.Value        = reactive.value(None)   # conservation table
    _syn_placement_df:  reactive.Value        = reactive.value(None)   # placement report
    _syn_png:           reactive.Value[bytes] = reactive.value(b"")    # matplotlib PNG 300dpi
    _syn_svg:           reactive.Value[bytes] = reactive.value(b"")    # matplotlib SVG (vector)
    _syn_pdf:           reactive.Value[bytes] = reactive.value(b"")    # matplotlib PDF (vector)
    _syn_pgv_png:       reactive.Value[bytes] = reactive.value(b"")    # pyGenomeViz PNG
    _syn_freq_png:      reactive.Value[bytes] = reactive.value(b"")    # frequency PNG (script 24)
    _syn_tsv_path:      reactive.Value[str]   = reactive.value("")     # path to TSV on disk
    _syn_clinker_html:  reactive.Value[str]   = reactive.value("")     # clinker HTML path

    @output
    @render.ui
    def synteny_source_note():
        mode = input.synteny_mode()
        notes = {
            "auto":    "🔵 Tries local GenBank files first, falls back to NCBI Entrez.",
            "scripts": "🟢 Calls project scripts 18_synteny_analysis.py + 24_synteny_figure.py.",
            "entrez":  "🌐 NCBI Entrez only — requires valid accession IDs in hit headers.",
        }
        return ui.tags.small(notes.get(mode, ""), class_="text-muted")

    @reactive.effect
    @reactive.event(input.run_synteny)
    async def _on_run_synteny():
        import asyncio as _aio
        import sys as _sys

        _syn_df.set(None)
        _syn_cons_df.set(None)
        _syn_placement_df.set(None)
        _syn_png.set(b"")
        _syn_svg.set(b"")
        _syn_pdf.set(b"")
        _syn_pgv_png.set(b"")
        _syn_freq_png.set(b"")
        _syn_clinker_html.set("")
        _logs["synteny"].set([])

        pd_       = _proj_dir()
        if pd_ is None:
            _log("synteny", "❌  Project not loaded.")
            return

        mode      = input.synteny_mode()
        email     = (input.synteny_email() or "").strip() or "researcher@example.com"
        flanks    = input.synteny_flanks()
        max_gen   = input.synteny_max_genomes()
        local_gb  = (input.synteny_local_gb_dir() or "").strip()

        # ── Mode: project scripts 18 + 24 ──────────────────────────────────
        if mode == "scripts":
            _log("synteny", "▶ Running 18_synteny_analysis.py …")
            # Locate scripts relative to project dir
            scripts_root = pd_.parent.parent / "scripts"
            script18 = scripts_root / "18_synteny_analysis.py"
            script24 = scripts_root / "24_synteny_figure.py"

            if not script18.exists():
                _log("synteny", f"❌  18_synteny_analysis.py not found at {script18}")
            else:
                proc18 = await _aio.create_subprocess_exec(
                    _sys.executable, str(script18),
                    "--email", email, "--flanks", str(flanks),
                    stdout=_aio.subprocess.PIPE, stderr=_aio.subprocess.STDOUT,
                    cwd=str(pd_.parent.parent),
                )
                async for raw in proc18.stdout:
                    _log("synteny", raw.decode(errors="replace").rstrip())
                await proc18.wait()
                _log("synteny", f"Script 18 exit {proc18.returncode}")

            if not script24.exists():
                _log("synteny", f"❌  24_synteny_figure.py not found at {script24}")
            else:
                _log("synteny", "▶ Running 24_synteny_figure.py …")
                proc24 = await _aio.create_subprocess_exec(
                    _sys.executable, str(script24),
                    stdout=_aio.subprocess.PIPE, stderr=_aio.subprocess.STDOUT,
                    cwd=str(pd_.parent.parent),
                )
                async for raw in proc24.stdout:
                    _log("synteny", raw.decode(errors="replace").rstrip())
                await proc24.wait()
                _log("synteny", f"Script 24 exit {proc24.returncode}")

            # Load produced figures into reactive bytes
            fig_dir = pd_.parent.parent / "results" / "figures"
            genemap_f = fig_dir / "synteny_genemap.png"
            freq_f    = fig_dir / "synteny_frequency.png"
            if genemap_f.exists():
                _syn_png.set(genemap_f.read_bytes())
                _log("synteny", f"✅  Loaded {genemap_f.name}")
            if freq_f.exists():
                _syn_freq_png.set(freq_f.read_bytes())
                _log("synteny", f"✅  Loaded {freq_f.name}")

            # Load TSV for conservation table
            tsv = pd_.parent.parent / "results" / "synteny_table.tsv"
            if not tsv.exists():
                tsv = pd_.parent.parent / "results" / "intermediate" / "synteny_table.tsv"
            if tsv.exists():
                _syn_tsv_path.set(str(tsv))
                try:
                    import pandas as _pd
                    syn_df = _pd.read_csv(tsv, sep="\t")
                    _syn_df.set(syn_df)
                except Exception as exc:
                    _log("synteny", f"Warning: could not parse TSV: {exc}")

            # ── Run selected viz tool on produced GenBanks ──────────────
            gbk_dir  = pd_.parent.parent / "results" / "neighborhood_gbk"
            viz_tool = input.synteny_viz_tool()
            await _dispatch_viz_tool(pd_, viz_tool, gbk_dir)
            return

        # ── Mode: auto / entrez  (pipeline module) ──────────────────────────
        hits_path = pd_ / "results" / "hits_main.tsv"
        if not hits_path.exists():
            # Try parent results dir
            hits_path = pd_.parent.parent / "results" / "master_hits_table.tsv"
        if not hits_path.exists():
            _log("synteny", "❌  No hits_main.tsv found. Run search first.")
            return

        _log("synteny", f"Loading hits from {hits_path.name} …")
        try:
            import pandas as _pd
            hits_df = _pd.read_csv(hits_path, sep="\t")
            _log("synteny", f"  {len(hits_df)} hits loaded.")
        except Exception as exc:
            _log("synteny", f"❌  Could not read hits: {exc}")
            return

        _log("synteny", f"Fetching neighbourhoods (mode={mode}, flanks={flanks}, "
                         f"max_genomes={max_gen}) …")
        try:
            from pipeline.synteny import (  # type: ignore
                build_synteny_table, conservation_scores,
                synteny_figure_plotly, export_gff3,
                export_synteny_figures, build_neighborhood_genbanks,
            )

            local_dirs = [local_gb] if local_gb else []
            if mode == "entrez":
                local_dirs = []

            # build_synteny_table now returns (syn_df, placement_df)
            syn_df, placement_df = build_synteny_table(
                hits_df,
                email=email,
                flanks=flanks,
                max_genomes=max_gen,
                local_genbank_dirs=local_dirs,
                sequence_cache_dir=pd_ / "results" / "synteny_context_cache",
                log_callback=lambda m: _log("synteny", m),
            )
            _log("synteny", f"  Neighbourhood rows: {len(syn_df)}")

            placed_n   = int(placement_df["placed"].sum())  if not placement_df.empty else 0
            total_n    = len(placement_df)
            _log("synteny", f"  Placement: {placed_n}/{total_n} hits placed")

            _syn_placement_df.set(placement_df)

            if syn_df.empty:
                _log("synteny", "⚠️  No neighbourhood genes found.")
                if not placement_df.empty:
                    skipped = placement_df[~placement_df["placed"]]
                    for _, sr in skipped.head(5).iterrows():
                        _log("synteny", f"    • {sr['protein_id'][:40]} → {sr['status']}: {sr['reason'][:80]}")
                    if len(skipped) > 5:
                        _log("synteny", f"    … and {len(skipped) - 5} more (see Placement Report card below).")
                return

            cons_df = conservation_scores(syn_df)
            _syn_df.set(syn_df)
            _syn_cons_df.set(cons_df)

            # ── Export publication figures: PNG (300dpi) + SVG + PDF ──────
            out_dir  = pd_ / "results"
            fig_dir  = pd_ / "figures"
            out_dir.mkdir(parents=True, exist_ok=True)
            _log("synteny", "▶ Exporting publication figures (PNG 300dpi, SVG, PDF) …")
            multi = export_synteny_figures(
                syn_df, cons_df,
                out_dir=fig_dir,
                flanks=flanks,
                max_genomes=max_gen,
                dpi=300,
                log_callback=lambda m: _log("synteny", m),
            )
            if multi.get("png"):
                _syn_png.set(multi["png"].read_bytes())
            if multi.get("svg"):
                _syn_svg.set(multi["svg"].read_bytes())
            if multi.get("pdf"):
                _syn_pdf.set(multi["pdf"].read_bytes())

            # ── Save TSV + GFF3 ────────────────────────────────────────────
            tsv_path = out_dir / "synteny_table.tsv"
            syn_df.to_csv(tsv_path, sep="\t", index=False)
            _syn_tsv_path.set(str(tsv_path))
            export_gff3(syn_df, out_dir / "synteny_neighborhoods.gff3")

            # Save placement report
            (out_dir / "synteny_placement_report.tsv").write_text(
                placement_df.to_csv(sep="\t", index=False)
            )

            # ── Build neighbourhood GenBanks + run selected viz tool ──────
            gbk_dir  = out_dir / "neighborhood_gbk"
            viz_tool = input.synteny_viz_tool()
            _log("synteny", f"▶ Building neighbourhood GenBanks for viz tool: {viz_tool} …")
            try:
                gbk_files = build_neighborhood_genbanks(
                    syn_df, gbk_dir, log_callback=lambda m: _log("synteny", m)
                )
                _log("synteny", f"  {len(gbk_files)} GenBank files written → {gbk_dir}")
            except Exception as exc2:
                _log("synteny", f"⚠️  GenBank build error: {exc2}")

            await _dispatch_viz_tool(pd_, viz_tool, gbk_dir, syn_df, max_gen)
            _log("synteny", "✅  Done.")

        except ImportError as exc:
            _log("synteny", f"❌  pipeline.synteny not importable: {exc}")
        except Exception as exc:
            _log("synteny", f"❌  {exc}")

    # ── Viz-tool dispatcher (called from _on_run_synteny) ──────────────────────
    async def _dispatch_viz_tool(pd_, viz_tool, gbk_dir, syn_df=None, max_genomes=20):
        """Run the selected synteny visualization tool and store results."""
        out_dir = Path(pd_) / "results" if pd_ else Path(gbk_dir).parent

        if viz_tool == "clinker":
            _log("synteny", "▶ Running clinker …")
            try:
                from pipeline.synteny import run_clinker  # type: ignore
                html_path = run_clinker(
                    gbk_dir, out_dir / "clinker",
                    log_callback=lambda m: _log("synteny", m),
                    identity=float(input.synteny_clinker_id()),
                )
                if html_path:
                    _syn_clinker_html.set(str(html_path))
            except Exception as exc:
                _log("synteny", f"❌  clinker error: {exc}")

        elif viz_tool == "pygenomeviz":
            _log("synteny", "▶ Running pyGenomeViz …")
            if syn_df is None:
                # Try loading from TSV
                tsv = _syn_tsv_path.get()
                if tsv and Path(tsv).exists():
                    try:
                        import pandas as _pd2
                        syn_df = _pd2.read_csv(tsv, sep="\t")
                    except Exception:
                        pass
            if syn_df is not None and not (hasattr(syn_df, 'empty') and syn_df.empty):
                try:
                    from pipeline.synteny import run_pygenomeviz  # type: ignore
                    png = run_pygenomeviz(
                        syn_df, out_dir / "pygenomeviz",
                        log_callback=lambda m: _log("synteny", m),
                        max_genomes=max_genomes,
                    )
                    if png:
                        _syn_pgv_png.set(png)
                except Exception as exc:
                    _log("synteny", f"❌  pyGenomeViz error: {exc}")

        elif viz_tool == "easyfig":
            _log("synteny", "▶ Running EasyFig …")
            try:
                from pipeline.synteny import run_easyfig  # type: ignore
                out_path = run_easyfig(
                    gbk_dir, out_dir / "easyfig",
                    log_callback=lambda m: _log("synteny", m),
                )
                if out_path and out_path.suffix in (".png", ".svg"):
                    if out_path.suffix == ".png":
                        _syn_pgv_png.set(out_path.read_bytes())
                    else:
                        # Store SVG as bytes for display
                        _syn_pgv_png.set(out_path.read_bytes())
            except Exception as exc:
                _log("synteny", f"❌  EasyFig error: {exc}")

        # matplotlib is the default — already set by caller
        else:
            _log("synteny", "ℹ️  Using built-in matplotlib figure (already rendered above).")

    # ── Plotly interactive ─────────────────────────────────────────────────────
    @output
    @render.ui
    def synteny_interactive():
        syn_df  = _syn_df.get()
        cons_df = _syn_cons_df.get()
        if syn_df is None or (hasattr(syn_df, 'empty') and syn_df.empty):
            return ui.tags.p(
                "Click ▶ Run Synteny Analysis to build the interactive map.",
                class_="text-muted text-center py-4",
            )
        try:
            from pipeline.synteny import synteny_figure_plotly  # type: ignore
            fig = synteny_figure_plotly(syn_df, cons_df, max_genomes=30)
            return _plotly_html(fig, height="500px")
        except Exception as exc:
            return ui.tags.p(f"Plotly render error: {exc}", class_="text-danger small")

    # ── clinker interactive HTML ────────────────────────────────────────────────
    @output
    @render.ui
    def clinker_figure():
        html_path = _syn_clinker_html.get()
        if not html_path or not Path(html_path).exists():
            return ui.tags.p(
                "Select 'clinker' as the visualization tool and run synteny analysis "
                "to see the interactive gene cluster comparison.",
                class_="text-muted text-center py-4",
            )
        try:
            html_content = Path(html_path).read_text(encoding="utf-8", errors="replace")
            # Embed clinker HTML in an iframe for safety
            import base64
            b64 = base64.b64encode(html_content.encode()).decode()
            return ui.tags.div(
                ui.HTML(
                    f'<iframe src="data:text/html;base64,{b64}" '
                    f'style="width:100%; height:600px; border:none;" '
                    f'title="clinker output"></iframe>'
                ),
                ui.tags.small(
                    f"Source: {html_path}", class_="text-muted d-block mt-1"
                ),
            )
        except Exception as exc:
            return ui.tags.p(f"Error loading clinker HTML: {exc}", class_="text-danger small")

    # ── Static gene-map PNG (matplotlib / pyGenomeViz / EasyFig / script 24) ──
    @output
    @render.ui
    def synteny_genemap_figure():
        import base64

        viz = input.synteny_viz_tool() if hasattr(input, "synteny_viz_tool") else "matplotlib"

        # pyGenomeViz / EasyFig output stored in _syn_pgv_png
        if viz in ("pygenomeviz", "easyfig"):
            data = _syn_pgv_png.get()
            if data:
                # Check if it's SVG (starts with < or <?xml)
                try:
                    text = data.decode("utf-8", errors="ignore")[:100]
                    if "<svg" in text or "<?xml" in text:
                        return ui.HTML(data.decode("utf-8", errors="replace"))
                except Exception:
                    pass
                # PNG fallback
                b64 = base64.b64encode(data).decode()
                return ui.tags.div(
                    ui.tags.img(
                        src=f"data:image/png;base64,{b64}",
                        style="max-width:100%; height:auto; display:block; margin:auto;",
                    ),
                    ui.tags.small(f"Produced by {viz}", class_="text-muted d-block text-center"),
                )
            return ui.tags.p(
                f"Run synteny with '{viz}' selected to see the figure here.",
                class_="text-muted text-center py-4",
            )

        # Default: matplotlib / script 24 PNG stored in _syn_png
        png = _syn_png.get()
        if not png:
            return ui.tags.p(
                "Gene-map figure will appear here after running synteny analysis.",
                class_="text-muted text-center py-4",
            )
        b64 = base64.b64encode(png).decode()
        return ui.tags.img(
            src=f"data:image/png;base64,{b64}",
            style="max-width:100%; height:auto; display:block; margin:auto;",
        )

    # ── Frequency chart PNG (script 24) ────────────────────────────────────────
    @output
    @render.ui
    def synteny_freq_figure():
        import base64
        png = _syn_freq_png.get()
        if not png:
            return ui.tags.p(
                "Frequency chart available when using project scripts (mode = 'Use project scripts 18+24').",
                class_="text-muted text-center py-3 small",
            )
        b64 = base64.b64encode(png).decode()
        return ui.tags.img(
            src=f"data:image/png;base64,{b64}",
            style="max-width:100%; height:auto; display:block; margin:auto;",
        )

    # ── Conservation table ─────────────────────────────────────────────────────
    @output
    @render.ui
    def neighborhood_conservation():
        cons_df = _syn_cons_df.get()
        if cons_df is None or (hasattr(cons_df, 'empty') and cons_df.empty):
            # Try loading from disk (scripts mode writes intermediate TSV)
            tsv_path = _syn_tsv_path.get()
            if tsv_path:
                try:
                    import pandas as _pd
                    from pipeline.synteny import conservation_scores  # type: ignore
                    syn_df = _pd.read_csv(tsv_path, sep="\t")
                    if "position_rel" in syn_df.columns and "hit_protein_id" in syn_df.columns:
                        cons_df = conservation_scores(syn_df)
                    else:
                        return ui.tags.p("Synteny TSV missing required columns.", class_="text-muted small")
                except Exception:
                    return ui.tags.p("No conservation data yet.", class_="text-muted small")
            else:
                return ui.tags.p("Run synteny analysis to see conservation scores.", class_="text-muted small")

        try:
            rows = [
                ui.tags.tr(
                    ui.tags.td(str(r["position_rel"])),
                    ui.tags.td(str(r.get("gene_name", ""))),
                    ui.tags.td(str(r.get("function", ""))),
                    ui.tags.td(f"{r.get('presence_fraction', 0):.0%}"),
                    ui.tags.td(f"{r.get('conservation_fraction', 0):.0%}"),
                    ui.tags.td(
                        ui.tags.span("Core", class_="badge bg-success")
                        if r.get("is_core")
                        else ui.tags.span("Variable", class_="badge bg-secondary")
                    ),
                )
                for _, r in cons_df.iterrows()
            ]
            return ui.tags.div(
                ui.tags.table(
                    ui.tags.thead(ui.tags.tr(
                        ui.tags.th("Position"), ui.tags.th("Gene"),
                        ui.tags.th("Function"),
                        ui.tags.th("Presence"), ui.tags.th("Conservation"),
                        ui.tags.th("Status"),
                    )),
                    ui.tags.tbody(*rows),
                    class_="table table-sm table-striped table-hover",
                ),
                style="max-height:350px; overflow-y:auto;",
            )
        except Exception as exc:
            return ui.tags.p(f"Error rendering table: {exc}", class_="text-danger small")

    @output
    @render.text
    def synteny_log():
        lines = _logs["synteny"].get()
        return "\n".join(lines) if lines else "No log yet."

    # ── Downloads ──────────────────────────────────────────────────────────────
    @render.download(filename="synteny_genemap.png")
    def dl_synteny_png_8():
        png = _syn_png.get()
        if png:
            yield png

    @render.download(filename="synteny_frequency.png")
    def dl_synteny_freq():
        png = _syn_freq_png.get()
        if png:
            yield png

    @render.download(filename="synteny_table.tsv")
    def dl_synteny_tsv_8():
        tsv_path = _syn_tsv_path.get()
        if tsv_path and Path(tsv_path).exists():
            yield Path(tsv_path).read_bytes()

    @render.download(filename="synteny_neighborhoods.gff3")
    def dl_synteny_gff3_8():
        rd = _results_dir()
        f  = rd / "synteny_neighborhoods.gff3" if rd else None
        if f and f.exists():
            yield f.read_bytes()

    @render.download(filename="synteny_pygenomeviz.png")
    def dl_synteny_pgv_png():
        png = _syn_pgv_png.get()
        if png:
            yield png

    @render.download(filename="clinker_output.html")
    def dl_synteny_clinker():
        html_path = _syn_clinker_html.get()
        if html_path and Path(html_path).exists():
            yield Path(html_path).read_bytes()

    @render.download(filename="synteny_map.svg")
    def dl_synteny_svg_8():
        svg = _syn_svg.get()
        if svg:
            yield svg

    @render.download(filename="synteny_map.pdf")
    def dl_synteny_pdf_8():
        pdf = _syn_pdf.get()
        if pdf:
            yield pdf

    @render.download(filename="synteny_placement_report.tsv")
    def dl_placement_report():
        df = _syn_placement_df.get()
        if df is not None and not (hasattr(df, "empty") and df.empty):
            yield df.to_csv(sep="\t", index=False).encode()

    # ── Placement report render ────────────────────────────────────────────
    @output
    @render.ui
    def synteny_placement_report():
        df = _syn_placement_df.get()
        if df is None or (hasattr(df, "empty") and df.empty):
            return ui.tags.p(
                "Run synteny analysis to see the placement report.",
                class_="text-muted small p-2",
            )

        placed   = df[df["placed"]  == True]   # noqa: E712
        unplaced = df[df["placed"]  == False]  # noqa: E712
        total    = len(df)

        # Summary badges
        summary = ui.tags.div(
            ui.tags.span(f"Total hits: {total}", class_="badge bg-secondary me-1"),
            ui.tags.span(f"✅ Placed: {len(placed)}", class_="badge bg-success me-1"),
            ui.tags.span(f"⚠️ Not placed: {len(unplaced)}", class_="badge bg-warning text-dark me-1"),
            class_="mb-2",
        )

        # Status breakdown for unplaced
        status_badges = []
        if not unplaced.empty:
            for status_val, grp in unplaced.groupby("status"):
                color_map = {
                    "no_accession": "danger",
                    "no_id": "danger",
                    "custom_db": "warning",
                    "non_ncbi_db": "warning",
                    "protein_only_ncbi": "info",
                    "no_coords": "info",
                    "capped": "secondary",
                    "duplicate": "light",
                }
                cls = color_map.get(str(status_val), "secondary")
                status_badges.append(
                    ui.tags.span(
                        f"{status_val}: {len(grp)}",
                        class_=f"badge bg-{cls} text-{'dark' if cls in ('warning','light') else 'white'} me-1",
                    )
                )

        # Top unplaced rows table
        show_df = unplaced.drop(columns=["placed"], errors="ignore").head(15)
        if not show_df.empty:
            thead = ui.tags.thead(ui.tags.tr(*[
                ui.tags.th(c, style="font-size:0.72rem; white-space:nowrap;")
                for c in show_df.columns
            ]))
            trows = [
                ui.tags.tr(*[
                    ui.tags.td(
                        str(v)[:80],
                        style="font-size:0.68rem; max-width:260px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;",
                        title=str(v),
                    )
                    for v in row
                ])
                for row in show_df.itertuples(index=False)
            ]
            table = ui.tags.div(
                ui.tags.table(
                    thead, ui.tags.tbody(*trows),
                    class_="table table-sm table-bordered table-hover mb-0",
                ),
                style="max-height:320px; overflow-y:auto; font-size:0.72rem;",
                class_="mt-2",
            )
        else:
            table = ui.tags.p("All hits placed successfully.", class_="text-success small mt-1")

        return ui.tags.div(
            summary,
            ui.tags.div(*status_badges, class_="mb-2"),
            ui.tags.p(
                "Rows below show unplaced hits with the reason and how to fix them. "
                "Download the full report (⬇ Placement Report button) for all hits.",
                class_="text-muted small",
            ),
            table,
        )

    # ==========================================================================
    # TAB 2: TAXONOMY
    # ==========================================================================

    @reactive.effect
    @reactive.event(input.run_taxonomy)
    async def _on_run_taxonomy():
        pd_ = _proj_dir()
        if pd_ is None:
            return
        script = pd_.parent.parent / "scripts" / "16_taxonomy_analysis.py"
        await _run_script("synteny", [  # reuse synteny log for now
            "python", str(script), "--proj-dir", str(pd_),
        ])

    @output
    @render.ui
    def taxonomy_sankey():
        rd = _results_dir()
        if rd is None:
            return ui.tags.p("No results directory.", class_="text-muted small")
        f = rd / "taxonomy_sankey.html"
        if f.exists():
            return ui.tags.div(ui.HTML(f.read_text()), style="height:450px;overflow:auto;")
        try:
            import pandas as pd
            import plotly.graph_objects as go

            tax_file = rd / "taxonomy_table.tsv"
            if not tax_file.exists():
                return ui.tags.p("Run taxonomy analysis first.", class_="text-muted text-center py-4")
            df = pd.read_csv(tax_file, sep="\t")
            # Build simple Sankey from phylum→class
            if not {"phylum", "class"}.issubset(df.columns):
                return ui.tags.p("Taxonomy table missing phylum/class columns.", class_="text-warning small")
            labels_list = list(set(df["phylum"].dropna()) | set(df["class"].dropna()))
            label_idx = {l: i for i, l in enumerate(labels_list)}
            sources = [label_idx[p] for p in df["phylum"].dropna()]
            targets = [label_idx[c] for c in df["class"].dropna()]
            values = [1] * len(sources)
            fig = go.Figure(go.Sankey(
                node=dict(label=labels_list, pad=15, thickness=20),
                link=dict(source=sources, target=targets, value=values),
            ))
            fig.update_layout(height=400, margin=dict(l=10, r=10, t=20, b=10))
            return _plotly_html(fig)
        except ImportError:
            return ui.tags.p("plotly not installed.", class_="text-warning small")
        except Exception as exc:
            return ui.tags.p(f"Error: {exc}", class_="text-danger small")

    @output
    @render.ui
    def taxonomy_treemap():
        rd = _results_dir()
        if rd is None:
            return ui.tags.p("No results directory.", class_="text-muted small")
        try:
            import pandas as pd
            import plotly.express as px

            tax_file = rd / "taxonomy_table.tsv"
            if not tax_file.exists():
                return ui.tags.p("Run taxonomy analysis first.", class_="text-muted text-center py-4")
            df = pd.read_csv(tax_file, sep="\t")
            path_cols = [c for c in ["superkingdom", "phylum", "class", "genus"] if c in df.columns]
            if not path_cols:
                return ui.tags.p("No taxonomy hierarchy columns found.", class_="text-warning small")
            df["_count"] = 1
            fig = px.treemap(df, path=path_cols, values="_count", height=400)
            fig.update_layout(margin=dict(l=10, r=10, t=20, b=10))
            return _plotly_html(fig)
        except ImportError:
            return ui.tags.p("plotly not installed.", class_="text-warning small")
        except Exception as exc:
            return ui.tags.p(f"Error: {exc}", class_="text-danger small")

    @output
    @render.data_frame
    def taxonomy_outliers():
        import pandas as pd

        rd = _results_dir()
        if rd is None:
            return render.DataGrid(pd.DataFrame(), height="200px")
        f = rd / "taxonomy_outliers.tsv"
        if not f.exists():
            return render.DataGrid(pd.DataFrame(columns=["protein_id", "taxon", "reason"]), height="200px")
        df = pd.read_csv(f, sep="\t")
        return render.DataGrid(df, height="300px", filters=True)

    @render.download(filename="taxonomy_table.tsv")
    def dl_taxonomy_tsv_8():
        rd = _results_dir()
        f = (rd / "taxonomy_table.tsv") if rd else None
        if f and f.exists():
            yield f.read_bytes()

    @render.download(filename="taxonomy_outliers.tsv")
    def dl_taxonomy_outliers_8():
        rd = _results_dir()
        f = (rd / "taxonomy_outliers.tsv") if rd else None
        if f and f.exists():
            yield f.read_bytes()

    # ==========================================================================
    # TAB 3: PHYLOGENETIC TREE
    # ==========================================================================

    @reactive.effect
    @reactive.event(input.run_iqtree)
    async def _on_run_iqtree():
        pd_ = _proj_dir()
        if pd_ is None:
            _log("iqtree", "ERROR: Project dir not set.")
            return
        if not _tool_available("iqtree2") and not _tool_available("iqtree"):
            _log("iqtree", "ERROR: iqtree2/iqtree not found on PATH.")
            return
        hits_aln = None
        for cand in [pd_ / "results" / "hits_aligned.faa", pd_ / "alignments" / "hits_aligned.faa"]:
            if cand.exists():
                hits_aln = cand
                break
        if hits_aln is None:
            _log("iqtree", "ERROR: Aligned hits FASTA not found.")
            return
        exe = "iqtree2" if _tool_available("iqtree2") else "iqtree"
        cmd = [
            exe,
            "-s", str(hits_aln),
            "-m", input.tree_model(),
            "-B", str(max(int(input.tree_bootstrap() or 1000), 1000)),
            "-T", str(input.tree_cpu()),
            "--prefix", str(pd_ / "results" / "tree"),
            "--redo",
        ]
        await _run_script("iqtree", cmd)

    @output
    @render.ui
    def tree_figure():
        rd = _results_dir()
        if rd is None:
            return ui.tags.p("No results directory.", class_="text-muted small")
        for ext in ["tree.png", "tree.svg"]:
            f = rd / ext
            if f.exists():
                if ext.endswith(".png"):
                    b64 = base64.b64encode(f.read_bytes()).decode()
                    return ui.HTML(f'<img src="data:image/png;base64,{b64}" style="max-width:100%;max-height:600px;">')
                else:
                    return ui.HTML(f.read_text())
        return ui.tags.p("Run IQ-TREE to generate the tree figure.", class_="text-muted text-center py-4")

    @output
    @render.text
    def iqtree_log():
        return "\n".join(_logs["iqtree"].get()) or "Waiting…"

    @render.download(filename="tree.treefile")
    def dl_treefile():
        rd = _results_dir()
        f = rd / "tree.treefile" if rd else None
        if f and f.exists():
            yield f.read_bytes()

    @render.download(filename="tree.png")
    def dl_tree_png():
        rd = _results_dir()
        f = rd / "tree.png" if rd else None
        if f and f.exists():
            yield f.read_bytes()

    @render.download(filename="tree.svg")
    def dl_tree_svg():
        rd = _results_dir()
        f = rd / "tree.svg" if rd else None
        if f and f.exists():
            yield f.read_bytes()

    # ==========================================================================
    # TAB 4: PRESENCE/ABSENCE MATRIX
    # ==========================================================================

    @reactive.effect
    @reactive.event(input.run_matrix)
    async def _on_run_matrix():
        pd_ = _proj_dir()
        if pd_ is None:
            return
        script = pd_.parent.parent / "scripts" / "17_presence_absence.py"
        tiers = ",".join(input.matrix_tiers())
        await _run_script("synteny", [
            "python", str(script),
            "--proj-dir", str(pd_),
            "--tiers", tiers,
        ])

    @output
    @render.ui
    def heatmap_figure():
        rd = _results_dir()
        if rd is None:
            return ui.tags.p("No results directory.", class_="text-muted small")
        try:
            import pandas as pd
            import plotly.graph_objects as go

            mat_file = rd / "presence_absence_matrix.tsv"
            if not mat_file.exists():
                return ui.tags.p("Run 'Build Matrix' to generate the heatmap.", class_="text-muted text-center py-4")
            df = pd.read_csv(mat_file, sep="\t", index_col=0)
            if df.empty or df.shape[0] == 0 or df.shape[1] == 0:
                return ui.tags.p(
                    "⚠️ No hits match the selected tiers — adjust tier filters or run the search first.",
                    class_="text-warning text-center py-4",
                )
            fig = go.Figure(go.Heatmap(
                z=df.values,
                x=df.columns.tolist(),
                y=df.index.tolist(),
                colorscale=[[0, "#f8f9fa"], [1, "#0d6efd"]],
                showscale=True,
            ))
            fig.update_layout(
                height=max(300, min(900, 20 * len(df))),
                margin=dict(l=120, r=20, t=20, b=80),
                xaxis=dict(tickangle=-45, tickfont=dict(size=9)),
                yaxis=dict(tickfont=dict(size=9)),
            )
            return _plotly_html(fig)
        except ImportError:
            return ui.tags.p("plotly not installed.", class_="text-warning small")
        except Exception as exc:
            return ui.tags.p(f"Error: {exc}", class_="text-danger small")

    @output
    @render.ui
    def matrix_stats():
        rd = _results_dir()
        if rd is None:
            return ui.tags.span("")
        mat_file = rd / "presence_absence_matrix.tsv" if rd else None
        if not mat_file or not mat_file.exists():
            return ui.tags.span("")
        try:
            import pandas as pd
            df = pd.read_csv(mat_file, sep="\t", index_col=0)
            n_genomes = df.shape[0]   # rows = genomes
            n_proteins = df.shape[1]  # columns = genes/proteins
            col_sums = df.sum(axis=0)  # sum per gene across genomes
            core = (col_sums == n_genomes).sum()
            accessory = ((col_sums > 1) & (col_sums < n_genomes)).sum()
            unique_ = (col_sums == 1).sum()
            return ui.layout_columns(
                stat_card("Genomes", n_genomes, "primary"),
                stat_card("Proteins", n_proteins, "secondary"),
                stat_card("Core", core, "success"),
                stat_card("Accessory", accessory, "warning"),
                stat_card("Unique", unique_, "info"),
                col_widths=[2, 2, 3, 3, 2],
            )
        except Exception as exc:
            return ui.tags.p(f"Error: {exc}", class_="text-danger small")

    # ==========================================================================
    # TAB 5: SEQUENCE CLUSTERS
    # ==========================================================================

    @reactive.effect
    @reactive.event(input.run_clustering)
    async def _on_run_clustering():
        pd_ = _proj_dir()
        if pd_ is None:
            _log("clustering", "ERROR: Project dir not set.")
            return
        tool = input.cluster_tool()
        exe = "cd-hit" if tool == "cd-hit" else "mmseqs"
        if not _tool_available(exe):
            _log("clustering", f"ERROR: {exe} not found on PATH.")
            return
        hits_faa = None
        for cand in [pd_ / "results" / "hits_proteins.faa", pd_ / "hits_proteins.faa"]:
            if cand.exists():
                hits_faa = cand
                break
        if hits_faa is None:
            _log("clustering", "ERROR: hits_proteins.faa not found.")
            return
        out = pd_ / "results" / "cluster_reps.faa"
        identity = input.cluster_identity()
        if tool == "cd-hit":
            cmd = ["cd-hit", "-i", str(hits_faa), "-o", str(out),
                   "-c", str(identity), "-aL", str(input.cluster_coverage()), "-T", "4"]
        else:
            tmp = pd_ / "results" / "mmseqs_tmp"
            tmp.mkdir(exist_ok=True)
            clust_out = pd_ / "results" / "mmseqs_clusters"
            cmd = ["mmseqs", "easy-cluster", str(hits_faa), str(clust_out), str(tmp),
                   "--min-seq-id", str(identity), "-c", str(input.cluster_coverage())]
        await _run_script("clustering", cmd)

    @output
    @render.text
    def cluster_log():
        lines = _logs.get("clustering", reactive.value([])).get()
        return "\n".join(lines) if lines else ""

    @output
    @render.text
    def meme_log():
        lines = _logs.get("meme", reactive.value([])).get()
        return "\n".join(lines) if lines else ""

    @output
    @render.ui
    def cluster_treemap():
        rd = _results_dir()
        if rd is None:
            return ui.tags.p("No results directory.", class_="text-muted small")
        try:
            import pandas as pd
            import plotly.express as px

            clust_file = rd / "cluster_summary.tsv"
            if not clust_file.exists():
                return ui.tags.p("Run clustering to see bubble chart.", class_="text-muted text-center py-4")
            df = pd.read_csv(clust_file, sep="\t")
            fig = px.scatter(
                df,
                x="cluster_id" if "cluster_id" in df.columns else df.index,
                y="cluster_size" if "cluster_size" in df.columns else df.columns[1],
                size="cluster_size" if "cluster_size" in df.columns else df.columns[1],
                hover_data=df.columns.tolist()[:5],
                height=350,
            )
            fig.update_layout(template="plotly_white", margin=dict(l=40, r=20, t=20, b=40))
            return _plotly_html(fig)
        except ImportError:
            return ui.tags.p("plotly not installed.", class_="text-warning small")
        except Exception as exc:
            return ui.tags.p(f"Error: {exc}", class_="text-danger small")

    @output
    @render.data_frame
    def cluster_table():
        import pandas as pd

        rd = _results_dir()
        if rd is None:
            return render.DataGrid(pd.DataFrame(), height="200px")
        f = rd / "cluster_summary.tsv"
        if not f.exists():
            return render.DataGrid(pd.DataFrame(columns=["cluster_id", "cluster_size", "representative"]), height="200px")
        df = pd.read_csv(f, sep="\t")
        return render.DataGrid(df, height="350px", filters=True)

    # ==========================================================================
    # TAB 6: MOTIF DISCOVERY
    # ==========================================================================

    @reactive.effect
    @reactive.event(input.run_meme)
    async def _on_run_meme():
        pd_ = _proj_dir()
        if pd_ is None:
            _log("meme", "ERROR: Project dir not set.")
            return
        if not _tool_available("meme"):
            _log("meme", "ERROR: meme not found on PATH.")
            return
        hits_faa = None
        for cand in [pd_ / "results" / "hits_proteins.faa", pd_ / "hits_proteins.faa"]:
            if cand.exists():
                hits_faa = cand
                break
        if hits_faa is None:
            _log("meme", "ERROR: hits_proteins.faa not found.")
            return
        out_dir = pd_ / "results" / "meme_out"
        out_dir.mkdir(exist_ok=True)
        cmd = [
            "meme", str(hits_faa), "-protein", "-oc", str(out_dir),
            "-nmotifs", str(input.motif_n()),
            "-minw", str(input.motif_min_width()),
            "-maxw", str(input.motif_max_width()),
            "-mod", "zoops",
        ]
        await _run_script("meme", cmd)

    @output
    @render.ui
    def motif_logos():
        rd = _results_dir()
        if rd is None:
            return ui.tags.p("No results directory.", class_="text-muted small")
        meme_dir = rd / "meme_out"
        if not meme_dir.exists():
            return ui.tags.p("Run motif discovery to see logos.", class_="text-muted text-center py-4")
        logo_files = sorted(meme_dir.glob("logo*.png"))
        if not logo_files:
            logo_files = sorted(meme_dir.glob("logo*.eps"))
        if not logo_files:
            return ui.tags.p("No logo files found in meme_out/.", class_="text-muted small")
        imgs = []
        for lf in logo_files[:10]:
            if lf.suffix == ".png":
                b64 = base64.b64encode(lf.read_bytes()).decode()
                imgs.append(ui.tags.div(
                    ui.tags.p(lf.stem, class_="text-muted small mb-0"),
                    ui.HTML(f'<img src="data:image/png;base64,{b64}" style="max-height:80px; margin-right:8px;">'),
                    class_="d-inline-block me-3 mb-2",
                ))
        return ui.tags.div(*imgs, class_="d-flex flex-wrap align-items-center")

    @output
    @render.data_frame
    def fimo_table():
        import pandas as pd

        rd = _results_dir()
        if rd is None:
            return render.DataGrid(pd.DataFrame(), height="200px")
        fimo_tsv = rd / "meme_out" / "fimo.tsv"
        if not fimo_tsv.exists():
            fimo_tsv = rd / "fimo_out" / "fimo.tsv"
        if not fimo_tsv.exists():
            return render.DataGrid(pd.DataFrame(columns=["motif_id", "sequence_name", "start", "stop", "score", "p-value"]), height="200px")
        df = pd.read_csv(fimo_tsv, sep="\t", comment="#")
        return render.DataGrid(df, height="350px", filters=True)

    # ==========================================================================
    # TAB 7: STRUCTURE
    # ==========================================================================

    _structure_log_lines: reactive.Value[list] = reactive.value([])

    @reactive.effect
    @reactive.event(input.run_structure)
    async def _on_run_structure():
        pd_ = _proj_dir()
        if pd_ is None:
            lines = _structure_log_lines.get()
            lines.append("ERROR: Project dir not set.")
            _structure_log_lines.set(lines)
            return
        import shutil as _shutil
        lines = _structure_log_lines.get()

        # Check for Foldseek (preferred) or ESMFold
        if not _shutil.which("foldseek"):
            lines.append("❌ Foldseek not found on PATH.")
            lines.append("   Install with: conda install -c bioconda foldseek")
            lines.append("   Or download from: https://github.com/steineggerlab/foldseek")
            _structure_log_lines.set(lines)
            return

        script = pd_.parent.parent / "scripts" / "20_structure_prediction.py"
        if not script.exists():
            lines.append("❌ Structure prediction script not found.")
            lines.append(f"   Expected at: {script}")
            lines.append("   The structure sub-tab currently requires the project scripts.")
            lines.append("   Alternatively, run Foldseek manually on results/hits_proteins.faa")
            _structure_log_lines.set(lines)
            return
        await _run_script("structure", ["python", str(script), "--proj-dir", str(pd_)])

    @output
    @render.data_frame
    def structure_table():
        import pandas as pd

        rd = _results_dir()
        if rd is None:
            return render.DataGrid(pd.DataFrame(), height="200px")
        f = rd / "structure_results.tsv"
        if not f.exists():
            return render.DataGrid(
                pd.DataFrame(columns=["protein_id", "pdb_path", "foldseek_top_hit", "tmscore"]),
                height="200px",
            )
        df = pd.read_csv(f, sep="\t")
        return render.DataGrid(df, height="350px", filters=True)

    @output
    @render.text
    def structure_log():
        lines = _logs["structure"].get()
        return "\n".join(lines) if lines else "Waiting for structure prediction…"
