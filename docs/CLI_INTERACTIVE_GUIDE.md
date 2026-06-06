# Command-Line Pipeline — Interactive Guide

A friendly, hands-on walkthrough of the HMM Discovery **command-line** scripts.
By the end you'll know how to run the whole pipeline, how the scripts talk to
you, and how to switch them into silent batch mode for a cluster or a paper.

> This guide teaches the *experience*. For the complete flag-by-flag reference of
> every script, see [`scripts/README.md`](../scripts/README.md). To explore it
> all by clicking, open [`cli_interactive_guide.html`](cli_interactive_guide.html)
> in a browser.

---

## Quick start

You do not need to memorise anything. Run the tour:

```bash
python3 scripts/guide.py
```

It asks where you are, explains each step, shows the command, and offers to run
it. When you'd rather drive a single step yourself, just run it with **no
arguments** and it interviews you.

### What the wizard looks like

```text
$ python3 scripts/03_search.py

════════════════════════════════════════════════════════════════
  Step 3: HMM Search
  Score every sequence in a database against your profile HMM.
════════════════════════════════════════════════════════════════

  Let's set up your database search.
    This is the .hmm file produced by 02_build_hmm.py.
  Path to your profile HMM? [results/profile.hmm] > results/profile.hmm

  Database FASTA to search? > databases/inphared.faa
  Add another database? [y/N] > n

  Are these NUCLEOTIDE databases (raw DNA / genomes)? [y/N] > n

  How strict should the search be?
    → 1) standard — recommended for most families
      2) permissive — catches more distant homologs (more noise)
      3) strict — only strong, unambiguous matches
  Choose 1-3 [1] > 1
```

Every question explains itself, shows a sensible default in `[brackets]`, and
accepts <kbd>Enter</kbd> to take that default.

### The explain-and-confirm gate

Before it runs an external tool, the script shows you the **exact command** and
explains it, then waits for your go-ahead:

```text
  [CMD] hmmsearch --tblout inphared.tblout -E 1e-5 --cpu 4 profile.hmm inphared.faa
  ↳ Score every protein in inphared against the HMM; keep matches with E ≤ 1e-5.

  Search inphared now? [Y]es / [n]o-skip > y
```

This is also where the commands for your Methods section come from — they are
real and copy-pasteable.

### Narration that interprets results

The scripts don't just dump numbers — they tell you what the numbers *mean*:

```text
  ✓ 47 hits total · 12 strong (bit ≥ 45)
    ↳ 12 strong matches → probable true family members.

✓ Search complete. Results in: results/
    ↳ Next: 04_score_hits.py assigns confidence tiers to these hits.
```

If something looks off, the narration suggests the fix (e.g. *"No matches — try a
higher `--evalue`, or check the DB type (protein vs nucleotide)."*).

---

## The three interactive modes (and when they turn off)

| Mode | Trigger | Purpose |
|------|---------|---------|
| 🧭 **Guided wizard** | a needed argument is missing, in a terminal | fill in inputs by answering questions |
| ✅ **Explain-and-confirm** | before each external tool | see + approve the exact command |
| 💬 **Narration** | always | running commentary + result interpretation |

**The auto-detection rule.** A script is interactive only when **both** stdin and
stdout are real terminals **and** you didn't pass `--yes`. The moment you pipe it,
redirect it, run it from another script, or add `--yes`, every prompt silently
takes its default and nothing blocks.

```bash
python3 scripts/03_search.py              # you, at a keyboard → prompts
echo "" | python3 scripts/03_search.py    # piped              → silent, uses defaults
python3 scripts/03_search.py --yes        # forced hands-off   → silent
```

Useful switches:

- `--yes` / `-y` — force non-interactive (this is what HPC jobs and the master
  runner use).
- `--interactive` — force prompts even when stdout isn't a terminal (demos,
  screen recordings).
- `--explain-only` — a **dry run**: print the explanations and the commands that
  *would* run, then stop. Perfect for drafting a Methods section.
- `--no-color` — plain text, no ANSI colour (also honours the `NO_COLOR` env var).

---

## The steps, in order

A one-line "what and why" for each step. Full flags live in
[`scripts/README.md`](../scripts/README.md).

| Step | Script | What it does, and why |
|------|--------|-----------------------|
| 1 | `01_align.py` | **Align** your seeds so a model can see which positions are conserved. |
| 2 | `02_build_hmm.py` | **Build the HMM** — a position-by-position statistical fingerprint of the family. |
| 3 | `03_search.py` | **Search** a database; score every protein (or 6-frame ORF) against the HMM. |
| 4 | `04_score_hits.py` | **Tier** the hits by combined evidence into high-confidence / putative / divergent. |
| 5 | `05_classify_hits.py` | **Assemble** the canonical hits table and pull out the hit protein sequences. |
| 6 | `06_iterate.py` | *(optional)* **Grow** the family: add strong new hits to the seeds and rebuild. |
| 7 | `07_synteny.py` | **Genomic context** — fetch flanking genes and draw neighbourhood maps. |
| 8 | `08_taxonomy.py` | **Who carries it** — infer host / organism / taxonomy from sequence IDs. |
| 9 | `09_phylogeny.py` | **Tree** — maximum-likelihood phylogeny with IQ-TREE. |
| 10 | `10_matrix.py` | **Presence/absence** — which genome has which gene, as a heatmap. |
| 11 | `11_cluster.py` | **Cluster** sequences into subfamilies (CD-HIT / MMseqs2). |
| 12 | `12_motifs.py` | **Motifs** — discover conserved sequence motifs (MEME) and scan for them (FIMO). |
| 13 | `13_annotate.py` | **Function** — domain architecture and membrane topology. |
| 14 | `14_report.py` | **Report** — HTML summary, Methods text, reproducibility JSON, export ZIP. |

---

## Using the runnable tour

`guide.py` is the same experience, conducted for you:

```bash
python3 scripts/guide.py
```

```text
  Where are you in the workflow?
    → 1) Just starting — I have seed sequences
      2) I already have hits — I want downstream analysis
      3) Run everything end-to-end (the master pipeline)
      4) Just explain a single step to me
      5) Show me the batch / HPC / Methods workflow
  Choose 1-5 [1] >
```

- **1** walks the discovery path (align → build → search → score → classify → report).
- **2** walks the analysis path (synteny → taxonomy → tree → matrix → clusters → motifs → annotate → report).
- **3** hands off to `run_pipeline.py` for the full end-to-end run.
- **4** explains any single step.
- **5** shows the batch / HPC / Methods recipes.

For each step it prints the explanation and the real command, then asks *"Run it
now?"* — say no and it's a pure teaching tool; say yes and it does the work.

---

## Batch, HPC & Methods extraction

When there's no human watching — a cluster job, a cron task, a reproducible
re-run — make everything silent with `--yes` (or just pipe/redirect it).

```bash
# Whole pipeline, hands-off:
python3 scripts/run_pipeline.py \
  --seeds my_seeds.faa --db databases/inphared.faa \
  --proj-dir my_project/ --email you@uni.edu --cpu 8 --yes
```

**Getting your Methods section.** Every tool invocation is printed as a `[CMD]`
line. Capture them either with a dry run or from a real log:

```bash
# Dry run — explanations + commands, runs nothing:
python3 scripts/03_search.py --hmm profile.hmm --db db.faa --explain-only

# Or harvest from a real run:
python3 scripts/run_pipeline.py ... --yes 2>&1 | tee run.log
grep '\[CMD\]' run.log
```

`14_report.py` additionally writes a polished `methods.txt` and a
`reproducibility.json` (tool versions, exact parameters, database provenance) so
you can drop them straight into a manuscript or supplement.

**Resume or skip steps** without re-running the slow ones:

```bash
python3 scripts/run_pipeline.py ... --start-at 07 --skip 09 11 --yes
```

> **Rule of thumb:** explore and learn in a terminal (let it prompt and narrate);
> reproduce and publish with `--yes` (so the run is deterministic and logged).

---

## See also

- [`scripts/README.md`](../scripts/README.md) — complete flag & I/O reference.
- [`cli_interactive_guide.html`](cli_interactive_guide.html) — click-to-explore
  version with a live command builder.
- [`METHODOLOGY.md`](METHODOLOGY.md) — the science behind each step.
- Top-level [`README.md`](../README.md) — the Shiny web-app version of this
  workflow.
