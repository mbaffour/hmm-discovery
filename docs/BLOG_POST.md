# From Protein Seeds to Phage Gene Discovery: A Deployable HMM Workflow

Finding distant homologs of a protein family is often a multi-tool workflow: clean seed sequences, build a multiple sequence alignment, train a profile HMM, search large public databases, classify hits, and then ask whether the surrounding genes make biological sense. HMM Discovery packages that workflow into a Shiny app designed for research groups that need repeatable analyses without hand-running every command.

## Who Is This For?

HMM Discovery is designed for three audiences: bench scientists who have a curated seed alignment and want to search public databases without writing shell scripts; bioinformatics trainees who are learning profile HMM workflows and benefit from step-by-step guidance; and core facility staff who need to deploy a reproducible analysis tool for multiple lab groups. If you have used BLAST to find homologs and wished you could catch more divergent members without losing specificity, profile HMMs are the next step, and this app removes the command-line barrier.

The app starts with a FASTA or GenBank input and walks users through alignment, HMM construction, database search, validation, refinement, analysis, and export. It supports phage-focused searches against INPHARED and RefSeq viral databases, along with broader protein databases such as SwissProt. For nucleotide databases, users can choose fast Prodigal gene prediction or exhaustive six-frame ORF scanning for short, overlapping, noncanonical, or annotation-missed genes. For annotation, VOGDB VFAM is the supported viral ortholog/family layer and Pfam provides broader domain context. The deployment build caches compressed public database files resumably, searches translated proteins with HMMER, and preserves enough coordinate information for downstream synteny analysis.

## A Concrete Use Case: Studying a Phage Depolymerase Family

Suppose you study phage-encoded depolymerases — enzymes that degrade bacterial capsular polysaccharides. You have five characterized depolymerase sequences from published phage genomes. With HMM Discovery, you load those five sequences, build an alignment and a profile HMM, then search INPHARED phage proteins to find additional candidates. The app classifies hits by confidence tier, shows which phage genomes carry them, recovers their genomic neighborhoods for synteny analysis, and annotates them against VOGDB and Pfam. You can then expand to RefSeq viral genomes using six-frame ORF scanning to catch unannotated depolymerases that conventional gene callers missed. The entire workflow — from five seed sequences to a publication-ready export ZIP — happens inside the browser.

One emphasis is research auditability. Each project writes tabular outputs, figures, logs, methods text, and a reproducibility JSON. Synteny outputs include TSV and GFF3 formats so users can move results into other visualization tools. The app also creates a ZIP export for sharing analysis artifacts with collaborators, and users can save that export to a chosen output folder from the interface.

The deployment bundle includes a conda environment, Dockerfile, setup scripts, a synthetic demo FASTA, and browser-based user documentation. No private research data is included. A new lab member can clone the repository, install the environment, launch the app, and run the demo before moving to their own protein family.

## Getting Started

1. Clone the repository and install the conda environment (`conda env create -f environment.yml`).
2. Launch the app with `./run_app.sh` and open `http://127.0.0.1:8081`.
3. Create a new project, load `example_data/demo_protein_family.fasta`, and click through the alignment, HMM build, and self-search validation steps.
4. When ready for real data, replace the demo FASTA with your curated seed sequences and select the databases relevant to your biology.

## What Makes This Different?

The traditional profile HMM workflow involves running `mafft`, `trimal`, `hmmbuild`, `hmmsearch`, parsing tblout files, writing classification scripts, and manually tracking database versions. HMM Discovery replaces that scattered shell pipeline with a single interface that handles alignment, model building, multi-database search, hit classification, synteny analysis, and reproducible export. It also provides scientific context at each step: explaining why six-frame ORF scanning catches genes that Prodigal misses, when VOGDB annotation adds value beyond Pfam, and how genomic neighborhood conservation supports or weakens a candidate hit.

## What's Included in the Deployment Bundle?

The repository ships with everything needed to run the app: a conda environment file, a Dockerfile, setup scripts, a synthetic demo FASTA for testing, browser-based documentation, presentation-ready workflow diagrams, and deployment checklists. No private research data, downloaded databases, or prior run outputs are included. Public databases are fetched on demand from their original sources, with resumable downloads and provenance tracking.

The most important design choice is that the app teaches users as they run. Step 4 explains why each database matters, when six-frame ORF discovery is more appropriate than Prodigal, and how VOGDB/Pfam annotation complements discovery without replacing manual biological review. Step 9 turns the run into a package: methods text, reproducibility JSON, run summary, database provenance, and export files that can be reviewed, rerun, or shared.

For effective use, start small. First run the synthetic demo to verify the environment. Then build the HMM from a curated seed set and confirm seed recovery. Search fast protein databases before launching large nucleotide scans. Use INPHARED and RefSeq viral genomes when unannotated ORFs may matter. Add GPD, GVD-AVrC, and RefSeq bacterial proteins when the biological question needs broader diversity or specificity checks. Use VOGDB, Pfam, synteny, motifs, clustering, and phylogeny as interpretation layers rather than as substitutes for careful hit review.

This project is intended for collaborative science: one interface, transparent outputs, and enough guardrails that multiple scientists can run comparable analyses across different machines. It does not remove the need for scientific judgment, but it makes the evidence easier to generate, inspect, cite, and defend.
