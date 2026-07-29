#!/usr/bin/env python3
"""Deterministic verifier for the cross-Agent Skill fixture."""

import hashlib
import json
from pathlib import Path


payload = Path(__file__).resolve().parents[1] / "references" / "payload.txt"
digest = hashlib.sha256(payload.read_bytes()).hexdigest()[:16]
print(
    json.dumps(
        {
            "status": "ok",
            "fixture": "checksum-skill-v1",
            "token": f"SRI-{digest}",
        },
        separators=(",", ":"),
    )
)

