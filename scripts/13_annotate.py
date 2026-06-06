#!/usr/bin/env python3
"""
13_annotate.py — Functional annotation: domains, TM topology, signal peptides.
==============================================================================

WHAT THIS STEP DOES (the biology)
---------------------------------
This step adds functional context to each hit by answering three questions:

    1. DOMAIN ARCHITECTURE — which known Pfam domains does the protein contain,
       and in what order? A "domain architecture string" (e.g. SignalP–TM–
       Peptidase) is a compact fingerprint of a protein's likely function.
       It is built from a Pfam hmmsearch --domtblout file you supply.

    2. TRANSMEMBRANE TOPOLOGY — Phobius and/or TMHMM predict membrane-spanning
       helices, telling you whether the protein is membrane-anchored, secreted,
       or cytoplasmic.

    3. SIGNAL PEPTIDES — Phobius also flags N-terminal signal peptides, which
       mark proteins destined for secretion or the membrane.

Together these turn a bare sequence into a testable functional hypothesis.

WHAT THE KEY PARAMETERS MEAN
----------------------------
    --domtblout  A Pfam hmmsearch --domtblout file → domain architecture.
    --hmm        Your profile HMM (used for length context).
    --phobius    Run Phobius (TM + signal peptide). Optional external tool.
    --tmhmm      Run TMHMM (TM topology). Optional external tool.

OUTPUTS
-------
    results/domain_architecture.tsv   per-protein domain order strings
    results/annotation_summary.tsv    domains merged with TM/signal annotations

INTERACTIVITY
-------------
Run it in a terminal with no/partial arguments and it becomes a guided wizard,
shows each external command, and confirms before running Phobius/TMHMM. Pipe it
or pass --yes for hands-off operation (safe for HPC / run_pipeline.py).

EXAMPLES
--------
    # Guided — the script will interview you:
    python3 scripts/13_annotate.py

    # Explicit / hands-off:
    python3 scripts/13_annotate.py \\
        --faa results/hits_proteins.faa --hmm profile.hmm \\
        --domtblout pfam_hits.domtblout --out-dir results/ --yes

    # With Phobius and TMHMM:
    python3 scripts/13_annotate.py --faa hits.faa --hmm profile.hmm \\
        --domtblout pfam.domtblout --phobius --tmhmm
"""
import argparse
import sys
from pathlib import Path

# Make the app package importable no matter what directory we are run from,
# and make cli_common (which lives beside this script) importable too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from pipeline.annotation import domain_architecture, run_phobius, run_tmhmm, annotate_from_tm
from pipeline.hmm_builder import parse_hmm_file
from pipeline.utils import ensure_tools_on_path
from cli_common import Guide, add_common_args


def parse_args():
    p = argparse.ArgumentParser(
        description="Annotate hit sequences: domain architecture, TM topology, signal peptides.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Not required=True: a human in a terminal can supply these via the wizard.
    p.add_argument("--faa",       type=Path,
                   help="Hit protein FASTA (output of 05_classify_hits.py).")
    p.add_argument("--hmm",       type=Path,
                   help="Profile HMM used to build the domain tblout.")
    p.add_argument("--domtblout", type=Path,
                   help="Pfam hmmsearch --domtblout file for domain architecture.")
    p.add_argument("--out-dir",   default=Path("results"), type=Path,
                   help="Output directory.")
    p.add_argument("--phobius",   action="store_true",
                   help="Run Phobius for TM topology + signal peptide prediction.")
    p.add_argument("--tmhmm",     action="store_true",
                   help="Run TMHMM for transmembrane topology prediction.")
    add_common_args(p)          # --yes / --interactive / --no-color / --explain-only
    return p.parse_args()


def main():
    args = parse_args()
    guide = Guide.from_args(args)
    ensure_tools_on_path()

    guide.header(13, "Functional Annotation",
                 "Add domain architecture, transmembrane topology, and signal peptides.")

    # ── GUIDED WIZARD ────────────────────────────────────────────────────
    if guide.interactive and (args.faa is None or args.hmm is None or args.domtblout is None):
        guide.wizard_intro("Let's annotate the hit proteins.")
        if args.faa is None:
            args.faa = guide.ask_path(
                "Path to your hit protein FASTA?",
                default="results/hits_proteins.faa",
                help_text="hits_proteins.faa from 05_classify_hits.py.",
            )
        if args.hmm is None:
            args.hmm = guide.ask_path(
                "Path to your profile HMM?",
                default="results/profile.hmm",
                help_text="Used only for length context.",
            )
        if args.domtblout is None:
            args.domtblout = guide.ask_path(
                "Path to the Pfam domtblout file?",
                help_text="hmmsearch --domtblout of your hits against Pfam-A.",
            )
        args.phobius = guide.ask_yesno(
            "Run Phobius (TM topology + signal peptides)?",
            default_yes=False,
            help_text="Requires Phobius to be installed.",
        )
        args.tmhmm = guide.ask_yesno(
            "Run TMHMM (TM topology)?",
            default_yes=False,
            help_text="Requires TMHMM to be installed.",
        )

    # ── Validate (works in both modes) ───────────────────────────────────
    missing = [n for n, v in [("--faa", args.faa), ("--hmm", args.hmm),
                              ("--domtblout", args.domtblout)] if v is None]
    if missing:
        guide.error(f"Missing required input(s): {', '.join(missing)}. "
                    "Provide them, or run in a terminal for the wizard.")
        sys.exit(2)

    faa = args.faa.resolve()
    hmm = args.hmm.resolve()
    domtblout = args.domtblout.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    for pth, name in [(faa, "--faa"), (hmm, "--hmm"), (domtblout, "--domtblout")]:
        if not pth.exists():
            guide.error(f"{name} file not found: {pth}")
            sys.exit(1)

    guide.narrate(f"FASTA     : {faa.name}")
    guide.narrate(f"HMM       : {hmm.name}")
    guide.narrate(f"domtblout : {domtblout.name}")
    guide.narrate(f"Phobius   : {args.phobius}")
    guide.narrate(f"TMHMM     : {args.tmhmm}")

    # Parse HMM length for context.
    hmm_meta = parse_hmm_file(hmm)
    hmm_length = hmm_meta.get("LENG", 0)

    # ── EXPLAIN-AND-CONFIRM: domain architecture ─────────────────────────
    guide.command(f"domain_architecture({domtblout.name}, hmm_length={hmm_length})",
                  "Build an ordered domain-architecture string for each protein from Pfam hits.")
    if guide.confirm("Build domain architecture table now?") != "yes":
        guide.warn("Annotation skipped — nothing written.")
        sys.exit(0)

    guide.narrate("Building domain architecture table …")
    dom_arch_df = domain_architecture(domtblout, hmm_length=hmm_length)
    dom_out = out_dir / "domain_architecture.tsv"
    dom_arch_df.to_csv(dom_out, sep="\t", index=False)
    guide.result(f"Domain architecture ({len(dom_arch_df)} proteins) → {dom_out}")

    if not dom_arch_df.empty:
        top_archs = dom_arch_df["domain_architecture"].value_counts().head(5)
        guide.header(None, "Top domain architectures")
        for arch, count in top_archs.items():
            guide.narrate(f"{str(arch):<50} {count:>5}")
        guide.detail("A dominant shared architecture supports a single coherent family.")

    # ── Phobius (optional external tool) ─────────────────────────────────
    phobius_df = pd.DataFrame()
    if args.phobius:
        guide.command(f"phobius.pl -short < {faa}",
                      "Predict transmembrane helices and signal peptides.")
        if guide.confirm("Run Phobius now?") == "yes":
            phobius_df = run_phobius(faa, out_dir)
            if phobius_df.empty:
                guide.warn("Phobius returned no results (not installed or no TM hits).")
            else:
                guide.result(f"Phobius: {len(phobius_df)} proteins annotated.")
        else:
            guide.warn("Phobius skipped.")

    # ── TMHMM (optional external tool) ───────────────────────────────────
    tmhmm_df = pd.DataFrame()
    if args.tmhmm:
        guide.command(f"tmhmm --short < {faa}",
                      "Predict transmembrane topology.")
        if guide.confirm("Run TMHMM now?") == "yes":
            tmhmm_df = run_tmhmm(faa, out_dir)
            if tmhmm_df.empty:
                guide.warn("TMHMM returned no results (not installed or no TM hits).")
            else:
                guide.result(f"TMHMM: {len(tmhmm_df)} proteins annotated.")
        else:
            guide.warn("TMHMM skipped.")

    # Combine TM annotations with domain architecture.
    combined_tm = pd.concat([phobius_df, tmhmm_df], ignore_index=True) \
        if (not phobius_df.empty or not tmhmm_df.empty) else pd.DataFrame()

    # Merge all annotation into the summary table.
    summary_df = dom_arch_df.copy()
    if not combined_tm.empty and "protein_id" in combined_tm.columns:
        tm_cols = [c for c in combined_tm.columns if c != "protein_id"]
        summary_df = summary_df.merge(
            combined_tm[["protein_id"] + tm_cols],
            on="protein_id",
            how="left",
        )

    summary_out = out_dir / "annotation_summary.tsv"
    summary_df.to_csv(summary_out, sep="\t", index=False)
    guide.result(f"Annotation summary ({len(summary_df)} rows) → {summary_out}")

    guide.done(f"Annotation complete. Outputs in: {out_dir}")
    guide.detail("Next: 14_report.py compiles everything into an HTML report + methods text.")
    sys.exit(0)


if __name__ == "__main__":
    main()
