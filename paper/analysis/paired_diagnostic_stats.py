#!/usr/bin/env python3
"""Reproduce descriptive paired diagnostic statistics for the paper.

The 126 rows instantiate seven repeated fault-family templates.  Rows within a
template are strongly dependent, so this script deliberately emits no
case-level significance test.  Case counts describe the frozen matrix;
template-level higher/lower/equal counts bound the comparative claim.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


METRICS = ("exact", "boundary_exact", "status_exact", "citation_entailment_valid")


def summarize(
    payload: dict[str, Any],
    right_payload: dict[str, Any],
    left_view: str,
    right_view: str,
) -> dict[str, Any]:
    by_view: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in payload["rows"]:
        if row["view"] == left_view:
            by_view[left_view][row["case_id"]] = row
    for row in right_payload["rows"]:
        if row["view"] == right_view:
            by_view[right_view][row["case_id"]] = row

    case_ids = sorted(set(by_view[left_view]) & set(by_view[right_view]))
    if len(case_ids) != 126:
        raise ValueError(f"expected 126 paired cases, found {len(case_ids)}")

    summary: dict[str, Any] = {
        "paired_cases": len(case_ids),
        "fault_family_templates": len(
            {str(by_view[left_view][case_id]["fault_mode"]) for case_id in case_ids}
        ),
        "left_view": left_view,
        "right_view": right_view,
        "inference_boundary": (
            "Case counts describe the frozen matrix. Rows repeat seven fault-family "
            "templates and are not independent samples; no population-level p-value "
            "is reported."
        ),
        "metrics": {},
    }

    families: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"left": 0, "right": 0, "n": 0})
    )
    for case_id in case_ids:
        family = str(by_view[left_view][case_id]["fault_mode"])
        for metric in METRICS:
            families[family][metric]["left"] += bool(
                by_view[left_view][case_id][metric]
            )
            families[family][metric]["right"] += bool(
                by_view[right_view][case_id][metric]
            )
            families[family][metric]["n"] += 1

    for metric in METRICS:
        left_only = right_only = ties = left_total = right_total = 0
        for case_id in case_ids:
            left = bool(by_view[left_view][case_id][metric])
            right = bool(by_view[right_view][case_id][metric])
            left_total += left
            right_total += right
            left_only += left and not right
            right_only += right and not left
            ties += left == right

        template_directions = {"left_higher": 0, "right_higher": 0, "equal": 0}
        for family in families.values():
            left = family[metric]["left"]
            right = family[metric]["right"]
            if left > right:
                template_directions["left_higher"] += 1
            elif right > left:
                template_directions["right_higher"] += 1
            else:
                template_directions["equal"] += 1

        summary["metrics"][metric] = {
            "left_case_count": left_total,
            "right_case_count": right_total,
            "left_only_cases": left_only,
            "right_only_cases": right_only,
            "tied_cases": ties,
            "template_directions": template_directions,
        }

    summary["fault_families"] = {
        family: {metric: dict(counts) for metric, counts in metrics.items()}
        for family, metrics in sorted(families.items())
    }
    summary["distinct_predictions_within_family"] = {
        family: {
            view: len(
                {
                    json.dumps(by_view[view][case_id]["predicted"], sort_keys=True)
                    for case_id in case_ids
                    if str(by_view[view][case_id]["fault_mode"]) == family
                }
            )
            for view in (left_view, right_view)
        }
        for family in sorted(families)
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--right-report", type=Path)
    parser.add_argument("--left-view", default="raw")
    parser.add_argument("--right-view", default="panorama")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.report.read_text())
    right_payload = (
        json.loads(args.right_report.read_text()) if args.right_report else payload
    )
    rendered = json.dumps(
        summarize(payload, right_payload, args.left_view, args.right_view),
        indent=2,
        sort_keys=True,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
