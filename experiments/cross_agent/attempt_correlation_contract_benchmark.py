#!/usr/bin/env python3
"""Controlled contract study for pre-session attempt late binding."""

import argparse
import hashlib
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report
from experiments.privacy_safe_attempt_correlation import (
    CORRELATION_SCHEMA,
    attempt_correlation_token,
)


CASES = (
    ("authentication_failure", False),
    ("timeout_before_session", False),
    ("crash_after_session", True),
    ("malformed_response", True),
)


def _schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE sessions (
            session_id TEXT PRIMARY KEY,
            adapter TEXT NOT NULL
        );
        CREATE TABLE attempts (
            attempt_id TEXT PRIMARY KEY,
            adapter TEXT NOT NULL,
            token_sha256 TEXT NOT NULL UNIQUE
                CHECK(length(token_sha256) = 64
                    AND token_sha256 NOT GLOB '*[^0-9a-f]*'),
            state TEXT NOT NULL CHECK(state IN ('pending', 'bound')),
            session_id TEXT,
            evidence_grade TEXT NOT NULL CHECK(evidence_grade = 'Experimental'),
            CHECK((state = 'pending' AND session_id IS NULL)
                OR (state = 'bound' AND session_id IS NOT NULL)),
            FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                ON DELETE RESTRICT
        );
        """
    )


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def _bind(
    connection: sqlite3.Connection,
    token: str,
    adapter: str,
    session_id: str,
) -> str:
    attempt = connection.execute(
        "SELECT attempt_id, adapter, state, session_id FROM attempts "
        "WHERE token_sha256 = ?",
        (_token_digest(token),),
    ).fetchone()
    if attempt is None:
        raise ValueError("unknown correlation token")
    attempt_id, expected_adapter, state, existing_session = attempt
    if adapter != expected_adapter:
        raise ValueError("adapter mismatch")
    session = connection.execute(
        "SELECT adapter FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    if session is None or session[0] != adapter:
        raise ValueError("session adapter mismatch")
    if state == "bound":
        if existing_session != session_id:
            raise ValueError("attempt already bound to another session")
        return "idempotent"
    connection.execute(
        "UPDATE attempts SET state = 'bound', session_id = ? "
        "WHERE attempt_id = ? AND state = 'pending'",
        (session_id, attempt_id),
    )
    return "bound"


def run_benchmark(trials: int, token_pool_size: int) -> Dict[str, Any]:
    if trials < 1 or token_pool_size < 4:
        raise ValueError("trials must be positive and token pool at least four")
    stable = 0
    domain_separated = 0
    collision_free = 0
    late_binding_passed = 0
    wrong_adapter_rejected = 0
    unknown_token_rejected = 0
    conflicting_rebind_rejected = 0
    raw_token_absent = 0
    pending_counts = []
    bound_counts = []

    with tempfile.TemporaryDirectory(prefix="sri-attempt-correlation-") as root:
        secret_path = Path(root) / "study.secret"
        for trial in range(trials):
            def derive(scope: str, adapter: str, nonce: str) -> Dict[str, str]:
                return attempt_correlation_token(secret_path, {
                    "schema_version": CORRELATION_SCHEMA,
                    "study_scope": scope,
                    "adapter": adapter,
                    "attempt_nonce": nonce,
                })

            base = derive("late-binding-v1", "qoder", f"trial-{trial}-base")
            stable += derive(
                "late-binding-v1", "qoder", f"trial-{trial}-base"
            )["token"] == base["token"]
            variants = {
                base["token"],
                derive("late-binding-v2", "qoder", f"trial-{trial}-base")["token"],
                derive("late-binding-v1", "codex", f"trial-{trial}-base")["token"],
                derive("late-binding-v1", "qoder", f"trial-{trial}-other")["token"],
            }
            domain_separated += len(variants) == 4
            pool = {
                derive("collision-study", "qoder", f"{trial}-{index}")["token"]
                for index in range(token_pool_size)
            }
            collision_free += len(pool) == token_pool_size

            connection = sqlite3.connect(":memory:")
            connection.execute("PRAGMA foreign_keys = ON")
            try:
                _schema(connection)
                tokens = {}
                for index, (case, has_session) in enumerate(CASES):
                    record = derive(
                        "late-binding-v1", "qoder", f"trial-{trial}-{case}"
                    )
                    tokens[case] = record["token"]
                    connection.execute(
                        "INSERT INTO attempts VALUES (?, ?, ?, 'pending', NULL, "
                        "'Experimental')",
                        (f"attempt-{trial}-{index}", "qoder", record["token_sha256"]),
                    )
                    if has_session:
                        connection.execute(
                            "INSERT INTO sessions VALUES (?, ?)",
                            (f"session-{trial}-{index}", "qoder"),
                        )
                first = []
                second = []
                for index, (case, has_session) in enumerate(CASES):
                    if not has_session:
                        continue
                    session_id = f"session-{trial}-{index}"
                    first.append(_bind(connection, tokens[case], "qoder", session_id))
                    second.append(_bind(connection, tokens[case], "qoder", session_id))
                late_binding_passed += (
                    first == ["bound", "bound"]
                    and second == ["idempotent", "idempotent"]
                )
                try:
                    _bind(
                        connection, tokens["crash_after_session"], "codex",
                        f"session-{trial}-2",
                    )
                except ValueError:
                    wrong_adapter_rejected += 1
                try:
                    _bind(connection, "sri_corr_" + "0" * 32, "qoder", f"session-{trial}-2")
                except ValueError:
                    unknown_token_rejected += 1
                connection.execute(
                    "INSERT INTO sessions VALUES (?, ?)",
                    (f"session-{trial}-conflict", "qoder"),
                )
                try:
                    _bind(
                        connection, tokens["crash_after_session"], "qoder",
                        f"session-{trial}-conflict",
                    )
                except ValueError:
                    conflicting_rebind_rejected += 1
                pending_counts.append(connection.execute(
                    "SELECT COUNT(*) FROM attempts WHERE state = 'pending'"
                ).fetchone()[0])
                bound_counts.append(connection.execute(
                    "SELECT COUNT(*) FROM attempts WHERE state = 'bound'"
                ).fetchone()[0])
                dump = "\n".join(connection.iterdump())
                raw_token_absent += all(token not in dump for token in tokens.values())
            finally:
                connection.close()

    metrics = {
        "trials": trials,
        "token_pool_size_per_trial": token_pool_size,
        "tokens_generated_for_collision_check": trials * token_pool_size,
        "stable_derivation_passes": stable,
        "domain_separation_passes": domain_separated,
        "collision_free_pools": collision_free,
        "late_binding_contract_passes": late_binding_passed,
        "wrong_adapter_rejections": wrong_adapter_rejected,
        "unknown_token_rejections": unknown_token_rejected,
        "conflicting_rebind_rejections": conflicting_rebind_rejected,
        "raw_token_absence_passes": raw_token_absent,
        "pending_attempts_per_trial": sorted(set(pending_counts)),
        "bound_attempts_per_trial": sorted(set(bound_counts)),
    }
    passed = all(value == trials for value in (
        stable, domain_separated, collision_free, late_binding_passed,
        wrong_adapter_rejected, unknown_token_rejected,
        conflicting_rebind_rejected, raw_token_absent,
    )) and set(pending_counts) == {2} and set(bound_counts) == {2}
    return {
        "schema_version": "sri.experiment.attempt-correlation-contract.v1",
        "experiment": {
            "name": "privacy-safe-attempt-late-binding-contract",
            "evidence_grade": "Experimental",
            "data_source": "controlled synthetic contract cases",
            "limitations": [
                "No installed Agent propagated these tokens in this experiment.",
                "Collision checks are finite observations, not a proof of uniqueness.",
                "The in-memory store does not test concurrent binders or crashes.",
                "A matching token supports correlation, not causal attribution.",
            ],
        },
        "metrics": metrics,
        "gate": {
            "name": "Attempt tokens bind exactly once without persisting raw tokens",
            "passed": passed,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--token-pool-size", type=int, default=1024)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_benchmark(arguments.trials, arguments.token_pool_size)
    output = write_report(
        EXPERIMENT_DIR, "attempt-correlation-contract", report, arguments.output
    )
    print(json.dumps({"metrics": report["metrics"], "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
