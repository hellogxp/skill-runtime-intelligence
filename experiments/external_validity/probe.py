#!/usr/bin/env python3
"""Execute a read-only multi-step repository contract with injected faults."""

import hashlib
import json
import os
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = Path(__file__).resolve().parents[3]
REPOSITORY = WORKSPACE / "repository"
CONFIG = json.loads((SKILL_ROOT / "profile.json").read_text(encoding="utf-8"))
MODE = os.environ.get("SRI_FAULT_MODE", "clean")
NONCE = os.environ.get("SRI_TRIAL_NONCE")
if not NONCE:
    raise SystemExit("SRI_TRIAL_NONCE is required")

STAGES = ("instructions", "resources", "execution", "artifacts", "outcome")
BOUNDARIES = {
    "clean": None,
    "instructions_failure": "instructions",
    "resource_missing": "resources",
    "execution_failure": "execution",
    "artifact_corruption": "artifacts",
    "outcome_unverified": "outcome",
    "verifier_conflict": "outcome",
}
EXIT_CODES = {
    "clean": 0,
    "instructions_failure": 31,
    "resource_missing": 32,
    "execution_failure": 33,
    "artifact_corruption": 34,
    "outcome_unverified": 0,
    "verifier_conflict": 35,
}
if MODE not in BOUNDARIES:
    raise SystemExit(f"unsupported fault mode: {MODE}")


def repository_digest():
    digest = hashlib.sha256()
    for relative in CONFIG["files"]:
        path = REPOSITORY / relative
        if not path.is_file():
            return None, relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest(), None


boundary = BOUNDARIES[MODE]
trace = []
for index, stage in enumerate(STAGES, 1):
    if boundary is None:
        status = "observed"
    elif STAGES.index(stage) < STAGES.index(boundary):
        status = "observed"
    elif stage == boundary:
        status = "not_verified" if MODE == "outcome_unverified" else "failed"
    else:
        status = "not_observed"
    trace.append({"evidence_id": f"O{index:02d}", "stage": stage, "status": status, "grade": "experimental"})

actual_digest = None
missing_resource = None
if boundary != "instructions":
    actual_digest, missing_resource = repository_digest()
if missing_resource and boundary != "resources":
    boundary = "resources"
if MODE == "execution_failure":
    try:
        json.loads((WORKSPACE / "faults/execution.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
if MODE == "artifact_corruption" and actual_digest:
    actual_digest = hashlib.sha256((actual_digest + "corrupt").encode()).hexdigest()

reported_status = "success" if MODE in {"clean", "outcome_unverified", "verifier_conflict"} else "failure"
if MODE == "clean":
    verifier_status = "passed" if actual_digest == CONFIG["source_digest"] else "failed"
elif MODE == "outcome_unverified":
    verifier_status = "not_configured"
elif MODE == "verifier_conflict":
    verifier_status = "failed"
else:
    verifier_status = "failed"

token_material = f"{CONFIG['repo_key']}:{CONFIG['skill_id']}:{MODE}:{NONCE}:{CONFIG['source_digest']}"
token = "SRI-" + hashlib.sha256(token_material.encode()).hexdigest()[:20]
result = {
    "repo_key": CONFIG["repo_key"],
    "skill_id": CONFIG["skill_id"],
    "fault_mode": MODE,
    "reported_status": reported_status,
    "verifier_status": verifier_status,
    "boundary": boundary or "none",
    "exit_code": EXIT_CODES[MODE],
    "token": token,
    "trace": trace,
}
print(json.dumps(result, separators=(",", ":"), sort_keys=True))
raise SystemExit(EXIT_CODES[MODE])
