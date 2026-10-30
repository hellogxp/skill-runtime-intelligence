## What changed

Describe the user-visible behavior and why it belongs in Skill runtime
diagnosis.

## Evidence and trust boundaries

- Evidence grades or causal scope affected:
- New adapter capability or limitation:
- Privacy and redaction impact:
- Non-interference impact:

## Verification

- [ ] Tests cover the observable behavior and missing-evidence boundary.
- [ ] `python -m unittest discover -s tests -v` passes.
- [ ] Browser JavaScript syntax checks pass.
- [ ] README, event model, capability matrix, and UI copy are updated where applicable.
- [ ] No transcript, secret, raw prompt, private path, or runtime database is included.
- [ ] The change does not proxy model traffic, orchestrate the Agent, or turn missing evidence into failure.
