#!/usr/bin/env python3
"""
cli_common.py — Shared interactive + teaching helpers for the HMM Discovery CLI.
================================================================================

Every step script (01_align.py … 14_report.py and run_pipeline.py) imports the
``Guide`` class from this module. ``Guide`` gives the scripts three behaviours,
all driven by ONE rule: *am I talking to a human in a terminal, or not?*

    1. GUIDED WIZARD      — when a required argument is missing and a human is
                            present, the script interviews the user for it
                            (``Guide.ask`` / ``ask_path`` / ``ask_choice``),
                            explaining every choice.
    2. EXPLAIN-AND-CONFIRM — before each external tool runs, the script prints
                            the exact command, explains what it does in plain
                            English, and asks "Proceed?" (``Guide.confirm``).
    3. NARRATE             — rich running commentary (``Guide.narrate`` /
                            ``Guide.result``) that interprets output as it
                            appears. This happens in BOTH modes; it never
                            blocks, so it is always safe.

Auto-detection (the important part)
-----------------------------------
``Guide`` is "interactive" only when **all** of these are true:

    * stdin is a real terminal   (``sys.stdin.isatty()``)
    * stdout is a real terminal  (``sys.stdout.isatty()``)
    * the user did NOT pass ``--yes`` / ``-y``

So the SAME script:

    $ python3 scripts/03_search.py            # human at a keyboard → prompts
    $ python3 scripts/03_search.py < /dev/null # piped              → silent
    $ python3 scripts/03_search.py --yes       # forced              → silent
    $ sbatch run_on_cluster.sh                 # HPC batch job       → silent

When non-interactive, every prompt resolves to its default and every
``confirm`` returns "yes" automatically — so cron jobs, pipes, and the master
``run_pipeline.py`` (which passes ``--yes`` to each step) never hang waiting
for input that will never come.

Colour
------
ANSI colour is emitted only on an interactive, colour-capable terminal and is
suppressed when the ``NO_COLOR`` environment variable is set (an emerging
cross-tool standard). On a dumb terminal or in a logfile you get clean plain
text with no escape-code noise.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional, Sequence


# ---------------------------------------------------------------------------
# ANSI colour codes — only ever used when colour is enabled (see Guide._paint)
# ---------------------------------------------------------------------------
# Kept as plain strings so there is zero dependency on any colour library.
_ANSI = {
    "reset":   "\033[0m",
    "bold":    "\033[1m",
    "dim":     "\033[2m",
    "cyan":    "\033[36m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "red":     "\033[31m",
    "blue":    "\033[34m",
    "magenta": "\033[35m",
    "grey":    "\033[90m",
}


def add_common_args(parser) -> None:
    """Attach the flags every step script shares.

    Call this from each script's ``argparse`` setup so the behaviour is
    identical everywhere:

        --yes / -y        Force non-interactive: accept all defaults, never
                          prompt. This is what run_pipeline.py and HPC jobs use.
        --interactive     Force interactive even when stdout is not a TTY
                          (rare; mostly for demos / recording sessions).
        --no-color        Disable ANSI colour explicitly.
        --explain-only    Print the explanations and the commands that WOULD
                          run, then stop — a dry run for writing Methods text.
    """
    g = parser.add_argument_group("interaction")
    g.add_argument("--yes", "-y", action="store_true",
                   help="Non-interactive: accept defaults, never prompt (for "
                        "scripts, pipes, HPC). run_pipeline.py sets this for you.")
    g.add_argument("--interactive", action="store_true",
                   help="Force interactive prompts even if stdout is not a terminal.")
    g.add_argument("--no-color", action="store_true",
                   help="Disable coloured output.")
    g.add_argument("--explain-only", action="store_true",
                   help="Dry run: show explanations and the commands that would "
                        "run, then exit without running them.")


class Guide:
    """A single object that handles all human-facing interaction for a script.

    Typical use at the top of a step script::

        args  = parse_args()
        guide = Guide.from_args(args)
        guide.header(3, "HMM Search",
                     "Score every protein in a database against your profile HMM.")
        ...
        if guide.confirm("Run hmmsearch now?"):
            run_hmmsearch_protein(...)

    The script author never has to check "are we interactive?" by hand — every
    method on ``Guide`` already does the right thing in both modes.
    """

    def __init__(self, *, assume_yes: bool = False,
                 force_interactive: bool = False,
                 no_color: bool = False,
                 explain_only: bool = False) -> None:
        # ── Decide interactivity once, up front ───────────────────────────
        stdin_tty  = sys.stdin.isatty()  if hasattr(sys.stdin,  "isatty") else False
        stdout_tty = sys.stdout.isatty() if hasattr(sys.stdout, "isatty") else False
        if assume_yes:
            # --yes always wins: the user (or run_pipeline.py) explicitly asked
            # for hands-off operation.
            self.interactive = False
        elif force_interactive:
            self.interactive = True
        else:
            self.interactive = stdin_tty and stdout_tty

        self.explain_only = explain_only
        # Colour only when it will actually be seen and is not opted out of.
        self._color = (
            self.interactive
            and stdout_tty
            and not no_color
            and os.environ.get("NO_COLOR") is None
        )

    @classmethod
    def from_args(cls, args) -> "Guide":
        """Build a Guide from a parsed argparse namespace that used
        ``add_common_args``. Falls back gracefully if any flag is absent."""
        return cls(
            assume_yes=getattr(args, "yes", False),
            force_interactive=getattr(args, "interactive", False),
            no_color=getattr(args, "no_color", False),
            explain_only=getattr(args, "explain_only", False),
        )

    # ─────────────────────────────────────────────────────────────────────
    # Low-level painting
    # ─────────────────────────────────────────────────────────────────────
    def _paint(self, text: str, *styles: str) -> str:
        """Wrap *text* in ANSI codes for *styles* — but only if colour is on."""
        if not self._color or not styles:
            return text
        prefix = "".join(_ANSI.get(s, "") for s in styles)
        return f"{prefix}{text}{_ANSI['reset']}"

    # ─────────────────────────────────────────────────────────────────────
    # Output: headers, explanations, narration, results
    # These NEVER block. They print in both interactive and silent modes,
    # so a logfile from a batch run still reads like a narrated session.
    # ─────────────────────────────────────────────────────────────────────
    def header(self, num, title: str, blurb: str = "") -> None:
        """Print a step banner: '=== Step 3: HMM Search ==='."""
        bar = "═" * 64
        print()
        print(self._paint(bar, "cyan", "dim"))
        label = f"  Step {num}: {title}" if num is not None else f"  {title}"
        print(self._paint(label, "bold", "cyan"))
        if blurb:
            print(self._paint(f"  {blurb}", "dim"))
        print(self._paint(bar, "cyan", "dim"))

    def explain(self, text: str) -> None:
        """A plain-English 'what this does / why it matters' block.

        Indented and dimmed so it is visually distinct from commands and
        results. Multi-line strings are indented line-by-line.
        """
        for line in text.strip("\n").splitlines():
            print(self._paint(f"    {line}", "dim"))

    def command(self, cmd, why: str = "") -> None:
        """Show the exact command that is about to run, plus an optional
        one-line explanation of the key parameters.

        Accepts either a string or a list (which is joined for display). The
        '[CMD]' prefix is kept so the old grep-for-commands habit still works
        and Methods-section extraction is trivial.
        """
        cmd_str = cmd if isinstance(cmd, str) else " ".join(str(c) for c in cmd)
        print()
        print("  " + self._paint("[CMD] ", "bold", "yellow") + self._paint(cmd_str, "yellow"))
        if why:
            print("  " + self._paint(f"↳ {why}", "grey"))

    def narrate(self, text: str) -> None:
        """Running commentary while something is happening (▶ prefix)."""
        print("  " + self._paint("▶ ", "blue") + text)

    def detail(self, text: str) -> None:
        """A secondary commentary line, indented under a narrate() line (↳)."""
        print("    " + self._paint(f"↳ {text}", "grey"))

    def result(self, text: str, good: bool = True) -> None:
        """Interpret an outcome: green ✓ for success, yellow ⚠ otherwise."""
        mark = self._paint("✓", "green") if good else self._paint("⚠", "yellow")
        print("  " + mark + " " + text)

    def warn(self, text: str) -> None:
        print("  " + self._paint("⚠ " + text, "yellow"))

    def error(self, text: str) -> None:
        print("  " + self._paint("✗ " + text, "red"), file=sys.stderr)

    def done(self, text: str) -> None:
        print()
        print(self._paint("✓ " + text, "bold", "green"))

    # ─────────────────────────────────────────────────────────────────────
    # Input: confirm, ask, ask_path, ask_choice
    # In NON-interactive mode every one of these returns its default WITHOUT
    # reading stdin, so nothing can ever hang.
    # ─────────────────────────────────────────────────────────────────────
    def confirm(self, action: str = "Proceed?", *,
                default_yes: bool = True,
                allow_skip: bool = True) -> str:
        """Explain-and-confirm gate. Returns one of: 'yes', 'no'.

        In interactive mode the user sees::

            Proceed? [Y]es / [n]o-skip >

        'no' means "skip this step" (the caller decides what skipping does).
        In non-interactive mode this immediately returns 'yes' (or whatever
        *default_yes* implies) and prints nothing blocking.
        """
        if self.explain_only:
            # Dry run — we never actually do the action, but report intent.
            print("  " + self._paint("(--explain-only: would proceed)", "grey"))
            return "no"
        if not self.interactive:
            return "yes" if default_yes else "no"

        yn = "[Y]es / [n]o-skip" if default_yes else "[y]es / [N]o-skip"
        prompt = "  " + self._paint(f"{action} ", "bold") + self._paint(f"{yn} > ", "dim")
        while True:
            try:
                ans = input(prompt).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return "no"
            if ans == "":
                return "yes" if default_yes else "no"
            if ans in ("y", "yes"):
                return "yes"
            if ans in ("n", "no", "s", "skip"):
                return "no"
            print("    " + self._paint("Please answer y or n.", "grey"))

    def ask(self, question: str, *, default: Optional[str] = None,
            help_text: str = "", required: bool = False) -> str:
        """Free-text wizard question.

        Non-interactive: returns *default* (or "" if none). Interactive: shows
        the question, optional *help_text*, and the default in brackets.
        """
        if not self.interactive:
            return default if default is not None else ""
        if help_text:
            print("    " + self._paint(help_text, "grey"))
        suffix = f" [{default}]" if default else ""
        prompt = "  " + self._paint(f"{question}{suffix} > ", "bold")
        while True:
            try:
                ans = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                if default is not None:
                    return default
                if not required:
                    return ""
                sys.exit("Aborted.")
            if ans:
                return ans
            if default is not None:
                return default
            if not required:
                return ""
            print("    " + self._paint("This one is required.", "grey"))

    def ask_path(self, question: str, *, default: Optional[str] = None,
                 must_exist: bool = True, help_text: str = "") -> Path:
        """Like ``ask`` but validates a filesystem path and re-asks on miss.

        In non-interactive mode it returns the default without checking — the
        caller's own existence check will produce a clean error if it is wrong.
        """
        if not self.interactive:
            return Path(default).expanduser() if default else Path()
        while True:
            raw = self.ask(question, default=default, help_text=help_text,
                           required=True)
            p = Path(raw).expanduser()
            if not must_exist or p.exists():
                return p
            print("    " + self._paint(f"Not found: {p} — try again.", "yellow"))

    def ask_choice(self, question: str, choices: Sequence[tuple],
                   *, default_index: int = 0, help_text: str = ""):
        """Numbered menu. *choices* is a list of (value, label) tuples.

        Returns the chosen *value*. Non-interactive returns the default value.

            ask_choice("How strict?", [
                ("1e-5",  "standard (recommended)"),
                ("1e-3",  "permissive — more distant hits"),
                ("1e-10", "strict — only strong matches"),
            ])
        """
        if not self.interactive:
            return choices[default_index][0]
        if help_text:
            print("    " + self._paint(help_text, "grey"))
        print("  " + self._paint(question, "bold"))
        for i, (_val, label) in enumerate(choices, start=1):
            marker = "→" if (i - 1) == default_index else " "
            print("    " + self._paint(f"{marker} {i}) ", "cyan") + label)
        while True:
            try:
                ans = input("  " + self._paint(
                    f"Choose 1-{len(choices)} [{default_index + 1}] > ", "dim")).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return choices[default_index][0]
            if ans == "":
                return choices[default_index][0]
            if ans.isdigit() and 1 <= int(ans) <= len(choices):
                return choices[int(ans) - 1][0]
            print("    " + self._paint("Enter one of the listed numbers.", "grey"))

    def ask_yesno(self, question: str, *, default_yes: bool = True,
                  help_text: str = "") -> bool:
        """A yes/no wizard question that returns a real bool.

        Distinct from ``confirm`` (which is the per-command gate). Use this for
        wizard branches like 'Do you want to run clinker as well?'.
        """
        if not self.interactive:
            return default_yes
        if help_text:
            print("    " + self._paint(help_text, "grey"))
        yn = "[Y/n]" if default_yes else "[y/N]"
        try:
            ans = input("  " + self._paint(f"{question} {yn} > ", "bold")).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return default_yes
        if ans == "":
            return default_yes
        return ans in ("y", "yes")

    # ─────────────────────────────────────────────────────────────────────
    # Convenience
    # ─────────────────────────────────────────────────────────────────────
    def wizard_intro(self, text: str) -> bool:
        """Print a friendly wizard preamble. Returns True if we are actually
        in wizard (interactive) mode, so callers can do:

            if guide.wizard_intro("Let's set up the search."):
                args.hmm = guide.ask_path("Path to your profile HMM?")
        """
        if not self.interactive:
            return False
        print()
        print(self._paint("  " + text, "bold", "magenta"))
        return True
