# Skill Runtime Intelligence experiment report

Date: 2026-07-29  
Protocol: `sri-experiment-v1`  
Status: local gates complete; confirmatory cross-Agent and human studies active

## Executive result

The current evidence supports a narrower and stronger product claim:

> Skill Runtime Intelligence can reconstruct and diagnose observable Skill
> lifecycle evidence without taking over the Agent, while explicitly separating
> observed facts, deterministic relationships, uncertain explanations, and
> controlled experimental outcomes.

It does **not** yet support claims that the Panorama improves human diagnosis,
that collection has negligible end-to-end latency, or that a Skill caused an
outcome across general tasks.

## Completed results

| Experiment | Result | Evidence strength |
|---|---|---|
| E0 deterministic diagnosis | 14/14 exact; Precision/Recall/F1 1.0; zero unsupported causal claims | reviewed synthetic fault corpus |
| E1 Codex reconstruction | 10/10 exact; 18 TP, 0 FP, 0 FN after fixes | de-identified golden fixtures |
| E2 paired collector microbenchmark | 2,400/2,400 events accepted; zero input/output mutation, loss, or duplicates | isolated local paired trials |
| E2 transport fast path | 640/640 events accepted across eight balanced runs; 7/8 latency gates passed; pooled shell p50 45.1 ms, p95 78.6 ms, p99 128.4 ms, max 204.8 ms; silent with zero exit failures | 8 × 40 balanced local process trials per condition; Experimental, with Derived aggregate |
| E2 contention integrity | 320/320 events accepted across forward/reverse load schedules; silent with zero exit failures; latency hypothesis did not replicate consistently | 2 × 5 local segments with 16 balanced trials per condition; Experimental |
| E2 Linux `nc` fallback | 80/80 events accepted across two runs; p50 2.0–2.8 ms, p95 6.0–6.1 ms; incremental p50 1.2–2.0 ms, p95 4.4–5.5 ms; silent with zero exit failures | 2 × 40 paired trials in one digest-pinned Linux/arm64 container; Experimental |
| E3 study readiness | 11 cases, 24 balanced participant slots, 264 assignments; first-visible-boundary and evidence-citation audits 1.0 | study-material audit; zero human responses |
| E4 export-profile equivalence | 6/6 profiles exact; comparable-field coverage 1.0; zero dangling parents after fix | equivalent synthetic export fixtures |
| E5 diagnosis representation ablation | rules exact 1.0/F1 1.0; lexical retrieval exact 0.214/F1 0.414; lifecycle-feature retrieval exact 0.071/F1 0.080; ordered relational templates exact 0.929/F1 0.963 | leave-one-out synthetic corpus; retrieval outputs Inferred |
| Real-run corpus readiness audit | privacy-safe aggregate gate passed in four audits; snapshots contained 97, 75, 77, and 77 SkillRuns and every audit passed only 1/7 readiness criteria; v3 added integrity-checked snapshot/schema/aggregate fingerprints | query-only consistent snapshots of one local Codex database; Derived aggregate, zero row-level records |
| Dataset cut-policy pilot | across three three-snapshot trials, pooled next-window stability was 222/240 all-observed, 205/216 terminal-status, 215/230 30-second watermark, and 188/206 prior-quiescence selections | one local live database; Experimental observational time series, non-independent run observations |
| Collection-checkpoint capability and mechanism | pre-deployment live runtime exposed 3/7 capabilities; post-deployment audit exposed 7/7, then a real completed epoch recorded one late arrival and a later retry completed with zero; isolated trials detected 8/8 modified and 8/8 newly created sources with 0/8 control false positives | query-only live snapshots (Derived), aggregate live epoch state (Observed), and controlled synthetic-adapter trials (Experimental); no row-level records |
| Production Codex watch epoch | pre-fix deletion boundary advanced 0/3; post-fix create, append, and delete paths each advanced 3/3, removal count was exact 3/3, historical sessions were retained 3/3, and watcher cleanup passed 3/3 | production Codex adapter/watch loop over isolated synthetic transcripts; Experimental mechanism evidence |
| Mixed provenance reconciliation | official-hook raw/event/run evidence survived transcript refresh 8/8 and correlation groups remained intact 8/8; cross-source relationship edges were available 0/8 | production adapter and collector over isolated synthetic correlated sources; Experimental, privacy-safe aggregate |
| Packaged product lifecycle | 6/6 post-fix isolated wheel runs completed install/start/status/doctor/stop/uninstall; latest 3/3 also verified native prewarm; project and Agent configs unchanged; state fully removed | six local packaged-product runs; Experimental |
| Live Codex reconstruction | 3/3 verified outcomes, unchanged workspaces, sessions, SkillRuns, instruction events, and resource events | real Codex 0.145.0 / GPT-5.6-sol, deterministic task |

The latest low-load-window reproducibility suite passed 7/7 selected local
experiment gates. Across all eight comparable transport runs, however, the
performance gate passed only 7/8; the Wilson 95% interval for the run-level
pass rate is 0.529–0.978. The latest expanded product unit/integration suite
passed 93/93 tests, including privacy-safe real-corpus audit, drift,
cut-policy, curve-summary, collection-epoch, and capability-audit tests,
lifecycle ownership safeguards, 15-locale catalog integrity, hooks,
Collector, OTLP export, storage, comparison, and deterministic diagnosis.
A local source distribution and wheel also built successfully; the
installed-wheel smoke test found all required native-source and web assets.

The live Codex trials had wall-time p50 23.04 s and p95 24.55 s. Input-token
p50 was 51,705 and p95 was 52,255; about 42,240 tokens per trial were reported
as cached. These counts include runtime context beyond the target Skill and
must not be attributed to the Skill alone.

## Defects discovered by experiments

### 1. Boundary-insensitive identity matching

Path-prefix and Skill-name-prefix fixtures produced false attribution:
`pdf-backup` could be assigned to `pdf`. Matching now respects path and
identifier boundaries. Both adversarial cases remain in E1.

### 2. Relative Skill resources were invisible

The real Codex pilot loaded `SKILL.md` with an absolute path but executed the
bundled script with a path relative to the session working directory. The
adapter attributed the tool through active scope but initially omitted
`resource.executed`. It now resolves paths relative to the observed session
cwd, and both the real session and a new fixture reconstruct the script event.

### 3. Correct nodes could still form an incorrect graph

Before the E4 fix, all six profile adapters emitted the expected event nodes
but produced 18 dangling parent references. Parent IDs had been constructed
using a fixed `runtime.span.started` type even when the normalized parent was
`skill.activated` or `tool.started`. E4 now scores graph-edge validity
separately; all six profiles have zero dangling parents.

### 4. Severity sorting hid the first lifecycle boundary

The E3 readiness audit initially achieved only 10/11 first-visible-boundary
accuracy. A later execution error was displayed before an earlier resource
evidence gap because severity outranked lifecycle order. Findings now sort by
lifecycle stage first and severity second; the audit is 11/11.

### 5. Hook process startup required a different transport

The enabled in-process path now adds p50 16.7 ms and p95 18.4 ms per batch of
80 events. The standalone Python fail-open/queue path has p50 129.1 ms and p95
217.5 ms. It is therefore retained for offline durability, not used as the
active-runtime fast path.

The new native Unix-socket sender delivered 640/640 events across eight
balanced runs. The local benchmark jointly balanced condition position and
baseline/actual measurement order in four-run blocks. Direct invocation
pooled p50 was 21.2 ms, p95 44.7 ms, p99 549.8 ms, and max 645.8 ms. The real
shell-command shape had pooled p50 45.1 ms, p95 78.6 ms, p99 128.4 ms, and max
204.8 ms. Both paths were silent with zero nonzero exits. Seven of the eight runs
passed the predeclared 100 ms shell p95 and 75 ms shell incremental-p95 gate.

A preceding blocked-order run failed the predeclared direct p95 gate at
109.6 ms, and the first native invocation in the balanced runs reached
409.8–601.4 ms. Excluding the first five trials only as a diagnostic—not as
the gate—reduced direct p95 to 24.6–51.2 ms. The cross-run aggregate made the
split sharper: all eight first direct trials exceeded 100 ms, with median
532.3 ms, while the pooled post-first-five direct p99 was 69.8 ms. This
supports a split between
steady-state transport overhead and cold process-launch behavior; it does not
support “negligible worst-case latency” or cross-platform generalization.

Two explicit prewarm runs moved 440–511 ms of fresh-binary execution cost into
installation. After prewarm, direct first-five maxima were 42–66 ms, and both
unchanged performance/integrity gates passed. The installer now performs the
same silent missing-socket prewarm once. Two packaged-wheel lifecycle runs
verified that prewarm completed in 428–443 ms during installation. This is
promising local mechanism evidence, not a cross-platform causal estimate.

The same experiment exposed a database-initialization race between the ingest
thread and observers opening SQLite. The bridge now initializes schema and WAL
mode before accepting clients. The previously failing native-sender test then
passed in 10/10 repeated runs and in the 41-test suite.

#### Contention follow-up

Two exploratory contention schedules delivered 320/320 events without sender
failures or output under bounded CPU, I/O, and mixed workers. Integrity held,
but the latency hypothesis did not replicate consistently. In the forward
schedule, shell p95 ratios to pooled idle were 1.05× for CPU, 1.92× for I/O,
and 0.86× for mixed load. In the reverse schedule they were 2.19×, 1.43×, and
1.46× respectively.

More importantly, pooled-idle shell p50 changed from 9.3 ms to 91.7 ms between
the two runs, while pooled-idle p95 changed from 15.7 ms to 265.6 ms. The host
later reported a one-minute load of 19.29 on 12 logical CPUs. Version 2 now
records ambient load and refuses to launch stress workers above a predeclared
0.75 load-per-CPU safety limit. The first guarded attempt was therefore
recorded as `not_run`, not as a failed or completed experiment. These results
support lossless delivery under the two observed schedules, but not a stable
contention latency estimate.

#### Linux fallback replication

The OpenBSD-netcat fallback was executed twice inside the cached Linux/arm64
image
`gcr.io/k8s-minikube/kicbase@sha256:fd2d445ddcc33ebc5c6b68a17e6219ea207ce63c005095ea1525296da2d1a279`.
It delivered 80/80 events without output or nonzero exits. Actual shell p50 was
2.0–2.8 ms and p95 was 6.0–6.1 ms; paired incremental p50 was 1.2–2.0 ms and
p95 was 4.4–5.5 ms.

This is evidence for the Linux `nc` fallback only. The read-only source mount
and explicit result mount make the run reproducible without network
installation, but the image has no C compiler, so it does not close the native
Linux fast-path gap.

### 6. Tool call IDs were not globally unique

The first transport benchmark accepted exactly half its events despite zero
sender failures. The two conditions reused tool call IDs in different
sessions, exposing that hook event identity was scoped only to the call ID.
Event identity now includes the Agent session identity. A cross-session
regression fixture and the transport gate preserve the fix.

### 7. Platform-specific `nc` flags were unsafe

The fallback command assumed OpenBSD/Linux `nc -N` semantics. On Apple `nc`,
`-N` requires a different argument and all invocations failed. Installation
now prefers the native sender and does not configure the incompatible `nc`
branch on Darwin. The Python queue path remains the offline fallback.

### 8. Runtime ownership cannot trust a mutable marker

The managed-process record initially accepted its own `marker` field as the
process-identity predicate. A locally modified record could therefore make an
unrelated process appear managed. Stop verification now requires the exact
state-record version, the fixed product marker, and the expected
`python -m skill_runtime_intelligence start --foreground` command shape. A
tampered-marker regression test preserves the refusal behavior.

### 9. Source-path leakage can invalidate a wheel smoke test

The first structured packaged-lifecycle attempt inherited `PYTHONPATH=src`.
Pip returned success because the checkout metadata made the package appear
available, but it installed no console entry point into the temporary virtual
environment. The experiment correctly failed before product startup. The
runner now removes `PYTHONPATH` and forces wheel reinstallation. Three subsequent
runs completed every lifecycle step, built the native sender from packaged
source while offline, left the fixture project and isolated Agent
configuration unchanged, and removed all product state.

### 10. Flat lifecycle similarity does not recover relational diagnosis

E5 added a leave-one-out nearest-case baseline over run status, completeness,
observed/failed/unsupported stages, event types, and event stages. After
correcting the similarity implementation so that two empty sets count as
agreement, the baseline still achieved only 1/14 exact matches, with precision
0.091, recall 0.071, and F1 0.080. The lexical baseline remained stronger at
3/14 exact and F1 0.414; deterministic lifecycle rules remained 14/14 exact on
this reviewed synthetic corpus.

The error pairs expose distinctions that flat set similarity cannot represent:
Observed versus Derived failure grades, an absent stage with versus without
later evidence, and the earliest failure when several failures are present.
This negative ablation supports preserving ordered, typed lifecycle relations
in the product and testing graph-aware or relational diagnosis before adding a
semantic explanation model. It does not establish performance on real failures
or show that deterministic rules will generalize beyond this small corpus.

A follow-up leave-one-out baseline extracted four predefined ordered relation
types without assigning finding codes, learned code templates from the other
13 cases, and rebound selected templates to the query relation's stage and
evidence grade. It reached 13/14 exact matches, precision 1.0, recall 0.929,
and F1 0.963. The only miss was the sole positive
`reported_outcome_without_verifier` case: after holding it out, no training
case contained that relation's finding code, and the conservative baseline
emitted nothing rather than inventing a label.

The contrast is useful but narrow. Ordered relations and template coverage
matter substantially more than flat similarity on this corpus. However, the
relation anchors closely mirror production rule predicates, so 13/14 is not
independent semantic intelligence and cannot estimate real-run generalization.
The remaining miss gives a concrete corpus-design criterion: each relation
type needs multiple independently labeled positive examples before
leave-one-out semantic or template evaluation is identifiable.

### 11. An interrupted lifecycle harness can leave an unowned runtime

A read-only process audit found one isolated packaged-lifecycle runtime still
listening on loopback more than two hours after its parent exited. The command
line pointed only to a temporary experiment home and port, and the process had
been reparented to PID 1. Its temporary runtime ownership record was already
absent, so the normal guarded `stop` command correctly refused to treat it as a
managed process. After resolving the exact PID and command, the experiment
process was terminated explicitly and the listener disappeared.

This observation does not invalidate the six completed lifecycle reports:
each of those reports recorded a successful stop and no running process. It
does expose a separate interrupted-harness failure mode. The experiment runner
needs a cleanup ledger outside its disposable directory and a scoped orphan
audit. The product must not weaken process-ownership checks or broadly kill
matching Python processes to compensate.

The next isolated wheel run passed all lifecycle gates with native prewarm at
404.9 ms. Its durable cleanup ledger was removed after verified stop, and a
post-run process audit found no temporary listener. This validates the normal
cleanup path once; crash-recovery behavior still requires a controlled
interruption experiment.

### 12. Mixed provenance is preserved but not relationally merged

Immediately before the live checkpoint deployment restart, the runtime
reported 56 sessions, 46 Skills, 17,122 normalized events, and 90 SkillRuns.
The post-restart initial index reported the same 56 sessions and 46 Skills but
12,740 normalized events and 86 SkillRuns. This is Observed aggregate drift
across one restart, not a causal estimate.

Initial code-path audit raised a Derived hypothesis that transcript
`replace_session` might cascade-delete official-hook evidence. A closer audit
showed that collector normalization creates a source-scoped internal session
ID from adapter, collection mode, and source session ID. Transcript and hook
records therefore occupy distinct session rows with a shared
`correlation_key`.

Eight isolated mixed-provenance trials then appended one official-hook event
and refreshed the correlated transcript. Hook raw, event, run, and session
records survived 8/8, and the two source sessions retained one correlation
group 8/8. This falsifies the proposed hook-erasure mechanism for the exercised
current path. The earlier aggregate restart drift remains Observed but
unexplained; it must not be attributed to hook deletion.

The experiment also found a narrower product gap: cross-source relationship
edges were present 0/8. Evidence is preserved and grouped, but the lifecycle
graph remains source-local. A future correlation layer should connect
source-scoped views without collapsing raw identity or inventing causal
parent/child order across sources.

## Real runs are not automatically a diagnosis corpus

A privacy-safe audit copied the live SQLite database through SQLite's backup
API, removed the snapshot after analysis, and emitted only aggregate
schema-level counts. The current runner enforces `PRAGMA query_only=ON`; on a
live WAL database SQLite may still create locking sidecars, so it does not
claim an OS-level read-only open. Its privacy gate passed: the report contains no run,
session, or Skill IDs; no names, prompts, summaries, paths, timestamps,
payloads, source locators, or row-level records.

The snapshot contained 97 Codex SkillRuns from 16 sessions and 11 Skill
definitions. All 97 runs had Derived activation evidence gaps, 51 had Derived
unverified-outcome findings, and 46 had Observed incomplete-run findings.
There were only three distinct finding signatures and two finding
combinations. No run contained an owned `skill.activated` or
`outcome.verified` event, no run produced a `runtime_failure` candidate, and
none had a human-reviewed label.

Only the minimum-run-count heuristic passed; six diversity, coverage, and
label criteria failed. These thresholds were defined after an initial
aggregate inspection and are exploratory, not preregistered power criteria.
The result nevertheless exposes a product and dataset-design problem:
randomly sampling available real runs would mostly reproduce one adapter
blind spot instead of testing diagnosis generalization. Corpus construction
must stratify by adapter capability, relation type, explicit failure, outcome
verification, and human label—not merely by run count.

A second snapshot after the runtime restart contained 75 SkillRuns from 15
sessions and 9 Skill definitions. Compared with the first audit, run count
changed by -22 (-22.7%), session count by -1, and Skill-definition count by
-2. Finding-signature types and readiness remained unchanged, but their counts
fell by 22 activation gaps, 13 unverified outcomes, and 9 incomplete runs.
This establishes aggregate population drift between these two snapshots; it
does not identify which records changed or whether restart, re-indexing, source
availability, or retention caused the difference. A research dataset must
therefore freeze an immutable snapshot plus manifest instead of treating the
live derived index as a stable corpus.

The second snapshot contained 150 run-level Finding occurrences but only three
adapter/signature groups. Grouping by adapter and signature would reduce the
candidate items by 98% (50 occurrences per group), and one activation-gap
signature covered 100% of runs. This is a Derived opportunity for an
adapter-level coverage summary—not evidence that notification grouping improves
human diagnosis. The human study must compare grouped versus per-run
presentation before it becomes default UX.

The v3 audit added integrity-checked SHA-256 fingerprints for the exact
temporary snapshot, SQLite schema, and privacy-safe aggregate. Two consecutive
audits 1.5 seconds apart both contained 77 runs, 15 sessions, nine Skill
definitions, 154 Finding occurrences, and unchanged Finding/readiness counts.
Nevertheless, their exact snapshot and full aggregate fingerprints differed:
the second snapshot contained one additional Observed `tool.started` event.
The schema fingerprint remained identical.

This short-window pair is Derived evidence that stability is layered. A
run-level diagnosis population can remain unchanged while an active run keeps
accruing events. Dataset export therefore needs an explicit cut policy
(terminal sessions, bounded watermark, or quiescence interval), an immutable
snapshot, and a manifest. The pair does not estimate a general drift rate, and
the fingerprints do not replace retaining an access-controlled snapshot for
independent re-analysis.

## Dataset cut policy: terminal is not immutable

Three repeated pilots took snapshots A, B, and C approximately 2.2 seconds
apart. Snapshot B selected runs under four policies; snapshot C measured
whether the selected private run fingerprints changed. Reports emitted only
aggregate counts and rates, and all three privacy/integrity gates passed.

| B selection policy | Pooled selected | Stable at C | Changed at C | Stable fraction |
|---|---:|---:|---:|---:|
| all observed | 240 | 222 | 18 | 92.5% |
| terminal status | 216 | 205 | 11 | 94.9% |
| 30-second event watermark | 230 | 215 | 15 | 93.5% |
| unchanged from A to B | 206 | 188 | 18 | 91.3% |

Terminal status had the highest pooled short-window stability in this pilot,
but 11 of 216 selected observations still changed. Prior two-second
quiescence retained fewer observations and did not improve pooled stability;
in one trial all 80 B runs had been unchanged from A, yet 16 changed by C.
This is a useful negative result: `completed`, `failed`, or `interrupted`
describes reconstructed run state, not an immutable research-data boundary,
and a brief quiet interval does not reliably predict the next quiet interval.

These pooled observations are repeated views of one local database, not
independent participants. The policies were deterministic rather than
randomized, and the experiment does not estimate causal policy effects or
source completeness. Product export should keep runtime status separate from
dataset freeze state, require an adapter collection checkpoint plus immutable
snapshot manifest, and expose late-arrival revisions explicitly.

A three-trial composite follow-up added terminal-plus-watermark and
terminal-plus-watermark-plus-prior-quiescence policies. The observed window was
quiet: all 246 all-observed selections remained unchanged. Terminal and
terminal-plus-watermark selected exactly the same 231 pooled observations,
while the three-condition policy selected 219 (mean retention 89.0% versus
93.9%) with no measurable stability advantage in this window. This negative
result makes the benefit unidentifiable rather than showing the composite is
ineffective. Future trials must span ingestion bursts, restart/re-index
boundaries, and longer outcome windows; otherwise additional gates mainly
discard data.

A six-trial observational wait curve then repeated the protocol twice at
requested 1-, 3-, and 8-second intervals:

| Policy | 1 s pooled stability | 3 s pooled stability | 8 s pooled stability |
|---|---:|---:|---:|
| all observed | 171/176 (97.2%) | 156/176 (88.6%) | 156/176 (88.6%) |
| terminal status | 161/166 (97.0%) | 148/166 (89.2%) | 148/166 (89.2%) |
| prior quiescence | 135/140 (96.4%) | 120/140 (85.7%) | 130/150 (86.7%) |

Longer observed quiet time did not monotonically improve subsequent stability.
Within each interval condition one trial could be fully stable while the other
contained 5 or 20 changed run fingerprints. The conditions were sequential,
not randomized, so ambient ingestion load is confounded with interval and the
curve is not a causal waiting-time estimate. The recurring batch-shaped changes
still expose a product requirement: wall-clock silence is an advisory signal,
not a collection checkpoint. Reproducible export needs an adapter/index epoch,
source high-water mark, and explicit late-arrival accounting.

## Collection-checkpoint capability audit

A pre-deployment query-only audit of a consistent live database snapshot found three of seven
required capabilities: a global monotonic revision, revision update timestamp,
and completed-import digest. It did not find a collection-epoch identifier,
running/completed epoch state, source high-water mark, or late-arrival counter.
The audit therefore reported `freeze_checkpoint_available=false`. It emitted
only schema and runtime-state category counts; no keys, paths, endpoints,
identifiers, or row-level records were exported.

This is Derived evidence about schema capability, not proof of collection
correctness or source completeness. It also confirms that the existing global
revision cannot delimit a multi-session watcher batch: a reader can observe a
valid revision while the watcher is between two session replacements.

A minimal local prototype now records a versioned collection epoch with
`running`, `completed`, and `failed` states; a SHA-256 source watermark;
processed/failed source counts; and explicit late-arrival count. Six focused
tests and the 84-test full suite passed, including an isolated changed-source
batch that ended in `completed`. This is engineering verification in a
temporary database, not a live-runtime experiment. The deployed live runtime
was subsequently restarted with the prototype.

An 8-pair controlled mechanism follow-up then mutated one source after the
epoch boundary while leaving its paired control unchanged. All eight injected
mutations changed the source watermark and produced `late_arrival_count=1`;
all eight controls retained their watermark and produced zero. The adapter
observed `running` during all 16 parse calls and the persisted state was
`completed` afterward. Four additional unexpected-error trials propagated the
error while persisting `failed` with an exact failed-source count. The
privacy-safe aggregate gate passed.

Code-path audit showed that the first implementation rechecked only paths
present at epoch start, leaving a newly created source outside its accounting
boundary by construction. The watcher now
re-enumerates eligible adapter sources after the batch and compares the union
of the before/after boundaries. Eight additional controlled creations were
then detected 8/8. This closes the exercised new-source gap, but does not prove
that a live adapter enumerates every upstream source.

These are Experimental mechanism results from temporary databases and a
synthetic adapter. Repetition checks deterministic implementation consistency;
the trials are not independent workload samples, do not estimate natural
late-arrival frequency, and do not validate the undeployed live watcher. The
result supports using a positive late-arrival count to invalidate a candidate
freeze, not interpreting the count as a quality or effectiveness score.

### Production Codex watcher: source removal is a boundary, not erasure

Three isolated trials then exercised the production `CodexAdapter` and
continuous watch loop rather than the controlled adapter. Initial transcript
ingestion and appended completion records were reconstructed 3/3, with the
collection epoch advancing in every case. Deleting the transcript exposed a
negative result: the pre-fix epoch advanced 0/3 and the indexed historical
session remained present 3/3.

The watcher now treats source disappearance as a collection-boundary change,
records `removed_source_count`, and advances an otherwise empty epoch. It does
not delete historical reconstructed evidence. In three post-fix trials,
deletion advanced the epoch 3/3, the removal count was exactly one 3/3,
historical sessions remained present 3/3, and all three watcher subprocesses
were cleaned up. Both privacy-safe aggregate gates passed.

This is Experimental mechanism evidence from synthetic transcripts in
temporary databases. It does not estimate live Codex deletion frequency or
prove upstream completeness. It establishes a product-state distinction:
source availability can change while historical observed/derived evidence
remains retained. Export and UI must disclose that distinction instead of
equating missing source, deleted history, and incomplete evidence.

### Live checkpoint convergence after deployment

After the production Codex watch gates and the 93-test suite passed, the local
development runtime was gracefully restarted with the current source. A new
query-only audit found all 7/7 checkpoint capabilities and
`freeze_checkpoint_available=true`. This is Derived schema-capability evidence,
not proof that every completed epoch is freeze-ready.

The active runtime then produced epoch 10 with status `completed`: two changed
sources were processed, zero failed, and one late arrival was recorded.
Because a positive late-arrival count invalidates a candidate freeze, this
epoch was not treated as stable. The watcher naturally retried changed input;
epoch 14 later completed with one processed source, zero failures, and zero
late arrivals. Both records are Observed aggregate runtime state. They are a
single local sequence, not a causal estimate or field failure-rate sample.

The sequence changes the product model from a one-shot checkpoint to a
convergence protocol:

1. `running` means the boundary is being processed;
2. `completed` with late arrivals means catch-up is still required;
3. `completed` with zero late arrivals is only a candidate freeze boundary;
4. an immutable snapshot and manifest are still required to declare a dataset
   revision frozen.

## New exploratory direction: Skill catalog footprint

A one-trial-per-condition Codex pilot kept the target Skill fixed and added 0,
8, or 32 non-applicable project Skills:

| Added distractors | Input tokens | Wall time | Correct target/result |
|---:|---:|---:|---|
| 0 | 51,626 | 21.71 s | yes |
| 8 | 53,404 | 23.76 s | yes |
| 32 | 56,531 | 23.72 s | yes |

The endpoint slope was approximately 153 additional input tokens per added
Skill. Outcome and target selection stayed correct in all three exploratory
conditions, while wall time was noisy. Because there is only one trial per
condition and global context remains uncontrolled, this is a hypothesis
generator, not a final estimate.

The resulting research question is:

> How do Skill catalog cardinality, description length, semantic overlap, and
> progressive disclosure jointly affect prompt footprint, activation
> precision, resource uptake, latency, and task outcome?

This direction supports both the open-source product (a catalog-footprint and
collision diagnostic) and the paper (a controlled activation/uptake study).

## Relationship to current research

SkillsBench shows that Skill gains vary substantially by configuration, that
some tasks have negative lift, and that larger Skill bundles are not
automatically better. Its public trajectories and paired-trial design are a
natural external benchmark for our runtime evidence layer:
[SkillsBench](https://arxiv.org/abs/2602.12670).

Skill Coverage argues that task success alone does not establish whether
specified Skill behavior was exercised. Its applicability-plus-expected-
behavior constraints suggest the missing bridge between our lifecycle
evidence and outcome verification:
[Skill Coverage](https://arxiv.org/abs/2606.20659).

SkillJuror reports that progressive disclosure changes resource uptake before
or even without changing final task outcome. This motivates treating
activation, instruction loading, resource uptake, behavior coverage, and
verified outcome as separate dependent variables:
[SkillJuror](https://arxiv.org/abs/2606.11543).

The execution-provenance literature motivates a typed graph rather than a flat
event list and highlights semantic provenance, privacy, and trace-benchmark
gaps that the current results also expose:
[Execution provenance survey](https://arxiv.org/abs/2606.04990).

The public Skill Coverage artifact was independently executed offline in this
environment. It reproduced 359 human-label checks, 38.66%–45.51% retained
behavior coverage across five Agent/model rows, and the reported
coverage-guided recovery summaries. The artifact omits raw trajectories, so it
supports aggregate replication but not our source-to-event adapter evaluation.

## Paper framing

The strongest paper contribution is not another success-rate benchmark. It is
an evidence architecture and evaluation methodology:

1. reconstruct the observable Skill lifecycle from versioned Agent adapters;
2. score event nodes, attribution edges, evidence grades, and unsupported
   capabilities separately;
3. diagnose the earliest observable boundary without converting missing
   evidence into causal claims;
4. connect lifecycle evidence to Skill behavior constraints and independent
   outcome verification;
5. measure non-interference, collection loss, and prompt/catalog footprint.

Candidate title:

> Evidence-Graded Runtime Intelligence for Agent Skills: Reconstructing
> Activation, Uptake, Behavior Coverage, and Outcomes

## Remaining confirmatory work

- Build and double-label a stratified, de-identified real-run corpus with
  multiple positive cases per relation type, explicit failures, verified
  outcomes, and more than one Agent. The current 97-run local aggregate is
  not confirmatory-ready.
- Repeat the catalog ablation with paired seeds, description-length and
  semantic-overlap factors, and bootstrap intervals.
- Repeat guarded hook transport measurements across low-ambient-load windows
  and on Linux; add p99/max and system-load covariates rather than attributing
  the observed tail changes to synthetic load alone. A local Linux container
  is available, but its base image lacks a compiler and the first ephemeral
  dependency-install attempt stalled before the experiment started; use a
  prebuilt, digest-pinned experiment image.
- Run the 24-slot participant pilot; then pre-register a powered confirmatory
  study.
- Run the same pinned Skill/task on a second authenticated Agent. The installed
  Claude binary is still terminated with exit 137. Qwen Code 0.9.1 is now
  executable, but its cached OAuth refresh failed and non-interactive execution
  requested a new device authorization; the probe was stopped with zero Agent
  turns and zero model tokens, so this is `not_run`, not a cross-Agent result.
- Evaluate an evidence-citing semantic model on novel real failures; keep all
  outputs Inferred and measure calibration and unsupported-claim rate. Compare
  it with an ordered relational/graph baseline, not only flat retrieval.
