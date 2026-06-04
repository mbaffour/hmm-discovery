# Methodology

This document describes the scientific workflow implemented by HMM Discovery.
It is written as a manuscript-facing companion to `reports/METHODS_TEXT.txt`,
which is generated for each run from the actual project settings and
reproducibility metadata.

Routine use is no-code: users can complete project setup, input loading,
alignment, HMM construction, database selection, single-genome scans, six-frame
ORF discovery, summary generation, cache cleanup, and export from the app UI.
Command-line entry points are retained for administrators, shared servers, and
advanced automation.

Presentation-ready workflow diagrams are bundled in `www/presentation/` for
talks, lab meetings, posters, and onboarding.

## Scope

HMM Discovery is designed to find distant homologs of a protein family from a
curated seed FASTA, then help users interpret those hits with confidence
classification, database provenance, synteny, motifs, clustering, phylogeny,
and annotation databases.

The app is intended for discovery and triage. Final biological claims should be
supported by the exported hit tables, HMM coverage, bit scores, genomic
context, database provenance, and any follow-up validation appropriate for the
study.

## Input Handling

Users provide protein FASTA, nucleotide FASTA, GenBank, or folders of sequence
files. Protein seed FASTA is the preferred input for building a protein-family
profile HMM. Nucleotide input can be translated through the app, but users
should inspect resulting proteins and remove obvious contaminants or unrelated
sequences before building a final family HMM.

Seed/input FASTA files are not registered as searchable databases. They are
used for alignment, HMM construction, and self-search recovery. Searchable
databases are public registry entries or custom targets explicitly registered
by the user.

## Alignment And HMM Construction

Seed proteins are aligned with MAFFT by default. trimAl is used to remove poorly
conserved alignment columns where appropriate. The trimmed alignment is used to
build an HMMER3 profile HMM with `hmmbuild`.

The app performs self-search validation by searching the seed proteins with the
new HMM. Strong seed recovery is expected before large database searches. Poor
self-recovery usually means the seed set is too divergent, contains unrelated
proteins, has problematic fragments, or needs manual curation.

## Discovery Searches

Protein databases are searched with HMMER `hmmsearch`. Nucleotide databases are
translated before HMMER search. The main discovery databases are:

- INPHARED genomes.
- INPHARED proteins.
- UniProt Swiss-Prot.
- NCBI RefSeq viral proteins.
- NCBI RefSeq viral genomes.
- Gut Phage Database (GPD).
- GVD-AVrC / Aggregated Gut Viral Catalogue.
- NCBI RefSeq bacterial proteins for host/background specificity checks.
- Pfam sequences when broad family context is needed.
- User-registered custom protein or nucleotide FASTA targets.

Large remote databases are downloaded or streamed only when selected. Benchmark
runs use resumable downloads, file-level provenance, disk guards, and sequential
cache cleanup so final results can be retained without keeping all raw database
caches.

## Nucleotide ORF Modes

For nucleotide databases and single-genome scans, the app offers two ORF modes.

**Exhaustive six-frame ORFs** is the discovery mode. Each nucleotide sequence is
scanned in three forward reading frames and three reverse-complement reading
frames. Each frame is split at stop codons. Every stop-to-stop peptide above
the selected minimum amino-acid length is retained and searched with HMMER.
Hit headers retain contig, strand, frame, coordinates, and amino-acid length
when available. This mode is sensitive to short, overlapping, noncanonical, or
annotation-missed genes.

**Prodigal predicted genes** is a faster conventional annotation baseline. It
is useful for ordinary prokaryotic gene prediction and for some synteny rescue
steps, but it should not be described as exhaustive evidence that unusual ORFs
are absent.

## Hit Classification

Hits are compiled into `results/hits_main.tsv` and related summary tables.
The app classifies hits using evidence such as:

- HMMER E-value.
- bit score.
- HMM profile coverage.
- seed/self-search recovery behavior.
- database source.
- nucleotide placement and genomic context when available.

Default confidence labels are intended as triage aids. Users should review
borderline hits, low-coverage hits, fragmented hits, and hits from very large
background databases before making biological claims.

## Annotation Layers

Annotation layers help interpret discovered proteins but are not the primary
discovery evidence.

**Pfam domain scan** uses HMMER `hmmscan` against Pfam-A HMMs to identify broad
conserved domains in hit proteins.

**VOGDB VFAM annotation** is the preferred viral ortholog/family annotation
layer. The built-in entry targets VOGDB release 230 / RefSeq release 230.
The app downloads `vfam.hmm.tar.gz`, extracts or concatenates HMM files as
needed, runs `hmmpress`, downloads `vfam.annotations.tsv.gz`, and scans current
hit proteins with `hmmscan`. Output is written to
`results/vogdb_vfam_annotation.tsv` with query protein ID, VFAM ID, E-value,
bit score, query coverage when available, and annotation/function/category
fields.

## Synteny Analysis

Synteny analysis attempts to place nucleotide hits and recover five upstream
and five downstream genes around each hit. Context can come from local GenBank
records, recovered nucleotide coordinates, streamed sequence context, or NCBI
Entrez/GenBank records when available.

Outputs include:

- `results/synteny_table.tsv`.
- `results/synteny_placement_report.tsv`.
- `results/synteny_neighborhoods.gff3`.
- synteny map figures in `figures/`.
- optional GenBank-style neighborhood exports.

These files are intended to support spreadsheet review, custom plotting,
clinker, pyGenomeViz, Easyfig-compatible workflows, or other synteny tools.

## Motifs, Clustering, And Phylogeny

When selected and installed, the app can run:

- MEME and FIMO for motif discovery and motif scanning.
- CD-HIT and/or MMseqs2 for sequence clustering.
- IQ-TREE with model selection and bootstrap support for phylogenetic analysis.

These analyses are downstream interpretation layers. They should be interpreted
in the context of seed selection, hit confidence, alignment quality, and
database provenance.

## Reproducibility Outputs

A complete run should export:

- `reports/METHODS_TEXT.txt`.
- `reports/reproducibility.json`.
- `reports/RUN_SUMMARY.md`.
- `reports/run_summary.json`.
- `results/hits_main.tsv`.
- `results/hits_best_per_genome.tsv`.
- `results/per_database_metrics.tsv` for benchmark runs.
- `results/all_database_summary.tsv` for benchmark runs.
- synteny, motif, clustering, phylogeny, and figure outputs when generated.
- a final export ZIP.

`reproducibility.json` records tool versions, selected databases, database
source URLs, access dates, source sizes, checksums when available, and citation
guidance. Benchmark manifests additionally record resumable per-database status
and file-level provenance.

## Deployment Validation

Deployment readiness is based on:

- successful environment checks.
- successful demo run.
- successful HMM construction and seed self-search recovery.
- dry-run expansion of registered databases.
- smoke or partial benchmark runs before large all-database runs.
- required discovery databases passing.
- optional annotation failures being recorded clearly rather than hidden.
- no private data, downloaded database caches, logs, or research outputs inside
  the clean Git repository.

VOGDB VFAM, Pfam, RefSeq, INPHARED, Swiss-Prot,
GPD, GVD-AVrC, and six-frame nucleotide searches provide the core deployment
story for viral protein-family discovery.

## Limitations

- HMM-based discovery depends on seed quality and alignment quality.
- Very divergent homologs may be missed if the seed set is narrow.
- Low-complexity or fragmented proteins can create borderline hits.
- Six-frame ORF mode is sensitive but can increase runtime and false-positive
  review burden.
- Public database snapshots change over time, so source URLs, access dates, and
  checksums should be treated as part of the scientific record.
- Synteny placement depends on available nucleotide coordinates and sequence
  context.
- Annotation databases are interpretive layers, not proof of function by
  themselves.

## Recommended Manuscript Package

For a paper, supplement, or reviewer response, include:

- the HMM profile or seed alignment if shareable.
- `METHODS_TEXT.txt`.
- `reproducibility.json`.
- `RUN_SUMMARY.md`.
- `hits_main.tsv`.
- `hits_best_per_genome.tsv`.
- database summary/provenance tables.
- synteny tables and figures.
- the exact repository commit or release.
- citations for HMM Discovery and every tool/database actually used.
