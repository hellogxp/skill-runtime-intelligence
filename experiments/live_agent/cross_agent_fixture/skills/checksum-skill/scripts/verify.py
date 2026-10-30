#!/usr/bin/env python3
"""Deterministic verifier for the cross-Agent live fixture."""

import hashlib
import json
from pathlib import Path


payload = Path(__file__).resolve().parents[1] / "references" / "payload.txt"
digest = hashlib.sha256(payload.read_bytes()).hexdigest()[:16]
print(json.dumps({
    "status": "ok",
    "fixture": "cross-agent-checksum-v1",
    "token": f"SRI-{digest}",
}, separators=(",", ":")))
