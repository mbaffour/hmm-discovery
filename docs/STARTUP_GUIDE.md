# HMM Discovery Startup Guide

This guide walks a new user from the GitHub page to a working HMM Discovery app. The app itself is no-code after launch: users click through project setup, input loading, HMM building, database search, review, cleanup, and export from the browser.

## What You Need

- A macOS, Linux, or workstation/server environment with internet access.
- Conda, Mamba, or Docker.
- Enough disk space for the run you choose. Small demo runs need little space; large RefSeq, GPD, GVD-AVrC, Pfam, or VOGDB runs can need many gigabytes.
- For real analyses, a curated protein FASTA or a nucleotide/GenBank file you want to scan.

## Option 1: Start With Conda Or Mamba

```bash
git clone https://github.com/mbaffour/hmm-discovery.git
cd hmm-discovery
conda env create -f environment.yml
conda activate hmm-discovery
./run_app.sh
```

Open:

```text
http://127.0.0.1:8081
```

If the environment already exists and you are updating:

```bash
git pull
conda env update -f environment.yml --prune
conda activate hmm-discovery
./run_app.sh
```

## Option 2: Start With Docker

```bash
git clone https://github.com/mbaffour/hmm-discovery.git
cd hmm-discovery
docker build -t hmm-discovery .
docker run --rm -p 8081:8081 hmm-discovery
```

Open:

```text
http://127.0.0.1:8081
```

For persistent projects:

```bash
mkdir -p projects
docker run --rm -p 8081:8081 \
  -v "$PWD/projects:/app/projects" \
  hmm-discovery
```

## First Demo Run

Use the bundled synthetic FASTA first. It confirms that the interface, environment, HMM build, and export path work before you use real data.

1. Open the app at `http://127.0.0.1:8081`.
2. In the sidebar, choose or create a project folder outside the Git repository.
3. Go to **Step 1: Input Sequences**.
4. Load `example_data/demo_protein_family.fasta`.
5. Run **Step 2: Multiple Sequence Alignment**.
6. Run **Step 3: Build Profile HMM**.
7. Run self-search/validation before large database searches.
8. Run **Step 9: Export** to confirm that summaries, methods text, reproducibility metadata, and ZIP export work.

## Starting A Real Protein-Family Run

1. Create a fresh project folder for the family.
2. Load your curated protein FASTA.
3. Build and inspect the alignment.
4. Build the HMM and confirm seed recovery.
5. Start with fast protein databases such as INPHARED proteins, RefSeq viral proteins, and SwissProt.
6. Add nucleotide databases only after the HMM behaves well.
7. Use VOGDB and Pfam as annotation layers.
8. Use GPD and GVD-AVrC when gut viral breadth matters.
9. Export the run package and keep it with your analysis notes.

## Starting A Single-Genome Scan

Use this mode when you want to ask whether one genome contains a candidate member of the family.

1. Open **Database Setup**.
2. Register one nucleotide FASTA or GenBank file as a custom/single-genome target.
3. In **Step 4: Database Search**, select only that target database.
4. Choose **exhaustive six-frame ORFs** when unusual, short, overlapping, or missed genes are important.
5. Run the search.
6. Inspect hit coordinates, strand, translated ORF length, HMM coverage, and synteny placement.

## Choosing Database Scale

- **Demo:** synthetic FASTA only; use this to check installation.
- **Fast biological signal:** INPHARED proteins, RefSeq viral proteins, and SwissProt.
- **Single genome:** one registered nucleotide FASTA or GenBank file.
- **Viral genome discovery:** INPHARED genomes and RefSeq viral genomes.
- **Gut viral breadth:** GPD and GVD-AVrC.
- **Specificity/background:** RefSeq bacterial proteins.
- **Annotation:** VOGDB VFAM and Pfam domain scan.

The app does not download every database automatically. Users choose databases for each run. Large files are cached or streamed according to the database type, and cache cleanup tools are available in the app.

## Keep The Computer Awake

For long runs on macOS, keep the machine awake:

```bash
caffeinate -dimsu
```

Stop it with `Control-C` when the run is finished. On laptops, keep the charger connected and avoid closing the lid unless an external display/power setup is configured.

## Where Outputs Go

There are two output locations to understand:

1. **Project folder:** this is the working folder you choose/create in the app sidebar. The app writes inputs, alignments, HMMs, intermediate files, results, reports, logs, and state here.
2. **Final export folder:** this is the folder you choose in **Step 9: Export** using **Choose final export folder (ZIP destination)**. You can type a path, browse from Home/Documents/Desktop/project folders, open subfolders, create a new subfolder, and click **Use This Folder**. The app copies the final export ZIP there for sharing, archiving, or uploading.

Each project can contain:

- run summaries
- hit tables
- alignments
- HMM files
- synteny tables and GFF3 files
- figures
- methods text
- reproducibility JSON
- export ZIPs

The default final export folder is:

```text
~/Documents/HMM-Discovery-Exports
```

You can replace it with any folder path, for example an external drive, a lab project folder, or a private manuscript analysis folder. The folder is created if it does not exist. If you do not want to type a path, use the Step 9 folder picker to navigate and select the folder.

Keep project folders, run outputs, downloaded databases, and unpublished sequences outside the Git repository.

## Common Startup Problems

### The app does not open

- Confirm the terminal still shows the app process running.
- Open `http://127.0.0.1:8081`.
- If port 8081 is busy, stop the old app process or launch on another port with Shiny directly.

### `conda` is not found

Install Miniforge, Miniconda, or Anaconda, then restart the terminal.

### A bioinformatics tool is missing

Run the setup/environment checks in the app, or update the environment:

```bash
conda env update -f environment.yml --prune
```

### A database run is too large

Start smaller. Run protein databases first, then add nucleotide/gut viral breadth checks once the HMM recovers seeds cleanly and disk space is sufficient.

## Deployment Checklist For Labs

- Use the GitHub repository as code only.
- Keep user projects on a persistent data volume.
- Keep private FASTA/GenBank files out of Git.
- Run the demo after installation.
- Confirm export ZIP creation.
- Record database versions and run summaries for manuscript work.
- Cite HMM Discovery plus every tool and database selected in the run.
