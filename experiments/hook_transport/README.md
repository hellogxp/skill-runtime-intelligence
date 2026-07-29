# Hook transport benchmark

Measures the latency-sensitive process boundary separately from Collector
normalization and SQLite work. Version 2 compares direct native AF_UNIX
delivery and the real shell command shape against paired `/usr/bin/true`
process-startup baselines. Version 3 also interleaves the direct and shell
conditions and rotates both condition order and baseline/actual order to reduce
temporal bias. Version 4 uses four-run blocks so condition position and
baseline/actual order are jointly balanced for each transport. Full-run
metrics remain the gate; post-first-five metrics are diagnostic only.
Version 5 records start/end host load averages as descriptive covariates
without changing the predeclared latency gate.
Version 6 adds descriptive p99 metrics without changing that gate.
`--prewarm-native` is a separately versioned mechanism probe: it executes the
fresh binary once against a missing socket, expects a silent exit code `1`,
then runs the unchanged balanced benchmark and gate. Prewarmed reports are not
pooled with default v4–v6 runs.

The predeclared local engineering gate checks silent fail-open behavior, exact
event delivery, direct/shell p95 below 100 ms, and shell incremental p95 below
75 ms. It does not claim that the numbers generalize across operating systems
or Agent implementations.

`run_contention.py` is a separate exploratory experiment. It runs idle
bookends around bounded CPU, I/O, and mixed synthetic load. Each segment keeps
the same four-run balance. Its gate covers load-worker health and lossless,
silent delivery only; latency ratios remain Experimental rather than becoming
an implicit release SLO. `--schedule-order reverse` reverses the three load
segments while preserving idle bookends, providing a basic order-sensitivity
replication. Version 2 records host load averages and refuses to start
synthetic workers when the initial one-minute load divided by logical CPUs
exceeds `0.75`; such attempts are explicitly recorded as `not_run`.

`run_nc_fallback.py` isolates the OpenBSD-netcat AF_UNIX fallback used on
compatible Linux systems. Its integrity gate requires exact, silent delivery;
latency is descriptive. It must not be reported as native-sender evidence.

`analyze_runs.py` aggregates only the comparable v4–v6 balanced reports. It
retains failed performance gates, reports a Wilson interval for the run-level
pass rate, and computes descriptive pooled/run-level p99 and max values.
