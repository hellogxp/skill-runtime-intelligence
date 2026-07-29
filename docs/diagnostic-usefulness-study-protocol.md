# Diagnostic usefulness participant protocol

Research question: Does an evidence-graded Skill Run Panorama help a developer
identify the first observable failure or evidence-gap boundary more accurately
and quickly than a redacted raw runtime view?

## Design

- Within-subject, counterbalanced raw/Panorama conditions.
- Each participant sees each case once.
- Case order is seeded and randomized; condition allocation is balanced per
  case.
- The evaluator records the first-boundary answer, correctness, elapsed time,
  confidence from 0–100, and whether the explanation makes an unsupported
  causal claim.
- Gold labels remain hidden until the response is submitted.

The initial 24 slots are an exploratory pilot, not a powered confirmatory
sample. A confirmatory sample size will be selected from the pilot variance
and effect estimate before inspecting confirmatory outcomes.

## Participant task

For each case:

1. Identify the earliest lifecycle boundary that is failed or lacks expected
   evidence before later activity.
2. State whether the evidence proves the Skill caused the final outcome.
3. Rate confidence from 0–100.

“No evidence observed” must not be treated as proof that an action did not
occur.

## Primary and secondary outcomes

- Primary: correct first-boundary identification.
- Secondary: diagnosis time, confidence calibration, and unsupported causal
  conclusion rate.
- Exploratory: which evidence link or next action participants use first.

Report all exclusions, missing responses, and case-level results. Do not merge
pilot and confirmatory estimates without labeling the analysis exploratory.

