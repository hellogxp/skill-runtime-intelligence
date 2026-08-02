#!/usr/bin/env python3
"""Emit a nonce-bound result, then realize the declared process outcome."""

import argparse
import hashlib
import json
import os
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument(
    "--mode",
    choices=("success", "execution-failure", "resource-failure"),
    required=True,
)
arguments = parser.parse_args()
nonce = os.environ.get("SRI_TRIAL_NONCE")
if not nonce:
    raise SystemExit("SRI_TRIAL_NONCE is required")

configuration = {
    "success": ("verified_success", "outcome", 0),
    "execution-failure": ("observed_failure", "execution", 7),
    "resource-failure": ("observed_failure", "resources", 8),
}
status, boundary, exit_code = configuration[arguments.mode]
if arguments.mode == "resource-failure":
    missing = Path(__file__).resolve().parents[1] / "references" / "required-missing.txt"
    if missing.exists():
        raise SystemExit("resource failure precondition was not satisfied")
token = hashlib.sha256(f"{arguments.mode}:{nonce}".encode()).hexdigest()[:20]
print(
    json.dumps(
        {
            "status": status,
            "boundary": boundary,
            "exit_code": exit_code,
            "token": f"SRI-{token}",
        },
        separators=(",", ":"),
    )
)
raise SystemExit(exit_code)
