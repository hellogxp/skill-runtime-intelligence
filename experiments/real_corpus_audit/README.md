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

Version 3 also records SHA-256 fingerprints for the exact temporary snapshot,
its SQLite schema, and the privacy-safe aggregate. These are locally linkable
identifiers: sharing reports can reveal that two reports used the same
snapshot. They contain no row-level fields and cannot reconstruct source rows,
but they do not replace retaining an access-controlled immutable snapshot when
independent re-analysis is required.
