# E5 — Semantic diagnosis lower bound

This experiment compares the production deterministic rules with three
leave-one-out baselines on the same reviewed fault corpus:

- flat lexical Jaccard retrieval; and
- lifecycle-aware retrieval over status, completeness, stage sets, and event
  types; and
- relational template retrieval over ordered evidence anchors such as the
  first failed stage and the first supported gap before later activity.

All retrieval outputs are always labeled **Inferred** and are evaluated
without changing Observed or Derived records. The lifecycle baseline is a
structured-feature ablation, not an LLM or deployment-general semantic model.
It intentionally tests whether flat similarity over typed lifecycle features
is sufficient; it does not encode event order or first-boundary relations.

The relational baseline extracts ordered anchors without assigning finding
codes, learns code templates only from the other cases, and rebinds each
selected template to the query anchor's stage and evidence grade. It requires
strict majority support over null and competing templates. These anchors are
close to the production rule predicates, so the result measures representation
and label coverage—not an independent intelligent diagnostician.

The purpose is to establish a reproducible lower bound and test evidence-layer
separation. It is not presented as an LLM result.

## De-identified real-run holdout

`prepare_real_failure_holdout.py` creates a consistent read-only SQLite
snapshot and selects up to N runs per distinct production Finding profile. It
exports only run/completeness state, ordered stage states, aggregate event
signatures, and deterministic candidate labels. It omits source identifiers,
Skill identity, content, summaries, payloads, paths, locators, and timestamps.

```bash
PYTHONPATH=src python3 \
  experiments/semantic_diagnosis/prepare_real_failure_holdout.py \
  --database .sri/panorama.db \
  --maximum-per-profile 4
```

`run_real_failure_model_study.py` compares an ordered graph baseline with a
schema-constrained OpenAI-compatible model. Model findings must cite exact
evidence IDs, pass a relation-specific citation-entailment guard, remain
Inferred, and deny causal proof. Diagnostic agreement remains a separate
metric: even an entailed citation does not make the deterministic candidate
labels independent gold.

```bash
PYTHONPATH=src python3 \
  experiments/semantic_diagnosis/run_real_failure_model_study.py \
  --cases experiments/semantic_diagnosis/results/REAL_HOLDOUT.json \
  --api-base http://127.0.0.1:8000/v1 \
  --model MODEL_ID
```

The current holdout labels come from the same deterministic production logic
used by the graph baseline. They measure rule reproduction, not independent
semantic correctness, and cannot be reported as human gold.

Run an independent model through the installed OpenCode scaffold and preserve
cross-model disagreement:

```bash
PYTHONPATH=src:. python3 \
  experiments/semantic_diagnosis/run_opencode_real_failure_study.py \
  --cases experiments/semantic_diagnosis/results/REAL_HOLDOUT.json \
  --model opencode/deepseek-v4-flash-free

PYTHONPATH=src:. python3 \
  experiments/semantic_diagnosis/summarize_double_adjudication.py \
  --cases experiments/semantic_diagnosis/results/REAL_HOLDOUT.json \
  --first QWEN_REPORT.json --second DEEPSEEK_REPORT.json
```

For rule-external hypothesis generation, freeze paired anomaly/clean graph
invariants, run each model separately, and summarize replication:

```bash
PYTHONPATH=src:. python3 \
  experiments/semantic_diagnosis/prepare_novel_pattern_holdout.py
PYTHONPATH=src:. python3 \
  experiments/semantic_diagnosis/run_novel_pattern_study.py \
  --cases NOVEL_HOLDOUT.json --backend opencode \
  --model opencode/deepseek-v4-flash-free
```

These controlled patterns test discovery and false positives. They do not
estimate production anomaly prevalence or replace independent incident labels.
