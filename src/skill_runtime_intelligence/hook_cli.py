"""Minimal fail-open process boundary for latency-sensitive Agent hooks."""

import json
import sys
from pathlib import Path
from typing import Dict, List

from .event_queue import DEFAULT_COLLECTOR_ENDPOINT, deliver_or_queue
from .hook_adapter import (
    HOOK_EVENT_TYPES,
    SUPPORTED_HOOK_AGENTS,
    build_hook_envelopes,
)


MAX_HOOK_INPUT_BYTES = 1024 * 1024


def _arguments(argv: List[str]) -> Dict[str, str]:
    result = {
        "agent": "",
        "event": "",
        "endpoint": DEFAULT_COLLECTOR_ENDPOINT,
        "event_queue": "",
        "timeout_ms": "150",
    }
    keys = {
        "--agent": "agent",
        "--event": "event",
        "--endpoint": "endpoint",
        "--event-queue": "event_queue",
        "--timeout-ms": "timeout_ms",
    }
    index = 0
    while index < len(argv):
        key = keys.get(argv[index])
        if key and index + 1 < len(argv):
            result[key] = argv[index + 1]
            index += 2
        else:
            index += 1
    return result


def main(argv=None) -> None:
    """Read one hook payload, deliver or queue it, and never affect the Agent."""
    try:
        arguments = _arguments(list(sys.argv[1:] if argv is None else argv))
        agent = arguments["agent"]
        event = arguments["event"]
        if agent not in SUPPORTED_HOOK_AGENTS or event not in HOOK_EVENT_TYPES:
            return
        raw = sys.stdin.buffer.read(MAX_HOOK_INPUT_BYTES + 1)
        if not raw or len(raw) > MAX_HOOK_INPUT_BYTES:
            return
        payload = json.loads(raw)
        envelopes = build_hook_envelopes(agent, event, payload)
        queue_value = arguments["event_queue"]
        try:
            timeout_seconds = max(0.01, int(arguments["timeout_ms"]) / 1000)
        except (TypeError, ValueError):
            timeout_seconds = 0.15
        deliver_or_queue(
            envelopes,
            endpoint=arguments["endpoint"],
            queue_path=Path(queue_value).expanduser() if queue_value else None,
            timeout_seconds=timeout_seconds,
        )
    except Exception:
        return


if __name__ == "__main__":
    main()
