# Skill Runtime Intelligence experiment protocol v1

Status: active  
Protocol version: `sri-experiment-v1`  
Date: 2026-07-29

## Research claim boundary

The experiments evaluate whether a local, observational evidence layer can
reconstruct and diagnose Agent Skill runs. They do not infer hidden model
reasoning and do not claim that a Skill caused success or failure from a single
run.

Every reported item is classified as:

- **Observed**: present in a source event;
- **Derived**: deterministic transformation or relationship;
- **Inferred**: uncertain model or heuristic explanation;
- **Experimental**: estimate from controlled comparisons.

Raw source records, normalized events, relationships, inferences, and
experimental results remain separate.

## Canonical experiment IDs

| ID | Experiment | Primary claim | Completion gate |
|---|---|---|---|
| E0 | deterministic diagnosis | first observable boundary and evidence wording | 100% exact match; zero unsupported causal claims |
| E1 | adapter reconstruction | source-to-event/run reconstruction | reviewed fixture precision/recall and exact match; real-corpus results reported separately |
| E2 | non-interference/overhead | collection is fail-open and observational | identical workload outputs/control-flow digest; overhead distribution and loss/duplicate rate disclosed |
| E3 | diagnostic usefulness | panorama improves diagnosis | offline proxy reported as proxy; confirmatory participant study pre-registered before recruitment |
| E4 | cross-Agent comparability | only capability-equivalent fields are compared | field coverage and false-equivalence audit, per adapter/version |
| E5 | semantic diagnosis | inferred layer adds value above deterministic rules | evidence citations, calibration, and no mutation of Observed/Derived layers |

The older positioning notes use overlapping E numbers for market research.
Those labels are not used in result schemas; this protocol is canonical for
product and paper experiments.

## Reproducibility

Each result bundle contains the schema/protocol version, UTC timestamp, Git
revision and dirty state, environment fingerprint, immutable input digest,
adapter/model/Skill versions when applicable, configuration and seed, raw
counts, aggregate metrics, and per-case results.

Machine-specific result bundles are ignored by Git. Reviewed aggregate tables
may be committed only after checking that no prompt, secret, private source
path, or sensitive raw content is present.

## Statistical policy

- Deterministic fixture gates use exact counts, not significance tests.
- Paired stochastic trials use the same task/workspace/Skill version and
  report paired deltas with bootstrap 95% confidence intervals.
- Latency reports p50 and p95 plus absolute and relative overhead.
- Accuracy reports numerator/denominator, precision, recall, F1, exact-match,
  and breakdowns by lifecycle stage and evidence grade.
- Missing data, unsupported adapter capabilities, and collection loss are
  reported explicitly and are never imputed as successful observations.
- Exploratory analyses and post-hoc hypotheses are labeled as such.

## Current execution tiers

1. **Local deterministic**: E0, fixture E1, E2 microbenchmark, E3 offline
   proxy, E4 export-profile fixtures, and E5 baselines.
2. **Public-artifact replication**: immutable published trajectories and
   artifact verifiers, with upstream version/digest.
3. **Live stochastic**: pinned Agent/model/workspace trials on local or PAI-DSW
   infrastructure.
4. **Human study**: pre-registered tasks, randomized counterbalancing, consent,
   and de-identified responses.

Results from one tier are not promoted into claims belonging to a stronger
tier.

