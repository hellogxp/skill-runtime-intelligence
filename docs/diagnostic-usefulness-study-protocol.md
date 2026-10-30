# Model-Agent diagnostic usefulness protocol

Research question: Under a pinned model and prompt protocol, does an
evidence-graded Skill Run Panorama help a diagnostic model identify the first
observable failure or evidence-gap boundary more reliably than a redacted raw
runtime view?

This protocol evaluates a product workflow for model Agents. It does not use
or require human participants, and its results must not be described as human
usability evidence.

## Design

- Each trial runs in a fresh model session with plugins and custom tools
  disabled. Prompt text is sent over stdin rather than a process argument;
  model data, config, cache, and state roots are redirected to a per-trial
  temporary directory and removed after the response.
- A trial sees one case in exactly one condition: Raw or Panorama.
- Model-session sample slots are seeded and counterbalanced so every case has
  approximately equal exposure to both conditions.
- Gold labels never enter the model prompt.
- The response is a bounded JSON object containing the first-boundary answer,
  confidence from 0–100, a causal-evidence boolean, and a short evidence
  reference. Chain-of-thought is neither requested nor stored.
- The report records provider, exact model ID, CLI version, prompt digest,
  condition, order, response status, latency, answer, correctness,
  confidence, unsupported causal claim, and a one-way session-ID digest.
- Repeated sessions of one model are stochastic samples. They are not
  independent people and are not independent model families.

The initial two-slot/22-trial run is an exploratory pilot. Replication uses
more sample slots and at least one additional model family before any
cross-model claim.

## Model task

For each case the model must:

1. identify the earliest lifecycle boundary that failed or lacks expected
   evidence before later activity;
2. state whether the evidence proves the Skill caused the final outcome;
3. rate confidence from 0–100.

“No evidence observed” must not be treated as proof that an action did not
occur.

## Outcomes

- Primary: correct first-boundary identification.
- Secondary: structured-response completion, unsupported causal conclusion
  rate, confidence calibration, and condition-specific latency.
- Exploratory: matched-case win/tie/loss direction and failure families.

Latency is provider/model/CLI-specific system behavior, not developer
time-to-diagnosis. The Raw/Panorama difference is an information-interface
comparison under the pinned protocol. A single pilot does not establish a
general causal product effect.

## Completion and claim boundary

A pilot integrity gate requires:

- every planned trial to produce a valid structured response;
- a unique fresh session for every completed trial;
- zero unsupported causal claims.

A failed integrity gate remains a valid reported result but cannot be promoted
to a confirmatory usefulness claim. Model-family replication additionally
requires pinned model identities, the same immutable corpus, per-model
breakdowns, and no pooling that hides heterogeneous failures.
