"""
HMM Protein Family Discovery App
==================================
A Shiny for Python web application for profile HMM-based protein family
discovery. Supports any protein family — phage, bacterial, or eukaryotic.

Usage:
    shiny run scripts/hmm_discovery_app/app.py --port 8080 --reload

Or with the helper script:
    source activate_hmm.sh && shiny run ...
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure our package is importable regardless of CWD
APP_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(APP_DIR))

# Make all conda-env bioinformatics tools (gs, mafft, hmmer, iqtree, …)
# discoverable by in-process libraries before anything else imports them.
try:
    from pipeline.utils import ensure_tools_on_path
    ensure_tools_on_path()
except Exception:
    pass

from shiny import App, Inputs, Outputs, Session, reactive, render, ui
import shinyswatch

# Core infrastructure
from core.runner import AsyncJobRunner
from core.state import PipelineState
from core.logger import AuditLogger, check_tools
from core.sessions import add_recent, load_recents, save_note, load_notes

# Database layer
from databases.registry import DatabaseRegistry

# Pipeline modules (injected into step register_outputs as kwargs)
_pipeline_modules: dict = {}
try:
    from pipeline import input_handler as _input_handler
    from pipeline import alignment as _alignment
    from pipeline import hmm_builder as _hmm_builder
    from pipeline import searcher as _searcher
    from pipeline import confidence as _confidence
    from pipeline import hit_classifier as _hit_classifier
    from pipeline import iterative as _iterative
    from pipeline import synteny as _synteny
    from pipeline import phylo as _phylo
    from pipeline import matrix as _matrix
    from pipeline import reporter as _reporter
    from pipeline import taxonomy as _taxonomy
    from pipeline import clustering as _clustering
    from pipeline import motifs as _motifs
    from pipeline import annotation as _annotation
    _pipeline_modules = dict(
        input_handler=_input_handler,
        alignment=_alignment,
        hmm_builder=_hmm_builder,
        searcher=_searcher,
        confidence=_confidence,
        hit_classifier=_hit_classifier,
        iterative=_iterative,
        synteny=_synteny,
        phylo=_phylo,
        matrix=_matrix,
        reporter=_reporter,
        taxonomy=_taxonomy,
        clustering=_clustering,
        motifs=_motifs,
        annotation=_annotation,
    )
except Exception as _e:
    import sys as _sys
    print(f"WARNING: Could not import pipeline modules: {_e}", file=_sys.stderr)

# UI panels
from ui.components import stat_card, tool_badge
from ui import (
    step_00_setup,
    step_01_input,
    step_02_msa,
    step_03_hmm,
    step_04_search,
    step_05_validate,
    step_06_iteration,
    step_07_results,
    step_08_analysis,
    step_09_export,
)

# ---------------------------------------------------------------------------
# App UI
# ---------------------------------------------------------------------------

def _css_tag() -> ui.Tag:
    """Load and inline www/styles.css so it's always applied regardless of
    how the app is launched (avoids static-asset path issues)."""
    try:
        css = (APP_DIR / "www" / "styles.css").read_text()
    except Exception:
        css = ""
    return ui.tags.style(css)


def make_ui():
    return ui.page_sidebar(
        # ── Sidebar ────────────────────────────────────────────────────
        ui.sidebar(
            ui.tags.div(
                ui.tags.h6("🧬 HMM Discovery", class_="mb-0 text-white"),
                ui.tags.small("Protein family discovery", class_="text-white-50"),
                class_="mb-3",
            ),

            # Recent projects dropdown
            ui.tags.div(
                ui.output_ui("recent_projects_ui"),
                class_="mb-2",
            ),

            # Project directory
            ui.tags.div(
                ui.input_text(
                    "proj_dir",
                    "Project directory",
                    value=str(Path.home() / "Documents" / "HMM_Projects" / "my_project"),
                    placeholder="/path/to/project",
                ),
                ui.layout_columns(
                    ui.input_action_button(
                        "load_project", "📂 Load",
                        class_="btn btn-outline-light btn-sm w-100 mt-1",
                    ),
                    ui.input_action_button(
                        "reset_project", "🗑 Reset",
                        class_="btn btn-outline-danger btn-sm w-100 mt-1",
                        title="Delete all pipeline outputs and start this project over",
                    ),
                    col_widths=[7, 5],
                ),
                ui.tags.small(
                    "One folder per protein family. Reset clears all outputs but keeps your input file.",
                    class_="text-white-50",
                    style="font-size:0.7rem; line-height:1.3; display:block; margin-top:4px;",
                ),
                class_="mb-2",
            ),

            # New project creator
            ui.tags.div(
                ui.input_text(
                    "new_proj_name", None,
                    placeholder="new_project_name",
                ),
                ui.input_action_button(
                    "create_project", "✨ Create New Project",
                    class_="btn btn-outline-success btn-sm w-100 mt-1",
                ),
                class_="mb-3",
            ),

            # Project status
            ui.output_ui("project_status"),

            # Session notes
            ui.output_ui("session_history_ui"),

            # Save session note
            ui.tags.div(
                ui.input_text(
                    "session_note", None,
                    placeholder="Note: what did I just do?",
                ),
                ui.input_action_button(
                    "save_session_note", "💾 Save Note",
                    class_="btn btn-outline-light btn-sm w-100 mt-1",
                ),
                class_="mb-2",
            ),

            ui.tags.hr(class_="border-secondary"),

            # Complexity toggle
            ui.tags.div(
                ui.tags.label("Complexity mode", class_="form-label text-white-50 small"),
                ui.input_radio_buttons(
                    "complexity_mode", None,
                    choices={"beginner": "Beginner", "advanced": "Advanced"},
                    selected="beginner",
                    inline=True,
                ),
                class_="sidebar-mode-section mb-2",
            ),

            # Biology context
            ui.tags.div(
                ui.tags.label("Biology context", class_="form-label text-white-50 small"),
                ui.input_radio_buttons(
                    "biology_mode", None,
                    choices={"generic": "Generic", "phage": "Phage", "bacterial": "Bacterial"},
                    selected="generic",
                    inline=True,
                ),
                class_="mb-3",
            ),

            ui.tags.div(
                ui.tags.div(
                    ui.tags.strong("Workflow coach", class_="d-block text-white mb-1"),
                    ui.tags.ul(
                        ui.tags.li(ui.tags.small("Normal runs only use databases you select.", class_="text-white-50")),
                        ui.tags.li(ui.tags.small("For single genomes or weird genes, register a nucleotide FASTA and use six-frame ORFs.", class_="text-white-50")),
                        ui.tags.li(ui.tags.small("Generate a Run Summary before export or cleanup.", class_="text-white-50")),
                        class_="ps-3 mb-0",
                    ),
                    class_="workflow-coach",
                ),
                class_="mb-3",
            ),

            # Step nav (shows completion status)
            ui.output_ui("step_nav"),

            # Help link
            ui.tags.div(
                ui.tags.a(
                    "📖 User Guide",
                    href="guide.html",
                    target="_blank",
                    class_="btn btn-outline-light btn-sm w-100 mt-2",
                ),
                class_="mt-auto pt-3",
            ),

            width=300,
            bg="#212529",
            fg="white",
            open="desktop",
        ),

        # ── Main content (tabbed) ───────────────────────────────────────
        # Each panel_ui() already returns a ui.nav_panel(); use directly.
        ui.navset_tab(
            step_00_setup.panel_ui(),
            step_01_input.panel_ui(),
            step_02_msa.panel_ui(),
            step_03_hmm.panel_ui(),
            step_04_search.panel_ui(),
            step_05_validate.panel_ui(),
            step_06_iteration.panel_ui(),
            step_07_results.panel_ui(),
            step_08_analysis.panel_ui(),
            step_09_export.panel_ui(),
            id="main_nav",
        ),

        # Page options
        title="HMM Discovery",
        theme=shinyswatch.theme.darkly(),
        fillable=True,
        lang="en",
    )


def _make_ui_with_css():
    """Wrap make_ui() output with our inline stylesheet injected into the page."""
    page = make_ui()
    # Shiny for Python page objects are htmltools Tag trees — append the style tag
    try:
        page.children.insert(0, _css_tag())
    except Exception:
        pass
    return page


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class _StateProxy:
    """Transparent proxy so step files can call state.method() while state_rv
    may still be None (before a project is loaded).  Each attribute access
    resolves the current PipelineState from the reactive value at call time.
    Returns a no-op callable when no project is loaded yet."""

    def __init__(self, rv):
        object.__setattr__(self, "_rv", rv)

    def __getattr__(self, name: str):
        val = object.__getattribute__(self, "_rv").get()
        if val is None:
            # Return a safe no-op lambda so callers don't raise AttributeError
            return lambda *a, **kw: None
        return getattr(val, name)

    def __bool__(self) -> bool:
        return object.__getattribute__(self, "_rv").get() is not None


class _RegistryProxy:
    """Transparent proxy for DatabaseRegistry — delegates to registry_rv.get()."""

    def __init__(self, rv):
        object.__setattr__(self, "_rv", rv)

    def __getattr__(self, name: str):
        val = object.__getattribute__(self, "_rv").get()
        if val is None:
            if name in ("get_all", "list_all", "get_enabled"):
                return lambda *a, **kw: []
            return lambda *a, **kw: None
        return getattr(val, name)

    def __bool__(self) -> bool:
        return object.__getattribute__(self, "_rv").get() is not None


def server(input: Inputs, output: Outputs, session: Session):
    # ── Auto-install reactive state ─────────────────────────────────────
    # Tracks whether auto-install is running, completed, or idle.
    # "idle" | "running" | "done" | "failed"
    _auto_install_status: reactive.Value[str] = reactive.value("idle")
    _auto_install_log: reactive.Value[list[str]] = reactive.value([])

    def _ilog(line: str) -> None:
        lines = _auto_install_log.get()
        lines.append(line)
        _auto_install_log.set(lines[-500:])

    # ── First-run environment check + auto-install ──────────────────────
    # Runs ONCE when the session opens (the _ran guard prevents re-firing
    # on subsequent reactive flushes, which would hammer check_environment).
    _startup_ran = False   # plain bool — not reactive, so no re-invalidation

    @reactive.effect
    async def _startup_env_check():
        nonlocal _startup_ran
        if _startup_ran:
            return
        _startup_ran = True
        import asyncio as _asyncio
        try:
            from core.env_setup import check_environment, auto_install_async
            env = check_environment()

            if env.get("all_full_run_ok"):
                # Everything needed for a full pipeline run is installed.
                return

            # Missing something — show a brief notification then auto-install
            missing_tools = [
                t["name"] for t in env.get("required_tools", []) if not t["available"]
            ]
            missing_tools += [
                t["name"] for t in env.get("missing_full_run_tools", [])
                if t.get("auto_install", True)
            ]
            missing_py = [
                p["pkg"] for p in env.get("python_packages", []) if not p["ok"]
            ]
            parts = []
            if missing_tools:
                parts.append(f"tools: {', '.join(missing_tools)}")
            if missing_py:
                parts.append(f"packages: {', '.join(missing_py)}")

            if not env.get("conda_available"):
                # No conda — can't auto-install, just warn
                ui.notification_show(
                    f"⚠️ Missing {'; '.join(parts)}. "
                    "Run bash setup_environment.sh to install.",
                    type="warning",
                    duration=12,
                )
                return

            ui.notification_show(
                f"🔧 Auto-installing missing {'; '.join(parts)} — "
                "this happens once and takes a minute or two. "
                "The app is usable in the meantime.",
                type="message",
                duration=8,
            )
            _auto_install_status.set("running")
            _ilog("Starting auto-install of missing tools…")

            success = await auto_install_async(
                log_callback=_ilog,
                include_optional=False,   # required + full-run essentials
            )

            if success:
                _auto_install_status.set("done")
                ui.notification_show(
                    "✅ Tools installed successfully — all features now available.",
                    type="message",
                    duration=6,
                )
            else:
                _auto_install_status.set("failed")
                ui.notification_show(
                    "⚠️ Some tools could not be installed automatically. "
                    "Open Database Setup → Environment Check for details.",
                    type="warning",
                    duration=10,
                )
        except Exception as _exc:
            _auto_install_status.set("failed")
            _ilog(f"Auto-install error: {_exc}")

    # ── Reactive state ──────────────────────────────────────────────────
    proj_dir_rv: reactive.Value[Path] = reactive.value(Path.cwd())
    state_rv: reactive.Value[PipelineState | None] = reactive.value(None)
    registry_rv: reactive.Value[DatabaseRegistry | None] = reactive.value(None)
    tools_rv: reactive.Value[dict] = reactive.value({})
    audit_rv: reactive.Value[AuditLogger | None] = reactive.value(None)
    hits_df_rv: reactive.Value = reactive.value(None)

    # Per-step runners
    runners: dict[str, AsyncJobRunner] = {
        "msa":       AsyncJobRunner("msa"),
        "hmm":       AsyncJobRunner("hmm_build"),
        "search":    AsyncJobRunner("search"),
        "validate":  AsyncJobRunner("validate"),
        "iterate":   AsyncJobRunner("iterate"),
        "synteny":   AsyncJobRunner("synteny"),
        "phylo":     AsyncJobRunner("phylo"),
        "clusters":  AsyncJobRunner("clusters"),
        "motifs":    AsyncJobRunner("motifs"),
        "structure": AsyncJobRunner("structure"),
        "export":    AsyncJobRunner("export"),
    }

    # ── Auto-load default project on first session start ────────────────
    # So the pipeline always has a valid working directory even if the
    # user never touches the sidebar.
    _project_loaded = False

    @reactive.effect
    async def _auto_load_default():
        nonlocal _project_loaded
        if _project_loaded:
            return
        _project_loaded = True
        # Read reactive input BEFORE the await — reactive context is lost after await
        raw = input.proj_dir().strip()
        import asyncio as _aio
        await _aio.sleep(0.5)          # let the UI finish rendering first
        _do_load_project(raw)

    # ── Project load ────────────────────────────────────────────────────
    @reactive.effect
    @reactive.event(input.load_project)
    def _load_project():
        raw = input.proj_dir().strip()
        if not raw:
            ui.notification_show("Please enter a project directory path.", type="warning")
            return
        _do_load_project(raw)

    def _do_load_project(raw: str):
        if not raw:
            return
        proj = Path(raw)
        proj.mkdir(parents=True, exist_ok=True)

        # Initialise state, logger, registry
        state = PipelineState(proj)
        audit = AuditLogger(proj)
        tools = check_tools(proj)
        registry = DatabaseRegistry(proj)

        # Update runners with audit logger
        for name, runner in runners.items():
            runner.audit = audit
            runner.step_name = name

        proj_dir_rv.set(proj)
        state_rv.set(state)
        audit_rv.set(audit)
        tools_rv.set(tools)
        registry_rv.set(registry)

        # Seed/input FASTA files are not databases. Older app versions
        # auto-registered them as custom DBs; prune those entries on load so
        # searches use only built-ins or databases the user explicitly adds.
        _input_path = state.get_project("input_path", "")
        try:
            _ip = Path(_input_path).resolve() if _input_path else None
            _project = proj.resolve()

            def _inside_project(path: Path) -> bool:
                try:
                    path.relative_to(_project)
                    return True
                except Exception:
                    return False

            for _db in registry.get_all():
                _name = str(_db.get("name", ""))
                _path_raw = _db.get("path") or ""
                if not _path_raw:
                    continue
                _path = Path(_path_raw).expanduser().resolve()
                _lname = _name.lower()
                _looks_like_seed = (
                    _lname in {"seed", "seeds", "seed_sequences"}
                    or _lname.endswith("_seed_sequences")
                    or _path.parent.name.lower() in {"seed", "seeds", "input", "data"}
                )
                if _lname in {"seed", "seeds", "seed_sequences"} or _lname.endswith("_seed_sequences"):
                    registry.remove(_name)
                elif (_ip and _path == _ip) or (_inside_project(_path) and _looks_like_seed):
                    registry.remove(_name)
        except Exception:
            pass

        # Record in recent projects
        add_recent(str(proj))
        # Show last session note if any
        notes = load_notes(proj, last_n=1)
        if notes:
            last = notes[0]
            ts = last.get("timestamp", "")[:16].replace("T", " ")
            note_txt = last.get("note", "")
            if note_txt:
                ui.notification_show(
                    f"📝 Last session ({ts}): {note_txt}",
                    type="message",
                    duration=6,
                )

        ui.notification_show(
            f"Project loaded: {proj.name}",
            type="message",
            duration=3,
        )

    # ── Create new project ──────────────────────────────────────────────
    @reactive.effect
    @reactive.event(input.create_project)
    def _on_create_project():
        raw = (input.new_proj_name() or "").strip()
        import re
        safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", raw)
        if not safe:
            ui.notification_show("Enter a project name first.", type="warning")
            return
        base = Path.home() / "Documents" / "HMM_Projects"
        proj = base / safe
        proj.mkdir(parents=True, exist_ok=True)
        ui.update_text("proj_dir", value=str(proj))
        _do_load_project(str(proj))

    # ── Recent projects dropdown ────────────────────────────────────────
    @output
    @render.ui
    def recent_projects_ui():
        recents = load_recents()
        if not recents:
            return ui.tags.small(
                "No recent projects",
                class_="text-white-50 d-block",
                style="font-size:0.78rem;",
            )
        choices = {"": "— Open recent project —"}
        choices.update({r: Path(r).name for r in recents})
        return ui.input_select(
            "recent_project_sel", None,
            choices=choices,
            selected="",
        )

    @reactive.effect
    @reactive.event(input.recent_project_sel)
    def _on_recent_selected():
        sel = input.recent_project_sel()
        if sel and sel != "":
            ui.update_text("proj_dir", value=sel)
            _do_load_project(sel)

    # ── Reset project ───────────────────────────────────────────────────
    @reactive.effect
    @reactive.event(input.reset_project)
    def _on_reset_project():
        import shutil as _shutil
        proj = proj_dir_rv.get()
        if proj is None:
            ui.notification_show("No project loaded.", type="warning")
            return
        _KEEP = {"input", "data"}   # never delete the seed sequences
        deleted = []
        for sub in ["alignments", "hmm", "search_results", "results", "figures",
                    "logs", "databases", "reports"]:
            d = proj / sub
            if d.exists():
                _shutil.rmtree(d, ignore_errors=True)
                deleted.append(sub)
        # Wipe pipeline state
        state_file = proj / ".pipeline_state.json"
        state_file.unlink(missing_ok=True)
        # Re-init
        _do_load_project(str(proj))
        ui.notification_show(
            f"Project reset — cleared: {', '.join(deleted)}",
            type="warning",
            duration=5,
        )

    # ── Session notes ───────────────────────────────────────────────────
    @reactive.effect
    @reactive.event(input.save_session_note)
    def _on_save_note():
        note = (input.session_note() or "").strip()
        if not note:
            ui.notification_show("Type a note first.", type="warning")
            return
        proj = proj_dir_rv.get()
        state = state_rv.get()
        steps = {k: v["status"] for k, v in state.get_all_steps().items()} if state else {}
        save_note(proj, note, steps)
        ui.notification_show("Note saved.", type="message", duration=2)

    @output
    @render.ui
    def session_history_ui():
        proj = proj_dir_rv.get()
        if proj is None:
            return ui.tags.span("")
        notes = load_notes(proj, last_n=3)
        if not notes:
            return ui.tags.span("")
        items = []
        for n in notes:
            ts = n.get("timestamp", "")[:16].replace("T", " ")
            txt = n.get("note", "")
            if txt:
                items.append(ui.tags.li(
                    ui.tags.small(f"{ts}: ", class_="text-white-50"),
                    ui.tags.small(txt, class_="text-white"),
                ))
        if not items:
            return ui.tags.span("")
        return ui.accordion(
            ui.accordion_panel(
                "📝 Session history",
                ui.tags.ul(*items, class_="ps-3 mb-0", style="list-style:none;"),
            ),
            open=False,
            class_="mb-2",
        )

    # ── Project status ──────────────────────────────────────────────────
    @output
    @render.ui
    def project_status():
        # Self-refresh every 3s so the count reflects steps completing live,
        # reading fresh from disk (no global state_rv write — avoids cascading
        # invalidation that can stall the reactive flush).
        reactive.invalidate_later(3)
        proj = proj_dir_rv.get()
        state = state_rv.get()
        if state is None or proj is None:
            return ui.tags.div(
                ui.tags.small("No project loaded", class_="text-warning"),
                class_="mb-2",
            )
        try:
            disk_state = PipelineState(proj)
            steps = disk_state.get_all_steps()
        except Exception:
            steps = state.get_all_steps()
        n_done = sum(1 for s in steps.values() if s["status"] == "complete")
        return ui.tags.div(
            ui.tags.div(
                ui.tags.small(f"📁 {proj.name}", class_="text-white d-block"),
                ui.tags.small(f"{n_done}/{len(steps)} steps complete", class_="text-white-50"),
                class_="mb-1",
            ),
        )

    # ── Step navigation ─────────────────────────────────────────────────
    @output
    @render.ui
    def step_nav():
        # Self-refresh every 3s, reading fresh from disk so checkmarks update
        # live as pipeline steps complete.
        reactive.invalidate_later(3)
        proj = proj_dir_rv.get()
        state = state_rv.get()
        if proj is not None:
            try:
                state = PipelineState(proj)
            except Exception:
                pass

        step_info = [
            ("setup",    "⚙️ Database Setup"),
            ("input",    "1. Input"),
            ("msa",      "2. MSA"),
            ("hmm_build","3. HMM Build"),
            ("search",   "4. Search"),
            ("validate", "5. Calibrate"),
            ("iterate",  "6. Iterate"),
            ("classify", "7. Results"),
            ("synteny",  "8. Analysis"),
            ("export",   "9. Export"),
        ]

        items = []
        for step_key, label in step_info:
            status = state.get_status(step_key) if state else "pending"
            icon = {"complete": "✅", "running": "🔄", "failed": "❌"}.get(status, "○")
            items.append(
                ui.tags.div(
                    ui.tags.span(label, class_="small"),
                    ui.tags.span(icon, class_="step-status"),
                    class_="d-flex justify-content-between px-2 py-1 rounded",
                    style="cursor:default;",
                )
            )

        return ui.tags.div(*items, class_="step-nav mt-1")

    # ── Periodic state refresh (keeps sidebar nav in sync) ──────────────
    # Re-reads the pipeline_state.json every 4 seconds so checkmarks update
    # after pipeline steps complete, without each step file having to call
    # state_rv.set() explicitly.
    #
    # IMPORTANT: uses reactive.invalidate_later (NOT a `while True` loop) so
    # the reactive graph can settle between ticks — an infinite loop here
    # would block every other output from rendering. state_rv is read inside
    # reactive.isolate() so calling state_rv.set() does not re-trigger this
    # effect in a tight loop.
    # Sidebar live-refresh is handled locally inside the project_status and
    # step_nav renders (each calls reactive.invalidate_later and re-reads the
    # pipeline state from disk). A global polling effect that wrote state_rv
    # was removed: writing a shared reactive value on a timer cascaded
    # invalidation to every output and stalled the initial reactive flush.

    # ── Register outputs for each step panel ───────────────────────────
    # Proxies let step files call state.method() / registry.method() while
    # the underlying reactive values may still be None (no project loaded).
    _state_proxy    = _StateProxy(state_rv)
    _registry_proxy = _RegistryProxy(registry_rv)

    common_kwargs = dict(
        proj_dir_rv=proj_dir_rv,
        state_rv=state_rv,
        registry_rv=registry_rv,
        tools_rv=tools_rv,
        audit_rv=audit_rv,
        hits_df_rv=hits_df_rv,
        runners=runners,
        complexity_mode=input.complexity_mode,
        biology_mode=input.biology_mode,
        app_dir=APP_DIR,
        # Aliases used by step files via positional / kwargs
        state=_state_proxy,
        runner_dict=runners,
        registry=_registry_proxy,
        # Auto-install status (exposed to step_00_setup for live display)
        auto_install_status_rv=_auto_install_status,
        auto_install_log_rv=_auto_install_log,
        # Pipeline modules — injected so step files can call them directly
        **_pipeline_modules,
    )

    step_00_setup.register_outputs(input, output, render, reactive, session, **common_kwargs)
    step_01_input.register_outputs(input, output, render, reactive, session, **common_kwargs)
    step_02_msa.register_outputs(input, output, render, reactive, session, **common_kwargs)
    step_03_hmm.register_outputs(input, output, render, reactive, session, **common_kwargs)
    step_04_search.register_outputs(input, output, render, reactive, session, **common_kwargs)
    step_05_validate.register_outputs(input, output, render, reactive, session, **common_kwargs)
    step_06_iteration.register_outputs(input, output, render, reactive, session, **common_kwargs)
    step_07_results.register_outputs(input, output, render, reactive, session, **common_kwargs)
    step_08_analysis.register_outputs(input, output, render, reactive, session, **common_kwargs)
    step_09_export.register_outputs(input, output, render, reactive, session, **common_kwargs)


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------
app = App(
    _make_ui_with_css(),
    server,
    static_assets=str(APP_DIR / "www"),
)
