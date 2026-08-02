# Paper workspace

Selected submission plan: **PROFES 2026 Research Papers**. The author confirmed
the track on 2026-08-01 after reviewing the Research--Industry comparison in
`review/profes-2026-track-decision.md`. The earlier A-TEST Tool/WIP plan is now
superseded. Industry remains unsuitable without a genuine industrial
application and lessons-learned study.

Working title: **Evidence-Calibrated Runtime Reconstruction for Agent Skills
Across Heterogeneous Coding Agents**.

Files:

- `main.tex`: LNCS full-length Research Paper draft;
- `references.bib`: primary papers, standards, and the Agent Skills specification;
- `claims-evidence-matrix.md`: claim boundaries tied to frozen evidence.

The draft uses the LNCS proceedings class. Replace the explicit author metadata
placeholder before submission; PROFES is single-anonymous. Do not change the
selected Research Papers track without an explicit author decision.

Compile when a TeX distribution is available:

```bash
latexmk -pdf -interaction=nonstopmode main.tex
```

The current workstation compiles the paper with Tectonic. Experimental artifact
hashes are frozen in
`experiments/external_validity/confirmatory_manifest_20260801.json`.
