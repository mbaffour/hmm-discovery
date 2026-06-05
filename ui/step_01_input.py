"""
ui/step_01_input.py — Input Sequences Panel (Step 1).

Accepts a FASTA / GenBank / gzip file or a folder path, optionally runs ORF
prediction on nucleotide inputs, then shows summary stats and a preview of
the first 10 sequences.
"""
from __future__ import annotations

from pathlib import Path

from shiny import ui

from .components import (
    filesystem_picker_ui,
    guidance_callout,
    step_guidance,
    log_panel,
    register_filesystem_picker,
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
        "1. Input Sequences",
        ui.tags.div(
            step_guidance(
                "Validate and characterise your seed protein sequences — the starting point for the entire discovery pipeline.",
                [
                "Sequence count and average length",
                "Sequence type detection (protein vs nucleotide)",
                "Duplicate count and preview of first 10 sequences",
                ],
                "Use protein sequences (.faa) if you already know them. For nucleotide genomes, enable ORF prediction.",
            ),
            section_header("Input Source", "Upload a file or browse to a local file/folder"),

            # ---- file upload -------------------------------------------------
            ui.layout_columns(
                ui.card(
                    ui.card_header("Upload File"),
                    ui.input_file(
                        "seq_file",
                        "Upload FASTA / GenBank / .gz",
                        accept=[".fasta", ".fa", ".faa", ".fna", ".gz", ".gb", ".gbk"],
                        multiple=False,
                    ),
                    ui.tags.small(
                        "Accepted: .fasta .fa .faa .fna .gb .gbk and .gz compressed variants.",
                        class_="text-muted",
                    ),
                ),
                ui.card(
                    ui.card_header("Browse Local File Or Folder"),
                    ui.input_text(
                        "folder_path",
                        "Local file or folder path",
                        placeholder="/path/to/sequences.fasta or /path/to/genomes/",
                    ),
                    filesystem_picker_ui(
                        "input_path_picker",
                        "Input File / Folder Picker",
                        "Navigate to a FASTA, GenBank, .gz file, or a folder for batch mode. Click Use Selected for a file, or Use Current Folder for batch mode.",
                    ),
                    ui.tags.small(
                        "Files are analyzed directly. Folders are batch mode: all FASTA / GenBank files inside are processed.",
                        class_="text-muted",
                    ),
                ),
                col_widths=[6, 6],
            ),

            # ---- options -----------------------------------------------------
            section_header("Options"),
            ui.layout_columns(
                ui.tags.div(
                    ui.input_radio_buttons(
                        "orf_method",
                        "ORF prediction (for nucleotide input)",
                        choices={
                            "prodigal": "Prodigal (recommended)",
                            "sixframe": "6-frame translation",
                        },
                        selected="prodigal",
                    ),
                ),
                ui.tags.div(
                    ui.tags.p(
                        ui.tags.small(
                            "Biology context is set in the sidebar (Generic / Phage / Bacterial).",
                            class_="text-muted",
                        )
                    ),
                ),
                col_widths=[6, 6],
            ),

            # ---- run button --------------------------------------------------
            ui.tags.div(
                ui.input_action_button(
                    "analyze_input",
                    "Analyze Input",
                    class_="btn btn-primary",
                ),
                class_="mt-2 mb-3",
            ),

            # ---- results -----------------------------------------------------
            ui.output_ui("input_stats"),
            ui.tags.div(
                ui.output_ui("input_preview"),
                class_="mt-3",
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
    input_handler = kwargs.get("input_handler", None)

    # Reactive values local to this step
    _summary = reactive.value(None)          # dict from input_handler.input_summary()
    _seq_type = reactive.value("")
    _seq_count = reactive.value(0)
    _input_path = reactive.value("")
    _preview_rows = reactive.value([])       # list[tuple[str, int]]

    register_filesystem_picker(
        input,
        output,
        render,
        reactive,
        session,
        picker_id="input_path_picker",
        target_input_id="folder_path",
        mode="both",
        initial_dir=Path.home() / "Documents",
        project_dir_getter=lambda: proj_dir_rv.get(),
        file_suffixes={".fasta", ".fa", ".faa", ".fna", ".gz", ".gb", ".gbk"},
    )

    # ---- analyze button event -----------------------------------------------
    @reactive.effect
    @reactive.event(input.analyze_input)
    async def _on_analyze():
        # Determine path: uploaded file takes priority over folder_path
        file_info = input.seq_file()
        path_str = ""
        if file_info:
            path_str = file_info[0]["datapath"]
        elif input.folder_path():
            path_str = input.folder_path().strip()

        if not path_str:
            return

        _input_path.set(path_str)

        if input_handler is not None:
            try:
                summary = input_handler.input_summary(path_str)
            except Exception as exc:
                summary = {
                    "seq_count": 0,
                    "avg_length": 0,
                    "seq_type": "unknown",
                    "duplicates": 0,
                    "preview": [],
                    "error": str(exc),
                }
        else:
            # Fallback: minimal summary without the pipeline module
            from pathlib import Path as _Path
            summary = {"seq_count": 0, "avg_length": 0, "seq_type": "unknown",
                       "duplicates": 0, "preview": []}
            try:
                p = _Path(path_str)
                if p.is_file():
                    import gzip as _gz
                    _open = _gz.open if p.suffix == ".gz" else open
                    ids: list[tuple[str, int]] = []
                    seq_id = ""
                    cur_len = 0
                    with _open(p, "rt", errors="replace") as fh:
                        for line in fh:
                            line = line.rstrip()
                            if line.startswith(">"):
                                if seq_id:
                                    ids.append((seq_id, cur_len))
                                seq_id = line[1:].split()[0]
                                cur_len = 0
                            else:
                                cur_len += len(line)
                        if seq_id:
                            ids.append((seq_id, cur_len))
                    summary["seq_count"] = len(ids)
                    summary["avg_length"] = int(sum(l for _, l in ids) / max(len(ids), 1))
                    summary["preview"] = ids
            except Exception:
                pass

        _summary.set(summary)
        _seq_type.set(summary.get("seq_type", "unknown"))
        _seq_count.set(summary.get("seq_count", 0))
        _preview_rows.set(summary.get("preview", [])[:10])

        # Persist to pipeline state — write to BOTH project dict (set_input)
        # AND the steps dict (mark_complete) so downstream steps can find
        # the input path via state.get_params("input").
        if state is not None:
            state.set_input(
                input_path=_input_path.get(),
                seq_type=_seq_type.get(),
                seq_count=_seq_count.get(),
                mode=input.biology_mode(),
            )
            # Also write to steps dict so state.get_params("input") works
            state.mark_complete("input", {
                "input_path": _input_path.get(),
                "seq_type":   _seq_type.get(),
                "seq_count":  _seq_count.get(),
            })

    # ---- input_stats ---------------------------------------------------------
    @output
    @render.ui
    def input_stats():
        summary = _summary.get()
        if summary is None:
            return ui.tags.p(
                "Click 'Analyze Input' to inspect your sequences.",
                class_="text-muted",
            )
        err = summary.get("error")
        if err:
            return ui.tags.div(
                ui.tags.span(f"⚠️ {err}", class_="text-danger"),
            )

        count = summary.get("seq_count", 0)
        avg_len = summary.get("avg_length", summary.get("avg_len", 0))
        seq_type = summary.get("seq_type", "unknown")
        dups = summary.get("duplicates", 0)

        cards = ui.tags.div(
            section_header("Input Summary"),
            ui.layout_columns(
                stat_card("sequences", count, color="primary", icon="🧬"),
                stat_card("avg length (aa/nt)", avg_len, color="info", icon="📏"),
                stat_card("type detected", seq_type, color="secondary", icon="🔬"),
                stat_card("duplicates", dups, color="warning" if dups else "success", icon="♻️"),
                col_widths=[3, 3, 3, 3],
            ),
        )
        if count > 0:
            next_step = guidance_callout(
                "Next Step",
                f"Input looks good: {count} {seq_type} sequences detected. "
                "Proceed to Step 2 (Multiple Sequence Alignment) to build an alignment.",
                "success",
            )
            return ui.tags.div(cards, next_step)
        return cards

    # ---- input_preview -------------------------------------------------------
    @output
    @render.ui
    def input_preview():
        rows = _preview_rows.get()
        if not rows:
            return ui.tags.span("")

        header = ui.tags.tr(
            ui.tags.th("#"),
            ui.tags.th("Sequence ID"),
            ui.tags.th("Length"),
        )
        body_rows = [
            ui.tags.tr(
                ui.tags.td(str(i + 1)),
                ui.tags.td(
                    ui.tags.code(seq_id, style="font-size:11px;"),
                ),
                ui.tags.td(str(length)),
            )
            for i, (seq_id, length) in enumerate(rows)
        ]
        return ui.tags.div(
            section_header("Sequence Preview", "First 10 sequences"),
            ui.tags.div(
                ui.tags.table(
                    ui.tags.thead(header),
                    ui.tags.tbody(*body_rows),
                    class_="table table-sm table-striped table-hover",
                ),
                style="max-height:300px; overflow-y:auto;",
            ),
        )
