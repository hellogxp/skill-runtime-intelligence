# E3 — Diagnostic usefulness study

`prepare_study.py` creates a deterministic, counterbalanced within-subject
study packet for raw-source versus Skill Run Panorama diagnosis. It audits
condition balance, evidence citations, and whether the first visible finding
matches the earliest gold lifecycle boundary.

The generated bundle intentionally reports `human_responses_collected: 0`.
Passing this gate means the study is ready to run; it is not evidence that the
Panorama helps people until participant correctness, time, confidence, and
false-causal-claim data are collected.

