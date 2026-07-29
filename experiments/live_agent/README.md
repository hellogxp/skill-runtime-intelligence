# Live same-Skill Agent experiment

The fixture contains one versioned project Skill with a deterministic script
and reference file. Each Agent receives the same task and a read-only
workspace. A trial passes only when:

- the final JSON exactly matches direct script execution;
- the Agent run leaves the fixture tree unchanged;
- the runtime evidence shows the Skill instructions and bundled script path;
- source, normalized, and inferred records remain separate.

Pilot runs establish harness feasibility. Paper estimates require repeated
trials with pinned Agent/model versions and paired bootstrap intervals.

