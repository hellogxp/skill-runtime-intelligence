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

Audit an explicit privacy-safe task alignment key:

```bash
PYTHONPATH=src python3 \
  experiments/cross_agent/paired_task_key_contract_benchmark.py \
  --trials 20 \
  --task-pool-size 1024
```

The assignment contains an opaque task ID, study scope, and protocol version.
A 0600 study secret derives a scope-specific exported HMAC key; raw prompts,
semantic similarity, timestamps, and Agent identity do not participate in the
derivation. The benchmark checks same-assignment convergence, task/scope/
protocol domain separation, synthetic collision absence, export redaction,
and fail-closed secret/manifest handling. It validates an explicit assignment
mechanism, not semantic task equivalence, secret-distribution UX, or live
cross-Agent comparison accuracy.

Link the verified installed-Agent reports back to live sessions and import
their outcomes into an isolated temporary evidence database:

```bash
PYTHONPATH=src python3 \
  experiments/cross_agent/experiment_evidence_import_benchmark.py \
  --database .sri/panorama.db
```

The join hashes each adapter's source-session identity locally and matches it
to the digest already stored in the privacy-safe experiment report. It checks
exact resolution, adapter consistency, idempotent re-import, and fail-closed
handling of missing, mismatched, or conflicting evidence. The production
database is read-only and never receives the experimental outcome records.

Exercise an additive Experimental task/outcome schema on a consistent copy of
the live Panorama database:

```bash
PYTHONPATH=src python3 \
  experiments/cross_agent/experiment_evidence_schema_migration_benchmark.py \
  --database .sri/panorama.db
```

The benchmark checks failed-migration rollback, task/outcome idempotency,
verifier-digest constraints, task-delete cascade, session preservation,
downgrade cleanup, core-table count preservation, and SQLite integrity. All
writes target a temporary backup; passing does not authorize changing the
production schema or establish consent, concurrency, UI, or release behavior.

Import real failed CLI calls without manufacturing session outcomes:

```bash
PYTHONPATH=src python3 \
  experiments/cross_agent/experiment_attempt_failure_import_benchmark.py \
  --database .sri/panorama.db
```

The benchmark keeps execution errors and invalid responses as Experimental
attempt records. A failure becomes session-linked only when its privacy-safe
source identity resolves exactly once to the same adapter. Otherwise it stays
explicitly unresolved and cannot create an outcome edge.

Exercise the privacy-safe pre-session late-binding contract:

```bash
PYTHONPATH=src python3 \
  experiments/cross_agent/attempt_correlation_contract_benchmark.py \
  --trials 20 \
  --token-pool-size 1024
```

This controlled synthetic benchmark checks HMAC domain separation, finite-pool
collisions, exactly-once binding, idempotent replay, adapter isolation,
conflicting rebind rejection, pending pre-session failures, and raw-token
absence from persistence. It does not show that any installed Agent can yet
propagate the token.

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

Sweep the clock policy independently of other comparison dimensions:

```bash
PYTHONPATH=src python3 \
  experiments/cross_agent/alignment_clock_sensitivity.py
```

The synthetic sweep evaluates 11 offsets against eight tolerance policies.
Its invariant requires lifecycle/outcome comparability and causal-attribution
status to remain unchanged while only the absolute-time mask changes. This
tests policy isolation and monotonicity; it does not estimate real clock skew
or choose an optimal threshold.

Audit whether stored timestamps carry enough provenance for absolute-time
comparison:

```bash
PYTHONPATH=src python3 \
  experiments/cross_agent/timestamp_provenance_audit.py
```

The audit checks the temporary production schema and controlled hook builders
for event time, origin, ingestion time, clock domain, uncertainty, precision,
and a source-versus-fallback marker. It emits aggregate booleans and counts
only. Schema coverage and populated provenance are scored separately from
absolute-time readiness: representable fields do not establish synchronized
clocks. Missing capability is not evidence that a timestamp is inaccurate.

Exercise the additive migration against a consistent copy opened from a live
database in read-only mode:

```bash
PYTHONPATH=src python3 \
  experiments/cross_agent/timestamp_provenance_live_copy_audit.py \
  --database .sri/panorama.db
```

Only aggregate counts and integrity status are emitted. Legacy rows remain
unknown/null; the audit neither mutates the source database nor reconstructs
historical clock metadata.

Audit whether current live evidence supports cross-Agent claims:

```bash
PYTHONPATH=src python3 \
  experiments/cross_agent/coverage_readiness_audit.py \
  --database .sri/panorama.db
```

The audit separates multi-Adapter presence, descriptive cross-Agent readiness,
and confirmatory cross-Agent readiness. It emits only per-Adapter aggregate
counts, imbalance, shared-stage counts, and shared Skill-digest group counts;
it does not emit session IDs, Skill names or digests, paths, timestamps, or
content. Thresholds are exploratory. An audit-integrity pass does not mean
that either comparison-readiness gate passed, and no gate authorizes causal
attribution.
