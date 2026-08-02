# Native performance phase protocol

Status: exploratory protocol derived from the v0.1.6 native sender studies.

## Purpose

Native launch measurements can change across invocation position, run, path,
artifact, and host state. This protocol prevents a pooled latency statistic
from being presented as a stable product property before the underlying phases
are supported by evidence.

## Evidence record

Every measurement must retain:

- raw trial and monotonic duration;
- run identifier and within-run position;
- artifact digest and final executable path identity;
- operation and realized-state manipulation checks;
- success/failure output contract;
- host/platform identity at a privacy-safe granularity;
- measurement window and declared first-use/washout boundary;
- evidence grade and explicit unsupported claims.

The collector must preserve raw trials separately from phase labels and
aggregates. A phase label is Derived unless its boundary is directly supplied
by a verified external mechanism.

## Readiness states

`Integrity only` means the raw trials or manipulation checks are incomplete.

`Descriptive ready` requires raw trials, passed correctness and manipulation
checks, explicit run boundaries, and balanced within-run position. Results may
describe phase-preserving associations but not steady-state or causal effects.

`Confirmatory ready` additionally requires a justified sample size, stable
privacy-safe host identity, independent environment replication, and an
analysis capable of establishing or rejecting a steady-state assumption.
Current native launch results are not confirmatory ready.

A host identity must not be derived from hostname, user, MAC address, or
hardware serial. The candidate contract uses a local UUIDv4 secret stored with
0600 permissions and exports only a scope-specific HMAC alias. Different
export/study scopes receive different aliases. Rotation and consent remain
separate product requirements.

## Analysis rules

1. Show run- and phase-level summaries before any pooled statistic.
2. Do not discard early observations merely because they are slow.
3. Do not assume that warmup exists, ends once, or reaches peak performance.
4. Treat direction reversal and large between-run shifts as evidence against a
   single stationary aggregate.
5. Report change points only when the sequence length and method support them;
   otherwise report that steady state was not established.
6. Bind prewarm evidence to artifact digest, final path, host context, and time.
7. Keep latency thresholds separate from correctness and non-interference
   gates.

## Research basis

Barrett et al. show that benchmark runs should not be assumed to reach a
steady state and use changepoint analysis to distinguish warmup outcomes:
[Virtual Machine Warmup Blows Hot and Cold](https://arxiv.org/abs/1602.00602).

Kalibera and Jones model multiple levels of experimental repetition and
recommend reporting effect uncertainty rather than relying on flat repeated
iterations:
[Rigorous Benchmarking in Reasonable Time](https://kar.kent.ac.uk/33611/).

Mytkowicz et al. demonstrate that innocuous setup details can bias performance
conclusions and motivate randomized setup and explicit bias detection:
[Producing Wrong Data Without Doing Anything Obviously Wrong](https://sape.inf.usi.ch/publications/asplos09.html).

These works concern broader systems and managed-runtime benchmarking. They
support the methodology, not a claim that the native sender's observed phase
shift has the same mechanism.
