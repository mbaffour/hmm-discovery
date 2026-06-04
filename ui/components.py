"""
ui/components.py — Shared UI building blocks used across all step panels.
"""
from __future__ import annotations

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
