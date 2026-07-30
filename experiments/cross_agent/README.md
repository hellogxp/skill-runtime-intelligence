# E4 — Cross-Agent/export-profile comparability

The local gate feeds semantically equivalent parent/child Skill traces through
the OTel, Phoenix, LangSmith, Langfuse, Weave, and Datadog export profiles. It
checks only fields that the profiles can represent equivalently and audits
parent references for dangling IDs.

This is a canonicalization test. Live same-Skill comparisons across independent
Agents remain a stronger experiment tier.

Exercise Agent-scoped source identity with deliberately colliding labels:

```bash
PYTHONPATH=src python3 \
  experiments/cross_agent/source_instance_contract_benchmark.py \
  --trials 8
```

The benchmark sends equivalent official-hook events from Qoder, OpenCode, and
Claude Code through the production hook builders, Collector normalization, and
Evidence Store. All three use the same synthetic upstream session, turn, and
call labels. The gate checks that Agent namespaces prevent session/event
collisions, that a later event from the same Agent appends to its existing
stream, and that no cross-source causal relationship is invented. Payloads are
synthetic and the report is aggregate-only; this is a mechanism test, not a
live cross-Agent behavior comparison.

Audit field-level comparability decisions for an explicit alignment manifest:

```bash
PYTHONPATH=src python3 \
  experiments/cross_agent/alignment_manifest_benchmark.py
```

Nine synthetic contract cases cover equivalent runs, clock skew, task and
Skill-digest mismatch, missing terminal evidence, outcome capability masks,
reported outcome conflict, verified outcome difference, and an explicit
Skill-version comparison axis. The evaluator returns separate lifecycle,
outcome, and absolute-time comparability dimensions. It never authorizes
causal attribution. The five-second clock tolerance is a test policy rather
than an empirically optimized threshold.
