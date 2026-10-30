# E1 — Adapter reconstruction golden corpus

This benchmark materializes de-identified Codex JSONL sources from reviewed
scenario specifications, runs the production `CodexAdapter`, and scores three
claims separately:

- SkillRun identity, activation mode, evidence grade, and terminal status;
- Skill-specific normalized events and their evidence grades;
- active-scope attribution of tool events.

Run:

```bash
PYTHONPATH=src python3 experiments/adapter_reconstruction/run_benchmark.py
```

The fixtures deliberately include path/name collisions, malformed input,
interruptions, active-scope inheritance, and two Skills in one turn. These are
adapter-unit golden cases, not a substitute for independently double-labeled
real transcripts.

