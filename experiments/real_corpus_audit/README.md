# Real-run corpus readiness audit

This exploratory experiment creates a transactionally consistent SQLite
snapshot through a connection with `PRAGMA query_only=ON` and reports only
aggregate lifecycle coverage. It never emits
run IDs, Skill names, prompts, summaries, paths, timestamps, payloads, source
locators, or row-level records.

On a live WAL database, SQLite may create `-shm`/`-wal` locking sidecars even
though query-only enforcement prevents content writes. The report records this
boundary explicitly instead of claiming an OS-level read-only open.

The output distinguishes:

- successful privacy-safe aggregation; from
- readiness for a human-labeled real-failure corpus.

Production diagnostic findings remain **Derived candidate labels**. They are
not converted into human gold labels. The readiness heuristics were defined
after an initial aggregate inspection and are exploratory, not preregistered
power criteria.

Run locally:

```bash
PYTHONPATH=src python3 experiments/real_corpus_audit/run_benchmark.py \
  --database .sri/panorama.db
```

This experiment is intentionally excluded from the default reproducibility
suite because it depends on a private local runtime database.

Compare two privacy-safe aggregate reports without reading the source database:

```bash
PYTHONPATH=src python3 experiments/real_corpus_audit/compare_reports.py \
  --before experiments/real_corpus_audit/results/BEFORE.json \
  --after experiments/real_corpus_audit/results/AFTER.json
```

Population drift is reported as Derived aggregate evidence. The comparison
cannot identify changed runs or attribute the drift to restart, re-indexing,
source availability, or retention.

Measure whether runtime terminality and evidence sufficiency move together
inside one snapshot-A cohort:

```bash
PYTHONPATH=src python3 \
  experiments/real_corpus_audit/cohort_evidence_transition_benchmark.py \
  --database .sri/panorama.db \
  --interval-seconds 2
```

The experiment uses private run keys only inside the process to align two
query-only snapshots. Its report contains four-state transition counts, never
run keys or row-level content. “Evidence sufficient” requires an observed
Skill activation plus either a verified outcome or an explicit failed event.

Version 3 also records SHA-256 fingerprints for the exact temporary snapshot,
its SQLite schema, and the privacy-safe aggregate. These are locally linkable
identifiers: sharing reports can reveal that two reports used the same
snapshot. They contain no row-level fields and cannot reconstruct source rows,
but they do not replace retaining an access-controlled immutable snapshot when
independent re-analysis is required.

Pilot dataset cut policies on three consecutive privacy-safe snapshots:

```bash
PYTHONPATH=src python3 \
  experiments/real_corpus_audit/cut_policy_benchmark.py \
  --database .sri/panorama.db \
  --interval-seconds 2 \
  --watermark-seconds 30
```

The middle snapshot selects runs using all-observed, terminal-status,
event-watermark, observed-quiescence, terminal-plus-watermark, and
terminal-plus-watermark-plus-quiescence policies. The third snapshot measures
which selected private run fingerprints changed. Only aggregate counts and
rates are emitted. This is an observational pilot: a stable fingerprint does
not prove source completeness, and one time series cannot establish a causal
policy advantage.

Aggregate two or more privacy-safe pilot reports:

```bash
PYTHONPATH=src python3 \
  experiments/real_corpus_audit/summarize_cut_policy_reports.py \
  --inputs experiments/real_corpus_audit/results/dataset-cut-policy-*.json
```

The summary reports pooled counts plus across-trial means and ranges. Pooled
run observations are not treated as independent participants, and the output
does not estimate a causal policy effect.

Group repeated pilot reports into an observational wait curve:

```bash
PYTHONPATH=src python3 \
  experiments/real_corpus_audit/summarize_cut_policy_curve.py \
  --inputs experiments/real_corpus_audit/results/dataset-cut-policy-*.json
```

Each wait condition must have at least two trials. Conditions are run
sequentially rather than randomized, so ambient ingestion load is a covariate
and the curve must not be presented as a causal waiting-time effect.

Audit whether the live schema exposes an actual collection checkpoint:

```bash
PYTHONPATH=src python3 \
  experiments/real_corpus_audit/epoch_capability_audit.py \
  --database .sri/panorama.db
```

The audit emits only schema and runtime-state category counts. It does not
export raw state keys, source paths, endpoints, session identifiers, or row
records. A global revision counter is scored separately from an epoch
identifier, running/completed state, source watermark, and late-arrival
counter.

Run the isolated collection-epoch mechanism experiment:

```bash
PYTHONPATH=src python3 \
  experiments/real_corpus_audit/collection_epoch_benchmark.py \
  --paired-trials 8 \
  --failure-trials 4
```

The experiment pairs a controlled late source mutation with an unchanged
control, injects a newly created source inside the epoch, observes epoch state
during parsing and after completion, and separately exercises the failed
transition. It uses temporary databases and a synthetic adapter. Passing
validates mechanism behavior only; it does not prove live watcher deployment,
source completeness, or a natural late-arrival rate.

Exercise epochs through the production Codex adapter and watch loop:

```bash
PYTHONPATH=src python3 \
  experiments/real_corpus_audit/codex_watch_epoch_benchmark.py \
  --trials 3
```

Each isolated trial creates a transcript, appends its completion records, and
then removes the source. The experiment checks epoch advancement, exact
removed-source accounting, historical session retention, and watcher-process
cleanup. The transcripts are synthetic, so the result validates the
production adapter/watch mechanism but is not a live-Agent replication or a
field failure-rate estimate.

Audit mixed transcript and official-hook provenance:

```bash
PYTHONPATH=src python3 \
  experiments/real_corpus_audit/mixed_provenance_benchmark.py \
  --trials 8
```

The experiment refreshes a transcript after appending a correlated
official-hook event. It scores hook evidence preservation, correlation-group
preservation, and availability of cross-source relationship edges separately.
An overall failed gate can therefore mean evidence is safely retained but a
merged relationship view is still absent.

Localize full-reindex drift by collection provenance:

```bash
PYTHONPATH=src python3 \
  experiments/real_corpus_audit/provenance_reindex_benchmark.py \
  --database .sri/panorama.db \
  --project .
```

The experiment makes a consistent query-only database snapshot, performs two
full transcript reindexes on an isolated temporary copy, and emits aggregate
deltas by collection mode. A live-snapshot comparison is identifiable only
when the captured collection checkpoint is completed with zero failures and
late arrivals, its source watermark matches the reindex input, and no source
changes during the comparison. The working database is deleted afterward;
no row-level records, raw content, identifiers, source paths, or watermark
hashes are included in the report. A non-identifiable gate is not evidence of
reindex failure.

Test repeated reconstruction on a frozen historical transcript subset:

```bash
PYTHONPATH=src python3 \
  experiments/real_corpus_audit/frozen_corpus_reindex_benchmark.py \
  --project . \
  --repeats 3
```

The default selection is limited to 12 transcripts older than one hour, no
larger than 8 MiB each or 64 MiB total. Raw files are copied only into an
auto-deleted local temporary directory. The report includes aggregate source
identity multiplicities, copy integrity, table counts, and equality booleans;
it emits no paths, IDs, contents, or fingerprint values. The gate checks both
repeat fingerprint equality and preservation of each physical source instance,
because a deterministic overwrite is not a correct reconstruction.

Audit source-identity cardinality across the complete local Codex corpus:

```bash
PYTHONPATH=src python3 \
  experiments/real_corpus_audit/source_identity_audit.py
```

This lightweight audit reads at most the first 20 lines of each transcript and
emits only source counts, upstream-identity multiplicities, and an aggregate
ratio. It never exports identities, paths, content, timestamps, or row-level
records. Repeated identities establish a many-to-one cardinality condition;
they do not by themselves prove that the underlying streams diverge.
