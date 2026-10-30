# Research paper agenda

This document records a possible research direction. Product usefulness comes first; paper work must not delay the MVP.

## 1. Candidate research question

> How can dynamically loaded Agent Skill behavior be reconstructed and attributed across heterogeneous agent harnesses while distinguishing direct observation, deterministic derivation, uncertain inference, and experimentally measured effect?

## 2. Why a paper could be needed

A dashboard alone is not a research contribution. A paper becomes meaningful if the project develops and evaluates:

- a cross-harness Skill runtime event model;
- an evidence-grade attribution taxonomy;
- reconstruction algorithms across incomplete and changing transcripts;
- a benchmark or labeled dataset for attribution accuracy;
- controlled methods for measuring Skill marginal utility;
- empirical findings about where Skill lifecycle failures occur.

## 3. Candidate contributions

1. **Skill lifecycle event model**

   A normalized representation of discovery, activation, instruction loading, resource loading, tool execution, artifacts, and outcomes.

2. **Evidence attribution model**

   A separation between Observed, Derived, Inferred, and Experimental claims.

3. **Cross-harness adapters**

   Implementations for Claude Code and Codex, with explicit capability and observability matrices.

4. **Reconstruction evaluation**

   A labeled set of sessions measuring event recall, relationship precision, and uncertainty calibration.

5. **Empirical study**

   Characterization of silent Skill failures, missing activation, incomplete resource loading, context loss, and harness-specific behavior.

6. **Controlled effect evaluation**

   Repeated with-Skill/without-Skill trials with deterministic or independently specified verifiers.

## 4. Hypotheses

- H1: Skill lifecycle failures are not limited to non-activation; resource loading and execution boundaries contribute substantial silent failure.
- H2: Cross-source reconstruction identifies more Skill behavior than transcript-only analysis.
- H3: Explicit evidence grading reduces unsupported attribution claims without making the interface unusable.
- H4: Skill activation frequency is a poor proxy for Skill effectiveness.
- H5: The same Skill produces materially different lifecycle behavior across agent harnesses and versions.

## 5. Evaluation dimensions

### Reconstruction quality

- event precision and recall;
- parent/child relationship precision;
- artifact attribution precision;
- missing-telemetry detection;
- inference calibration.

### System quality

- collection overhead;
- indexing throughput;
- storage cost;
- adapter robustness across versions;
- privacy/redaction effectiveness.

### Human usefulness

- time to diagnose a failed Skill run;
- accuracy of developer explanations;
- usability compared with raw transcripts;
- trust calibration between observed and inferred claims.

### Skill effectiveness

- paired success-rate delta;
- token and latency overhead;
- variance across models and harnesses;
- regressions across Skill versions.

## 6. Experimental discipline

- Never infer causal Skill value from one run.
- Use matched tasks and controlled with/without conditions.
- Repeat stochastic runs.
- Prefer deterministic verifiers where appropriate.
- Report unknown and unsupported signals.
- Separate product telemetry from research datasets.
- Obtain explicit consent before collecting or publishing session data.
- Remove prompts, code, paths, credentials, and identities from shared traces.

## 7. Product-paper relationship

```text
Product need
    ↓
Runtime event model
    ↓
Useful local panorama
    ↓
Labeled reconstruction evaluation
    ↓
Empirical and methodological paper
```

The product is not required to conform to a paper narrative. The paper should describe and evaluate mechanisms that proved useful in the product.

## 8. Possible artifact

A research artifact may eventually contain:

- normalized event schema;
- adapter capability matrix;
- sanitized session fixtures;
- reconstruction benchmark;
- evaluation scripts;
- reproducible figures and tables;
- the local panorama UI.

