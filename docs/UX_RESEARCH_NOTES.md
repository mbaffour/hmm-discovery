# UX Research Notes

These notes capture the rationale behind the in-app guidance added for HMM Discovery.

## Design Direction

- Use progressive disclosure: keep the primary workflow visible, then expose caveats and expert controls near the decision point.
- Treat the app as both a research instrument and a teaching tool: each risky control should explain what it means biologically and computationally.
- Keep reproducibility visible in the workflow through run summaries, methods text, manifest files, and export/cleanup boundaries.

## Sources Consulted

- IBM documentation on progressive disclosure recommends revealing only the information needed for the current task, with deeper help in contextual UI text, field hints, banners, and tooltips: https://www.ibm.com/docs/en/technical-content?topic=practices-progressive-disclosure
- Arneson, Fu, and Gatzke argue that user-centered design improves usability, reproducibility, and sustainability in scientific software: https://experts.illinois.edu/en/publications/toward-more-usable-reproducible-and-sustainable-scientific-softwa/
- Queiroz et al. summarize usability practices for computational science software and note that usability is often overlooked in scientific tools: https://arxiv.org/abs/1709.00111
- NCBI ORFfinder documents ORF search as finding open reading frames and returning ranges plus protein translations; it also exposes minimum ORF length, genetic code, and start-codon choices: https://www.ncbi.nlm.nih.gov/orffinder
- Pohl et al. describe scientific workflows as important for reuse, reproducibility, and traceability, while noting that exploratory workflows change during hypothesis testing: https://arxiv.org/abs/2309.14097

## Product Decisions Applied

- Step 0 now distinguishes single-genome scans, selected-database searches, and all-database benchmarks.
- Step 4 now explains the difference between exhaustive six-frame ORF discovery and Prodigal predicted-gene baseline searches.
- Step 8 now explains synteny placement caveats and external synteny export formats.
- Step 9 now separates publication-grade outputs from regenerable intermediates that can be cleared.
- The sidebar includes a persistent workflow coach for the highest-risk decisions.
