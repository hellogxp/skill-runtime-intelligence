---
name: boundary-probe-skill
description: Executes the declared deterministic boundary probe and returns its exact JSON result.
---

# Boundary Probe Skill

For the experiment task:

1. Run the exact command named in `task.txt` from the repository root.
2. The command can intentionally exit non-zero. This is expected evidence.
3. Return only the single JSON object printed by the command, even when its exit code is non-zero.
4. Do not read the probe implementation and do not calculate its token yourself.
5. Do not modify any file.
