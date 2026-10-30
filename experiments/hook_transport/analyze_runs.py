#!/usr/bin/env python3
"""Aggregate comparable balanced hook-transport runs without hiding failures."""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import percentile, write_report


COMPARABLE_SCHEMAS = {
    "sri.experiment.hook-transport.v4",
    "sri.experiment.hook-transport.v5",
    "sri.experiment.hook-transport.v6",
}
TRANSPORTS = ("native_direct", "native_via_shell")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson_interval(successes, total, z=1.96):
    if total == 0:
        return None
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    radius = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / total
            + z * z / (4 * total * total)
        )
        / denominator
    )
    return {"low": center - radius, "high": center + radius}


def summarize(values):
    return {
        "count": len(values),
        "p50_ms": percentile(values, 0.5),
        "p95_ms": percentile(values, 0.95),
        "p99_ms": percentile(values, 0.99),
        "max_ms": max(values),
    }


def run_metric(rows, key, quantile):
    return percentile([row[key] for row in rows], quantile)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results",
        type=Path,
        default=EXPERIMENT_DIR / "results",
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()

    sources = []
    ignored = []
    for path in sorted(arguments.results.glob("hook-transport-*.json")):
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("schema_version") not in COMPARABLE_SCHEMAS:
            ignored.append(
                {
                    "file": path.name,
                    "schema_version": report.get("schema_version"),
                }
            )
            continue
        metrics = report.get("metrics", {})
        transport_rows = {
            transport: metrics.get(transport, {}).get("trials", [])
            for transport in TRANSPORTS
        }
        if not all(transport_rows.values()):
            ignored.append(
                {"file": path.name, "reason": "missing raw balanced trials"}
            )
            continue
        expected = metrics.get("expected_events")
        accepted = metrics.get("accepted_events")
        integrity_passed = (
            accepted == expected
            and all(
                metrics[transport].get("exit_failures") == 0
                and metrics[transport].get("non_silent_invocations") == 0
                for transport in TRANSPORTS
            )
        )
        load = report.get("experiment", {}).get("host_load") or {}
        sources.append(
            {
                "file": path.name,
                "sha256": sha256(path),
                "schema_version": report["schema_version"],
                "performance_gate_passed": bool(
                    report.get("gate", {}).get("passed")
                ),
                "integrity_passed": integrity_passed,
                "expected_events": expected,
                "accepted_events": accepted,
                "host_load": load,
                "rows": transport_rows,
            }
        )

    if not sources:
        raise SystemExit("no comparable balanced hook-transport reports found")

    aggregate = {}
    steady_aggregate = {}
    first_trial_aggregate = {}
    threshold_exceedances = {}
    run_level = {}
    for transport in TRANSPORTS:
        rows = [
            row
            for source in sources
            for row in source["rows"][transport]
        ]
        aggregate[transport] = {
            "actual": summarize([row["actual_wall_ms"] for row in rows]),
            "incremental": summarize(
                [row["incremental_wall_ms"] for row in rows]
            ),
        }
        steady_rows = [
            row
            for source in sources
            for row in source["rows"][transport][5:]
        ]
        first_rows = [source["rows"][transport][0] for source in sources]
        steady_aggregate[transport] = {
            "definition": "pooled trials after the first five in every run",
            "actual": summarize(
                [row["actual_wall_ms"] for row in steady_rows]
            ),
            "incremental": summarize(
                [row["incremental_wall_ms"] for row in steady_rows]
            ),
        }
        first_trial_aggregate[transport] = {
            "definition": "first trial from every run",
            "actual": summarize(
                [row["actual_wall_ms"] for row in first_rows]
            ),
            "incremental": summarize(
                [row["incremental_wall_ms"] for row in first_rows]
            ),
        }
        actual_limit = 100
        incremental_limit = 75 if transport == "native_via_shell" else None
        threshold_exceedances[transport] = {
            "actual_limit_ms": actual_limit,
            "actual_count": sum(
                row["actual_wall_ms"] >= actual_limit for row in rows
            ),
            "actual_rate": sum(
                row["actual_wall_ms"] >= actual_limit for row in rows
            )
            / len(rows),
            "incremental_limit_ms": incremental_limit,
            "incremental_count": (
                sum(
                    row["incremental_wall_ms"] >= incremental_limit
                    for row in rows
                )
                if incremental_limit is not None
                else None
            ),
            "incremental_rate": (
                sum(
                    row["incremental_wall_ms"] >= incremental_limit
                    for row in rows
                )
                / len(rows)
                if incremental_limit is not None
                else None
            ),
        }
        run_level[transport] = {
            metric: {
                "min_ms": min(values),
                "max_ms": max(values),
                "values_ms": values,
            }
            for metric, values in {
                "actual_p50": [
                    run_metric(source["rows"][transport], "actual_wall_ms", 0.5)
                    for source in sources
                ],
                "actual_p95": [
                    run_metric(source["rows"][transport], "actual_wall_ms", 0.95)
                    for source in sources
                ],
                "actual_p99": [
                    run_metric(source["rows"][transport], "actual_wall_ms", 0.99)
                    for source in sources
                ],
                "incremental_p95": [
                    run_metric(
                        source["rows"][transport],
                        "incremental_wall_ms",
                        0.95,
                    )
                    for source in sources
                ],
                "incremental_p99": [
                    run_metric(
                        source["rows"][transport],
                        "incremental_wall_ms",
                        0.99,
                    )
                    for source in sources
                ],
            }.items()
        }

    performance_passes = sum(
        source["performance_gate_passed"] for source in sources
    )
    integrity_passes = sum(source["integrity_passed"] for source in sources)
    load_observed = [
        source
        for source in sources
        if source["host_load"].get("ambient_at_start")
    ]
    report = {
        "schema_version": "sri.experiment.hook-transport-aggregate.v1",
        "experiment": {
            "name": "hook-transport-cross-run-aggregate",
            "evidence_grade": "Derived",
            "source_evidence_grade": "Experimental",
            "comparable_schemas": sorted(COMPARABLE_SCHEMAS),
            "limitations": [
                "Runs share one host and are not independent cross-host samples.",
                "Per-run p99 uses only 40 trials and is descriptive.",
                "Pooled trial percentiles do not replace the per-run release gate.",
                "Too few runs contain load covariates for correlation analysis.",
            ],
        },
        "metrics": {
            "run_count": len(sources),
            "trials_per_transport": sum(
                len(source["rows"]["native_direct"]) for source in sources
            ),
            "expected_events": sum(source["expected_events"] for source in sources),
            "accepted_events": sum(source["accepted_events"] for source in sources),
            "integrity_passes": integrity_passes,
            "performance_gate_passes": performance_passes,
            "performance_gate_rate": performance_passes / len(sources),
            "performance_gate_rate_wilson_95": wilson_interval(
                performance_passes, len(sources)
            ),
            "runs_with_load_covariates": len(load_observed),
            "pooled": aggregate,
            "pooled_steady_after_first_five": steady_aggregate,
            "first_trial_across_runs": first_trial_aggregate,
            "trial_threshold_exceedances": threshold_exceedances,
            "run_level": run_level,
        },
        "sources": [
            {key: value for key, value in source.items() if key != "rows"}
            for source in sources
        ],
        "ignored_sources": ignored,
        "gate": {
            "name": "all comparable runs preserved lossless silent delivery",
            "passed": integrity_passes == len(sources),
        },
    }
    output = write_report(
        EXPERIMENT_DIR, "hook-transport-aggregate", report, arguments.output
    )
    print(
        json.dumps(
            {
                "run_count": report["metrics"]["run_count"],
                "trials_per_transport": report["metrics"][
                    "trials_per_transport"
                ],
                "expected_events": report["metrics"]["expected_events"],
                "accepted_events": report["metrics"]["accepted_events"],
                "integrity_passes": integrity_passes,
                "performance_gate_passes": performance_passes,
                "performance_gate_rate": report["metrics"][
                    "performance_gate_rate"
                ],
                "performance_gate_rate_wilson_95": report["metrics"][
                    "performance_gate_rate_wilson_95"
                ],
                "pooled": aggregate,
                "pooled_steady_after_first_five": steady_aggregate,
                "first_trial_across_runs": first_trial_aggregate,
                "trial_threshold_exceedances": threshold_exceedances,
                "gate": report["gate"],
            },
            indent=2,
        )
    )
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
