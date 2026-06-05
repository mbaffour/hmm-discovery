"""
ui/step_00_setup.py — Database Setup Panel (Step 0).

Lets the user download or register databases before running any searches.
Streaming databases are queried live; downloadable databases need a local copy.
"""
from __future__ import annotations

from pathlib import Path

from shiny import ui

from .components import (
    click_go_strip,
    db_status_card,
    empty_state,
    gene_context_strip,
    guidance_callout,
    learning_card,
    log_panel,
    section_header,
    stat_badge,
    step_card,
    tool_badge,
)


# ---------------------------------------------------------------------------
# Panel UI
# ---------------------------------------------------------------------------

def panel_ui() -> ui.TagChild:
    return ui.nav_panel(
        "Database Setup",
        ui.tags.div(
            # ---- Environment check banner ------------------------------------
            ui.output_ui("env_check_banner"),

            # ---- Auto-install progress card (visible while installing) -------
            ui.output_ui("auto_install_card"),

            # ---- intro -------------------------------------------------------
            ui.tags.p(
                "Download or register databases before searching. "
                "Streaming databases are searched live — no download needed.",
                class_="text-muted mb-3",
            ),
            click_go_strip([
                ("Choose folder", "Create or load a project directory"),
                ("Check tools", "Install missing requirements in-app"),
                ("Add targets", "Register public databases or a single genome"),
                ("Run analysis", "Move through the tabs without writing code"),
            ]),
            gene_context_strip(),
            ui.layout_columns(
                learning_card(
                    "Run modes",
                    [
                        "Single genome: register one nucleotide FASTA here, then scan it in Step 4.",
                        "Selected databases: only checked databases are searched; remote sources download or stream on demand.",
                        "All-database benchmark: validation mode for reviewers; it expands every registered database sequentially.",
                    ],
                    tone="info",
                ),
                learning_card(
                    "Disk behavior",
                    [
                        "Normal searches do not fetch every database.",
                        "Large benchmark databases are processed in chunks and raw cache can be cleared later.",
                        "Keep final tables, reports, figures, HMMs, logs, and reproducibility files for publication.",
                    ],
                    tone="success",
                ),
                learning_card(
                    "Updating the app",
                    [
                        "Pull the newest GitHub version, update the environment, then restart the app server.",
                        "Refresh the browser tab at http://127.0.0.1:8081 after the server restarts.",
                        "Users still run analyses through buttons and forms; no analysis code edits are needed.",
                    ],
                    tone="warning",
                ),
                col_widths=[4, 4, 4],
                class_="mb-3",
            ),

            # ---- database status cards ---------------------------------------
            section_header("Available Databases", "Detected from registry"),
            ui.tags.div(
                ui.input_action_button(
                    "refresh_dbs",
                    "🔄 Refresh Status",
                    class_="btn btn-outline-secondary btn-sm mb-2",
                ),
                class_="mb-1",
            ),
            ui.output_ui("db_cards"),

            # ---- download section --------------------------------------------
            section_header("Downloads", "Databases with a download URL that are not yet local"),
            ui.output_ui("download_section"),
            ui.tags.div(
                log_panel("download_log", height="180px"),
                class_="mt-2",
            ),

            # ---- custom database registration --------------------------------
            ui.tags.div(
                ui.accordion(
                    ui.accordion_panel(
                        "➕ Add Custom Database / Single Genome Target",
                        ui.layout_columns(
                            ui.tags.div(
                                ui.input_text(
                                    "custom_db_name",
                                    "Database name",
                                    placeholder="e.g. my_phage_proteins",
                                ),
                                ui.input_select(
                                    "custom_db_type",
                                    "Molecule type",
                                    {"protein": "Protein", "nucleotide": "Nucleotide"},
                                ),
                            ),
                            ui.tags.div(
                                ui.input_text(
                                    "custom_db_path",
                                    "Local file path (optional)",
                                    placeholder="/path/to/genome.fna or database.faa",
                                ),
                                ui.input_text(
                                    "custom_db_url",
                                    "Download URL (optional)",
                                    placeholder="https://...",
                                ),
                            ),
                            col_widths=[6, 6],
                        ),
                        ui.tags.div(
                            ui.input_text_area(
                                "custom_db_notes",
                                "Notes",
                                placeholder="Any notes about this database...",
                                rows=2,
                            ),
                            class_="mb-2",
                        ),
                        ui.tags.div(
                            ui.tags.strong("Single-genome tip: "),
                            ui.tags.span(
                                "Register a genome FASTA as molecule type Nucleotide, then search it in Step 4. "
                                "Use Exhaustive six-frame ORFs for weird, short, overlapping, or noncanonical genes; "
                                "use Prodigal predicted genes when you want cleaner conventional annotation."
                            ),
                            ui.tags.br(),
                            ui.tags.small(
                                "Seed/input FASTA files are not databases. They build and validate the HMM; target genomes/databases are registered here.",
                                class_="text-muted",
                            ),
                            class_="alert alert-info py-2",
                        ),
                        guidance_callout(
                            "What counts as a database?",
                            "A target database is something you scan against: a genome FASTA, a protein FASTA, or a registered remote source. The seed/input FASTA is reserved for building and validating the HMM, so it is intentionally not offered as a search database.",
                            "secondary",
                        ),
                        ui.input_action_button(
                            "register_custom_db",
                            "Register Database",
                            class_="btn btn-primary btn-sm",
                        ),
                        ui.output_ui("register_feedback"),
                    ),
                    id="setup_accordion",
                    open=False,
                ),
                class_="mt-3",
            ),

            # ---- Environment check section ----------------------------------
            ui.tags.hr(class_="my-4"),
            ui.tags.div(
                ui.accordion(
                    ui.accordion_panel(
                        "🔧 Environment Check",
                        ui.tags.p(
                            "Verify that all required bioinformatics tools are installed "
                            "and on your PATH. Click 'Check Environment' to scan.",
                            class_="text-muted small mb-2",
                        ),
                        ui.tags.div(
                            ui.input_action_button(
                                "run_env_check",
                                "🔍 Check Environment",
                                class_="btn btn-outline-info btn-sm me-2",
                            ),
                            ui.input_action_button(
                                "run_env_install",
                                "⬇️ Install Missing Tools",
                                class_="btn btn-outline-warning btn-sm",
                            ),
                            class_="mb-2",
                        ),
                        ui.output_ui("env_check_results"),
                        ui.tags.div(
                            log_panel("env_install_log", height="150px"),
                            class_="mt-2",
                        ),
                    ),
                    id="env_accordion",
                    open=False,
                ),
                class_="mt-2",
            ),

            # ---- Exhaustive benchmark runner -------------------------------
            ui.tags.hr(class_="my-4"),
            ui.tags.div(
                ui.accordion(
                    ui.accordion_panel(
                        "All-Database Research Validation",
                        ui.tags.p(
                            "Run the same resumable benchmark used for deployment validation from inside the app.",
                            class_="text-muted small mb-2",
                        ),
                        ui.layout_columns(
                            ui.tags.div(
                                ui.input_text(
                                    "benchmark_fasta",
                                    "Input FASTA",
                                    value="example_data/demo_protein_family.fasta",
                                    placeholder="/path/to/seed_sequences.fasta",
                                ),
                                ui.input_action_button(
                                    "benchmark_use_current_input",
                                    "Use Current Project Input",
                                    class_="btn btn-outline-secondary btn-sm",
                                ),
                            ),
                            ui.tags.div(
                                ui.input_text(
                                    "benchmark_out",
                                    "Benchmark output folder",
                                    value=str(Path.home() / "Documents" / "HMM-Discovery-Benchmark"),
                                    placeholder="/path/to/benchmark_outputs",
                                ),
                            ),
                            col_widths=[7, 5],
                        ),
                        ui.layout_columns(
                            ui.input_select(
                                "benchmark_preset",
                                "Database preset",
                                choices={
                                    "smoke": "Smoke test",
                                    "partial": "Real partial",
                                    "all": "All registered databases",
                                },
                                selected="smoke",
                            ),
                            ui.input_numeric(
                                "benchmark_min_free_gb",
                                "Minimum free disk (GiB)",
                                value=20,
                                min=1,
                                step=1,
                            ),
                            ui.input_numeric(
                                "benchmark_cpu",
                                "CPU threads",
                                value=4,
                                min=1,
                                step=1,
                            ),
                            col_widths=[4, 4, 4],
                        ),
                        ui.layout_columns(
                            ui.input_select(
                                "benchmark_nt_orf_mode",
                                "Nucleotide benchmark ORF mode",
                                choices={
                                    "sixframe": "Exhaustive six-frame ORFs (discovery default)",
                                    "prodigal": "Prodigal predicted genes (fast baseline)",
                                },
                                selected="sixframe",
                            ),
                            ui.input_numeric(
                                "benchmark_min_orf_aa",
                                "Six-frame minimum ORF length (aa)",
                                value=30,
                                min=10,
                                step=5,
                            ),
                            col_widths=[7, 5],
                        ),
                        ui.tags.div(
                            ui.tags.strong("Benchmark caveat: "),
                            ui.tags.span(
                                "Use six-frame for unusual-gene discovery claims. Prodigal is useful as a speed/annotation baseline, "
                                "but it can miss short, overlapping, noncanonical, or weird genes."
                            ),
                            class_="alert alert-warning py-2",
                        ),
                        ui.layout_columns(
                            learning_card(
                                "How six-frame works",
                                [
                                    "Forward strand: translate frames +1, +2, and +3.",
                                    "Reverse complement: translate frames -1, -2, and -3.",
                                    "Keep every stop-to-stop peptide above the minimum amino-acid length, then search those peptides with HMMER.",
                                    "Coordinates are retained so a hit can be mapped back to the original genome.",
                                ],
                                tone="success",
                            ),
                            learning_card(
                                "Reviewer-grade setting",
                                [
                                    "Use exhaustive six-frame ORFs when the claim is sensitive to missed small or unusual genes.",
                                    "Keep the benchmark output folder outside the public Git repository.",
                                    "Use the Run Summary and reproducibility JSON when reporting methods.",
                                ],
                                tone="warning",
                            ),
                            learning_card(
                                "When to use Prodigal",
                                [
                                    "Good fast baseline for conventional prokaryotic annotation.",
                                    "Not a complete ORF enumerator.",
                                    "Useful for comparing predicted-gene hits against exhaustive ORF hits.",
                                ],
                                tone="secondary",
                            ),
                            col_widths=[4, 4, 4],
                            class_="mb-2",
                        ),
                        ui.tags.div(
                            ui.input_action_button(
                                "benchmark_dry_run",
                                "Dry-Run Expansion",
                                class_="btn btn-outline-info btn-sm me-2",
                            ),
                            ui.input_action_button(
                                "benchmark_start",
                                "Start / Resume",
                                class_="btn btn-success btn-sm me-2",
                            ),
                            ui.input_action_button(
                                "benchmark_refresh",
                                "Refresh",
                                class_="btn btn-outline-secondary btn-sm me-2",
                            ),
                            ui.input_action_button(
                                "benchmark_stop",
                                "Stop",
                                class_="btn btn-outline-danger btn-sm",
                            ),
                            class_="mb-2",
                        ),
                        ui.output_ui("benchmark_status"),
                        ui.tags.div(
                            log_panel("benchmark_live_log", height="220px"),
                            class_="mt-2",
                        ),
                    ),
                    id="benchmark_accordion",
                    open=False,
                ),
                class_="mt-2",
            ),

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
    # Grab optional collaborators from kwargs (injected by app.py)
    registry = kwargs.get("registry", None)
    auto_install_status_rv = kwargs.get("auto_install_status_rv", None)
    auto_install_log_rv    = kwargs.get("auto_install_log_rv", None)

    def _safe_input_id(name: str) -> str:
        """Return a Shiny-safe input ID: only letters, numbers, underscore."""
        import re as _re
        safe = _re.sub(r"[^a-z0-9_]", "_", name.lower()).strip("_")
        return safe or "database"

    # Internal reactive trigger for manual refresh
    _refresh_trigger = reactive.value(0)
    _install_log: reactive.Value = reactive.value([])
    _benchmark_refresh: reactive.Value = reactive.value(0)
    _benchmark_message: reactive.Value = reactive.value("")

    # ── Auto-install live progress card ────────────────────────────────────
    @output
    @render.ui
    def auto_install_card():
        status = auto_install_status_rv.get() if auto_install_status_rv else "idle"
        if status == "idle":
            return ui.tags.span("")   # nothing to show — all tools already installed

        lines = (auto_install_log_rv.get() if auto_install_log_rv else [])
        log_text = "\n".join(lines[-40:]) if lines else "Starting…"

        if status == "running":
            header = ui.tags.div(
                ui.tags.span("🔧 ", style="font-size:1.1rem"),
                ui.tags.strong("Auto-installing missing tools"),
                ui.tags.span(
                    "  This runs once — the app is usable in the meantime.",
                    class_="text-muted small ms-2",
                ),
                class_="d-flex align-items-center mb-2",
            )
            alert_cls = "alert alert-info"
        elif status == "done":
            header = ui.tags.div(
                ui.tags.span("✅ ", style="font-size:1.1rem"),
                ui.tags.strong("Tools installed — all features ready"),
                class_="d-flex align-items-center mb-2",
            )
            alert_cls = "alert alert-success"
        else:  # failed
            header = ui.tags.div(
                ui.tags.span("⚠️ ", style="font-size:1.1rem"),
                ui.tags.strong("Auto-install did not complete — see log below"),
                ui.tags.small(
                    " Run bash setup_environment.sh in the app folder.",
                    class_="text-muted ms-2",
                ),
                class_="d-flex align-items-center mb-2",
            )
            alert_cls = "alert alert-warning"

        return ui.tags.div(
            header,
            ui.tags.pre(
                log_text,
                style=(
                    "background:#1e1e1e;color:#d4d4d4;font-size:11px;"
                    "max-height:180px;overflow-y:auto;border-radius:4px;"
                    "padding:8px 12px;margin:0;"
                ),
            ),
            class_=f"{alert_cls} mb-3",
        )

    # ---- db_cards ------------------------------------------------------------
    @output
    @render.ui
    def db_cards():
        _refresh_trigger.get()  # reactive dependency
        if registry is None:
            return ui.tags.p("Registry not available.", class_="text-muted")
        dbs = registry.list_all() if hasattr(registry, "list_all") else []
        if not dbs:
            return empty_state(
                "No databases registered yet.",
                icon="🗃️",
                suggestion="Use the 'Add Custom Database' section below, or wait for the registry to load.",
            )
        cards = [db_status_card(db) for db in dbs]
        return ui.layout_columns(*cards, col_widths=[4] * min(len(cards), 3))

    # ---- download_section ----------------------------------------------------
    @output
    @render.ui
    def download_section():
        _refresh_trigger.get()
        if registry is None:
            return ui.tags.span("")
        dbs = registry.list_all() if hasattr(registry, "list_all") else []
        downloadable = [
            db for db in dbs
            if db.get("download_url") and not db.get("path")
        ]
        if not downloadable:
            return ui.tags.p(
                "✅ All downloadable databases are already local.",
                class_="text-success small",
            )
        buttons = []
        for db in downloadable:
            btn_id = f"download_{_safe_input_id(db['name'])}"
            buttons.append(
                ui.tags.div(
                    ui.input_action_button(
                        btn_id,
                        f"⬇️ Download {db['name']}",
                        class_="btn btn-outline-primary btn-sm me-2 mb-1",
                    ),
                    ui.tags.small(
                        db.get("size_hint", ""),
                        class_="text-muted",
                    ),
                    class_="d-inline-flex align-items-center",
                )
            )
        return ui.tags.div(*buttons)

    # ---- download_log --------------------------------------------------------
    @output
    @render.text
    def download_log():
        lines = _install_log.get()
        if lines:
            return "\n".join(lines)
        return "No download in progress. Use the ⬇️ buttons above to download databases."

    # ---- refresh trigger -----------------------------------------------------
    @reactive.effect
    @reactive.event(input.refresh_dbs)
    async def _on_refresh():
        _refresh_trigger.set(_refresh_trigger.get() + 1)

    # ---- register custom db --------------------------------------------------
    @reactive.effect
    @reactive.event(input.register_custom_db)
    async def _on_register_custom_db():
        if registry is None:
            return
        name = (input.custom_db_name() or "").strip()
        if not name:
            return
        registry.register(
            name=name,
            db_type=input.custom_db_type(),
            path=input.custom_db_path() or None,
            url=None,
            download_url=input.custom_db_url() or None,
            notes="",
            streaming=False,
        )
        _refresh_trigger.set(_refresh_trigger.get() + 1)

    # ---- register_feedback ---------------------------------------------------
    @output
    @render.ui
    def register_feedback():
        return ui.tags.span("")

    # =========================================================================
    # Environment check section
    # =========================================================================

    _env_report: reactive.Value[dict | None] = reactive.value(None)
    # _install_log is defined earlier in this function (before download_log)

    def _ilog(msg: str):
        lines = _install_log.get()
        lines.append(msg)
        _install_log.set(lines[-300:])

    # Auto-check on first render (runs once, not triggered by any input)
    @reactive.effect
    def _auto_env_check():
        if _env_report.get() is None:
            try:
                from core.env_setup import check_environment  # type: ignore
                _env_report.set(check_environment())
            except Exception as exc:
                _env_report.set({"error": str(exc)})

    @reactive.effect
    @reactive.event(input.run_env_check)
    async def _on_env_check():
        try:
            from core.env_setup import check_environment  # type: ignore
            report = check_environment()
            _env_report.set(report)
        except Exception as exc:
            _env_report.set({"error": str(exc)})

    @reactive.effect
    @reactive.event(input.run_env_install)
    async def _on_env_install():
        _install_log.set([])
        _ilog("Checking environment before installing…")
        try:
            from core.env_setup import check_environment, install_missing  # type: ignore
            report = check_environment()
            _env_report.set(report)
            _ilog("Starting installation of missing tools…")
            log_lines = install_missing(report)
            for line in log_lines:
                _ilog(line)
            # Re-check after install
            report2 = check_environment()
            _env_report.set(report2)
            _ilog("Re-check complete.")
        except Exception as exc:
            _ilog(f"ERROR: {exc}")

    # ---- Per-tool install buttons -------------------------------------------
    # Dynamically register a handler for every optional tool's install button.
    # We read the OPTIONAL_TOOLS list at render time to create button IDs
    # matching those generated in env_check_results above.

    async def _install_single_tool(tool_name: str, pkg: str, channel: str):
        """Install one conda tool, update the report, refresh UI."""
        _install_log.set([])
        _ilog(f"Installing {tool_name} ({pkg}) from {channel}…")
        try:
            if channel == "pip":
                import subprocess, sys
                cmd = [sys.executable, "-m", "pip", "install", pkg]
                _ilog(f"$ {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if result.returncode == 0:
                    _ilog(f"✅ {tool_name} installed successfully.")
                else:
                    _ilog(f"❌ Install failed:\n{result.stderr[-800:]}")
                try:
                    from pipeline.utils import ensure_tools_on_path  # type: ignore
                    ensure_tools_on_path()
                except Exception:
                    pass
            else:
                from core.env_setup import _find_conda  # type: ignore
                conda = _find_conda()
                if conda:
                    import subprocess, sys
                    cmd = [conda, "install", "-n", "hmm_env", "-y",
                           "-c", channel, "-c", "conda-forge", pkg]
                    _ilog(f"$ {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                    if result.returncode == 0:
                        _ilog(f"✅ {tool_name} installed successfully.")
                    else:
                        _ilog(f"❌ Install failed:\n{result.stderr[-800:]}")
                else:
                    _ilog("❌ conda not found — run: bash setup_environment.sh")
        except Exception as exc:
            _ilog(f"ERROR: {exc}")
        # Re-check environment
        try:
            from core.env_setup import check_environment  # type: ignore
            _env_report.set(check_environment())
        except Exception:
            pass

    # Register per-tool buttons for every optional tool
    try:
        from core.env_setup import OPTIONAL_TOOLS as _OPT  # type: ignore
        for _tool in _OPT:
            _name    = _tool["name"]
            _pkg     = _tool["pkg"]
            _channel = _tool.get("channel", "bioconda")
            _btn_id  = f"install_tool_{_name.replace('-', '_').replace('.', '_')}"

            # Closure capture — default args bind at definition time
            def _make_handler(n=_name, p=_pkg, ch=_channel):
                @reactive.effect
                @reactive.event(input[_btn_id])
                async def _handler():
                    await _install_single_tool(n, p, ch)
                return _handler

            _make_handler()
    except Exception:
        pass  # env_setup not available; buttons just won't fire

    @output
    @render.ui
    def env_check_banner():
        """Show a warning bar at the top of the panel if required tools are missing."""
        report = _env_report.get()
        if report is None:
            return ui.tags.span("")  # _auto_env_check will populate shortly

        if report.get("error"):
            return ui.tags.div(
                ui.tags.strong("⚠️ Environment check failed: "),
                report["error"],
                class_="alert alert-danger mb-3",
            )
        if report.get("all_full_run_ok"):
            return ui.tags.div(
                "✅ Full-run environment is installed.",
                class_="alert alert-success mb-3",
            )
        missing_tools = [
            t["name"] for t in report.get("required_tools", []) if not t["available"]
        ]
        missing_py = [
            p["pkg"] for p in report.get("python_packages", []) if not p["ok"]
        ]
        missing_full_tools = [
            t["name"] for t in report.get("missing_full_run_tools", [])
            if t.get("auto_install", True)
        ]
        parts = []
        if missing_tools:
            parts.append(f"Missing tools: {', '.join(missing_tools)}")
        if missing_full_tools:
            parts.append(f"Missing full-run tools: {', '.join(missing_full_tools)}")
        if missing_py:
            parts.append(f"Missing Python packages: {', '.join(missing_py)}")
        return ui.tags.div(
            ui.tags.strong("⚠️ Environment setup incomplete. "),
            " | ".join(parts),
            ui.tags.br(),
            ui.tags.small(
                "Open the 'Environment Check' section below and click "
                "'Install Missing Tools' or run: ",
                ui.tags.code(report.get("install_cmd", "bash setup_environment.sh")),
            ),
            class_="alert alert-warning mb-3",
        )

    @output
    @render.ui
    def env_check_results():
        report = _env_report.get()
        if report is None:
            return ui.tags.p(
                "Click 'Check Environment' to scan for installed tools.",
                class_="text-muted small",
            )
        if report.get("error"):
            return ui.tags.p(report["error"], class_="text-danger small")

        def _row(name, available, path, required, desc):
            icon  = "✅" if available else ("❌" if required else "⚠️")
            badge = (
                ui.tags.span("required", class_="badge bg-danger ms-1")
                if required and not available
                else ui.tags.span("optional", class_="badge bg-secondary ms-1")
                if not required
                else ui.tags.span("ok", class_="badge bg-success ms-1")
            )
            return ui.tags.tr(
                ui.tags.td(f"{icon} {name}"),
                ui.tags.td(badge),
                ui.tags.td(ui.tags.small(path or "not found", class_="font-monospace text-muted")),
                ui.tags.td(ui.tags.small(desc)),
            )

        def _tool_row(name, available, path, required, desc, pkg, channel):
            icon  = "✅" if available else ("❌" if required else "⚠️")
            badge = (
                ui.tags.span("required", class_="badge bg-danger ms-1")
                if required and not available
                else ui.tags.span("optional", class_="badge bg-secondary ms-1")
                if not required and not available
                else ui.tags.span("installed", class_="badge bg-success ms-1")
            )
            # Per-tool install button for missing tools
            install_btn = ui.tags.span("")
            if not available:
                btn_id = f"install_tool_{name.replace('-', '_').replace('.', '_')}"
                install_btn = ui.input_action_button(
                    btn_id,
                    f"⬇ Install",
                    class_="btn btn-outline-warning btn-xs py-0 px-1",
                    style="font-size:0.7rem;",
                )
            return ui.tags.tr(
                ui.tags.td(f"{icon} {name}"),
                ui.tags.td(badge, install_btn),
                ui.tags.td(ui.tags.small(path or "not found", class_="font-monospace text-muted")),
                ui.tags.td(ui.tags.small(desc)),
            )

        req_rows = [
            _tool_row(t["name"], t["available"], t.get("path"), True,
                      t.get("desc", ""), t.get("pkg", ""), t.get("channel", "bioconda"))
            for t in report.get("required_tools", [])
        ]
        # Show ALL optional tools — installed and missing — so users know what to install
        opt_rows = [
            _tool_row(t["name"], t["available"], t.get("path"), False,
                      t.get("desc", ""), t.get("pkg", ""), t.get("channel", "bioconda"))
            for t in report.get("optional_tools", [])
        ]
        py_rows = []
        for p in report.get("python_packages", []):
            icon = "✅" if p["ok"] else "❌"
            version_req = f"need ≥{p.get('min_version','?')}"
            if p.get("max_version"):
                version_req += f", <{p.get('max_version')}"
            if p.get("error"):
                version_req += f"; import error: {p.get('error')}"
            py_rows.append(
                ui.tags.tr(
                    ui.tags.td(f"{icon} {p['pkg']}"),
                    ui.tags.td(
                        ui.tags.span("installed", class_="badge bg-success")
                        if p["ok"]
                        else ui.tags.span("update needed", class_="badge bg-warning text-dark")
                    ),
                    ui.tags.td(
                        ui.tags.small(
                            f"{p.get('version','?')} ({version_req})",
                            class_="font-monospace text-muted",
                        )
                    ),
                    ui.tags.td(ui.tags.small("")),
                )
            )

        # Count missing optional tools
        missing_opt = [t for t in report.get("optional_tools", []) if not t["available"]]
        opt_note = ui.tags.div(
            ui.tags.small(
                f"⚠️ {len(missing_opt)} optional tool(s) not installed. "
                "These enable extra features (phylogenetics, motif discovery, etc.). "
                "Click ⬇ Install next to each, or click 'Install Missing Tools' above "
                "to install all at once.",
                class_="text-warning",
            ),
            class_="mb-2",
        ) if missing_opt else ui.tags.span("")

        return ui.tags.div(
            ui.tags.small(
                f"Python {report.get('python_version','?')} on {report.get('platform','?')}",
                class_="text-muted d-block mb-2",
            ),
            opt_note,
            ui.tags.h6("Required Tools", class_="mt-2 mb-1"),
            ui.tags.table(
                ui.tags.thead(
                    ui.tags.tr(
                        ui.tags.th("Tool"),
                        ui.tags.th("Status"),
                        ui.tags.th("Path"),
                        ui.tags.th("Description"),
                    )
                ),
                ui.tags.tbody(*req_rows),
                class_="table table-sm table-bordered mb-3",
            ),
            ui.tags.h6("Optional Tools", class_="mt-2 mb-1"),
            ui.tags.table(
                ui.tags.thead(
                    ui.tags.tr(
                        ui.tags.th("Tool"),
                        ui.tags.th("Status"),
                        ui.tags.th("Path"),
                        ui.tags.th("Description"),
                    )
                ),
                ui.tags.tbody(*opt_rows),
                class_="table table-sm table-bordered mb-3",
            ),
            ui.tags.h6("Python Packages", class_="mt-2 mb-1"),
            ui.tags.table(
                ui.tags.thead(
                    ui.tags.tr(
                        ui.tags.th("Package"),
                        ui.tags.th("Status"),
                        ui.tags.th("Version"),
                        ui.tags.th(""),
                    )
                ),
                ui.tags.tbody(*py_rows),
                class_="table table-sm table-bordered",
            ),
            ui.tags.small(
                "Install command: ",
                ui.tags.code(report.get("install_cmd", "# All installed ✓")),
                class_="text-muted d-block mt-2",
            ),
        )

    @output
    @render.text
    def env_install_log():
        lines = _install_log.get()
        return "\n".join(lines) if lines else "Install log will appear here…"

    # =========================================================================
    # All-database benchmark section
    # =========================================================================

    def _benchmark_form() -> dict:
        app_dir = Path(kwargs.get("app_dir") or Path(__file__).resolve().parents[1])
        return {
            "app_dir": app_dir,
            "fasta": input.benchmark_fasta() or "example_data/demo_protein_family.fasta",
            "out_dir": input.benchmark_out() or str(Path.home() / "Documents" / "HMM-Discovery-Benchmark"),
            "preset": input.benchmark_preset() or "smoke",
            "min_free_gb": float(input.benchmark_min_free_gb() or 20),
            "cpu": int(input.benchmark_cpu() or 4),
            "nt_orf_mode": input.benchmark_nt_orf_mode() or "sixframe",
            "min_orf_aa": int(input.benchmark_min_orf_aa() or 30),
        }

    @reactive.effect
    @reactive.event(input.benchmark_use_current_input)
    async def _on_benchmark_use_current_input():
        current = None
        try:
            current = state.get_project("input_path")
        except Exception:
            current = None
        if not current:
            try:
                params = state.get_params("input") or {}
                current = params.get("input_path")
            except Exception:
                current = None
        if current:
            ui.update_text("benchmark_fasta", value=str(current))
            _benchmark_message.set("Using the current analyzed input FASTA.")
        else:
            _benchmark_message.set("No analyzed project input found yet. Use Step 1 first or enter a FASTA path.")
        _benchmark_refresh.set(_benchmark_refresh.get() + 1)

    @reactive.effect
    @reactive.event(input.benchmark_dry_run)
    async def _on_benchmark_dry_run():
        try:
            from core.benchmark import launch_benchmark

            cfg = _benchmark_form()
            result = launch_benchmark(**cfg, dry_run=True)
            _benchmark_message.set(
                f"Dry-run launched with PID {result.get('pid')}."
                if result.get("status") == "started"
                else f"Dry-run status: {result.get('status')}."
            )
            ui.notification_show(_benchmark_message.get(), type="message", duration=5)
        except Exception as exc:
            _benchmark_message.set(f"Dry-run could not start: {exc}")
            ui.notification_show(_benchmark_message.get(), type="error", duration=8)
        _benchmark_refresh.set(_benchmark_refresh.get() + 1)

    @reactive.effect
    @reactive.event(input.benchmark_start)
    async def _on_benchmark_start():
        try:
            from core.benchmark import launch_benchmark

            cfg = _benchmark_form()
            result = launch_benchmark(**cfg, dry_run=False)
            if result.get("status") == "already_running":
                msg = f"Benchmark is already running with PID {result.get('pid')}."
            else:
                msg = f"Benchmark started with PID {result.get('pid')}."
            _benchmark_message.set(msg)
            ui.notification_show(msg, type="message", duration=5)
        except Exception as exc:
            _benchmark_message.set(f"Benchmark could not start: {exc}")
            ui.notification_show(_benchmark_message.get(), type="error", duration=8)
        _benchmark_refresh.set(_benchmark_refresh.get() + 1)

    @reactive.effect
    @reactive.event(input.benchmark_stop)
    async def _on_benchmark_stop():
        try:
            from core.benchmark import stop_benchmark

            cfg = _benchmark_form()
            result = stop_benchmark(cfg["out_dir"])
            _benchmark_message.set(f"Stop request: {result.get('status')} PID {result.get('pid', '')}")
            ui.notification_show(_benchmark_message.get(), type="warning", duration=5)
        except Exception as exc:
            _benchmark_message.set(f"Stop request failed: {exc}")
            ui.notification_show(_benchmark_message.get(), type="error", duration=8)
        _benchmark_refresh.set(_benchmark_refresh.get() + 1)

    @reactive.effect
    @reactive.event(input.benchmark_refresh)
    async def _on_benchmark_refresh():
        _benchmark_refresh.set(_benchmark_refresh.get() + 1)

    @output
    @render.ui
    def benchmark_status():
        _benchmark_refresh.get()
        from core.benchmark import (
            benchmark_is_running,
            current_pid,
            log_path,
            manifest_path,
            read_manifest,
            resolve_path,
        )

        cfg = _benchmark_form()
        out_dir = resolve_path(cfg["out_dir"], cfg["app_dir"])
        manifest = read_manifest(out_dir)
        running = benchmark_is_running(out_dir)
        if running:
            reactive.invalidate_later(5)

        status = manifest.get("status") or ("running" if running else "not_started")
        badge_cls = {
            "complete": "bg-success",
            "dry_run_complete": "bg-info text-dark",
            "running": "bg-warning text-dark",
            "failed": "bg-danger",
            "not_started": "bg-secondary",
        }.get(status, "bg-secondary")

        selected = manifest.get("selected_databases", []) or []
        databases = manifest.get("databases", {}) or {}
        active = manifest.get("active_command", {}) or {}
        nt_mode = active.get("nt_orf_mode") or cfg.get("nt_orf_mode", "sixframe")
        rows = []
        dry_rows = manifest.get("dry_run", []) if status == "dry_run_complete" else []
        if dry_rows:
            for rec in dry_rows:
                rows.append(
                    ui.tags.tr(
                        ui.tags.td(ui.tags.small(rec.get("database", ""))),
                        ui.tags.td(ui.tags.small("listed")),
                        ui.tags.td(ui.tags.small("")),
                        ui.tags.td(ui.tags.small(str(rec.get("file_count", "")))),
                        ui.tags.td(ui.tags.small(str(rec.get("first_url", ""))[:120])),
                    )
                )
        order = [] if dry_rows else (selected or list(databases.keys()))
        for name in order:
            rec = databases.get(name, {})
            db_status = rec.get("status", "queued")
            hits = rec.get("hit_count", "")
            files = rec.get("file_count", "")
            error = rec.get("error") or rec.get("message") or ""
            rows.append(
                ui.tags.tr(
                    ui.tags.td(ui.tags.small(name)),
                    ui.tags.td(ui.tags.small(db_status)),
                    ui.tags.td(ui.tags.small(str(hits))),
                    ui.tags.td(ui.tags.small(str(files))),
                    ui.tags.td(ui.tags.small(str(error)[:120])),
                )
            )
        if not rows:
            rows.append(
                ui.tags.tr(
                    ui.tags.td(
                        ui.tags.small("No manifest yet. Start with Dry-Run Expansion or Start / Resume."),
                        colspan="5",
                    )
                )
            )

        report = out_dir / "reports" / "all_database_benchmark_report.html"
        report_link = (
            ui.tags.a("Open benchmark report", href=str(report), target="_blank", class_="btn btn-outline-info btn-sm")
            if report.exists()
            else ui.tags.span("")
        )

        msg = _benchmark_message.get()
        return ui.tags.div(
            ui.layout_columns(
                stat_badge("status", status, "secondary"),
                stat_badge("PID", str(current_pid(out_dir) or "-"), "primary"),
                stat_badge("selected DBs", str(len(selected)), "info"),
                stat_badge("process", "running" if running else "stopped", "warning" if running else "secondary"),
                col_widths=[3, 3, 3, 3],
            ),
            ui.tags.div(
                ui.tags.span(status, class_=f"badge {badge_cls} me-2"),
                ui.tags.span(f"nucleotide mode: {nt_mode}", class_="badge bg-light text-dark me-2"),
                ui.tags.small(msg, class_="text-muted"),
                class_="mb-2",
            ),
            ui.tags.small("Manifest: ", class_="text-muted"),
            ui.tags.code(str(manifest_path(out_dir))),
            ui.tags.br(),
            ui.tags.small("Log: ", class_="text-muted"),
            ui.tags.code(str(log_path(out_dir))),
            ui.tags.div(report_link, class_="mt-2 mb-2"),
            ui.tags.div(
                ui.tags.table(
                    ui.tags.thead(
                        ui.tags.tr(
                            ui.tags.th("Database"),
                            ui.tags.th("Status"),
                            ui.tags.th("Hits"),
                            ui.tags.th("Files"),
                            ui.tags.th("Message"),
                        )
                    ),
                    ui.tags.tbody(*rows),
                    class_="table table-sm table-bordered mb-0",
                ),
                style="max-height:260px; overflow:auto;",
                class_="mt-2",
            ),
        )

    @output
    @render.text
    def benchmark_live_log():
        _benchmark_refresh.get()
        from core.benchmark import benchmark_is_running, tail_log, resolve_path

        cfg = _benchmark_form()
        out_dir = resolve_path(cfg["out_dir"], cfg["app_dir"])
        if benchmark_is_running(out_dir):
            reactive.invalidate_later(5)
        return tail_log(out_dir, max_lines=80)
