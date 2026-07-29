# E2 — Non-interference and overhead microbenchmark

This local benchmark alternates baseline and collector-enabled runs of the
same deterministic action workload. It checks output/control-input digests,
event loss and duplication, SQLite size, wall/CPU distributions, and a
closed-endpoint fail-open subprocess path.

Run:

```bash
PYTHONPATH=src python3 experiments/non_interference/run_benchmark.py
```

Passing the invariant gate means this isolated fixture did not mutate the
workload and did not lose events. It does not by itself prove negligible
end-to-end overhead or unchanged model behavior; pinned live Agent trials are
the confirmatory tier.

