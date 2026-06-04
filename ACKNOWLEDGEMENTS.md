# Acknowledgements And Citation Guidance

HMM Discovery is a workflow wrapper around public scientific software and
public biological databases. Please cite the app repository and also cite every
tool and database that contributed to a particular run.

The app records selected databases, source URLs, access times, file sizes, and
SHA256 checksums in `reports/reproducibility.json`,
`reports/RUN_SUMMARY.md`, and benchmark summary tables when those metadata are
available.

## Core Bioinformatics Tools

- HMMER: `hmmbuild`, `hmmsearch`, `hmmscan`, and `hmmpress` for profile-HMM
  construction, discovery search, domain/family annotation, and HMM indexing.
- MAFFT for multiple sequence alignment.
- trimAl for automated alignment trimming.
- Clustal Omega when used as an alternate aligner.
- Prodigal for conventional prokaryotic gene prediction and synteny-context
  rescue.
- seqkit for splitting large FASTA files during nucleotide database processing.
- IQ-TREE, ModelFinder, and ultrafast bootstrap when phylogenies are inferred.
- MEME Suite, including MEME and FIMO, when motif discovery/scanning is run.
- CD-HIT and MMseqs2 when sequence clustering is run.
- DIAMOND when reciprocal/background similarity checks are run.
- clinker, pyGenomeViz, and Easyfig-compatible GenBank exports when synteny
  visualizations are generated.
- toytree, toyplot, Ghostscript, matplotlib, Plotly, and Kaleido when figures
  are rendered or exported.
- Foldseek, Phobius, and TMHMM when optional structural/topology annotations
  are used.
- curl for resumable public database downloads and streaming.
- Git for repository/version tracking when release commits are used for
  reproducibility.

## Python And App Libraries

- Python and Shiny for Python for the interactive application.
- shinyswatch and Bootstrap for app styling.
- pandas, NumPy, SciPy, Biopython, matplotlib, Plotly, Jinja2, openpyxl,
  aiohttp, aiofiles, urllib3, faicons, toytree, toyplot, pyGenomeViz, and
  Kaleido for parsing, analysis, reporting, visualization, and export.

## Public Databases And Reference Collections

- INPHARED genomes.
- INPHARED vConTACT2 proteins.
- UniProt Swiss-Prot.
- NCBI RefSeq viral proteins.
- NCBI RefSeq viral genomes.
- NCBI RefSeq bacterial proteins.
- Gut Phage Database (GPD).
- GVD-AVrC / Aggregated Gut Viral Catalogue.
- Pfam-A sequences.
- Pfam-A HMM/domain library.
- VOGDB VFAM HMMs and annotations. The built-in entry currently targets VOGDB
  release 230 / RefSeq release 230 (`vfam.hmm.tar.gz` and
  `vfam.annotations.tsv.gz`).
- NCBI Entrez, GenBank, and RefSeq records when remote synteny context is
  fetched for placed nucleotide hits.

## Discovery Versus Annotation

Discovery evidence usually comes from HMMER searches against INPHARED, RefSeq,
Swiss-Prot, GPD, GVD-AVrC, Pfam sequences, or user-registered custom FASTA
targets. Annotation evidence usually comes from Pfam domain scan, VOGDB VFAM,
synteny context, motifs, clustering, and phylogeny.

For nucleotide discovery, the app's exhaustive six-frame ORF mode translates
all stop-to-stop ORFs above the selected length cutoff in three forward and
three reverse-complement reading frames. Prodigal is included as a faster
conventional gene-calling baseline, but Prodigal-only searches should not be
described as exhaustive evidence that unusual or annotation-missed ORFs are
absent.

## How To Cite A Run

In a manuscript or report, include:

- The HMM Discovery repository/version or commit.
- `reports/METHODS_TEXT.txt`.
- `reports/reproducibility.json`.
- `reports/RUN_SUMMARY.md` when generated.
- Each selected database name, release/snapshot if available, source URL,
  access date, and checksum.
- Each external tool used in the steps actually run.

If a tool or database was installed but not selected or used in a run, it does
not need to be cited for that run.
