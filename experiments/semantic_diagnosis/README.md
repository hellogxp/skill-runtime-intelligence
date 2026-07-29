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
