#!/usr/bin/env python3
"""
12_motifs.py — De-novo motif discovery with MEME, scanning with FIMO.
=====================================================================

WHAT THIS STEP DOES (the biology)
---------------------------------
A motif is a short, recurring sequence pattern — often a functional site such as
a catalytic residue cluster, a binding pocket, or a structural signature. MEME
scans your hit sequences and discovers, with no prior knowledge, the conserved
ungapped patterns they share. Each motif comes with a consensus, a width, the
number of sites, and an E-value (lower = less likely to be a chance pattern).

FIMO then takes those discovered motifs and SCANS them back across the sequences
to report exactly where each motif occurs — useful for asking "does every member
carry the catalytic motif, or only some?"

WHAT THE KEY PARAMETERS MEAN
----------------------------
    --nmotifs    How many distinct motifs MEME should try to find.
    --minw/maxw  Allowed motif width range, in residues.
    --no-fimo    Skip the FIMO scan (discovery only).

OUTPUTS
-------
    results/meme_out/             full MEME output (HTML, text, logos)
    results/fimo_hits.tsv         FIMO motif occurrences (unless --no-fimo)

Requires the MEME Suite (https://meme-suite.org/).

INTERACTIVITY
-------------
Run it in a terminal with no/partial arguments and it becomes a guided wizard,
shows the exact MEME/FIMO commands, and confirms before running. Pipe it or pass
--yes for hands-off operation (safe for HPC / run_pipeline.py). See cli_common.py.

EXAMPLES
--------
    # Guided — the script will interview you:
    python3 scripts/12_motifs.py

    # Explicit / hands-off:
    python3 scripts/12_motifs.py --faa results/hits_proteins.faa --out-dir results/ --yes

    # More, wider motifs:
    python3 scripts/12_motifs.py --faa hits.faa --nmotifs 10 --minw 8 --maxw 40 --cpu 8
"""
import argparse
import sys
from pathlib import Path

# Make the app package importable no matter what directory we are run from,
# and make cli_common (which lives beside this script) importable too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.motifs import run_meme, run_fimo, parse_meme_txt
from pipeline.utils import ensure_tools_on_path
from cli_common import Guide, add_common_args


def parse_args():
    p = argparse.ArgumentParser(
        description="Discover protein sequence motifs with MEME and scan with FIMO.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Not required=True: a human in a terminal can supply this via the wizard.
    p.add_argument("--faa",     type=Path,
                   help="Input protein FASTA.")
    p.add_argument("--out-dir", default=Path("results"), type=Path,
                   help="Output directory.")
    p.add_argument("--nmotifs", default=5,    type=int,
                   help="Number of motifs to find (MEME -nmotifs).")
    p.add_argument("--minw",    default=6,    type=int,
                   help="Minimum motif width in residues (MEME -minw).")
    p.add_argument("--maxw",    default=50,   type=int,
                   help="Maximum motif width in residues (MEME -maxw).")
    p.add_argument("--cpu",     default=4,    type=int,
                   help="Number of parallel processes (MEME -p).")
    p.add_argument("--no-fimo", action="store_true",
                   help="Skip FIMO scanning step.")
    add_common_args(p)          # --yes / --interactive / --no-color / --explain-only
    return p.parse_args()


def main():
    args = parse_args()
    guide = Guide.from_args(args)
    ensure_tools_on_path()

    guide.header(12, "Motif Discovery",
                 "Find conserved sequence motifs (MEME) and map where they occur (FIMO).")

    # ── GUIDED WIZARD ────────────────────────────────────────────────────
    if guide.interactive and args.faa is None:
        guide.wizard_intro("Let's discover sequence motifs.")
        args.faa = guide.ask_path(
            "Path to your protein FASTA?",
            default="results/hits_proteins.faa",
            help_text="hits_proteins.faa (or cluster_reps.faa for a non-redundant set).",
        )
        args.nmotifs = int(guide.ask(
            "How many motifs should MEME look for?",
            default=str(args.nmotifs),
            help_text="MEME reports up to this many distinct conserved patterns.",
        ))
        args.no_fimo = not guide.ask_yesno(
            "Scan the discovered motifs back across the sequences with FIMO?",
            default_yes=True,
            help_text="Yes → also report exactly where each motif occurs.",
        )

    # ── Validate (works in both modes) ───────────────────────────────────
    if args.faa is None:
        guide.error("No --faa given. Provide one, or run in a terminal for the wizard.")
        sys.exit(2)

    faa = args.faa.resolve()
    out_dir = args.out_dir.resolve()
    meme_dir = out_dir / "meme_out"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not faa.exists():
        guide.error(f"FASTA not found: {faa}")
        sys.exit(1)

    guide.narrate(f"Input  : {faa.name}")
    guide.narrate(f"Motifs : {args.nmotifs}")
    guide.narrate(f"Width  : {args.minw}–{args.maxw}")
    guide.narrate(f"CPU    : {args.cpu}")

    # ── EXPLAIN-AND-CONFIRM: MEME ────────────────────────────────────────
    guide.command(f"meme {faa} -oc {meme_dir} -protein "
                  f"-nmotifs {args.nmotifs} -minw {args.minw} -maxw {args.maxw} "
                  f"-p {args.cpu} -mod zoops",
                  "Discover up to the requested number of conserved motifs de novo.")
    if guide.confirm("Run MEME now?") != "yes":
        guide.warn("Motif discovery skipped — nothing written.")
        sys.exit(0)

    guide.narrate("Running MEME …")
    meme_result = run_meme(
        faa_path=faa,
        out_dir=meme_dir,
        n_motifs=args.nmotifs,
        min_width=args.minw,
        max_width=args.maxw,
        cpu=args.cpu,
    )

    if not meme_result.get("success"):
        guide.error(f"MEME failed: {meme_result.get('error', 'unknown')}")
        sys.exit(1)

    n_found = meme_result.get("n_motifs_found", 0)
    guide.result(f"MEME output → {meme_dir}  ({n_found} motifs found)")

    # ── NARRATE: show the discovered motifs ──────────────────────────────
    if n_found > 0:
        guide.header(None, "Discovered motifs")
        for m in meme_result.get("motifs", []):
            mid       = m.get("id", "?")
            consensus = m.get("consensus", "")
            evalue    = m.get("evalue", "")
            width     = m.get("width", "")
            nsites    = m.get("nsites", "")
            guide.narrate(f"{mid:<10} width={width:<4} nsites={nsites:<5} "
                          f"evalue={evalue:<12} consensus={consensus}")
        guide.detail("Low-E-value motifs are the most likely to be functionally real.")
    else:
        guide.warn("No motifs found — sequences may be too divergent or too few.")

    # ── FIMO scanning ────────────────────────────────────────────────────
    if not args.no_fimo:
        meme_txt = meme_result.get("meme_txt")
        if meme_txt and Path(meme_txt).exists():
            fimo_dir = out_dir / "fimo_out"
            fimo_dir.mkdir(parents=True, exist_ok=True)
            guide.command(f"fimo --oc {fimo_dir} {meme_txt} {faa}",
                          "Locate every occurrence of the discovered motifs in the sequences.")
            if guide.confirm("Run FIMO now?") == "yes":
                guide.narrate("Running FIMO …")
                fimo_df = run_fimo(
                    meme_txt=Path(meme_txt),
                    faa_path=faa,
                    out_dir=fimo_dir,
                )
                fimo_out = out_dir / "fimo_hits.tsv"
                if fimo_df is not None and not fimo_df.empty:
                    fimo_df.to_csv(fimo_out, sep="\t", index=False)
                    guide.result(f"FIMO hits ({len(fimo_df)} rows) → {fimo_out}")
                else:
                    guide.warn("FIMO returned no occurrences.")
            else:
                guide.warn("FIMO skipped.")
        else:
            guide.warn("meme.txt not found; skipping FIMO.")

    guide.done(f"Motif analysis complete. MEME output in: {meme_dir}")
    guide.detail("Next: 13_annotate.py adds domain architecture and TM topology.")
    sys.exit(0)


if __name__ == "__main__":
    main()
