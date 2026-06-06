"""
ui/step_04_search.py — Database Search Panel (Step 4).

Runs hmmsearch against one or more databases. Per-database progress is shown
in a live-updating table. Supports protein and nucleotide databases (with
on-the-fly ORF extraction for NT targets).
"""
from __future__ import annotations

from shiny import ui

from .components import (
    click_go_strip,
    gene_context_strip,
    guidance_callout,
    info_tooltip,
    learning_card,
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
        "4. Database Search",
        ui.tags.div(
            step_guidance(
                "Scan discovery databases with the HMM, then optionally annotate hits with Pfam or VOGDB.",
                [
                "hits_main.tsv: all hits with confidence tiers, e-values, and bit scores",
                "VOGDB/Pfam annotation tables when selected",
                "Hits per database bar chart",
                "Results table ready for browsing in Step 7",
                ],
                "For viral family annotation, use VOGDB VFAM. It runs through HMMER hmmscan, matching the same stable setup pattern used for Pfam domain annotation.",
            ),
            ui.layout_columns(
                learning_card(
                    "Single-genome discovery recipe",
                    [
                        "Register the genome in Database Setup as a nucleotide target.",
                        "Select only that genome here.",
                        "Use Exhaustive six-frame ORFs with a low minimum ORF length for short or unusual genes.",
                    ],
                    tone="success",
                ),
                learning_card(
                    "Database search recipe",
                    [
                        "Choose only the databases needed for the question.",
                        "Remote databases download or stream only when selected.",
                        "Use the progress table and Run Summary to document exactly what was searched.",
                    ],
                    tone="info",
                ),
                learning_card(
                    "Annotation recipe",
                    [
                        "Use VOGDB VFAM to attach viral ortholog/family context to hits.",
                        "Use Pfam to check broader conserved domains.",
                        "Both annotation routes use HMMER, so they are easier to reproduce across laptops and workstations.",
                    ],
                    tone="info",
                ),
                col_widths=[4, 4, 4],
                class_="mb-3",
            ),
            click_go_strip([
                ("Select", "Pick only the databases needed"),
                ("Scan", "Run HMMER against proteins or translated ORFs"),
                ("Annotate", "Use VOGDB/Pfam for context"),
                ("Summarize", "Review hit counts and run status"),
            ]),
            gene_context_strip(),
            section_header("Database Selection", "Select databases to search — local files search instantly, others download automatically on first use"),

            # ---- database checklist (rendered server-side) -------------------
            ui.card(
                ui.card_header(
                    ui.tags.div(
                        "Available Databases",
                        ui.tags.small(
                            " — 🔵 Local (instant)  ·  🟢 Streamed live (no download, no disk space)",
                            class_="text-muted ms-2",
                        ),
                        class_="d-flex align-items-center",
                    )
                ),
                ui.output_ui("db_checklist"),
                ui.output_ui("db_download_status"),

                # Tip box
                ui.tags.div(
                    ui.tags.strong("💡 How it works:  "),
                    ui.tags.span(
                        "🔵 Local: your uploaded sequences — instant. "
                        "🟢 Stream: data flows through hmmsearch live (no download, no disk). "
                        "🔧 Auto-setup: downloads the HMM library once, then scans in seconds. "
                        "Tick what you want → ▶ Run Selected. Progress updates every second.",
                        style="font-size:0.82rem;"
                    ),
                    class_="alert alert-info mt-2 mb-1 py-2",
                ),
            ),

            # ---- search parameters -------------------------------------------
            section_header("Search Parameters"),
            ui.layout_columns(
                ui.tags.div(
                    ui.input_text(
                        "search_evalue",
                        "E-value threshold",
                        value="1e-5",
                    ),
                    ui.tags.small(
                        "Hits above this E-value are discarded.",
                        class_="text-muted",
                    ),
                ),
                ui.tags.div(
                    ui.input_slider(
                        "search_cpu",
                        ui.span("CPU threads", info_tooltip(
                            "More threads = faster search but more RAM. "
                            "A good default is your core count minus one.")),
                        min=1, max=32, value=4,
                    ),
                    ui.input_slider(
                        "min_aa",
                        ui.span("Min ORF length (aa, NT databases only)", info_tooltip(
                            "For nucleotide databases: shortest translated ORF to keep. "
                            "Lower catches small genes but adds noise.")),
                        min=10, max=100, value=30,
                    ),
                ),
                col_widths=[6, 6],
            ),
            ui.tags.div(
                ui.input_radio_buttons(
                    "nt_orf_mode",
                    ui.span("Nucleotide ORF scan mode", info_tooltip(
                        "Prodigal is faster and predicts likely genes. Exhaustive six-frame "
                        "translates every stop-to-stop ORF above the length cutoff, which is "
                        "better for weird, short, overlapping, or noncanonical genes."
                    )),
                    choices={
                        "sixframe": "Exhaustive six-frame ORFs",
                        "prodigal": "Prodigal predicted genes",
                    },
                    selected="sixframe",
                    inline=True,
                ),
                ui.tags.small(
                    "Use six-frame for single genomes or novel phage genes; use Prodigal for large database-scale scans when speed matters.",
                    class_="text-muted",
                ),
                ui.layout_columns(
                    guidance_callout(
                        "Exhaustive six-frame mode",
                        "Translates stop-to-stop ORFs in all six reading frames above the length cutoff. This is the discovery-first mode for weird, short, overlapping, or noncanonical genes, but it produces more candidates and more noise.",
                        "success",
                    ),
                    guidance_callout(
                        "Prodigal mode",
                        "Predicts likely coding genes quickly and gives cleaner conventional annotations. It is not designed to enumerate every possible ORF, so it should not be the only benchmark for genes we expect standard callers to miss.",
                        "warning",
                    ),
                    col_widths=[6, 6],
                    class_="mt-2",
                ),
                learning_card(
                    "How six-frame ORF scanning works",
                    [
                        "The app reads each nucleotide sequence in the three forward frames and the three reverse-complement frames.",
                        "In each frame, it splits the sequence at stop codons and keeps every stop-to-stop peptide at least as long as the minimum ORF length.",
                        "Those translated peptides are searched with your profile HMM, and hit headers keep strand/frame/coordinate information for follow-up and synteny.",
                        "This does not require Prodigal to predict a gene first, so it can catch short, overlapping, noncanonical, or annotation-missed ORFs.",
                        "Tradeoff: because it tests many more candidates, expect more runtime and more borderline hits that need score, coverage, and context review.",
                    ],
                    tone="success",
                ),
                class_="mt-2",
            ),

            # ---- run buttons -------------------------------------------------
            ui.tags.div(
                ui.input_action_button(
                    "run_selected_dbs",
                    "▶ Run Selected",
                    class_="btn btn-primary me-2",
                ),
                ui.input_action_button(
                    "run_all_dbs",
                    "▶▶ Run All",
                    class_="btn btn-outline-primary",
                ),
                class_="mt-2 mb-3",
            ),

            # ---- live activity banner -------------------------------------------
            ui.output_ui("search_activity_banner"),

            # ---- per-db progress table ---------------------------------------
            section_header("Search Progress"),
            ui.output_ui("search_progress_table"),

            # ---- database search summary (appears after completion) ----------
            ui.output_ui("search_summary_card"),

            # ---- live log (always visible, auto-scrolls) --------------------
            section_header("Live Output"),
            log_panel("search_log", height="300px"),

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
    registry   = kwargs.get("registry", None)
    registry_rv = kwargs.get("registry_rv", None)
    hits_df_rv  = kwargs.get("hits_df_rv", None)
    app_dir     = kwargs.get("app_dir", None)

    # Persistent checkbox state — survives db_checklist re-renders
    _checked_dbs: reactive.Value[set] = reactive.value(set())

    def _safe_input_id(name: str) -> str:
        """Return a Shiny-safe input ID: only letters, numbers, underscore."""
        import re as _re
        return _re.sub(r"[^a-z0-9_]", "_", name.lower())

    def _aug_path() -> str:
        """Augmented PATH that includes conda env bin dirs so tools like hmmsearch are found."""
        import os as _os, shutil as _sh
        from pathlib import Path as _P
        extras = []
        for var in ("CONDA_PREFIX", "VIRTUAL_ENV"):
            val = _os.environ.get(var)
            if val:
                extras.append(str(_P(val) / "bin"))
                break
        home = _P.home()
        for base in [home/"miniforge3", home/"miniconda3", home/"anaconda3",
                     _P("/opt/anaconda3"), _P("/opt/miniconda3"), _P("/opt/homebrew")]:
            for envname in ["hmm_env", "base", ""]:
                subdir = base/"envs"/envname/"bin" if envname else base/"bin"
                if subdir.is_dir() and _sh.which("hmmsearch", path=str(subdir)):
                    extras.append(str(subdir))
                    break
        current = _os.environ.get("PATH", "")
        return _os.pathsep.join(extras + [p for p in current.split(_os.pathsep) if p not in extras])

    def _get_registry():
        """Return the live DatabaseRegistry, preferring registry_rv over the proxy."""
        if registry_rv is not None:
            rv = registry_rv.get()
            if rv is not None:
                return rv
        if registry is not None and bool(registry):
            return registry
        # Last resort: construct directly from project dir
        try:
            pd = proj_dir_rv.get() if proj_dir_rv is not None else None
            if pd:
                from databases.registry import DatabaseRegistry as _DR
                from pathlib import Path as _P
                return _DR(_P(pd))
        except Exception:
            pass
        return None

    # Per-database status: {db_name: {"status": str, "hits": int|None}}
    _db_status: reactive.Value[dict] = reactive.value({})

    # Accumulates log lines from all db runners
    _search_log_lines: reactive.Value[list[str]] = reactive.value([])

    # ---- Recover search state from disk on session start --------------------
    def _recover_search_state() -> None:
        """Restore _db_status and _search_log_lines from tblout files on disk.

        Called once on session start so that reconnecting mid-search (or after
        completion) shows what was found rather than "No searches started yet".
        """
        try:
            if state is None:
                return
            search_step_status = state.get_status("search")
            if search_step_status not in ("running", "complete", "failed"):
                return
            pd_ = proj_dir_rv.get() if proj_dir_rv is not None else None
            if not pd_:
                return
            search_dir = Path(pd_) / "search_results"
            if not search_dir.exists():
                return

            # Read persistent log first (written during run)
            log_file = search_dir / "search_log.txt"
            if log_file.exists():
                saved_lines = [l.rstrip() for l in log_file.read_text().splitlines()]
                if saved_lines:
                    _search_log_lines.set(saved_lines[-200:])  # keep last 200 lines

            # Scan tblout files → rebuild per-db status
            recovered: dict = {}
            for tblout in sorted(search_dir.glob("*.tblout")):
                db_name = tblout.stem
                try:
                    lines = [
                        l for l in tblout.read_text().splitlines()
                        if l.strip() and not l.startswith("#")
                    ]
                    hits = len(lines)
                except Exception:
                    hits = 0
                recovered[db_name] = {
                    "status": f"✅ Complete (recovered — {hits} hits)",
                    "hits": hits,
                    "elapsed": "—",
                    "_recovered": True,
                }
            if recovered:
                _db_status.set(recovered)
                recovery_msg = (
                    f"[Session recovered from disk — {len(recovered)} database(s) found]"
                )
                cur_log = list(_search_log_lines.get())
                if not cur_log or cur_log[0] != recovery_msg:
                    _search_log_lines.set([recovery_msg] + cur_log)
        except Exception:
            pass  # never block the session from starting

    _recover_search_state()

    # ---- Persistent log helper -----------------------------------------------
    def _log_to_disk(lines: list) -> None:
        """Append log lines to search_log.txt so they survive session reconnects."""
        try:
            pd_ = proj_dir_rv.get() if proj_dir_rv is not None else None
            if not pd_:
                return
            log_path = Path(pd_) / "search_results" / "search_log.txt"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a") as fh:
                for line in lines:
                    fh.write(str(line) + "\n")
        except Exception:
            pass

    # Tracks inline download progress per db name
    _download_status: reactive.Value[dict] = reactive.value({})

    # ---- db_checklist --------------------------------------------------------
    @output
    @render.ui
    def db_checklist():
        reg = _get_registry()
        dbs = reg.get_all() if reg is not None and hasattr(reg, "get_all") else []
        if not dbs:
            return ui.tags.div(
                ui.tags.p("No databases registered yet.", class_="text-warning mb-1"),
                ui.tags.small(
                    "Load a project first — databases are auto-populated on first load.",
                    class_="text-muted",
                ),
            )

        dl_statuses = _download_status.get()

        def _size_gb(db) -> float:
            """Parse size_hint → approx GB (0 = unknown)."""
            import re as _re
            hint = db.get("size_hint", "").lower()
            m = _re.search(r"([\d.]+)\s*(gb|mb)", hint)
            if not m:
                return 0.0
            val = float(m.group(1))
            return val if m.group(2) == "gb" else val / 1024

        def _avail_badge(db):
            name      = db["name"]
            has_path  = bool(db.get("path"))
            has_url   = bool(db.get("download_url") or db.get("url"))
            dl_state  = dl_statuses.get(name, {})
            size_gb   = _size_gb(db)
            size_hint = db.get("size_hint", "")

            if dl_state.get("status") == "downloading":
                return ui.tags.span("⬇️ Downloading…", class_="badge bg-warning text-dark")
            if dl_state.get("status") == "done":
                return ui.tags.span("🔵 Local — ready", class_="badge bg-primary")
            if dl_state.get("status") == "error":
                return ui.tags.span("❌ Download failed", class_="badge bg-danger")
            if has_path:
                return ui.tags.span("🔵 Local — ready", class_="badge bg-primary")
            if db.get("search_mode") == "hmmscan":
                est = db.get("est_time", "")
                label = f"🔧 Auto-setup ({est})" if est else "🔧 Auto-setup"
                return ui.tags.span(label, class_="badge bg-info text-dark")
            if has_url:
                est = db.get("est_time", "")
                label = f"🟢 Stream ({est})" if est else "🟢 Stream"
                return ui.tags.span(label, class_="badge bg-success")
            return ui.tags.span("⚠️ No path set", class_="badge bg-secondary")

        def _dl_btn(db):
            """Download button only for large databases that need manual download."""
            name      = db["name"]
            safe_id   = _safe_input_id(name)
            has_path  = bool(db.get("path"))
            has_url   = bool(db.get("download_url") or db.get("url"))
            dl_state  = dl_statuses.get(name, {})
            size_gb   = _size_gb(db)
            # No button needed — all databases stream or are local
            if has_path or has_url or dl_state.get("status") in ("downloading", "done"):
                return ui.tags.span("")
            size_hint = db.get("size_hint", "")
            label = f"⬇️ {size_hint}".strip() if size_hint else "⬇️ Download"
            return ui.input_action_button(
                f"dl_inline_{safe_id}", label,
                class_="btn btn-outline-secondary btn-sm py-0 px-2",
            )

        # Build table rows: [checkbox | name | type | status | download btn]
        header = ui.tags.thead(ui.tags.tr(
            ui.tags.th("", style="width:32px"),
            ui.tags.th("Database"),
            ui.tags.th("Type", style="width:90px"),
            ui.tags.th("Availability", style="width:120px"),
            ui.tags.th("", style="width:140px"),
        ))

        rows = []
        for db in dbs:
            if not db.get("enabled", False):
                continue
            name      = db["name"]
            safe_id   = _safe_input_id(name)
            streaming = db.get("streaming", False)
            has_path  = bool(db.get("path"))
            db_type   = db.get("type", "protein")
            relevance = db.get("relevance") or db.get("notes", "")
            caveats = []
            release = db.get("release", "")
            if release:
                caveats.append(release)
            if db.get("setup_handler") == "vogdb_hmmscan":
                caveats.append("Preferred viral ortholog annotation; HMMER hmmscan; optional/non-blocking.")

            rows.append(ui.tags.tr(
                ui.tags.td(
                    ui.input_checkbox(
                        f"db_sel_{safe_id}", "",
                        value=(has_path or (streaming and not db.get("optional", False))),
                    ),
                    class_="align-middle",
                ),
                ui.tags.td(
                    ui.tags.strong(name, class_="small"),
                    ui.tags.div(
                        ui.tags.span("Why scan this: ", class_="fw-semibold"),
                        relevance,
                        class_="database-relevance small text-muted mt-1",
                    ) if relevance else "",
                    ui.tags.div(
                        *[
                            ui.tags.span(note, class_="badge text-bg-warning me-1 mt-1")
                            for note in caveats
                        ],
                        class_="mt-1",
                    ) if caveats else "",
                    class_="align-middle",
                ),
                ui.tags.td(
                    ui.tags.span(
                        db_type,
                        class_="badge bg-light text-dark",
                    ),
                    class_="align-middle",
                ),
                ui.tags.td(_avail_badge(db), class_="align-middle"),
                ui.tags.td(_dl_btn(db), class_="align-middle"),
            ))

        if not rows:
            return ui.tags.p("No databases enabled.", class_="text-warning")

        return ui.tags.div(
            ui.tags.table(
                header,
                ui.tags.tbody(*rows),
                class_="table table-sm table-hover mb-0",
            ),
            class_="px-1",
        )

    # ---- db_download_status (inline progress messages) ----------------------
    @output
    @render.ui
    def db_download_status():
        dl = _download_status.get()
        if not dl:
            return ui.tags.span("")
        msgs = []
        for db_name, info in dl.items():
            s = info.get("status", "")
            if s == "downloading":
                msgs.append(ui.tags.div(
                    f"⬇️ Downloading {db_name}… {info.get('pct', 0)}% "
                    f"({info.get('downloaded_mb', 0):.0f} / {info.get('total_mb', 0):.0f} MB)",
                    class_="text-warning small",
                ))
            elif s == "done":
                msgs.append(ui.tags.div(
                    f"✅ {db_name} downloaded and ready.",
                    class_="text-success small",
                ))
            elif s == "error":
                msgs.append(ui.tags.div(
                    f"❌ {db_name}: {info.get('error', 'download failed')}",
                    class_="text-danger small",
                ))
        return ui.tags.div(*msgs, class_="px-2 pb-1") if msgs else ui.tags.span("")

    # ── Inline download handler ────────────────────────────────────────────────
    # NOTE: The old _watch_inline_downloads had no @reactive.event, causing it
    # to fire on every reactive flush and create a dependency loop that prevented
    # db_checklist from rendering. Removed — downloads now happen automatically
    # inside _run_one_db when a database has no local path.

    async def _do_inline_download(db: dict):
        """Stream-download a database inline, updating _download_status reactively."""
        import asyncio as _asyncio
        name     = db["name"]
        url      = db.get("download_url") or db.get("url") or ""
        safe_id  = name.replace(" ", "_").lower()
        proj_dir = proj_dir_rv.get()

        if not url:
            cur = dict(_download_status.get())
            cur[name] = {"status": "error", "error": "No download URL registered."}
            _download_status.set(cur)
            return

        import urllib.request as _req
        from pathlib import Path as _Path

        dest_dir = _Path(proj_dir) / "databases" / safe_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        filename  = url.split("/")[-1].split("?")[0] or f"{safe_id}.faa.gz"
        dest_file = dest_dir / filename

        cur = dict(_download_status.get())
        cur[name] = {"status": "downloading", "pct": 0, "downloaded_mb": 0, "total_mb": 0}
        _download_status.set(cur)

        try:
            # Use curl for resumable download with progress
            import shutil as _shutil
            curl = _shutil.which("curl") or "curl"
            cmd  = [curl, "-L", "-C", "-", "-o", str(dest_file), "--progress-bar", url]
            proc = await _asyncio.create_subprocess_exec(
                *cmd,
                stdout=_asyncio.subprocess.PIPE,
                stderr=_asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode == 0 and dest_file.exists():
                size_mb = dest_file.stat().st_size / 1_048_576
                cur = dict(_download_status.get())
                cur[name] = {"status": "done", "pct": 100,
                             "downloaded_mb": size_mb, "total_mb": size_mb}
                _download_status.set(cur)
                # Register the downloaded path back to the registry
                if registry is not None and hasattr(registry, "update_path"):
                    registry.update_path(name, str(dest_file))
            else:
                err = stderr.decode(errors="replace").strip()[-200:]
                cur = dict(_download_status.get())
                cur[name] = {"status": "error", "error": err}
                _download_status.set(cur)
        except Exception as exc:
            cur = dict(_download_status.get())
            cur[name] = {"status": "error", "error": str(exc)}
            _download_status.set(cur)

    # ---- sync checkbox inputs → persistent _checked_dbs set -----------------
    @reactive.effect
    def _sync_checkbox_state():
        """Read all db_sel_* inputs and persist their state so it survives re-renders."""
        reg = _get_registry()
        if reg is None:
            return
        all_dbs = reg.get_all() if hasattr(reg, "get_all") else []
        checked = set()
        for db in all_dbs:
            name     = db["name"]
            input_id = f"db_sel_{_safe_input_id(name)}"
            try:
                if input[input_id]():
                    checked.add(name)
            except Exception:
                pass
        if checked:   # only update if we read at least one checkbox
            _checked_dbs.set(checked)

    # ---- helper: collect selected db names -----------------------------------
    def _selected_db_names() -> list[str]:
        reg = _get_registry()
        if reg is None:
            return []
        all_dbs = reg.get_all() if hasattr(reg, "get_all") else []

        # Try reading live inputs first
        live_checked = set()
        any_input_worked = False
        for db in all_dbs:
            name     = db["name"]
            input_id = f"db_sel_{_safe_input_id(name)}"
            try:
                if input[input_id]():
                    live_checked.add(name)
                any_input_worked = True
            except Exception:
                pass

        if any_input_worked and live_checked:
            return list(live_checked)

        # Fall back to persistent set from last successful checkbox read
        persisted = _checked_dbs.get()
        if persisted:
            return [db["name"] for db in all_dbs if db["name"] in persisted]

        # Last resort: any database that has a URL or local path
        return [
            db["name"] for db in all_dbs
            if db.get("path") or db.get("download_url") or db.get("url")
        ]

    def _status_text(info: dict) -> str:
        return str(info.get("status", ""))

    def _is_running_status(status: str) -> bool:
        return any(
            token in status
            for token in (
                "Queued",
                "running",
                "Searching",
                "Scanning",
                "Streaming",
                "Downloading",
                "Listing",
                "File ",
                "translated",
                "Indexing",
            )
        )

    def _is_complete_status(status: str) -> bool:
        return "✅" in status or "Complete" in status

    def _is_failed_status(status: str) -> bool:
        return any(token in status for token in ("❌", "Failed", "failed", "No local file", "No files found"))

    def _search_status_summary() -> tuple[int, int, int]:
        statuses = _db_status.get()
        complete = sum(1 for info in statuses.values() if _is_complete_status(_status_text(info)))
        failed = sum(1 for info in statuses.values() if _is_failed_status(_status_text(info)))
        running = sum(1 for info in statuses.values() if _is_running_status(_status_text(info)))
        return complete, failed, running

    def _db_file_stem(name: str) -> str:
        return name.replace(" ", "_").lower()

    def _count_tblout_hits(path) -> int:
        try:
            with open(path) as fh:
                return sum(1 for line in fh if line.strip() and not line.startswith("#"))
        except Exception:
            return 0

    def _persisted_search_statuses() -> dict:
        """Recover the last search status from project files after app reload."""
        import json as _json
        from pathlib import Path as _Path

        try:
            proj = _Path(proj_dir_rv.get()) if proj_dir_rv is not None and proj_dir_rv.get() else None
        except Exception:
            proj = None
        if not proj or not proj.exists():
            return {}

        state_info = {}
        try:
            state_file = proj / ".pipeline_state.json"
            if state_file.exists():
                state_info = _json.loads(state_file.read_text()).get("steps", {}).get("search", {})
        except Exception:
            state_info = {}

        db_names = []
        try:
            params = state_info.get("params", {}) if isinstance(state_info, dict) else {}
            db_names = list(params.get("databases") or [])
        except Exception:
            db_names = []

        search_dir = proj / "search_results"
        tblouts = list(search_dir.glob("*.tblout")) if search_dir.exists() else []
        if not db_names and tblouts:
            by_stem = {}
            try:
                reg = _get_registry()
                dbs = reg.get_all() if reg is not None and hasattr(reg, "get_all") else []
                by_stem = {_db_file_stem(db.get("name", "")): db.get("name", "") for db in dbs}
            except Exception:
                by_stem = {}
            db_names = [by_stem.get(tbl.stem, tbl.stem.replace("_", " ").title()) for tbl in tblouts]

        if state_info.get("status") == "failed":
            reason = state_info.get("error", "Previous search failed.")
            return {"Previous search": {"status": f"❌ {reason}", "hits": 0}}

        if state_info.get("status") != "complete" and not tblouts:
            return {}

        statuses = {}
        for name in db_names:
            tbl = search_dir / f"{_db_file_stem(name)}.tblout"
            statuses[name] = {
                "status": "✅ Complete (previous run)" if tbl.exists() else "⚠️ No tblout found for previous run",
                "hits": _count_tblout_hits(tbl) if tbl.exists() else 0,
            }

        if not statuses and (proj / "results" / "hits_main.tsv").exists():
            try:
                with open(proj / "results" / "hits_main.tsv") as fh:
                    rows = max(sum(1 for _ in fh) - 1, 0)
            except Exception:
                rows = 0
            statuses["Previous search"] = {"status": "✅ Complete (previous run)", "hits": rows}

        return statuses

    def _lookup_db(db_name: str, proj_dir: str) -> "dict | None":
        """Resolve built-in, streamed, and custom DB metadata by display name."""
        import json as _json
        from pathlib import Path as _Path

        all_dbs = []
        try:
            reg = _get_registry()
            if reg is not None:
                if hasattr(reg, "get_all"):
                    all_dbs.extend(reg.get_all())
                elif hasattr(reg, "list_all"):
                    all_dbs.extend(reg.list_all())
        except Exception:
            pass

        try:
            db_file = _Path(proj_dir) / "databases.json"
            if db_file.exists():
                saved = _json.loads(db_file.read_text())
                if isinstance(saved, list):
                    by_name = {db.get("name"): db for db in all_dbs if isinstance(db, dict)}
                    for db in saved:
                        if not isinstance(db, dict):
                            continue
                        name = db.get("name")
                        if name in by_name:
                            by_name[name].update({k: v for k, v in db.items() if v not in (None, "")})
                        else:
                            all_dbs.append(db)
        except Exception:
            pass

        return next((db for db in all_dbs if db.get("name") == db_name), None)

    # ---- helper: run search for one database ---------------------------------
    async def _run_one_db(db_name: str, hmm_path: str, proj_dir: "Path",
                          db_dict: "dict | None" = None) -> None:
        from pathlib import Path as _Path

        # Use passed db_dict, or look up from full registry/database metadata.
        db = db_dict or _lookup_db(db_name, str(proj_dir))
        if db is None:
            cur = dict(_db_status.get())
            cur[db_name] = {"status": "❌ Database metadata not found", "hits": 0}
            _db_status.set(cur)
            lines = list(_search_log_lines.get())
            lines.append(f"\n=== {db_name} ===")
            lines.append("  ERROR: Database metadata not found. Refresh database setup and try again.")
            _search_log_lines.set(lines)
            return

        # Update status to running
        cur = dict(_db_status.get())
        cur[db_name] = {"status": "running", "hits": None}
        _db_status.set(cur)
        _log_to_disk([f"\n=== {db_name} — STARTED ==="
                      f" ({__import__('datetime').datetime.now().strftime('%H:%M:%S')}) ==="])

        out_dir = _Path(proj_dir) / "search_results"
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_name = db_name.replace(" ", "_").lower()
        out_tbl = out_dir / f"{safe_name}.tblout"

        # Read search parameters upfront (needed by both streaming and local paths)
        evalue = "1e-5"
        try:
            evalue = input.search_evalue() or "1e-5"
        except Exception:
            pass
        cpu = 4
        try:
            cpu = input.search_cpu()
        except Exception:
            pass
        min_aa = 30
        try:
            min_aa = int(input.min_aa())
        except Exception:
            pass
        nt_orf_mode = "sixframe"
        try:
            nt_orf_mode = input.nt_orf_mode() or "sixframe"
        except Exception:
            pass

        # ── hmmscan mode: download HMM library, index, scan hits ──────────
        if db.get("search_mode") == "hmmscan":
            await _run_hmmscan_db(db_name, db, hmm_path, _Path(proj_dir), evalue, cpu)
            return

        # Only use the local path — hmmsearch always needs a local file.
        # If no path but a download_url exists, download it first then search.
        db_path = db.get("path") or db.get("db_path") or ""
        if not db_path:
            download_url = db.get("download_url") or db.get("url") or ""
            if not download_url:
                cur = dict(_db_status.get())
                cur[db_name] = {
                    "status": "❌ No local file or download URL — register a local path in Database Setup",
                    "hits": None,
                }
                _db_status.set(cur)
                return

            # ── True streaming search: curl | gunzip | [6-frame] | hmmsearch ─
            # hmmsearch reads sequences from stdin when given '-' as the db arg.
            # No disk space needed — data streams from the remote URL through the
            # search pipeline and only the tiny .tblout result is saved locally.
            import shutil as _shutil
            import sys as _sys

            import time as _time

            size_hint = db.get("size_hint", "unknown size")
            _hmmsearch_path = _shutil.which("hmmsearch", path=_aug_path()) or "hmmsearch"
            _curl_path      = _shutil.which("curl")      or "curl"
            _prodigal_path  = _shutil.which("prodigal", path=_aug_path())
            _seqkit_path    = _shutil.which("seqkit", path=_aug_path())
            _python_path    = _sys.executable
            db_type_local   = db.get("type", "protein")

            # Expand wildcard URLs (e.g. RefSeq viral.*.protein.faa.gz)
            if "*" in download_url:
                cur = dict(_db_status.get())
                cur[db_name] = {"status": f"📡 Listing files from NCBI FTP…", "hits": None}
                _db_status.set(cur)

                lines = list(_search_log_lines.get())
                lines.append(f"\n=== {db_name} (multi-file streaming) ===")
                _search_log_lines.set(lines)

                try:
                    from databases.downloader import check_ncbi_ftp_files
                    last_slash = download_url.rfind("/")
                    base_url = download_url[:last_slash + 1]
                    pattern = download_url[last_slash + 1:]
                    file_urls = check_ncbi_ftp_files(base_url, pattern)
                except Exception as _exc:
                    file_urls = []
                    lines = list(_search_log_lines.get())
                    lines.append(f"  ERROR listing FTP: {_exc}")
                    _search_log_lines.set(lines)

                if not file_urls:
                    cur = dict(_db_status.get())
                    cur[db_name] = {"status": "❌ No files found at FTP URL", "hits": 0}
                    _db_status.set(cur)
                    return

                lines = list(_search_log_lines.get())
                lines.append(f"  Found {len(file_urls)} files to stream")
                _search_log_lines.set(lines)
            else:
                file_urls = [download_url]

            total_hits = 0
            t_start = _time.time()
            import asyncio as _asyncio

            for file_idx, single_url in enumerate(file_urls):
                file_label = single_url.split("/")[-1]
                cur = dict(_db_status.get())
                cur[db_name] = {
                    "status": f"🌊 File {file_idx+1}/{len(file_urls)}: {file_label}",
                    "hits": total_hits if total_hits > 0 else None,
                }
                _db_status.set(cur)

                is_gz = single_url.endswith(".gz")

                from core.runner import AsyncJobRunner as _AJR
                cache_dir = out_dir / "stream_cache"
                cache_dir.mkdir(parents=True, exist_ok=True)
                safe_file_label = "".join(
                    ch if ch.isalnum() or ch in "._-" else "_"
                    for ch in file_label
                )[:160]
                cache_file = cache_dir / f"{safe_name}_part{file_idx}_{safe_file_label}"
                cache_done = _Path(str(cache_file) + ".complete")

                if not cache_done.exists():
                    dl_cmd = [
                        "bash", "-c",
                        (
                            f"'{_curl_path}' -sS -f -L -C - --retry 20 "
                            f"--retry-delay 10 --retry-all-errors "
                            f"--connect-timeout 30 -o '{cache_file}' '{single_url}' "
                            f"&& touch '{cache_done}'"
                        ),
                    ]
                    runner_key = f"download_{safe_name}_{file_idx}"
                    if runner_key not in runner_dict:
                        runner_dict[runner_key] = _AJR(step_name=runner_key)
                    dl_runner = runner_dict[runner_key]
                    dl_runner.start(dl_cmd, cwd=_Path(proj_dir))

                    while dl_runner.is_running.get():
                        await _asyncio.sleep(1.0)
                        elapsed = _time.time() - t_start
                        mins = int(elapsed // 60)
                        secs = int(elapsed % 60)
                        size_mb = (
                            cache_file.stat().st_size / 1_048_576
                            if cache_file.exists() else 0
                        )
                        cur = dict(_db_status.get())
                        cur[db_name] = {
                            "status": (
                                f"⬇️ {file_idx+1}/{len(file_urls)} {file_label} "
                                f"cached {size_mb:.0f} MB — {mins}m {secs:02d}s"
                            ),
                            "hits": total_hits if total_hits > 0 else None,
                        }
                        _db_status.set(cur)

                    dl_rc = dl_runner.returncode.get()
                    if (
                        dl_rc != 0
                        or not cache_done.exists()
                        or not cache_file.exists()
                        or cache_file.stat().st_size == 0
                    ):
                        cur = dict(_db_status.get())
                        cur[db_name] = {
                            "status": f"❌ Download failed: {file_label}",
                            "hits": total_hits if total_hits > 0 else 0,
                        }
                        _db_status.set(cur)
                        lines = list(_search_log_lines.get())
                        lines.append(f"  {file_label}: download failed (rc={dl_rc})")
                        _search_log_lines.set(lines)
                        return

                source_cmd = (
                    f"gzip -cd '{cache_file}' "
                    if is_gz else
                    f"cat '{cache_file}' "
                )

                if db_type_local == "nucleotide":
                    _sf_script = None
                    _translate_script = None
                    if nt_orf_mode == "sixframe":
                        import tempfile as _tempfile
                        _sf_script = _tempfile.NamedTemporaryFile(
                            mode='w', suffix='_6frame.py', delete=False,
                            dir=str(_Path(proj_dir) / "search_results"),
                        )
                        _sf_script.write(f"""
import sys
import warnings
from Bio import BiopythonWarning
from Bio import SeqIO

for r in SeqIO.parse(sys.stdin, 'fasta'):
    seq = r.seq
    seq_len = len(seq)
    for s, nuc in [(1, seq), (-1, seq.reverse_complement())]:
        for f in range(3):
            frame_seq = nuc[f:]
            usable = len(frame_seq) - (len(frame_seq) % 3)
            if usable <= 0:
                continue
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', BiopythonWarning)
                trans = str(frame_seq[:usable].translate())
            aa_offset = 0
            for i, aa in enumerate(trans.split('*')):
                if len(aa) >= {min_aa}:
                    if s == 1:
                        start = f + aa_offset * 3 + 1
                        end = start + len(aa) * 3 - 1
                    else:
                        end = seq_len - (f + aa_offset * 3)
                        start = end - len(aa) * 3 + 1
                    sys.stdout.write(f'>{{r.id}}_s{{s}}_f{{f}}_o{{i}} # {{start}} # {{end}} # {{s}}\\n')
                    sys.stdout.write(aa + '\\n')
                aa_offset += len(aa) + 1
""")
                        _sf_script.close()
                        _sixframe = f"| {_python_path} '{_sf_script.name}' "
                    elif _prodigal_path and _seqkit_path:
                        import os as _os
                        import tempfile as _tempfile
                        split_parts = max(int(cpu or 1), 1)
                        prodigal_gff = out_dir / f"{safe_name}_part{file_idx}.prodigal.gff"
                        chunk_base = out_dir / f"{safe_name}_part{file_idx}_chunks"
                        _translate_script = _tempfile.NamedTemporaryFile(
                            mode="w", suffix="_prodigal_parallel.sh", delete=False,
                            dir=str(_Path(proj_dir) / "search_results"),
                        )
                        _translate_script.write(f"""#!/usr/bin/env bash
set -euo pipefail
cache_file="$1"
work_dir="$2"
out_gff="$3"
rm -rf "$work_dir"
mkdir -p "$work_dir/chunks" "$work_dir/plain" "$work_dir/proteins"
'{_seqkit_path}' split2 -p {split_parts} -O "$work_dir/chunks" "$cache_file" >/dev/null
find "$work_dir/chunks" -type f \\( -name '*.fa' -o -name '*.faa' -o -name '*.fasta' -o -name '*.fna' -o -name '*.fa.gz' -o -name '*.faa.gz' -o -name '*.fasta.gz' -o -name '*.fna.gz' \\) -print0 | \\
  xargs -0 -I{{}} -P {split_parts} sh -c '
    in_file="$1"
    out_dir="$2"
    prodigal="$3"
    base="$(basename "$in_file")"
    plain="$out_dir/plain/$base.fna"
    if [ "${{in_file%.gz}}" != "$in_file" ]; then
      gzip -cd "$in_file" > "$plain"
    else
      cp "$in_file" "$plain"
    fi
    "$prodigal" -i "$plain" \\
      -a "$out_dir/proteins/$base.faa" \\
      -o "$out_dir/proteins/$base.gff" \\
      -f gff -p meta -q
    rm -f "$plain"
  ' sh {{}} "$work_dir" '{_prodigal_path}'
test "$(find "$work_dir/proteins" -type f -name '*.faa' -size +0c | wc -l | tr -d ' ')" != "0"
cat "$work_dir"/proteins/*.gff > "$out_gff" 2>/dev/null || true
cat "$work_dir"/proteins/*.faa
""")
                        _translate_script.close()
                        _os.chmod(_translate_script.name, 0o755)
                        source_cmd = (
                            f"'{_translate_script.name}' '{cache_file}' "
                            f"'{chunk_base}' '{prodigal_gff}' "
                        )
                        _sixframe = ""
                    elif _prodigal_path:
                        # Fast default for deployment-scale nucleotide streams.
                        # Prodigal preserves genomic coordinates in the FASTA
                        # description; synteny parses those from HMMER tblout.
                        prodigal_gff = out_dir / f"{safe_name}_part{file_idx}.prodigal.gff"
                        _sixframe = (
                            f"| '{_prodigal_path}' -i /dev/stdin -a /dev/stdout "
                            f"-o '{prodigal_gff}' -f gff -p meta -q "
                        )
                    else:
                        # Fallback: incremental 6-frame translation. This avoids
                        # loading the full decompressed database into memory.
                        import tempfile as _tempfile
                        _sf_script = _tempfile.NamedTemporaryFile(
                            mode='w', suffix='_6frame.py', delete=False,
                            dir=str(_Path(proj_dir) / "search_results"),
                        )
                        _sf_script.write(f"""
import sys
import warnings
from Bio import BiopythonWarning
from Bio import SeqIO

for r in SeqIO.parse(sys.stdin, 'fasta'):
    seq = r.seq
    seq_len = len(seq)
    for s, nuc in [(1, seq), (-1, seq.reverse_complement())]:
        for f in range(3):
            frame_seq = nuc[f:]
            usable = len(frame_seq) - (len(frame_seq) % 3)
            if usable <= 0:
                continue
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', BiopythonWarning)
                trans = str(frame_seq[:usable].translate())
            aa_offset = 0
            for i, aa in enumerate(trans.split('*')):
                if len(aa) >= {min_aa}:
                    if s == 1:
                        start = f + aa_offset * 3 + 1
                        end = start + len(aa) * 3 - 1
                    else:
                        end = seq_len - (f + aa_offset * 3)
                        start = end - len(aa) * 3 + 1
                    sys.stdout.write(f'>{{r.id}}_s{{s}}_f{{f}}_o{{i}} # {{start}} # {{end}} # {{s}}\\n')
                    sys.stdout.write(aa + '\\n')
                aa_offset += len(aa) + 1
""")
                        _sf_script.close()
                        _sixframe = f"| {_python_path} '{_sf_script.name}' "
                else:
                    _sixframe = ""
                    _sf_script = None

                part_tbl = out_dir / f"{safe_name}_part{file_idx}.tblout"
                part_hits = 0
                rc = None
                max_attempts = 3

                for attempt in range(1, max_attempts + 1):
                    part_tbl.unlink(missing_ok=True)
                    stream_cmd = (
                        "set -o pipefail; "
                        f"{source_cmd}"
                        f"{_sixframe}"
                        f"| '{_hmmsearch_path}' --tblout '{part_tbl}' -E {evalue} "
                        f"--cpu {cpu} --noali '{hmm_path}' -"
                    )
                    cmd = ["bash", "-c", stream_cmd]

                    runner_key = f"search_{safe_name}_{file_idx}_{attempt}"
                    if runner_key not in runner_dict:
                        runner_dict[runner_key] = _AJR(step_name=runner_key)
                    runner = runner_dict[runner_key]
                    runner.start(cmd, cwd=_Path(proj_dir))

                    while runner.is_running.get():
                        await _asyncio.sleep(1.0)
                        elapsed = _time.time() - t_start
                        mins = int(elapsed // 60)
                        secs = int(elapsed % 60)
                        cur = dict(_db_status.get())
                        cur[db_name] = {
                            "status": (
                                f"🌊 {file_idx+1}/{len(file_urls)} {file_label} "
                                f"attempt {attempt}/{max_attempts} — {mins}m {secs:02d}s"
                            ),
                            "hits": total_hits if total_hits > 0 else None,
                        }
                        _db_status.set(cur)

                    rc = runner.returncode.get()
                    if rc == 0 and part_tbl.exists():
                        try:
                            with open(part_tbl) as fh:
                                part_hits = sum(
                                    1 for ln in fh
                                    if not ln.startswith("#") and ln.strip()
                                )
                        except Exception:
                            part_hits = 0
                        break

                    lines = list(_search_log_lines.get())
                    lines.append(
                        f"  {file_label}: attempt {attempt}/{max_attempts} "
                        f"failed (rc={rc})"
                    )
                    _search_log_lines.set(lines)

                if rc != 0:
                    cur = dict(_db_status.get())
                    cur[db_name] = {
                        "status": f"❌ Failed after {max_attempts} attempts: {file_label}",
                        "hits": total_hits if total_hits > 0 else 0,
                    }
                    _db_status.set(cur)

                    # Clean up temp 6-frame script before leaving this database.
                    if _sf_script is not None:
                        try:
                            import os as _os
                            _os.unlink(_sf_script.name)
                        except Exception:
                            pass
                    if "_translate_script" in locals() and _translate_script is not None:
                        try:
                            import os as _os
                            _os.unlink(_translate_script.name)
                        except Exception:
                            pass
                    return

                total_hits += part_hits

                # Clean up temp 6-frame script
                if _sf_script is not None:
                    try:
                        import os as _os
                        _os.unlink(_sf_script.name)
                    except Exception:
                        pass
                if "_translate_script" in locals() and _translate_script is not None:
                    try:
                        import os as _os
                        _os.unlink(_translate_script.name)
                    except Exception:
                        pass

                lines = list(_search_log_lines.get())
                lines.append(f"  {file_label}: {part_hits} hits (rc={rc})")
                _search_log_lines.set(lines)

            # Merge all part tblouts into the main tblout
            with open(out_tbl, "w") as out_fh:
                for i in range(len(file_urls)):
                    part = out_dir / f"{safe_name}_part{i}.tblout"
                    if part.exists():
                        for line in part.read_text().splitlines():
                            if not line.startswith("#"):
                                out_fh.write(line + "\n")
                        part.unlink(missing_ok=True)

            elapsed = _time.time() - t_start
            cur = dict(_db_status.get())
            cur[db_name] = {
                "status": f"✅ Complete ({int(elapsed)}s, {len(file_urls)} files)",
                "hits": total_hits,
            }
            _db_status.set(cur)

            lines = list(_search_log_lines.get())
            completion_line = f"  TOTAL: {total_hits} hits in {int(elapsed)}s across {len(file_urls)} files"
            lines.append(completion_line)
            _search_log_lines.set(lines)
            _log_to_disk([completion_line, f"=== {db_name} — COMPLETE ==="])
            return   # done — streaming search complete

        import time as _time
        t_start = _time.time()

        # Log the local search
        lines = list(_search_log_lines.get())
        lines.append(f"\n=== {db_name} (local) ===")
        lines.append(f"Path: {db_path}")
        lines.append(f"E-value: {evalue}, CPU: {cpu}")
        _search_log_lines.set(lines)

        # Nucleotide DBs must be translated before hmmsearch (which needs proteins)
        db_type = db.get("type", "protein")
        if db_type == "nucleotide":
            from pathlib import Path as _Path2
            nt_path = _Path2(db_path)
            prot_path = out_dir / f"{safe_name}_{nt_orf_mode}.faa"
            if not prot_path.exists():
                try:
                    n_written = 0
                    if nt_orf_mode == "prodigal":
                        import subprocess as _subprocess
                        import shutil as _shutil
                        _prodigal = _shutil.which("prodigal", path=_aug_path())
                        if not _prodigal:
                            raise RuntimeError("Prodigal is not installed; choose exhaustive six-frame mode.")
                        prodigal_gff = out_dir / f"{safe_name}.prodigal.gff"
                        result = _subprocess.run(
                            [
                                _prodigal,
                                "-i", str(nt_path),
                                "-a", str(prot_path),
                                "-o", str(prodigal_gff),
                                "-f", "gff",
                                "-p", "meta",
                                "-q",
                            ],
                            capture_output=True,
                            text=True,
                            timeout=3600,
                        )
                        if result.returncode != 0:
                            raise RuntimeError((result.stderr or result.stdout)[-800:])
                        from Bio import SeqIO as _SeqIO
                        n_written = sum(1 for _ in _SeqIO.parse(str(prot_path), "fasta"))
                    else:
                        import warnings as _warnings
                        from Bio import BiopythonWarning as _BiopythonWarning
                        from Bio import SeqIO as _SeqIO
                        with open(prot_path, "w") as _fh:
                            for _rec in _SeqIO.parse(str(nt_path), "fasta"):
                                _seq = _rec.seq
                                _seq_len = len(_seq)
                                for _strand, _nuc in [(1, _seq), (-1, _seq.reverse_complement())]:
                                    for _frame in range(3):
                                        _frame_seq = _nuc[_frame:]
                                        _usable = len(_frame_seq) - (len(_frame_seq) % 3)
                                        if _usable <= 0:
                                            continue
                                        with _warnings.catch_warnings():
                                            _warnings.simplefilter("ignore", _BiopythonWarning)
                                            _trans = str(_frame_seq[:_usable].translate())
                                        _aa_offset = 0
                                        for _i, _aa in enumerate(_trans.split("*")):
                                            if len(_aa) >= min_aa:
                                                if _strand == 1:
                                                    _start = _frame + _aa_offset * 3 + 1
                                                    _end = _start + len(_aa) * 3 - 1
                                                else:
                                                    _end = _seq_len - (_frame + _aa_offset * 3)
                                                    _start = _end - len(_aa) * 3 + 1
                                                _fh.write(
                                                    f">{_rec.id}_s{_strand}_f{_frame}_o{_i} "
                                                    f"# {_start} # {_end} # {_strand}\n{_aa}\n"
                                                )
                                                n_written += 1
                                            _aa_offset += len(_aa) + 1
                    cur2 = dict(_db_status.get())
                    cur2[db_name] = {
                        "status": f"{nt_orf_mode} translated ({n_written} ORFs) — searching…",
                        "hits": None,
                    }
                    _db_status.set(cur2)
                except Exception as _exc:
                    cur2 = dict(_db_status.get())
                    cur2[db_name] = {"status": f"❌ Translation failed: {_exc}", "hits": 0}
                    _db_status.set(cur2)
                    return
            db_path = str(prot_path)

        cmd = [
            "hmmsearch",
            "--tblout", str(out_tbl),
            "-E", evalue,
            "--cpu", str(cpu),
            "--noali",
            hmm_path,
            db_path,
        ]

        runner_key = f"search_{safe_name}"
        # Reuse or create a runner for this db
        from core.runner import AsyncJobRunner
        if runner_key not in runner_dict:
            runner_dict[runner_key] = AsyncJobRunner(step_name=runner_key)

        runner = runner_dict[runner_key]
        runner.start(cmd, cwd=_Path(proj_dir))

        import asyncio as _asyncio
        while runner.is_running.get():
            await _asyncio.sleep(1.0)
            elapsed = _time.time() - t_start
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            cur = dict(_db_status.get())
            cur[db_name] = {"status": f"🔄 Searching… {mins}m {secs:02d}s", "hits": None}
            _db_status.set(cur)

        rc = runner.returncode.get()
        elapsed = _time.time() - t_start
        hits = 0
        if rc == 0 and out_tbl.exists():
            try:
                with open(out_tbl) as fh:
                    hits = sum(1 for ln in fh if not ln.startswith("#") and ln.strip())
            except Exception:
                hits = 0

        cur = dict(_db_status.get())
        if rc == 0:
            cur[db_name] = {"status": f"✅ Complete ({int(elapsed)}s)", "hits": hits}
        else:
            cur[db_name] = {"status": f"❌ Failed (exit {rc})", "hits": 0}
        _db_status.set(cur)

        lines = list(_search_log_lines.get())
        lines.append(f"  → {hits} hits found in {int(elapsed)}s")
        lines.extend(runner.log_lines.get())
        _search_log_lines.set(lines)

    # ---- hmmscan handler (Pfam / VOGDB domain annotation) ---------------------
    async def _run_hmmscan_db(db_name, db, user_hmm_path, proj_dir, evalue, cpu):
        """Download an HMM library, index it, then hmmscan the user's hit proteins."""
        import asyncio as _asyncio
        import csv as _csv
        import gzip as _gzip
        import shutil as _shutil
        import tarfile as _tarfile
        import time as _time
        from pathlib import Path as _P

        download_url = db.get("download_url") or ""
        if not download_url:
            cur = dict(_db_status.get())
            cur[db_name] = {"status": "⚠️ No download URL", "hits": None}
            _db_status.set(cur)
            return

        safe_name = db_name.replace(" ", "_").replace("(", "").replace(")", "").lower()
        db_dir = proj_dir / "databases" / safe_name
        db_dir.mkdir(parents=True, exist_ok=True)

        filename = download_url.split("/")[-1].split("?")[0]
        is_tar_gz = filename.endswith((".tar.gz", ".tgz"))
        is_gz = filename.endswith(".gz") and not is_tar_gz
        archive_path = db_dir / filename
        if is_tar_gz:
            local_hmm = db_dir / ("vfam.hmm" if "vfam" in filename.lower() else f"{safe_name}.hmm")
        elif is_gz:
            local_hmm = db_dir / filename[:-3]
        else:
            local_hmm = db_dir / filename

        def _open_text(path):
            if str(path).endswith(".gz"):
                return _gzip.open(path, "rt", encoding="utf-8", errors="replace")
            return open(path, "r", encoding="utf-8", errors="replace")

        def _annotation_id(row, header):
            lower = {h.lower().strip(): h for h in header}
            for key in ("vfam", "vfam_id", "vog", "vog_id", "group", "group_id", "groupname", "hmm"):
                if key in lower and row.get(lower[key]):
                    return str(row.get(lower[key])).strip()
            return str(row.get(header[0], "")).strip() if header else ""

        def _pick_field(row, header, tokens):
            for h in header:
                low = h.lower()
                if any(tok in low for tok in tokens) and row.get(h):
                    return str(row.get(h)).strip()
            return ""

        def _load_vogdb_annotations(path):
            if not path or not path.exists():
                return {}
            with _open_text(path) as fh:
                sample = []
                for line in fh:
                    if line.strip() and not line.startswith("#"):
                        sample.append(line.rstrip("\n"))
                        break
                if not sample:
                    return {}
                first = sample[0].split("\t")
                first_lower = [value.lower().strip() for value in first]
                has_header = (
                    first_lower[0] in {"vfam", "vfam_id", "vog", "vog_id", "group", "group_id", "groupname", "hmm"}
                    or any(value in {"function", "annotation", "category", "description"} for value in first_lower)
                )
                if has_header:
                    header = first
                    rows_iter = _csv.DictReader(fh, fieldnames=header, delimiter="\t")
                else:
                    header = [f"column_{idx + 1}" for idx in range(len(first))]
                    rows_iter = _csv.DictReader([sample[0], *fh], fieldnames=header, delimiter="\t")
                annotations = {}
                for row in rows_iter:
                    if not row:
                        continue
                    group_id = _annotation_id(row, header)
                    if not group_id:
                        continue
                    annotation = _pick_field(row, header, ("annot", "description", "consensus", "name"))
                    function = _pick_field(row, header, ("function", "description"))
                    category = _pick_field(row, header, ("category", "class"))
                    if header and header[0].startswith("column_"):
                        function = function or str(row.get("column_2", "")).strip()
                        category = category or str(row.get("column_3", "")).strip()
                        annotation = annotation or str(row.get("column_4", "")).strip() or function
                    annotations[group_id] = {
                        "annotation": annotation,
                        "function": function,
                        "category": category,
                    }
                return annotations

        def _parse_domtbl_qcov(path):
            qcov = {}
            if not path.exists():
                return qcov
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if not line.strip() or line.startswith("#"):
                        continue
                    parts = line.split(maxsplit=22)
                    if len(parts) < 19:
                        continue
                    try:
                        target, query = parts[0], parts[3]
                        qlen = float(parts[5])
                        ali_from, ali_to = int(parts[17]), int(parts[18])
                        cov = round(max(0, ali_to - ali_from + 1) / qlen, 4) if qlen else ""
                    except Exception:
                        continue
                    key = (query, target)
                    if key not in qcov or cov > qcov[key]:
                        qcov[key] = cov
            return qcov

        def _write_vogdb_annotation_table(tblout, domtbl, annotation_file):
            if db.get("setup_handler") != "vogdb_hmmscan":
                return 0
            annotations = _load_vogdb_annotations(annotation_file)
            qcov = _parse_domtbl_qcov(domtbl)
            rows = []
            if tblout.exists():
                with open(tblout, encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        if not line.strip() or line.startswith("#"):
                            continue
                        parts = line.split(maxsplit=18)
                        if len(parts) < 6:
                            continue
                        vfam_id = parts[0]
                        query_id = parts[2] if len(parts) > 2 else ""
                        ann = annotations.get(vfam_id, {})
                        rows.append({
                            "query_protein_id": query_id,
                            "vfam_id": vfam_id,
                            "evalue": parts[4],
                            "bit_score": parts[5],
                            "query_coverage": qcov.get((query_id, vfam_id), ""),
                            "annotation": ann.get("annotation", ""),
                            "function": ann.get("function", ""),
                            "category": ann.get("category", ""),
                        })
            result_path = proj_dir / "results" / "vogdb_vfam_annotation.tsv"
            result_path.parent.mkdir(parents=True, exist_ok=True)
            with open(result_path, "w", encoding="utf-8", newline="") as out:
                fieldnames = [
                    "query_protein_id", "vfam_id", "evalue", "bit_score",
                    "query_coverage", "annotation", "function", "category",
                ]
                writer = _csv.DictWriter(out, fieldnames=fieldnames, delimiter="\t")
                writer.writeheader()
                writer.writerows(rows)
            return len(rows)

        t_start = _time.time()
        lines = list(_search_log_lines.get())
        lines.append(f"\n=== {db_name} (hmmscan — domain annotation) ===")
        _search_log_lines.set(lines)

        # Step 1: Download if not present
        if not local_hmm.exists():
            target = archive_path if (is_gz or is_tar_gz) else local_hmm
            if not target.exists():
                cur = dict(_db_status.get())
                cur[db_name] = {"status": f"⬇️ Downloading {filename}…", "hits": None}
                _db_status.set(cur)

                lines = list(_search_log_lines.get())
                lines.append(f"  Downloading {download_url}")
                _search_log_lines.set(lines)

                curl_path = _shutil.which("curl") or "curl"
                proc = await _asyncio.create_subprocess_exec(
                    curl_path, "-L", "-C", "-", "-o", str(target),
                    "--progress-bar", download_url,
                    stdout=_asyncio.subprocess.PIPE,
                    stderr=_asyncio.subprocess.PIPE,
                )
                _, stderr = await proc.communicate()
                if proc.returncode != 0 or not target.exists():
                    cur = dict(_db_status.get())
                    cur[db_name] = {"status": f"❌ Download failed", "hits": 0}
                    _db_status.set(cur)
                    return

                elapsed = _time.time() - t_start
                size_mb = target.stat().st_size / 1_048_576
                lines = list(_search_log_lines.get())
                lines.append(f"  Downloaded {size_mb:.0f} MB in {int(elapsed)}s")
                _search_log_lines.set(lines)

            # Step 2: Extract/decompress if needed
            if is_tar_gz and not local_hmm.exists():
                cur = dict(_db_status.get())
                cur[db_name] = {"status": f"📦 Extracting HMM archive…", "hits": None}
                _db_status.set(cur)

                try:
                    hmm_members = []
                    with _tarfile.open(archive_path, "r:gz") as tf:
                        for member in tf.getmembers():
                            if member.isfile() and member.name.lower().endswith(".hmm"):
                                hmm_members.append(member)
                        if not hmm_members:
                            raise RuntimeError("No .hmm files found in archive")
                        with open(local_hmm, "wb") as out_hmm:
                            for member in hmm_members:
                                src = tf.extractfile(member)
                                if src is None:
                                    continue
                                _shutil.copyfileobj(src, out_hmm)
                                out_hmm.write(b"\n")
                    lines = list(_search_log_lines.get())
                    lines.append(f"  Extracted/concatenated {len(hmm_members)} HMM file(s)")
                    _search_log_lines.set(lines)
                except Exception as exc:
                    cur = dict(_db_status.get())
                    cur[db_name] = {"status": f"❌ Extract failed: {exc}", "hits": 0}
                    _db_status.set(cur)
                    return

            if is_gz and not local_hmm.exists():
                cur = dict(_db_status.get())
                cur[db_name] = {"status": f"📦 Decompressing…", "hits": None}
                _db_status.set(cur)

                proc = await _asyncio.create_subprocess_exec(
                    "gunzip", "-k", str(local_gz),
                    stdout=_asyncio.subprocess.PIPE,
                    stderr=_asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                if not local_hmm.exists():
                    cur = dict(_db_status.get())
                    cur[db_name] = {"status": "❌ Decompress failed", "hits": 0}
                    _db_status.set(cur)
                    return

        annotation_file = None
        annotation_url = db.get("annotation_url") or ""
        if annotation_url:
            annotation_filename = annotation_url.split("/")[-1].split("?")[0]
            annotation_file = db_dir / annotation_filename
            if not annotation_file.exists():
                cur = dict(_db_status.get())
                cur[db_name] = {"status": "⬇️ Downloading VOGDB annotations…", "hits": None}
                _db_status.set(cur)
                curl_path = _shutil.which("curl") or "curl"
                proc = await _asyncio.create_subprocess_exec(
                    curl_path, "-L", "-C", "-", "-o", str(annotation_file),
                    "--progress-bar", annotation_url,
                    stdout=_asyncio.subprocess.PIPE,
                    stderr=_asyncio.subprocess.PIPE,
                )
                _, stderr = await proc.communicate()
                if proc.returncode != 0 or not annotation_file.exists():
                    lines = list(_search_log_lines.get())
                    lines.append("  Warning: annotation download failed; hmmscan will still run.")
                    _search_log_lines.set(lines)
                    annotation_file = None

        # Step 3: hmmpress if index files don't exist
        h3i = _P(str(local_hmm) + ".h3i")
        if not h3i.exists():
            cur = dict(_db_status.get())
            cur[db_name] = {"status": f"🔧 Indexing with hmmpress…", "hits": None}
            _db_status.set(cur)

            hmmpress_bin = _shutil.which("hmmpress", path=_aug_path()) or "hmmpress"
            proc = await _asyncio.create_subprocess_exec(
                hmmpress_bin, "-f", str(local_hmm),
                stdout=_asyncio.subprocess.PIPE,
                stderr=_asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                cur = dict(_db_status.get())
                cur[db_name] = {"status": f"❌ hmmpress failed: {stderr.decode()[-100:]}", "hits": 0}
                _db_status.set(cur)
                return

            lines = list(_search_log_lines.get())
            lines.append(f"  hmmpress complete — index built")
            _search_log_lines.set(lines)

        # Step 4: Find hit proteins to scan
        hits_faa = proj_dir / "results" / "hits_proteins.faa"
        if not hits_faa.exists():
            # Fall back to seed sequences
            for cand_dir in ["data", "seeds", "input"]:
                for cand in sorted((proj_dir / cand_dir).glob("*.faa")) + sorted((proj_dir / cand_dir).glob("*.fasta")):
                    hits_faa = cand
                    break
                if hits_faa.exists():
                    break

        if not hits_faa.exists():
            cur = dict(_db_status.get())
            cur[db_name] = {"status": "⚠️ No hit proteins — run search first", "hits": None}
            _db_status.set(cur)
            return

        # Step 5: Run hmmscan
        cur = dict(_db_status.get())
        cur[db_name] = {"status": f"🔍 Scanning hits against {db_name}…", "hits": None}
        _db_status.set(cur)

        out_dir = proj_dir / "search_results"
        out_dir.mkdir(parents=True, exist_ok=True)
        domtbl = out_dir / f"{safe_name}.domtblout"
        tblout = out_dir / f"{safe_name}.tblout"

        hmmscan_bin = _shutil.which("hmmscan", path=_aug_path()) or "hmmscan"
        cmd = [
            hmmscan_bin,
            "--domtblout", str(domtbl),
            "--tblout", str(tblout),
            "-E", str(evalue),
            "--cpu", str(cpu),
            "--noali",
            str(local_hmm),
            str(hits_faa),
        ]

        runner_key = f"search_{safe_name}"
        from core.runner import AsyncJobRunner as _AJR
        if runner_key not in runner_dict:
            runner_dict[runner_key] = _AJR(step_name=runner_key)
        runner = runner_dict[runner_key]
        runner.start(cmd, cwd=proj_dir)

        while runner.is_running.get():
            await _asyncio.sleep(1.0)
            elapsed = _time.time() - t_start
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            cur = dict(_db_status.get())
            cur[db_name] = {"status": f"🔍 Scanning… {mins}m {secs:02d}s", "hits": None}
            _db_status.set(cur)

        rc = runner.returncode.get()
        elapsed = _time.time() - t_start
        hits = 0
        if rc == 0 and tblout.exists():
            try:
                with open(tblout) as fh:
                    hits = sum(1 for ln in fh if not ln.startswith("#") and ln.strip())
            except Exception:
                pass

        cur = dict(_db_status.get())
        if rc == 0:
            annotation_rows = _write_vogdb_annotation_table(tblout, domtbl, annotation_file)
            cur[db_name] = {"status": f"✅ Complete ({int(elapsed)}s)", "hits": hits}
            if annotation_rows:
                cur[db_name]["status"] += f" — {annotation_rows} annotated rows"
        else:
            cur[db_name] = {"status": f"❌ hmmscan failed (exit {rc})", "hits": 0}
        _db_status.set(cur)

        lines = list(_search_log_lines.get())
        lines.append(f"  → {hits} domain hits in {int(elapsed)}s")
        if db.get("setup_handler") == "vogdb_hmmscan":
            lines.append("  VOGDB annotation table: results/vogdb_vfam_annotation.tsv")
        _search_log_lines.set(lines)

    # ---- run_selected_dbs event ----------------------------------------------
    @reactive.effect
    @reactive.event(input.run_selected_dbs)
    async def _on_run_selected():
        import asyncio as _asyncio
        import traceback as _tb
        from pathlib import Path as _Path

        # Clear previous state
        _db_status.set({})
        _search_log_lines.set(["=== Search started ==="])

        # Resolve project directory
        proj_dir = None
        try:
            pd = proj_dir_rv.get() if proj_dir_rv is not None else None
            if pd and _Path(pd).exists():
                proj_dir = str(pd)
        except Exception:
            pass
        if not proj_dir:
            ui.notification_show("❌ No project loaded. Open a project in the sidebar first.", type="warning", duration=5)
            _search_log_lines.set(["ERROR: No project directory. Load a project first."])
            return

        # Resolve HMM path — try multiple sources
        hmm_path = ""
        # 1. Try state proxy
        try:
            if state is not None:
                params = state.get_params("hmm_build")
                if isinstance(params, dict):
                    hmm_path = params.get("hmm_path", "")
        except Exception:
            pass
        # 2. Read from .pipeline_state.json directly
        if not hmm_path:
            import json as _json
            state_file = _Path(proj_dir) / ".pipeline_state.json"
            if state_file.exists():
                try:
                    d = _json.loads(state_file.read_text())
                    hmm_path = d.get("steps", {}).get("hmm_build", {}).get("params", {}).get("hmm_path", "")
                except Exception:
                    pass
        # 3. Scan hmm/ directory
        if not hmm_path:
            hmm_dir = _Path(proj_dir) / "hmm"
            found = sorted(hmm_dir.glob("*.hmm")) if hmm_dir.exists() else []
            hmm_path = str(found[-1]) if found else ""
        if not hmm_path or not _Path(hmm_path).exists():
            ui.notification_show("❌ No HMM profile found. Build the HMM in Step 3 first.", type="warning", duration=5)
            _search_log_lines.set(["ERROR: No HMM profile. Run Step 3 (Build HMM) first."])
            return

        # Get selected databases
        selected = _selected_db_names()
        if not selected:
            ui.notification_show("⚠️ No databases selected. Tick at least one checkbox above.", type="warning", duration=5)
            _search_log_lines.set(["ERROR: No databases selected."])
            return

        # Show immediate feedback
        import sys as _sys2
        print(f"[SEARCH] Starting: {len(selected)} dbs, hmm={hmm_path}, proj={proj_dir}", file=_sys2.stderr, flush=True)
        ui.notification_show(
            f"🔍 Searching {len(selected)} database(s): {', '.join(selected[:3])}{'…' if len(selected) > 3 else ''}",
            type="message", duration=4,
        )
        lines = list(_search_log_lines.get())
        lines.append(f"HMM: {hmm_path}")
        lines.append(f"Project: {proj_dir}")
        lines.append(f"Databases: {', '.join(selected)}")
        lines.append(f"E-value: {input.search_evalue()}")
        lines.append("")
        _search_log_lines.set(lines)

        # Set all selected databases to "pending"
        cur = {}
        for name in selected:
            cur[name] = {"status": "⏳ Queued", "hits": None}
        _db_status.set(cur)

        # Run all selected databases sequentially (each updates progress live)
        try:
            if state is not None:
                state.mark_running("search")
            for name in selected:
                # Yield to event loop so UI can flush the "Queued" → "Running" transition
                await _asyncio.sleep(0.1)
                await _run_one_db(name, hmm_path, proj_dir)
        except Exception as _exc:
            lines = list(_search_log_lines.get())
            lines.append(f"\n❌ ERROR: {_exc}")
            lines.append(_tb.format_exc()[:500])
            _search_log_lines.set(lines)

        # Compile all tblout files → results/hits_main.tsv
        compiled_rows = 0
        try:
            compiled_rows = await _compile_hits(proj_dir, hmm_path)
            lines = list(_search_log_lines.get())
            lines.append(f"\n=== Search output compiled: {compiled_rows} hit rows ===")
            _search_log_lines.set(lines)
        except Exception as _exc:
            lines = list(_search_log_lines.get())
            lines.append(f"\n⚠️ Warning compiling hits: {_exc}")
            _search_log_lines.set(lines)

        complete, failed, running = _search_status_summary()
        try:
            if state is not None:
                params = {
                    "databases": selected,
                    "evalue": input.search_evalue(),
                    "complete_databases": complete,
                    "failed_databases": failed,
                    "hit_rows": compiled_rows,
                }
                if failed or running or complete == 0:
                    state.mark_failed("search", f"{failed} failed, {complete} complete, {compiled_rows} hit rows")
                else:
                    state.mark_complete("search", params)
        except Exception:
            pass

        if failed or complete == 0:
            ui.notification_show("❌ Search finished with failures. See Step 4 log.", type="error", duration=7)
        else:
            ui.notification_show("✅ Search complete!", type="message", duration=4)

    def _resolve_proj_hmm() -> "tuple[str,str]":
        """Return (proj_dir_str, hmm_path_str) reading from disk if reactive state unavailable."""
        from pathlib import Path as _Path
        import json as _json

        # --- project dir ---
        proj_dir = ""
        try:
            pd = proj_dir_rv.get() if proj_dir_rv is not None else None
            if pd and _Path(pd).exists():
                proj_dir = str(pd)
        except Exception:
            pass

        # --- HMM path: try state first, then scan disk ---
        hmm_path = ""
        if proj_dir:
            try:
                if state is not None:
                    hmm_path = state.get_params("hmm_build").get("hmm_path", "")
            except Exception:
                pass
            if not hmm_path:
                # Read directly from .pipeline_state.json
                state_file = _Path(proj_dir) / ".pipeline_state.json"
                if state_file.exists():
                    try:
                        d = _json.loads(state_file.read_text())
                        hmm_path = d.get("steps", {}).get("hmm_build", {}).get("params", {}).get("hmm_path", "")
                    except Exception:
                        pass
            if not hmm_path:
                hmm_dir = _Path(proj_dir) / "hmm"
                found = sorted(hmm_dir.glob("*.hmm")) if hmm_dir.exists() else []
                hmm_path = str(found[0]) if found else ""
        return proj_dir, hmm_path

    async def _compile_hits(proj_dir: str, hmm_path: str) -> int:
        """Parse all tblout files in search_results/ → results/hits_main.tsv."""
        from pathlib import Path as _Path

        results_dir = _Path(proj_dir) / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        search_dir  = _Path(proj_dir) / "search_results"
        out_tsv     = results_dir / "hits_main.tsv"
        empty_cols = [
            "target_name",
            "query_name",
            "evalue",
            "bit_score",
            "bias_score",
            "description",
            "database_source",
            "hmm_coverage_pct",
            "confidence_tier",
            "why_classified",
            "genome_id",
            "source_contig",
            "seq_from",
            "seq_to",
            "strand",
        ]

        tblouts = list(search_dir.glob("*.tblout")) if search_dir.exists() else []
        if not tblouts:
            out_tsv.write_text("\t".join(empty_cols) + "\n")
            return 0

        # Get HMM length from state, then HMM file, then fall back to 100
        hmm_len = 0
        try:
            params = (state.get_params("hmm_build") or {})
            hmm_len = int(params.get("profile_length", params.get("LENG", 0)))
        except Exception:
            pass
        if hmm_len <= 0:
            try:
                for line in _Path(hmm_path).read_text().splitlines():
                    if line.startswith("LENG"):
                        hmm_len = int(line.split()[1])
                        break
            except Exception:
                pass
        if hmm_len <= 0:
            hmm_len = 100

        try:
            import pandas as _pd
            from pipeline.searcher import parse_tblout as _parse_tblout
        except Exception:
            return 0

        all_frames = []
        for tbl in tblouts:
            db_name = tbl.stem  # e.g. "seeds", "inphared"
            try:
                df = _parse_tblout(tbl)
                if df.empty:
                    continue
                df["database_source"] = db_name
                six = df["description"].astype(str).str.extract(
                    r"coords=([^:]+):(\d+)-(\d+)\(([+-])\)"
                )
                prod = df["description"].astype(str).str.extract(
                    r"^\s*#\s*(\d+)\s*#\s*(\d+)\s*#\s*(-?1)\s*#"
                )
                fallback_genome = (
                    df["target_name"]
                    .astype(str)
                    .str.replace(r"_sixframe_orf\d+$", "", regex=True)
                    .str.replace(r"_s-?1_f\d+_o\d+$", "", regex=True)
                )
                df["genome_id"] = six[0].where(six[0].notna() & (six[0] != ""), fallback_genome)
                df["source_contig"] = six[0].fillna("")
                df["seq_from"] = (
                    _pd.to_numeric(six[1], errors="coerce")
                    .fillna(_pd.to_numeric(prod[0], errors="coerce"))
                    .fillna(0)
                    .astype(int)
                )
                df["seq_to"] = (
                    _pd.to_numeric(six[2], errors="coerce")
                    .fillna(_pd.to_numeric(prod[1], errors="coerce"))
                    .fillna(0)
                    .astype(int)
                )
                df["strand"] = six[3].fillna(prod[2].map({"1": "+", "-1": "-"})).fillna("")
                # Compute HMM coverage from domain coords if available, else estimate
                if "hmm_from" in df.columns and "hmm_to" in df.columns:
                    df["hmm_coverage_pct"] = ((df["hmm_to"] - df["hmm_from"] + 1) / hmm_len * 100).round(1)
                else:
                    df["hmm_coverage_pct"] = 100.0
                # Simple confidence classification based on bit score
                strict   = 45.0
                moderate = 30.0
                def _classify(row):
                    bs = float(row.get("bit_score", 0))
                    cov = float(row.get("hmm_coverage_pct", 0))
                    if bs >= strict and cov >= 60:
                        return "high_confidence"
                    if bs >= moderate:
                        return "putative"
                    if bs > 0:
                        return "divergent"
                    return "likely_fp"
                df["confidence_tier"] = df.apply(_classify, axis=1)
                df["why_classified"] = df.apply(
                    lambda r: f"bit={r.get('bit_score',0)}; hmm_cov={r.get('hmm_coverage_pct',0):.1f}%",
                    axis=1,
                )
                all_frames.append(df)
            except Exception:
                continue

        if not all_frames:
            out_tsv.write_text("\t".join(empty_cols) + "\n")
            return 0

        combined = _pd.concat(all_frames, ignore_index=True)
        # Ensure evalue column consistency
        if "evalue" not in combined.columns and "e_value" in combined.columns:
            combined["evalue"] = combined["e_value"]
        combined.to_csv(out_tsv, sep="\t", index=False)

        # Also update hits_df_rv so Results tab reacts immediately
        try:
            if hits_df_rv is not None:
                hits_df_rv.set(combined)
        except Exception:
            pass

        # Update state
        try:
            if state is not None:
                state.mark_complete("classify", {
                    "total": len(combined),
                    "high_confidence": int((combined["confidence_tier"] == "high_confidence").sum()),
                })
        except Exception:
            pass

        return len(combined)

    def _resolve_local_dbs(proj_dir: str) -> "list[dict]":
        """Return list of database dicts that have a local path, reading directly from databases.json."""
        from pathlib import Path as _Path
        import json as _json

        # Try registry first
        try:
            reg = _get_registry()
            if reg is not None:
                dbs = reg.get_all() if hasattr(reg, "get_all") else reg.list_all()
                local = [db for db in dbs if db.get("path")]
                if local:
                    return local
        except Exception:
            pass

        # Fallback: read databases.json directly
        if proj_dir:
            db_file = _Path(proj_dir) / "databases.json"
            if db_file.exists():
                try:
                    dbs = _json.loads(db_file.read_text())
                    return [db for db in dbs if db.get("path")]
                except Exception:
                    pass
        return []

    # ---- run_all_dbs event ---------------------------------------------------
    @reactive.effect
    @reactive.event(input.run_all_dbs)
    async def _on_run_all():
        import traceback as _tb
        from pathlib import Path as _Path

        _db_status.set({})
        _search_log_lines.set(["=== Run All started ==="])

        proj_dir, hmm_path = _resolve_proj_hmm()
        if not proj_dir or not hmm_path:
            ui.notification_show("❌ No project or HMM found.", type="warning", duration=5)
            return

        # Get ALL enabled databases from registry (not just local ones)
        reg = _get_registry()
        all_dbs = reg.get_all() if reg is not None and hasattr(reg, "get_all") else []
        enabled_dbs = [db for db in all_dbs if db.get("enabled", True)]

        if not enabled_dbs:
            ui.notification_show("⚠️ No databases enabled.", type="warning", duration=5)
            return

        names = [db["name"] for db in enabled_dbs]
        ui.notification_show(
            f"🔍 Running ALL {len(names)} databases: {', '.join(names[:3])}…",
            type="message", duration=4,
        )

        cur = {name: {"status": "⏳ Queued", "hits": None} for name in names}
        _db_status.set(cur)

        try:
            for db in enabled_dbs:
                await _run_one_db(db["name"], hmm_path, proj_dir, db_dict=db)
        except Exception as _exc:
            lines = list(_search_log_lines.get())
            lines.append(f"\n❌ ERROR: {_exc}")
            lines.append(_tb.format_exc()[:500])
            _search_log_lines.set(lines)

        compiled_rows = 0
        try:
            compiled_rows = await _compile_hits(proj_dir, hmm_path)
        except Exception:
            pass

        complete, failed, running = _search_status_summary()
        try:
            if state is not None:
                params = {
                    "databases": names,
                    "evalue": "1e-5",
                    "complete_databases": complete,
                    "failed_databases": failed,
                    "hit_rows": compiled_rows,
                }
                if failed or running or complete == 0:
                    state.mark_failed("search", f"{failed} failed, {complete} complete, {compiled_rows} hit rows")
                else:
                    state.mark_complete("search", params)
        except Exception:
            pass

        if failed or complete == 0:
            ui.notification_show("❌ Run All finished with failures. See Step 4 log.", type="error", duration=7)
        else:
            ui.notification_show("✅ All searches complete!", type="message", duration=4)

    # ---- search_activity_banner (prominent live status) -----------------------
    @output
    @render.ui
    def search_activity_banner():
        reactive.invalidate_later(1)
        statuses = _db_status.get()
        if not statuses:
            statuses = _persisted_search_statuses()
        if not statuses:
            return ui.tags.span("")

        # Find what's currently running
        running = []
        queued = []
        done = []
        failed = []
        for name, info in statuses.items():
            s = _status_text(info)
            if _is_running_status(s) and "Queued" not in s:
                running.append((name, s))
            elif "Queued" in s:
                queued.append(name)
            elif _is_complete_status(s):
                done.append(name)
            elif _is_failed_status(s):
                failed.append((name, s))

        if not running and not queued:
            if failed:
                return ui.tags.div(
                    ui.tags.span("❌ Search finished with failures", class_="fs-6 fw-bold text-danger"),
                    ui.tags.div(
                        ui.tags.small(
                            f"Failed: {', '.join(name for name, _ in failed[:5])}"
                            f"{'…' if len(failed) > 5 else ''}",
                            class_="text-muted",
                        ),
                    ),
                    class_="alert alert-danger py-2 px-3 mb-3",
                )
            if done:
                # Check if results were recovered from disk rather than run live
                any_recovered = any(
                    info.get("_recovered") for info in statuses.values()
                )
                if any_recovered:
                    return ui.tags.div(
                        ui.tags.div(
                            ui.tags.span("⚠️ Session reconnected", class_="fs-6 fw-bold text-warning"),
                            ui.tags.span(" — results recovered from disk", class_="text-light"),
                        ),
                        ui.tags.div(
                            ui.tags.small(
                                f"Found {len(done)} completed database(s). "
                                "HMMER may still be running in the background. "
                                "Refresh the page to check for new completions. "
                                "Go to Step 7 → Results to review hits.",
                                class_="text-muted",
                            ),
                        ),
                        class_="alert alert-warning py-2 px-3 mb-3",
                    )
                return ui.tags.div(
                    ui.tags.span("✅ All searches complete", class_="fs-6 fw-bold text-success"),
                    ui.tags.div(
                        ui.tags.small(
                            f"Completed {len(done)} database(s). Go to Step 7 → Results to review hits.",
                            class_="text-muted",
                        ),
                    ),
                    class_="alert alert-success py-2 px-3 mb-3",
                )
            return ui.tags.span("")

        # Build the banner
        parts = []
        if running:
            name, status = running[0]
            parts.append(ui.tags.div(
                ui.tags.span("⚡ NOW RUNNING: ", class_="fw-bold"),
                ui.tags.span(f"{name} ", class_="fw-bold text-info"),
                ui.tags.span(f"— {status}", class_="text-light"),
                class_="fs-6",
            ))
        if queued:
            parts.append(ui.tags.div(
                ui.tags.small(f"⏳ Up next: {', '.join(queued[:3])}{'…' if len(queued) > 3 else ''}", class_="text-muted"),
            ))
        if done:
            parts.append(ui.tags.div(
                ui.tags.small(f"✅ Done: {', '.join(done[:5])}{'…' if len(done) > 5 else ''}", class_="text-muted"),
            ))

        return ui.tags.div(
            *parts,
            class_="alert alert-dark py-2 px-3 mb-3 border border-info",
            style="background:#1a1f25;",
        )

    # ---- search_progress_table -----------------------------------------------
    @output
    @render.ui
    def search_progress_table():
        reactive.invalidate_later(2)
        statuses = _db_status.get()
        if not statuses:
            statuses = _persisted_search_statuses()
        if not statuses:
            return ui.tags.p(
                "No searches started yet. Select databases above and click ▶ Run Selected.",
                class_="text-muted",
            )

        def _status_badge(s: str) -> ui.TagChild:
            if _is_failed_status(s):
                return ui.tags.span("❌ Failed", class_="badge bg-danger")
            if _is_complete_status(s):
                return ui.tags.span("✅ Complete", class_="badge bg-success")
            if _is_running_status(s):
                return ui.tags.span("🔄 Running", class_="badge bg-warning text-dark")
            if "Queued" in s:
                return ui.tags.span("⏳ Queued", class_="badge bg-secondary")
            return ui.tags.span(s or "pending", class_="badge bg-secondary")

        rows = []
        for db_name, info in statuses.items():
            status_str = info.get("status", "pending")
            hits = info.get("hits")
            hits_cell = str(hits) if hits is not None else "—"
            rows.append(
                ui.tags.tr(
                    ui.tags.td(db_name),
                    ui.tags.td(_status_badge(status_str)),
                    ui.tags.td(hits_cell),
                )
            )

        return ui.tags.div(
            ui.tags.table(
                ui.tags.thead(
                    ui.tags.tr(
                        ui.tags.th("Database"),
                        ui.tags.th("Status"),
                        ui.tags.th("Hits found"),
                    )
                ),
                ui.tags.tbody(*rows),
                class_="table table-sm table-bordered table-hover",
            ),
            style="max-height:350px; overflow-y:auto;",
        )

    # ---- search_log ----------------------------------------------------------
    @output
    @render.text
    def search_log():
        reactive.invalidate_later(2)
        lines = _search_log_lines.get()
        if not lines:
            active_logs: list[str] = []
            for key, runner in runner_dict.items():
                if key.startswith("search_") and runner.is_running.get():
                    active_logs.append(f"=== {key} ===")
                    active_logs.append(runner.get_log())
            return "\n".join(active_logs) if active_logs else "No search log yet."
        return "\n".join(lines)

    # ---- search_summary_card (post-search report for publications) -----------
    @output
    @render.ui
    def search_summary_card():
        reactive.invalidate_later(3)
        from pathlib import Path as _Path

        statuses = _db_status.get()
        if not statuses:
            statuses = _persisted_search_statuses()
        if not statuses:
            return ui.tags.span("")

        # Only show once at least one search has completed
        completed = {k: v for k, v in statuses.items()
                     if "Complete" in str(v.get("status", "")) or "✅" in str(v.get("status", ""))}
        still_running = any("Streaming" in str(v.get("status", ""))
                           or "Searching" in str(v.get("status", ""))
                           or "Queued" in str(v.get("status", ""))
                           for v in statuses.values())

        if not completed:
            return ui.tags.span("")

        # Build summary table
        total_hits = 0
        total_hc = 0
        rows = []
        for db_name, info in statuses.items():
            status_str = str(info.get("status", ""))
            hits = info.get("hits")
            if hits is None:
                hits = 0

            # Extract time from status string like "✅ Complete (87s)"
            import re
            time_match = re.search(r'\((\d+)s', status_str)
            time_str = f"{int(time_match.group(1))}s" if time_match else "—"

            # Determine badge
            if "✅" in status_str or "Complete" in status_str:
                status_badge = ui.tags.span("✅ Done", class_="badge bg-success")
            elif "❌" in status_str or "Failed" in status_str:
                status_badge = ui.tags.span("❌ Failed", class_="badge bg-danger")
            elif "Streaming" in status_str or "Searching" in status_str:
                status_badge = ui.tags.span("🔄 Running", class_="badge bg-warning text-dark")
            elif "Queued" in status_str:
                status_badge = ui.tags.span("⏳ Queued", class_="badge bg-secondary")
            else:
                status_badge = ui.tags.span(status_str[:20], class_="badge bg-secondary")

            # Hit count styling
            if hits > 0:
                hit_badge = ui.tags.span(str(hits), class_="badge bg-primary fs-6")
            else:
                hit_badge = ui.tags.span("0", class_="badge bg-light text-dark")

            total_hits += hits

            rows.append(ui.tags.tr(
                ui.tags.td(ui.tags.strong(db_name)),
                ui.tags.td(status_badge),
                ui.tags.td(hit_badge, class_="text-center"),
                ui.tags.td(time_str, class_="text-muted text-center"),
            ))

        # Read hits_main.tsv for tier breakdown if available
        tier_summary = ""
        pd_ = proj_dir_rv.get() if proj_dir_rv is not None else None
        if pd_:
            hits_file = _Path(pd_) / "results" / "hits_main.tsv"
            if hits_file.exists():
                try:
                    import pandas as _pd
                    df = _pd.read_csv(hits_file, sep="\t")
                    if "confidence_tier" in df.columns:
                        tiers = df["confidence_tier"].value_counts().to_dict()
                        total_hc = tiers.get("high_confidence", 0)
                        tier_badges = []
                        tier_colors = {
                            "high_confidence": "success",
                            "putative": "primary",
                            "divergent": "warning",
                            "likely_fp": "danger",
                        }
                        for tier_name in ["high_confidence", "putative", "divergent", "likely_fp"]:
                            count = tiers.get(tier_name, 0)
                            if count > 0:
                                color = tier_colors.get(tier_name, "secondary")
                                label = tier_name.replace("_", " ").title()
                                tier_badges.append(
                                    ui.tags.span(f"{label}: {count}", class_=f"badge bg-{color} me-1")
                                )
                        if tier_badges:
                            tier_summary = ui.tags.div(
                                ui.tags.small("Confidence breakdown: ", class_="text-muted"),
                                *tier_badges,
                                class_="mt-2",
                            )

                    # Cross-database overlap analysis — full detail
                    overlap_rows = []
                    if "database_source" in df.columns and "target_name" in df.columns:
                        import re as _re2
                        def _base_acc(pid):
                            return _re2.sub(r'_s-?[12]_f[012]_o\d+$', '', str(pid))
                        df["_base_acc"] = df["target_name"].apply(_base_acc)

                        for acc, grp in df.groupby("_base_acc"):
                            dbs_in = grp["database_source"].unique()
                            if len(dbs_in) > 1:
                                # One row per database for this accession
                                for _, hit_row in grp.iterrows():
                                    db_src = str(hit_row.get("database_source", ""))
                                    score = hit_row.get("bit_score", 0)
                                    ev = hit_row.get("evalue", 0)
                                    full_id = str(hit_row.get("target_name", ""))
                                    overlap_rows.append({
                                        "accession": str(acc),
                                        "n_dbs": len(dbs_in),
                                        "database": db_src,
                                        "full_id": full_id,
                                        "score": float(score),
                                        "evalue": float(ev),
                                    })

                        n_overlap = len(set(r["accession"] for r in overlap_rows))
                        df.drop(columns=["_base_acc"], inplace=True, errors="ignore")
                except Exception:
                    pass

        # Cross-database overlap detail
        overlap_summary = ""
        try:
            if n_overlap > 0:
                # Build table rows — group by accession with visual separator
                table_rows = []
                seen_accs = set()
                sorted_rows = sorted(overlap_rows, key=lambda r: (-r["n_dbs"], -r["score"]))
                for r in sorted_rows[:60]:
                    acc = r["accession"]
                    is_first = acc not in seen_accs
                    seen_accs.add(acc)
                    table_rows.append(ui.tags.tr(
                        ui.tags.td(
                            ui.tags.strong(acc) if is_first else "",
                            style="border-top:2px solid #444;" if is_first and len(table_rows) > 0 else "",
                        ),
                        ui.tags.td(
                            ui.tags.span(str(r["n_dbs"]), class_="badge bg-info") if is_first else "",
                            class_="text-center",
                        ),
                        ui.tags.td(r["database"]),
                        ui.tags.td(r["full_id"][:45], style="font-size:0.8rem;"),
                        ui.tags.td(f"{r['score']:.1f}", class_="text-end"),
                        ui.tags.td(f"{r['evalue']:.1e}", class_="text-end"),
                    ))

                overlap_summary = ui.card(
                    ui.card_header(
                        ui.tags.strong(f"🔗 Cross-Database Hits — {n_overlap} genome(s) found in multiple databases"),
                    ),
                    ui.tags.p(
                        "Each group below is the same genome/protein discovered independently in different databases. "
                        "You can compare scores across databases — consistent high scores mean strong evidence.",
                        class_="small text-muted px-3 pt-2 mb-1",
                    ),
                    ui.tags.div(
                        ui.tags.table(
                            ui.tags.thead(ui.tags.tr(
                                ui.tags.th("Genome"),
                                ui.tags.th("DBs", class_="text-center"),
                                ui.tags.th("Database"),
                                ui.tags.th("Hit ID"),
                                ui.tags.th("Score", class_="text-end"),
                                ui.tags.th("E-value", class_="text-end"),
                            )),
                            ui.tags.tbody(*table_rows),
                            class_="table table-sm table-bordered table-hover mb-0",
                        ),
                        style="max-height:450px; overflow-y:auto;",
                    ),
                    class_="mt-3",
                )
            else:
                overlap_summary = ui.tags.div(
                    ui.tags.small(
                        "ℹ️ No cross-database overlaps — each hit found in only one database.",
                        class_="text-muted",
                    ),
                    class_="mt-2",
                )
        except Exception:
            pass

        # Summary stat cards
        n_databases = len(completed)
        n_failed = sum(1 for v in statuses.values() if "❌" in str(v.get("status", "")))

        header_cards = ui.layout_columns(
            stat_card("Databases searched", n_databases, "primary", "🔍"),
            stat_card("Total hits", total_hits, "success" if total_hits > 0 else "secondary", "🎯"),
            stat_card("High confidence", total_hc, "success" if total_hc > 0 else "secondary", "⭐"),
            stat_card("Failed", n_failed, "danger" if n_failed > 0 else "success", "⚠️" if n_failed > 0 else "✅"),
            col_widths=[3, 3, 3, 3],
        )

        # Running indicator
        running_note = ""
        if still_running:
            running_note = ui.tags.div(
                ui.tags.span("🔄 Searches still running — summary updates automatically",
                             class_="text-warning small"),
                class_="mb-2",
            )

        return ui.card(
            ui.card_header(
                ui.tags.div(
                    ui.tags.strong("📊 Search Summary"),
                    ui.tags.small(
                        " — Use this data for your Methods & Results sections",
                        class_="text-muted ms-2",
                    ),
                    class_="d-flex align-items-center",
                )
            ),
            running_note,
            header_cards,
            tier_summary if tier_summary else "",
            overlap_summary if overlap_summary else "",
            ui.tags.div(
                ui.tags.table(
                    ui.tags.thead(ui.tags.tr(
                        ui.tags.th("Database"),
                        ui.tags.th("Status"),
                        ui.tags.th("Hits", class_="text-center"),
                        ui.tags.th("Time", class_="text-center"),
                    )),
                    ui.tags.tbody(*rows),
                    class_="table table-sm table-bordered table-hover mt-3 mb-0",
                ),
                style="max-height:400px; overflow-y:auto;",
            ),
            ui.tags.div(
                ui.tags.small(
                    f"Total unique hits across all databases: {total_hits}. "
                    f"Deduplicated results saved to results/hits_main.tsv.",
                    class_="text-muted mt-2 d-block",
                ),
            ),
            class_="mt-3 mb-3",
        )
