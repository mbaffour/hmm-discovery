"""
ui/components.py — Shared UI building blocks used across all step panels.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from shiny import ui


# ---------------------------------------------------------------------------
# Step card
# ---------------------------------------------------------------------------

def step_card(
    step_num: int,
    title: str,
    *content,
    status: str = "pending",   # pending | running | complete | failed
    collapsible: bool = False,
    id: str = "",
) -> ui.TagChild:
    """Wrap a step's content in a styled card with status badge."""
    badge_cls = {
        "pending":  "bg-secondary",
        "running":  "bg-warning text-dark",
        "complete": "bg-success",
        "failed":   "bg-danger",
    }.get(status, "bg-secondary")

    badge_icon = {
        "pending":  "⏳",
        "running":  "🔄",
        "complete": "✅",
        "failed":   "❌",
    }.get(status, "⏳")

    header_content = ui.tags.div(
        ui.tags.span(
            f"Step {step_num}",
            class_="text-muted small me-2",
        ),
        ui.tags.strong(title),
        ui.tags.span(
            f"{badge_icon} {status.title()}",
            class_=f"badge {badge_cls} ms-2",
        ),
        class_="d-flex align-items-center gap-1",
    )

    return ui.card(
        ui.card_header(header_content),
        *content,
        id=id or f"step_card_{step_num}",
        class_="mb-3",
    )


# ---------------------------------------------------------------------------
# Log panel
# ---------------------------------------------------------------------------

def log_panel(output_id: str, height: str = "250px") -> ui.TagChild:
    """Scrollable verbatim log output with auto-scroll JS."""
    return ui.tags.div(
        ui.output_text_verbatim(output_id, placeholder=True),
        ui.tags.script(
            f"""
            (function() {{
                var observer = new MutationObserver(function() {{
                    var el = document.getElementById('{output_id}');
                    if (el) el.scrollTop = el.scrollHeight;
                }});
                var target = document.getElementById('{output_id}');
                if (target) observer.observe(target, {{childList: true, subtree: true, characterData: true}});
            }})();
            """
        ),
        style=f"height:{height}; overflow-y:auto; background:#1e1e1e; color:#d4d4d4; font-size:12px; padding:8px; border-radius:4px; font-family:monospace;",
    )


# ---------------------------------------------------------------------------
# Stat badge / value box
# ---------------------------------------------------------------------------

def stat_badge(label: str, value: str, color: str = "primary") -> ui.TagChild:
    """Inline stat badge chip."""
    return ui.tags.span(
        ui.tags.strong(str(value)),
        f" {label}",
        class_=f"badge bg-{color} me-1 fs-6",
    )


def stat_card(label: str, value, color: str = "primary", icon: str = "") -> ui.TagChild:
    """Bootstrap 5 value-box-style stat card."""
    return ui.tags.div(
        ui.tags.div(
            ui.tags.div(
                ui.tags.span(icon + " " if icon else "", class_="fs-3"),
                ui.tags.div(ui.tags.strong(str(value), class_=f"fs-2 text-{color}"), label, class_="small text-muted"),
                class_="d-flex align-items-center gap-2",
            ),
            class_="card-body py-2 px-3",
        ),
        class_="card border-0 shadow-sm",
    )


# ---------------------------------------------------------------------------
# Learning and decision-support blocks
# ---------------------------------------------------------------------------

def guidance_callout(title: str, body: str, tone: str = "info", *extra) -> ui.TagChild:
    """Compact contextual guidance block for scientific caveats and next steps."""
    tone_class = {
        "info": "callout-info",
        "success": "callout-success",
        "warning": "callout-warning",
        "danger": "callout-danger",
        "secondary": "callout-secondary",
    }.get(tone, "callout-info")
    return ui.tags.div(
        ui.tags.div(
            ui.tags.strong(title, class_="d-block mb-1"),
            ui.tags.span(body, class_="small"),
            *extra,
        ),
        class_=f"guidance-callout {tone_class}",
    )


def learning_card(title: str, bullets: list[str], tone: str = "info") -> ui.TagChild:
    """Small educational card used where a control needs scientific context."""
    tone_class = {
        "info": "learning-card-info",
        "success": "learning-card-success",
        "warning": "learning-card-warning",
        "secondary": "learning-card-secondary",
    }.get(tone, "learning-card-info")
    return ui.tags.div(
        ui.tags.strong(title, class_="d-block mb-1"),
        ui.tags.ul(*[ui.tags.li(item) for item in bullets], class_="small mb-0 ps-3"),
        class_=f"learning-card {tone_class}",
    )


def click_go_strip(steps: list[tuple[str, str]]) -> ui.TagChild:
    """Compact no-code workflow rail for the app's educational surfaces."""
    return ui.tags.div(
        *[
            ui.tags.div(
                ui.tags.strong(title),
                ui.tags.span(body),
                class_="click-go-step",
            )
            for title, body in steps
        ],
        class_="click-go-strip",
    )


def gene_context_strip() -> ui.TagChild:
    """Small decorative genome-neighborhood graphic rendered with CSS."""
    return ui.tags.div(
        ui.tags.span(class_="gene", style="left:7%;top:20px;width:18%;"),
        ui.tags.span(class_="gene gene-blue", style="left:28%;top:52px;width:14%;"),
        ui.tags.span(class_="gene gene-copper", style="left:46%;top:32px;width:19%;"),
        ui.tags.span(class_="gene", style="left:69%;top:58px;width:21%;"),
        class_="gene-context-strip",
        aria_label="Genome neighborhood context graphic",
    )


# ---------------------------------------------------------------------------
# Local filesystem picker
# ---------------------------------------------------------------------------

def filesystem_picker_ui(
    picker_id: str,
    title: str,
    help_text: str,
    *,
    allow_create_dir: bool = False,
    class_: str = "mb-2 bg-light",
) -> ui.TagChild:
    """Reusable in-app file/folder navigator for local Shiny deployments."""
    create_controls = []
    if allow_create_dir:
        create_controls = [
            ui.layout_columns(
                ui.input_text(
                    f"{picker_id}_new_folder_name",
                    "Create subfolder here",
                    value="",
                    placeholder="new_folder",
                ),
                ui.tags.div(
                    ui.input_action_button(
                        f"{picker_id}_create",
                        "Create And Use",
                        class_="btn btn-outline-success mt-4",
                    ),
                    ui.output_ui(f"{picker_id}_status"),
                ),
                col_widths=[8, 4],
            )
        ]
    else:
        create_controls = [ui.output_ui(f"{picker_id}_status")]

    return ui.card(
        ui.card_header(ui.tags.strong("📂 " + title)),
        ui.tags.p(help_text, class_="text-muted small mb-2"),
        ui.output_ui(f"{picker_id}_browser"),
        ui.tags.div(
            ui.input_action_button(f"{picker_id}_home", "🏠 Home", class_="btn btn-outline-secondary btn-sm me-1 mb-1"),
            ui.input_action_button(f"{picker_id}_documents", "📄 Documents", class_="btn btn-outline-secondary btn-sm me-1 mb-1"),
            ui.input_action_button(f"{picker_id}_desktop", "🖥 Desktop", class_="btn btn-outline-secondary btn-sm me-1 mb-1"),
            ui.input_action_button(f"{picker_id}_project", "📁 Project Folder", class_="btn btn-outline-secondary btn-sm me-1 mb-1"),
            ui.input_action_button(f"{picker_id}_parent", "⬆ Parent", class_="btn btn-outline-secondary btn-sm me-1 mb-1"),
            ui.input_action_button(f"{picker_id}_from_typed", "🔍 Browse Typed Path", class_="btn btn-outline-secondary btn-sm me-1 mb-1"),
            ui.input_action_button(f"{picker_id}_open", "📂 Open Selected", class_="btn btn-outline-primary btn-sm me-1 mb-1"),
            ui.input_action_button(f"{picker_id}_use_selected", "✅ Use Selected", class_="btn btn-success btn-sm me-1 mb-1"),
            ui.input_action_button(f"{picker_id}_use_current", "✅ Use Current Folder", class_="btn btn-outline-success btn-sm me-1 mb-1"),
            class_="mb-2",
        ),
        *create_controls,
        class_=f"filesystem-picker-card {class_}",
    )


def _choose_native_path(mode: str, title: str, start_dir: Path | str | None = None) -> Path | None:
    """Open a native file/folder chooser on the machine running the Shiny app."""
    mode = "dir" if mode == "folder" else mode
    start = Path(start_dir or Path.home()).expanduser()
    if start.is_file():
        start = start.parent
    if not start.exists():
        start = Path.home()

    if sys.platform == "darwin":
        prompt = title.replace('"', '\\"')
        start_posix = str(start).replace('"', '\\"')
        target = "folder" if mode == "dir" else "file"
        script = (
            f'set startFolder to POSIX file "{start_posix}" as alias\n'
            f'set chosenItem to choose {target} with prompt "{prompt}" default location startFolder\n'
            "POSIX path of chosenItem"
        )
        proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if proc.returncode != 0:
            return None
        picked = proc.stdout.strip()
        return Path(picked) if picked else None

    if sys.platform.startswith("linux"):
        if mode == "dir":
            if shutil.which("zenity"):
                cmd = ["zenity", "--file-selection", "--directory", "--title", title, "--filename", str(start) + "/"]
            elif shutil.which("kdialog"):
                cmd = ["kdialog", "--getexistingdirectory", str(start), "--title", title]
            else:
                return None
        else:
            if shutil.which("zenity"):
                cmd = ["zenity", "--file-selection", "--title", title, "--filename", str(start) + "/"]
            elif shutil.which("kdialog"):
                cmd = ["kdialog", "--getopenfilename", str(start), "--title", title]
            else:
                return None
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            return None
        picked = proc.stdout.strip()
        return Path(picked) if picked else None

    if sys.platform.startswith("win"):
        escaped_start = str(start).replace("'", "''")
        escaped_title = title.replace("'", "''")
        if mode == "dir":
            ps = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$dlg = New-Object System.Windows.Forms.FolderBrowserDialog; "
                f"$dlg.Description = '{escaped_title}'; "
                f"$dlg.SelectedPath = '{escaped_start}'; "
                "if ($dlg.ShowDialog() -eq 'OK') { $dlg.SelectedPath }"
            )
        else:
            ps = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$dlg = New-Object System.Windows.Forms.OpenFileDialog; "
                f"$dlg.Title = '{escaped_title}'; "
                f"$dlg.InitialDirectory = '{escaped_start}'; "
                "if ($dlg.ShowDialog() -eq 'OK') { $dlg.FileName }"
            )
        proc = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
        if proc.returncode != 0:
            return None
        picked = proc.stdout.strip()
        return Path(picked) if picked else None

    return None


def register_native_path_dialog(
    input,
    output,
    render,
    reactive,
    session,
    *,
    button_id: str,
    target_input_id: str,
    mode: str,
    title: str,
    status_id: str | None = None,
    start_dir_getter=None,
) -> None:
    """Wire a Browse-style button to a native local file/folder chooser."""
    status = reactive.value("")

    def _start_dir() -> Path:
        if start_dir_getter is not None:
            try:
                value = start_dir_getter()
                if value:
                    return Path(value).expanduser()
            except Exception:
                pass
        try:
            current = getattr(input, target_input_id)()
            if current:
                path = Path(current).expanduser()
                return path.parent if path.is_file() else path
        except Exception:
            pass
        return Path.home() / "Documents"

    if status_id:
        @output(id=status_id)
        @render.ui
        def _native_status():
            msg = status.get()
            if not msg:
                return ui.tags.span("")
            cls = "text-success" if msg.startswith("Selected:") else "text-muted"
            return ui.tags.small(msg, class_=f"{cls} d-block mt-1")

    @reactive.effect
    @reactive.event(getattr(input, button_id))
    async def _open_dialog():
        picked = _choose_native_path(mode, title, _start_dir())
        if picked is None:
            status.set("No selection made, or native dialog is unavailable in this environment.")
            return
        ui.update_text(target_input_id, value=str(picked), session=session)
        status.set(f"Selected: {picked}")


def register_filesystem_picker(
    input,
    output,
    render,
    reactive,
    session,
    *,
    picker_id: str,
    target_input_id: str,
    mode: str = "both",
    initial_dir: Path | str | None = None,
    project_dir_getter=None,
    allow_create_dir: bool = False,
    file_suffixes: set[str] | None = None,
) -> None:
    """Attach server behavior for :func:`filesystem_picker_ui`.

    ``mode`` can be ``"file"``, ``"dir"``, or ``"both"``. The browser lists
    directories for navigation and files for selection when file selection is
    allowed. It updates an existing ``ui.input_text`` identified by
    ``target_input_id``.
    """
    mode = mode if mode in {"file", "dir", "both"} else "both"
    suffixes = {s.lower() for s in (file_suffixes or set())}
    start_dir = Path(initial_dir or (Path.home() / "Documents")).expanduser()
    _current_dir: reactive.Value[Path] = reactive.value(start_dir if start_dir.exists() else Path.home())
    _message: reactive.Value[str] = reactive.value("")

    def _target_value() -> str:
        try:
            getter = getattr(input, target_input_id)
            return (getter() or "").strip()
        except Exception:
            return ""

    def _nearest_existing_dir(path: Path) -> Path:
        cur = path.expanduser()
        if cur.is_file():
            return cur.parent
        while not cur.exists() and cur != cur.parent:
            cur = cur.parent
        return cur if cur.is_dir() else Path.home()

    def _set_dir(path: Path | str, message: str = "") -> None:
        target = Path(path).expanduser()
        if target.exists() and target.is_file():
            target = target.parent
        if target.exists() and target.is_dir():
            _current_dir.set(target.resolve())
            _message.set(message)
            return
        fallback = _nearest_existing_dir(target)
        _current_dir.set(fallback.resolve())
        _message.set(message or f"That path does not exist yet; browsing nearest existing folder: {fallback}")

    def _visible_children(path: Path, limit: int = 300) -> dict[str, str]:
        choices: dict[str, str] = {}
        try:
            dirs = sorted(
                [p for p in path.iterdir() if p.is_dir() and not p.name.startswith(".")],
                key=lambda p: p.name.lower(),
            )
            for child in dirs[:limit]:
                choices[str(child)] = f"[folder] {child.name}/"

            if mode in {"file", "both"}:
                remaining = max(limit - len(choices), 0)
                files = sorted(
                    [
                        p for p in path.iterdir()
                        if p.is_file()
                        and not p.name.startswith(".")
                        and (not suffixes or p.suffix.lower() in suffixes or Path(p.stem).suffix.lower() in suffixes)
                    ],
                    key=lambda p: p.name.lower(),
                )
                for child in files[:remaining]:
                    choices[str(child)] = f"[file] {child.name}"
        except Exception:
            return {"": "Cannot read this folder"}
        return choices or {"": "No selectable files or folders here"}

    def _selected_path() -> Path | None:
        try:
            raw = getattr(input, f"{picker_id}_child")()
        except Exception:
            raw = ""
        if not raw:
            return None
        return Path(raw)

    @output(id=f"{picker_id}_browser")
    @render.ui
    def _browser():
        current = _current_dir.get()
        choices = _visible_children(current)
        return ui.tags.div(
            ui.tags.div(
                ui.tags.strong("Current folder: "),
                ui.tags.code(str(current)),
                class_="small mb-2",
            ),
            ui.input_select(
                f"{picker_id}_child",
                "Files and folders",
                choices=choices,
                selected=next(iter(choices)),
            ),
        )

    @output(id=f"{picker_id}_status")
    @render.ui
    def _status():
        msg = _message.get()
        if not msg:
            return ui.tags.span("")
        cls = "text-success" if msg.startswith(("Using:", "Created:")) else "text-info"
        return ui.tags.small(msg, class_=f"{cls} d-block mt-2")

    @reactive.effect
    @reactive.event(getattr(input, f"{picker_id}_home"))
    async def _home():
        _set_dir(Path.home())

    @reactive.effect
    @reactive.event(getattr(input, f"{picker_id}_documents"))
    async def _documents():
        _set_dir(Path.home() / "Documents")

    @reactive.effect
    @reactive.event(getattr(input, f"{picker_id}_desktop"))
    async def _desktop():
        _set_dir(Path.home() / "Desktop")

    @reactive.effect
    @reactive.event(getattr(input, f"{picker_id}_project"))
    async def _project():
        project_dir = None
        if project_dir_getter is not None:
            try:
                project_dir = project_dir_getter()
            except Exception:
                project_dir = None
        if project_dir:
            _set_dir(Path(project_dir))
        else:
            _message.set("Load a project before jumping to the project folder.")

    @reactive.effect
    @reactive.event(getattr(input, f"{picker_id}_parent"))
    async def _parent():
        _set_dir(_current_dir.get().parent)

    @reactive.effect
    @reactive.event(getattr(input, f"{picker_id}_from_typed"))
    async def _from_typed():
        raw = _target_value()
        if not raw:
            _message.set("Enter a path first, or start from Home/Documents/Desktop.")
            return
        _set_dir(Path(raw).expanduser())

    @reactive.effect
    @reactive.event(getattr(input, f"{picker_id}_open"))
    async def _open_selected():
        selected = _selected_path()
        if selected is None:
            _message.set("No folder selected.")
            return
        if selected.is_dir():
            _set_dir(selected)
        else:
            _message.set("Selected item is a file. Use Selected to fill the path, or choose a folder to open.")

    @reactive.effect
    @reactive.event(getattr(input, f"{picker_id}_use_selected"))
    async def _use_selected():
        selected = _selected_path()
        if selected is None:
            _message.set("No file or folder selected.")
            return
        if mode == "file" and not selected.is_file():
            _message.set("Choose a file for this field.")
            return
        if mode == "dir" and not selected.is_dir():
            _message.set("Choose a folder for this field.")
            return
        ui.update_text(target_input_id, value=str(selected), session=session)
        _message.set(f"Using: {selected}")

    @reactive.effect
    @reactive.event(getattr(input, f"{picker_id}_use_current"))
    async def _use_current():
        if mode == "file":
            _message.set("Choose a file and click Use Selected for this field.")
            return
        current = _current_dir.get()
        ui.update_text(target_input_id, value=str(current), session=session)
        _message.set(f"Using: {current}")

    if allow_create_dir:
        @reactive.effect
        @reactive.event(getattr(input, f"{picker_id}_create"))
        async def _create():
            try:
                raw = (getattr(input, f"{picker_id}_new_folder_name")() or "").strip()
            except Exception:
                raw = ""
            if not raw:
                _message.set("Enter a subfolder name first.")
                return
            if any(part in raw for part in ("/", "\\")) or raw in {".", ".."}:
                _message.set("Use a simple folder name without slashes.")
                return
            try:
                new_dir = _current_dir.get() / raw
                new_dir.mkdir(parents=True, exist_ok=True)
                _set_dir(new_dir, f"Created: {new_dir}")
                ui.update_text(target_input_id, value=str(new_dir), session=session)
                ui.update_text(f"{picker_id}_new_folder_name", value="", session=session)
            except Exception as exc:
                _message.set(f"Could not create folder: {exc}")


# ---------------------------------------------------------------------------
# Elapsed timer UI + Cancel button
# ---------------------------------------------------------------------------

def make_elapsed_timer_renderer(reactive, runner):
    """Return a render.ui-compatible callable that shows a live elapsed-time display.

    Usage inside a step's register_outputs()::

        @output
        @render.ui
        def my_elapsed():
            return make_elapsed_timer_renderer(reactive, runner)()

    Or more simply call :func:`wire_elapsed_timer` which does everything.
    """
    import time as _time

    def _render():
        reactive.invalidate_later(1)          # tick every second
        is_running = runner.is_running.get()
        rc = runner.returncode.get()
        start = runner._start_time

        if start == 0.0:
            return ui.tags.span("")           # never started

        elapsed = _time.monotonic() - start
        mins, secs = divmod(int(elapsed), 60)
        time_str = f"{mins}m {secs:02d}s" if mins else f"{secs}s"

        if is_running:
            return ui.tags.span(
                f"⏱ Running for {time_str}…",
                class_="badge bg-secondary ms-2",
            )
        if rc == 0:
            return ui.tags.span(
                f"✅ Completed in {time_str}",
                class_="badge bg-success ms-2",
            )
        if rc is not None:
            return ui.tags.span(
                f"❌ Failed after {time_str}",
                class_="badge bg-danger ms-2",
            )
        return ui.tags.span("")

    return _render


def elapsed_timer_ui(output_id: str) -> ui.TagChild:
    """UI placeholder for :func:`register_elapsed_timer`."""
    return ui.output_ui(output_id)


def cancel_button_ui(button_id: str) -> ui.TagChild:
    """Small Cancel button; shown inline next to Run buttons."""
    return ui.input_action_button(
        button_id,
        "⬛ Cancel",
        class_="btn btn-sm btn-outline-danger ms-2",
    )


def register_cancel_button(reactive, input, *, button_id: str, runner) -> None:
    """Wire a cancel button to ``runner.cancel()``."""

    @reactive.effect
    @reactive.event(getattr(input, button_id))
    def _on_cancel():
        runner.cancel()

# ---------------------------------------------------------------------------
# Tool availability badge
# ---------------------------------------------------------------------------

def tool_badge(tool_name: str, description: str, available: bool) -> ui.TagChild:
    """Badge showing whether an optional tool is installed."""
    if available:
        return ui.tags.span(
            f"✅ {description}",
            class_="badge bg-success me-1",
            title=f"{tool_name} is available",
        )
    else:
        return ui.tags.span(
            f"⚠️ {description} (not installed)",
            class_="badge bg-warning text-dark me-1",
            title=f"Install {tool_name} to enable this feature",
        )


# ---------------------------------------------------------------------------
# Confidence tier badge
# ---------------------------------------------------------------------------

def tier_badge(tier: str) -> ui.TagChild:
    """Colored badge for a confidence tier."""
    config = {
        "high_confidence": ("bg-success", "High confidence"),
        "putative":        ("bg-primary", "Putative"),
        "divergent":       ("bg-warning text-dark", "Divergent"),
        "likely_fp":       ("bg-danger", "Likely FP"),
    }
    cls, label = config.get(tier, ("bg-secondary", tier))
    return ui.tags.span(label, class_=f"badge {cls}")


# ---------------------------------------------------------------------------
# QC flag badges
# ---------------------------------------------------------------------------

def qc_flag_badges(flags_str: str) -> ui.TagChild:
    """Render pipe-separated QC flags as colored badges."""
    if not flags_str or flags_str == "nan":
        return ui.tags.span("")
    flag_config = {
        "high_bias":       ("bg-danger",  "HIGH BIAS"),
        "short_alignment": ("bg-warning text-dark", "SHORT ALI"),
        "low_complexity":  ("bg-secondary", "LOW COMPLEX"),
        "contig_edge":     ("bg-info text-dark", "CONTIG EDGE"),
    }
    badges = []
    for flag in str(flags_str).split("|"):
        flag = flag.strip()
        if flag:
            cls, label = flag_config.get(flag, ("bg-secondary", flag))
            badges.append(ui.tags.span(label, class_=f"badge {cls} me-1"))
    return ui.tags.span(*badges)


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------

def progress_bar(value: float, label: str = "", color: str = "primary") -> ui.TagChild:
    """Bootstrap progress bar (0.0–1.0)."""
    pct = max(0.0, min(1.0, value)) * 100
    return ui.tags.div(
        ui.tags.div(
            ui.tags.div(
                ui.tags.span(label, class_="small text-white") if label else "",
                class_=f"progress-bar bg-{color}",
                style=f"width:{pct:.1f}%",
                role="progressbar",
                aria_valuenow=str(pct),
            ),
            class_="progress",
            style="height:24px;",
        ),
    )


# ---------------------------------------------------------------------------
# Section divider
# ---------------------------------------------------------------------------

def info_tooltip(text: str) -> ui.TagChild:
    """Small ℹ️ icon with a hover tooltip explaining a field or control."""
    return ui.tags.span(
        "ℹ️",
        class_="ms-1",
        style="cursor:help; font-size:0.78em; opacity:0.7;",
        title=text,
        role="img",
        aria_label=text,
        tabindex="0",
    )


def empty_state(message: str, icon: str = "📭", suggestion: str = "") -> ui.TagChild:
    """Placeholder shown when a section has no data to display."""
    parts = [
        ui.tags.div(
            ui.tags.span(icon, style="font-size:2rem;"),
            class_="mb-2",
        ),
        ui.tags.p(message, class_="text-muted mb-1"),
    ]
    if suggestion:
        parts.append(
            ui.tags.small(suggestion, class_="text-muted fst-italic"),
        )
    return ui.tags.div(
        *parts,
        class_="text-center py-4",
        role="status",
    )


def step_guidance(
    what: str,
    outputs: "list[str]",
    tip: str = "",
) -> ui.TagChild:
    """Collapsible 'About this step' panel shown at the top of each tab."""
    bullet_items = [ui.tags.li(o) for o in outputs]
    tip_el = (
        ui.tags.p(ui.tags.strong("💡 Tip: "), tip, class_="mb-0 mt-2 text-info small")
        if tip else ""
    )
    return ui.accordion(
        ui.accordion_panel(
            "ℹ️ About this step",
            ui.tags.p(what, class_="mb-1 small"),
            ui.tags.strong("You will get:", class_="small"),
            ui.tags.ul(*bullet_items, class_="small mb-1"),
            tip_el,
        ),
        id=None,
        open=False,
        class_="mb-3 border-0",
    )


def section_header(title: str, subtitle: str = "") -> ui.TagChild:
    return ui.tags.div(
        ui.tags.h5(title, class_="mb-0"),
        ui.tags.small(subtitle, class_="text-muted") if subtitle else "",
        ui.tags.hr(class_="mt-1 mb-2"),
        class_="mt-3",
    )


# ---------------------------------------------------------------------------
# Modal helpers
# ---------------------------------------------------------------------------

def simple_modal(modal_id: str, title: str, *body_content, footer_buttons=None) -> ui.TagChild:
    """A standard Bootstrap 5 modal."""
    footer = footer_buttons or [
        ui.tags.button("Close", type="button", class_="btn btn-secondary",
                       data_bs_dismiss="modal"),
    ]
    return ui.tags.div(
        ui.tags.div(
            ui.tags.div(
                # header
                ui.tags.div(
                    ui.tags.h5(title, class_="modal-title"),
                    ui.tags.button(type="button", class_="btn-close", data_bs_dismiss="modal"),
                    class_="modal-header",
                ),
                # body
                ui.tags.div(*body_content, class_="modal-body"),
                # footer
                ui.tags.div(*footer, class_="modal-footer"),
                class_="modal-content",
            ),
            class_="modal-dialog modal-lg",
        ),
        class_="modal fade",
        id=modal_id,
        tabindex="-1",
    )


# ---------------------------------------------------------------------------
# Database status card
# ---------------------------------------------------------------------------

def db_status_card(db: dict) -> ui.TagChild:
    """Card showing one database's status with download/enable controls."""
    status = db.get("status_badge", "not_configured")
    badge_map = {
        "local":              ("bg-success",  "✅ Local"),
        "streaming":          ("bg-info text-dark", "🔄 Streaming"),
        "download_available": ("bg-warning text-dark", "⬇️ Download available"),
        "not_configured":     ("bg-secondary", "⚠️ Not configured"),
    }
    badge_cls, badge_txt = badge_map.get(status, ("bg-secondary", status))

    return ui.card(
        ui.card_header(
            ui.tags.div(
                ui.tags.strong(db["name"]),
                ui.tags.span(
                    "protein" if db["type"] == "protein" else "nucleotide",
                    class_="badge bg-light text-dark ms-1",
                ),
                ui.tags.span(badge_txt, class_=f"badge {badge_cls} ms-2"),
                class_="d-flex align-items-center gap-1 flex-wrap",
            )
        ),
        ui.tags.div(
            ui.tags.div(
                ui.tags.strong("Why scan this: ", class_="text-info"),
                db.get("relevance", ""),
                class_="small mb-1",
            ) if db.get("relevance") else "",
            ui.tags.small(db.get("notes", ""), class_="text-muted d-block"),
            ui.tags.small(f"Size: {db.get('size_hint', 'unknown')}", class_="text-muted"),
            class_="card-body py-2 px-3",
        ),
        class_="mb-2",
    )
