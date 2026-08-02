# Skill Runtime Intelligence experiment report

Date: 2026-07-29  
Last updated: 2026-08-01
Protocol: `sri-experiment-v1`  
Status: local gates complete; cross-Agent and model-Agent studies active

## Executive result

The current evidence supports a narrower and stronger product claim:

> Skill Runtime Intelligence can reconstruct and diagnose observable Skill
> lifecycle evidence without taking over the Agent, while explicitly separating
> observed facts, deterministic relationships, uncertain explanations, and
> controlled experimental outcomes.

It does **not** yet support claims about human diagnosis, general cross-model
Panorama effects, negligible end-to-end collection latency, or a Skill causing
an outcome across general tasks.

## Completed results

| Experiment | Result | Evidence strength |
|---|---|---|
| E0 deterministic diagnosis | 14/14 exact; Precision/Recall/F1 1.0; zero unsupported causal claims | reviewed synthetic fault corpus |
| E1 Codex reconstruction | 10/10 exact; 18 TP, 0 FP, 0 FN after fixes | de-identified golden fixtures |
| E2 paired collector microbenchmark | 2,400/2,400 events accepted; zero input/output mutation, loss, or duplicates | isolated local paired trials |
| E2 transport fast path | initial eight balanced runs accepted 640/640 events and passed 7/8 latency gates, with pooled shell p50 45.1 ms and p95 78.6 ms; three suite follow-ups accepted 240/240 and passed 1/3 with shell p95 120.4, 51.5, and 127.2 ms; cumulative run gate 8/11, all silent with zero exit failures | 11 × 40 balanced local process trials per condition; Experimental, with Derived aggregate |
| E2 contention integrity | 320/320 events accepted across forward/reverse load schedules; silent with zero exit failures; latency hypothesis did not replicate consistently | 2 × 5 local segments with 16 balanced trials per condition; Experimental |
| E2 Linux `nc` fallback | 80/80 events accepted across two runs; p50 2.0–2.8 ms, p95 6.0–6.1 ms; incremental p50 1.2–2.0 ms, p95 4.4–5.5 ms; silent with zero exit failures | 2 × 40 paired trials in one digest-pinned Linux/arm64 container; Experimental |
| E3 model-Agent isolated replication | Under the current stdin + temporary-state harness, DeepSeek V4 Flash completed 20/22 responses: Raw 8/11 (72.7%), Panorama 9/11 (81.8%) intention-to-treat, +9.1 percentage points, with matched complete-case direction 2 wins/0 losses/7 ties. MiMo V2.5 completed 22/22: Raw 7/11 (63.6%), Panorama 11/11 (100%), +36.4 points, direction 4/0/7. The positive direction reproduced for both recorded model IDs, but DeepSeek made one unsupported causal claim and MiMo made three; both integrity gates failed. Earlier non-isolated pilots showed larger +18.2 and +45.5 point ITT differences, so run/harness sensitivity is retained rather than hidden | two recorded free model IDs over the same synthetic diagnostic corpus; Experimental interface-decoding evidence, not human evidence, independently verified model-family identity, or a general causal product claim |
| E3 post-hoc failure-mode audit | Both models located explicit runtime-failure boundaries correctly in 4/4 Raw and 4/4 Panorama cases per model, yet all four unsupported causal claims occurred in cases containing explicit runtime-failure evidence. For `run_incomplete`, each model scored 0/1 Raw and 1/1 Panorama. For `lifecycle_evidence_gap`, DeepSeek scored 3/5 Raw and 3/5 Panorama ITT because two Panorama responses were invalid; MiMo scored 2/5 Raw and 5/5 Panorama | Derived case-family stratification of the two isolated experimental reports; post-hoc, tiny cells, no causal or population claim |
| Causal-scope contract | All 14 deterministic Findings across 11 actionable cases used `causal_scope=none`; 14/14 descriptive claims were allowed and 0/14 Skill-to-outcome effect claims were allowed. The three-scope × three-claim policy matrix matched 9/9 expectations and 2/2 unknown inputs failed closed; E0 remained 14/14 exact with zero unsupported causal claims | Derived deterministic policy/mechanism audit over the synthetic diagnostic corpus |
| Adversarial causal-claim classifier | Pattern-v1 scored 30/30 on its co-developed contract corpus, but only 5/16 on a post-freeze synonym/counterfactual/quotation/multilingual challenge, with 5 unsafe false allows and 3 false denies. A fail-closed-v2 wrapper reduced false allows to 0/16 by abstaining on unrecognized wording, but classification fell to 1/16 and false denies rose to 10/16. Neither classifier is product-ready | Derived deterministic robustness probe over hand-authored development and post-freeze challenge corpora; no language-distribution generalization claim |
| Structured vs free-text claim output | DeepSeek completed 32/32 fresh sessions: structured kind/guard accuracy was 15/16 and 15/16, versus 4/16 and 7/16 for free-text post-classification; structured had one false allow, free text had nine false denies. MiMo completed 32/32: structured was 16/16 and 16/16 versus free text 2/16 and 7/16; structured had zero false allows/denies, free text had nine false denies. Both models showed a structured kind-accuracy advantage, but the combined safety gate failed because DeepSeek misclassified one negative-effect claim as descriptive | two recorded model IDs × 16 hand-authored challenge claims × 2 output modes; Experimental interface evidence, no pooled effect or population claim |
| Frozen deny-only verifier holdout | Fail-closed-v3, frozen after the first challenge, scored 16/16 on those known cases but only 1/16 on a newly authored holdout; it kept zero false allows but caused 10 false denies. On the new holdout, both DeepSeek and MiMo structured output scored 16/16 with zero false allows/denies across 32 fresh sessions per model. Intersecting either model guard with v3 preserved zero false allows but changed ten correct allows into false denies; v3 abstained on 12/16 cases. Free-text kind accuracy was 7/16 for DeepSeek and 3/16 for MiMo, with 8 and 10 false denies respectively | two recorded model IDs × 16 post-freeze hand-authored claims × 2 output modes; Experimental interface evidence plus Derived frozen-verifier audit, not a deployment error-rate or causal interface estimate |
| Cross-model semantic guard on discourse holdout | DeepSeek and MiMo each completed 24/24 fresh sessions on a new 12-case multi-sentence, nested-quotation, Chinese/Spanish holdout. Each structured path classified 11/12 kinds but made 12/12 correct scope decisions with zero false allows/denies; free-text kind accuracy was 5/12 and 1/12, with four and seven false denies. Cross-model scope intersection changed no decisions and retained zero errors, despite disagreement on two unique experimental-estimate cases. Requiring exact-kind consensus instead caused two false denies per direction (four directional errors) | two recorded model IDs × 12 hand-authored discourse claims × 2 output modes; Experimental interface and post-hoc policy-replay evidence, no independence, deployment-rate, or causal-effect claim |
| Cross-model guard accuracy/cost aggregate | Across three hand-authored corpora, 44 unique cases produced 88 structured calls and 88 directional producer decisions. Baselines contained one false allow; cross-model scope intersection removed it with zero aggregate false allows/denies, while exact-kind consensus produced four directional false denies on two unique cases. The second-model design requires 44 additional calls. All 88 calls reported 800,959 input and 885,353 total tokens; DeepSeek accounted for 424,076 input tokens and MiMo 376,883. Reconstructed additional visible prompts were only 28,682 bytes. Computed serial p50 paths were 17.2–27.0 seconds; with DeepSeek as producer, computed parallel incremental p50 was 5.2–11.0 seconds and p95 26.1–32.6 seconds | Derived aggregate of completed Experimental reports; latency paths are arithmetic replays over observed concurrent calls, not directly executed production schedules or a cost-effect estimate |
| Local-conflict semantic-review router | Replaying frozen-v3 only as a review trigger selected 16/88 directional cases (18.2%), including the sole baseline false allow. Intersecting the selected second-model decisions reduced aggregate false allows from one to zero without a false deny; 15/16 reviews did not change authorization. Selected reviews accounted for 144,756 reported input tokens and 10,745 reconstructed prompt bytes. The replay would avoid selecting 72/88 always-on reviews, but all source calls were already executed | Derived post-hoc policy replay over the same three hand-authored corpora; the captured error came from the challenge used to develop v3, so this is mechanism evidence with strong tuning bias, not prospective routing effectiveness or realized savings |
| Prospective selected-only routing vs shadow | On a newly frozen 16-case routing holdout, the DeepSeek producer completed 16/16 but made two false allows on unseen null-effect wording. The pre-verifier manifest selected only one legal descriptive case (6.25%) and missed both false allows. The actual selected-only MiMo queue completed 1/1, used 7,994 input tokens, and left both false allows with zero false denies. A separately executed 16/16 always-on MiMo shadow caught both false allows but introduced one false deny, using 137,714 input tokens. Computed serial p50 was 6.06 seconds selected-only versus 27.55 seconds always-on | Experimental prospective routing evidence over one hand-authored holdout; one response per model/case, separate verifier sessions, and computed path latency do not establish deployment error rates or causal policy effects |
| Contract-fragility review router | A text-independent development replay reviewed an allowed claim only when both alternative structured claim kinds would flip its scope decision. Across four corpora and 120 directional decisions it selected 32 reviews (26.7%), captured all three observed baseline false allows, and missed none; routed false denies increased from one to two. Selected reviews accounted for 290,659 reported input tokens. On the latest DeepSeek direction it selected 6/16 cases, captured 2/2 false allows, matched always-on's 0 false allow/1 false deny, and attributed 51,734 input tokens versus always-on's 137,714 | Derived post-hoc development evidence; the threshold was proposed after observing existing results and must be frozen before a new prospective holdout |
| Prospective contract-fragility routing | With threshold 1.0 frozen, a new 16-case scope-stratified holdout produced one DeepSeek false allow. Fragility selected 5/16 cases (31.25%), including that error; the actual selected MiMo queue completed 5/5 and reduced final errors to 0 false allows/0 false denies using 42,968 input tokens. A pre-manifested random sample covered 3/11 unselected cases; its MiMo shadow completed 3/3, used 23,918 input tokens, and made one guard error on a case the producer had already denied. Shadow output had no authorization authority | Experimental prospective evidence over one hand-authored holdout and one response per model/case; the single captured error and three-case shadow do not estimate population routing or verifier error rates |
| Prospective fragility replication summary | A second frozen 16-case English/Japanese/French holdout again produced one producer false allow. Fragility selected 5/16, captured it, and ended with zero false allows/denies; the three-case random shadow had zero errors. Across two prospective holdouts: 32 cases, 10 selected reviews, six random shadows, 2/2 observed false allows captured, zero routed errors, and one shadow verifier error; selected and shadow calls reported 85,143 and 48,639 input tokens. All promotion minimums remain unmet: 2/3 holdouts, 32/48 cases, 2/5 baseline false allows, and 6/12 shadow cases | Experimental replicated direction over two small hand-authored holdouts; sparse errors and one model-ID pair preclude stable rate, subgroup, or product-readiness claims |
| Third prospective fragility holdout (incomplete) | A frozen 16-case Korean/Arabic/Hindi and source-scope-heavy holdout completed 16/16 DeepSeek producer calls, with one false allow and zero false denies. The threshold-1.0 router selected 4/16 allowed outputs, including that false allow, and a pre-verifier seed selected 7/12 unselected cases for random shadow. Both the 4-case selected MiMo batch and 7-case shadow batch completed 0 calls on the initial attempt and 0 on a lower-concurrency retry because the verifier service returned execution errors. No routed-accuracy result was computed and this holdout was not added to the cumulative readiness summary | Experimental producer evidence and Derived frozen selection manifests; verifier execution is incomplete, so the prior 2-holdout readiness counts remain authoritative |
| E4 export-profile equivalence | 6/6 profiles exact; comparable-field coverage 1.0; zero dangling parents after fix | equivalent synthetic export fixtures |
| Cross-Agent source-instance contract | 8/8 trials kept Qoder, OpenCode, and Claude Code as three Agent-scoped sessions despite identical upstream session/turn/call labels; same-Agent append remained in one stream; zero event-ID collisions or cross-source causal edges | production hook builders, Collector, and storage over synthetic hook payloads; Experimental mechanism evidence |
| Privacy-safe paired-task key contract | expanded replication passed 20/20 trials and 60/60 synthetic Agent derivations for the same explicit assignment; task, study-scope, and protocol variants were distinct 20/20, twenty 1,024-task pools had no observed collisions, exports omitted task IDs and study secrets, and missing/prompt-only assignments plus corrupt, over-permissive, and symlink secrets failed closed 20/20 | Experimental local-filesystem mechanism evidence over 20,560 generated keys; no semantic-equivalence, cryptographic collision-rate, secret-distribution, or live integration claim |
| Live experiment-evidence isolated import | all 12 verified Codex/OpenCode/Qoder report rows linked exactly once to live sessions by a hash of the adapter source-session ID; adapter consistency passed 12/12, first import inserted 12 outcomes, repeated import was idempotent 12/12, and wrong digest, wrong adapter, and conflicting outcome were rejected 3/3 | Experimental linkage/import mechanism evidence against a live database and isolated temporary target; production schema was not mutated and UI, migration, consent, and failure-outcome coverage remain untested |
| Live OpenCode attempt correlation | 4/4 installed OpenCode 1.18.5 trials passed the deterministic verifier and linked the pre-session token digest to exactly the CLI-reported session; raw-token persistence findings 0/4, workload mutations 0/4, wall p50/p95 16.69/24.17 seconds; observer deltas +4 sessions/+26 events/+4 Observed SkillRuns | Experimental single-system official-hook mechanism evidence; no no-token randomized control, cross-Agent propagation, or causal effect claim |
| Randomized OpenCode token ablation | eight randomized within-block token-on/off pairs completed 16/16 verified outcomes with zero workload mutations; token-on correlation 8/8, token-off silent control 8/8; paired wall-time on-minus-off mean/median -2.03/-0.48 seconds with descriptive bootstrap 95% CI [-6.74, +2.51] seconds; observer deltas +16 sessions/+110 events/+16 Observed SkillRuns | Experimental single-machine randomized mechanism evidence; interval crosses zero and does not establish acceleration, zero overhead, or non-inferiority |
| Cross-Agent alignment manifest | 9/9 conflict cases exactly classified: 5 comparable, 2 partially comparable, 2 not comparable; zero cases authorized causal attribution | synthetic field-level alignment contract corpus; Experimental engineering evidence |
| Alignment clock sensitivity | 88/88 offset/tolerance evaluations preserved lifecycle/outcome decisions and causal safeguards; absolute-time acceptance changed monotonically from 1/11 at 0 seconds to 11/11 at 120 seconds | 11 synthetic offsets × 8 clock policies; Experimental policy-mechanism evidence |
| Timestamp provenance capability and migration | baseline schema exposed 1/7 required capabilities and labeled fallback provenance 0/4; the additive implementation exposed 7/7 fields, labeled fallback provenance 4/4, and persisted all 8/8 controlled events with ingestion/domain/precision metadata, while known clock uncertainty remained 0/8 and absolute-time readiness stayed false; a read-only live snapshot copy preserved 41,258/41,258 events and 150/150 sessions through migration with SQLite quick-check passing | before/after temporary schema audit, legacy-row migration fixture, controlled production hook builders for four profiles, and an isolated copy of one live local database; Derived capability and Experimental mechanism evidence |
| E5 diagnosis representation ablation | rules exact 1.0/F1 1.0; lexical retrieval exact 0.214/F1 0.414; lifecycle-feature retrieval exact 0.071/F1 0.080; ordered relational templates exact 0.929/F1 0.963 | leave-one-out synthetic corpus; retrieval outputs Inferred |
| PAI-DSW Linux x86_64 reproducibility | The first formally identified DSW run passed 10/13 suite gates and exposed one shared fixture-contract regression: `reported_outcome_only` omitted its declared verifier expectation, so E0, E3 readiness, and E5 separation failed identically on DSW and macOS. After adding only `behavior_assessment.verifier_expected=true` to that case, the DSW rerun passed 13/13 gates: 12/12 deterministic correctness gates and 1/1 environment-sensitive Linux transport gate | Experimental cross-environment replication on one PAI-DSW H20 instance; deterministic and transport-mechanism evidence, not a GPU-model result or proof of general Linux portability |
| Real-run corpus readiness audit | the latest privacy-safe snapshot contained 405 SkillRuns and still passed 4/7 coarse exploratory criteria; its cross-Agent audit passed 2/2 presence checks but 0/3 descriptive and 0/8 confirmatory checks, with a 403/1/1 Codex/OpenCode/Qoder split, zero shared Skill-digest groups, and no verified outcomes or human labels. Relative to the prior 372-run snapshot, runs increased by 33 while activation evidence gaps increased by 31 to 400 and unverified outcomes by 39 to 191; observed incomplete-run findings decreased by six to 214 | query-only consistent snapshots of one local multi-adapter database; Derived aggregate, drift, and readiness evidence, zero row-level records; count changes are not attributed to newly added runs or a product intervention |
| Cohort terminality × evidence transition pilot | a snapshot-A cohort contained 408 runs and was retained 408/408 after an observed 22.16-second interval. At both snapshots, 350 runs were terminal but evidence-insufficient and 58 were nonterminal and evidence-insufficient; zero runs met the strict observed-activation-plus-verified-outcome-or-explicit-failure rule, and zero four-state transitions occurred. The privacy and integrity gate passed | one short query-only observational interval on one local database; Experimental state-separation evidence, not a transition-rate, stability, or causal-effect estimate |
| Dataset cut-policy pilot | across three three-snapshot trials, pooled next-window stability was 222/240 all-observed, 205/216 terminal-status, 215/230 30-second watermark, and 188/206 prior-quiescence selections | one local live database; Experimental observational time series, non-independent run observations |
| Collection-checkpoint capability and mechanism | pre-deployment live runtime exposed 3/7 capabilities; post-deployment audit exposed 7/7, then a real completed epoch recorded one late arrival and a later retry completed with zero; isolated trials detected 8/8 modified and 8/8 newly created sources with 0/8 control false positives | query-only live snapshots (Derived), aggregate live epoch state (Observed), and controlled synthetic-adapter trials (Experimental); no row-level records |
| Production Codex watch epoch | pre-fix deletion boundary advanced 0/3; post-fix create, append, and delete paths each advanced 3/3, removal count was exact 3/3, historical sessions were retained 3/3, and watcher cleanup passed 3/3 | production Codex adapter/watch loop over isolated synthetic transcripts; Experimental mechanism evidence |
| Mixed provenance reconciliation | official-hook raw/event/run evidence survived transcript refresh 8/8 and correlation groups remained intact 8/8; cross-source relationship edges were available 0/8 | production adapter and collector over isolated synthetic correlated sources; Experimental, privacy-safe aggregate |
| Provenance-localized reindex pilot | official-hook aggregate counts changed by zero in both isolated reindexes; one source-stable comparison added 3 transcript raw records, 2 events, and 3 relationships, but its checkpoint cut was not recorded; a checkpoint-aware repeat had active source changes and was non-identifiable | two isolated copies of one local live database; Experimental/Derived aggregate, no row-level records |
| Frozen historical corpus identity | before the source-instance fix, 12 frozen transcripts with four divergent upstream identities collapsed to 4 sessions, 216 raw records, and 80 events; after the fix they produced 12 sessions, 802 raw records, and 300 events, with 3/3 exact repeat fingerprints | same bounded 2.87 MB historical Codex subset before/after adapter identity change; Experimental mechanism evidence with privacy-safe aggregates |
| Packaged product lifecycle | 7/7 post-fix isolated wheel runs completed install/start/status/doctor/stop/uninstall; latest 4/4 also verified native prewarm; project and Agent configs unchanged; state fully removed | seven local packaged-product runs; Experimental |
| Packaged upgrade migration | the built 0.1.6 wheel installed offline, applied the additive migration twice, preserved 41,686/41,686 legacy events and 151/151 sessions, then persisted one controlled event with exact time provenance; both migration and final SQLite quick-checks passed | one isolated read-only live-snapshot copy and packaged wheel; Experimental mechanism evidence |
| Partial migration recovery matrix | all 18/18 evaluations across zero through five already-applied provenance columns completed the additive migration, preserved unknown/null legacy semantics, passed a second idempotent open, and passed SQLite integrity checks | 6 preconstructed partial schema states × 3 repetitions; Experimental mechanism evidence |
| Process-kill migration recovery | 18/18 migration workers were terminated by signal before any addition or after each of five committed DDL boundaries; every clean restart completed the schema, preserved the legacy event as unknown/null, passed a second idempotent open, and passed SQLite integrity checking | 6 committed-boundary kill points × 3 repetitions on temporary WAL databases; Experimental mechanism evidence |
| Migration lock contention | 6/6 transient writer-lock cases at 50 ms, 250 ms, and 1 second completed within the five-second busy timeout; one 5.5-second lock failed initially as expected, then recovered cleanly; all 7/7 retained unknown/null legacy semantics and passed SQLite integrity checks | temporary WAL databases under one local writer lock; Experimental environment-sensitive mechanism evidence |
| Read-only migration recovery | 3/3 separate-process opens failed against read-only temporary databases, left the legacy schema and event unchanged, and recovered after write permission was restored | POSIX read-only file/directory fixtures on one local environment; Experimental mechanism evidence |
| Old-writer migration compatibility | 7/7 schedules preserved a legacy column-list write before, after, or beyond the migration lock budget; all old writes remained explicitly unknown/null for new provenance fields and every database recovered with integrity intact | raw SQLite legacy-writer fixture, one writer and one migrator on temporary WAL databases; Experimental mechanism evidence |
| Historical schema contract migration | 9/9 migrations across three distinct schema fingerprints created by verified Git history snapshots preserved the controlled legacy event as unknown/null, passed a second idempotent open, and passed integrity checking | bootstrap Panorama, SkillRun-core, and v0.1.0 commit snapshots × 3 trials; Experimental mechanism evidence |
| Release-artifact schema contract | the downloaded GitHub v0.1.0 wheel matched its published SHA-256, installed as 0.1.0 in an isolated runtime, and its database migrated successfully in 3/3 trials; a repository-local same-named wheel had a different digest and was not treated as the release artifact | one GitHub release wheel, digest and installed-metadata identity gates, three controlled temporary databases; Observed artifact identity plus Experimental migration evidence |
| v0.1 release-wheel matrix | all seven GitHub wheels from v0.1.0 through v0.1.6 matched their release digests and installed metadata; all 21/21 migration trials preserved unknown/null legacy semantics and were idempotent; the seven wheels produced one shared historical schema fingerprint | 7 identity-verified release wheels × 3 controlled databases on one local platform; Observed artifact identity plus Experimental migration evidence |
| Wheel/sdist distribution parity | all 7/7 v0.1 release pairs matched their individual digests and versions, generated the same schema fingerprint within each pair, and passed all 42/42 wheel-plus-sdist migration trials | 14 identity-verified release artifacts, three controlled databases per distribution, path-verified direct sdist execution; Observed artifact identity plus Experimental parity evidence |
| Offline sdist rebuild parity | all 7/7 offline-rebuilt wheels matched published-wheel metadata, CLI entry points, wheel tags, and schema contracts; all 14/14 release-plus-rebuilt migration trials passed; rebuilt bytes matched the published wheel in 0/7 pairs and two immediate rebuilds matched each other in 2/7 pairs | one recorded local no-network/no-build-isolation toolchain, 7 sdists × 2 rebuilds; Experimental semantic and byte-reproducibility evidence |
| Fixed-epoch rebuild repeatability | with `SOURCE_DATE_EPOCH=315532800`, all 7/7 version pairs produced one digest across three repeated offline builds and retained selected contract parity, while 0/7 matched the published wheel bytes; file audit found 21 differing common contents and four release-only/four rebuild-only member paths | same seven sdists × 3 fixed-epoch builds on one local toolchain; Experimental mechanism evidence, no general causal claim |
| Pinned-builder normalized content | Python 3.13.11/setuptools 83.0.0 fixed-epoch rebuilds matched published wheel member names and normalized content fingerprints in 7/7 version pairs, repeated raw digests in 7/7, but matched published raw digests in 0/7; all 249 member timestamp fields differed | 7 sdists × 2 pinned-builder rebuilds on macOS compared with Ubuntu-published pure-Python wheels; Experimental content-equivalence evidence |
| Digest-pinned Linux rebuild | a network-disabled Linux arm64 container rebuilt all seven sdists twice; normalized content, member names, and selected contracts matched published wheels in 7/7, and Linux raw rebuild digests matched the prior macOS pinned-builder digests in 7/7; published raw digest matches remained 0/7 due to 249 timestamp differences | digest-pinned Python 3.13.11 Bookworm image plus content-recorded builder dependencies; Experimental cross-environment evidence |
| Published native-sender four-layer contract | all 4/4 v0.1.6 assets matched recorded digest/size identity and exposed the required entry point across six Mach-O/ELF slices; Darwin arm64 and Linux arm64 each delivered 20/20 exact header-plus-payload messages, stayed silent on success, and returned the expected silent failure codes; both x86_64 functional paths remain `not_run`; the two architecture-labelled Darwin assets were byte-identical universal binaries | Observed release identity, Derived section/symbol evidence, and Experimental protocol evidence on macOS arm64 plus a digest-pinned Linux arm64 container |
| Verified-source native rebuild parity | v0.1.6 tag/commit/source/workflow identity and both selected published assets passed; Darwin universal2 and Linux arm64 rebuild pairs passed the external structure and protocol contract with 80/80 exact deliveries across four executions, while raw digest and section fingerprints matched 0/2 and full symbol fingerprints matched 1/2 | Observed source/published identity, Derived binary structure, and Experimental protocol parity under local Apple clang plus network-disabled digest-pinned Linux build/runtime containers |
| Native executable path-reuse sensitivity | three repeated balanced runs completed 144/144 silent missing-socket launches; pooled stable-path p50 was 28.2 ms published and 29.9 ms rebuilt, versus 213.0 ms and 220.6 ms for fresh-path copies; fresh copies were slower in 33/36 and 34/36 paired blocks respectively | Experimental single-host path association plus Derived three-report aggregate; no cache, signing, or scanning causal claim |
| Native launch-factor manipulation audit | the v1 pilot completed 8/8 launches but rejected provenance removal because the xattr was present again before launch in 4/4 removal cells; the retained v2 placement × signature matrix passed 96/96 launches and 96/96 factor audits across three runs, but neither factor retained a consistent run-level latency direction | Experimental temporary-copy manipulation checks plus Derived run-boundary summary; invalid factor excluded and latency nonstationarity preserved |
| Native launch phase-readiness audit | 96 raw trials, three run boundaries, factor audits, correctness, and position balance passed the descriptive gate; only 5/10 readiness criteria passed, so confirmatory effect readiness remained false; re-signed cell run-p50 ratios were 15.6–16.7× versus 1.04–1.17× for original-linker cells | post-hoc Derived readiness audit; no inferred change point, steady state, or cross-host effect |
| Privacy-safe host identity contract | two macOS invocations plus one network-disabled Linux arm64 invocation totaled 13 trials and 144 concurrent initializers; all 13/13 trials converged on one stable alias per scope, produced distinct cross-scope aliases, kept secret files at 0600, omitted the local secret from exports, and failed closed for corrupt, over-permissive, and symlink identities | Experimental temporary-filesystem mechanism evidence across macOS and digest-pinned Linux arm64 environments on one physical host; random local origin with scope-specific HMAC alias, no hardware/user fingerprint inputs |
| Live Codex reconstruction | 3/3 verified outcomes, unchanged workspaces, sessions, SkillRuns, instruction events, and resource events | real Codex 0.145.0 / GPT-5.6-sol, deterministic task |

The clean-commit reproducibility suite passed 9/9 selected local experiment
gates on `e3f47b3` with `git_dirty=false`. A later expanded suite contains 12
correctness gates and one environment-sensitive transport gate. Its recorded
run passed all 12 correctness gates and failed the transport latency gate, for
12/13 overall; the preceding 12-gate run had passed all selected gates before
the kill-recovery gate was added. Across all eleven comparable transport runs,
the performance gate passed 8/11; the Wilson 95% interval for the run-level
pass rate is 0.434–0.903.

The v0.3.0 release-candidate authoring checkout passed 244 unit and integration
tests on 2026-07-31, with two historical-distribution tests skipped because
their digest-pinned published fixtures are not stored in the repository. A
clean clone skips eight more artifact-backed reanalysis tests: three additional
distribution tests are exercised by the dedicated CI job after downloading and
verifying the published fixtures, while five study-report tests require local,
privacy-retained experiment outputs and say so explicitly. Coverage includes
behavior-constraint extraction, actual-activity summaries, evidence-bounded
diagnosis, lifecycle ownership safeguards, localized catalog integrity, hooks,
Collector, OTLP export, storage, comparison, release metadata, and experiment
contract helpers. Distribution build and installed-wheel lifecycle checks are
reported separately from the research results so that packaging success is not
presented as experimental evidence.

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

### 5. Structured evidence did not guarantee model claim safety

The initial 22-trial DeepSeek E3 pilot produced one malformed Panorama response
and one unsupported Raw causal claim. A separate 11-trial protocol-stability
re-execution again produced only 10/11 parseable responses and one unsupported
causal claim, this time under Panorama. The initial 22-trial MiMo replication
parsed 22/22 responses but produced two unsupported Raw causal claims.

After prompt transport and temporary-state isolation were tightened, DeepSeek
parsed 20/22 and still produced one unsupported causal claim; MiMo parsed 22/22
and produced three unsupported claims, including two under Panorama. The
diagnostic re-execution is not pooled into the predeclared pilot effect
estimate. Across both model IDs and both harness generations, schema
instructions and evidence grades were not sufficient enforcement: machine
consumers need parse status, abstention, and a deterministic post-model claim
guard.

The post-hoc family audit separates two failure modes. Boundary localization
was perfect for explicit runtime failures in both views and both models, while
all four unsupported causal claims appeared in cases that contained explicit
failure evidence. Conversely, Raw errors concentrated on lifecycle evidence
gaps and incomplete runs. This does not establish a psychological mechanism,
but it shows that boundary accuracy and causal safety must be measured and
guarded independently.

The claim-output-mode pilot further separates three gates: format/schema
validity, semantic `claim_kind` correctness, and authorization correctness.
Both structured paths parsed 16/16 responses and outperformed free-text
post-classification on both recorded model IDs. However, both models proposed
`allowed=true` for the same negative-effect sentence under `causal_scope=none`.
MiMo's correct `skill_outcome_effect` enum let the local validator override
that proposal; DeepSeek mislabeled it `descriptive`, producing the sole
structured false allow. Schema constraints reduce representation ambiguity but
do not guarantee semantic honesty or correct authorization.

The frozen deny-only follow-up exposes the opposite failure mode. A v3 phrase
verifier was changed only from the first challenge failures, where it then
scored 16/16. After freezing v3, a second 16-case holdout introduced new
uncertainty, source-attribution, causal, counterfactual, Chinese, and Spanish
wording. V3 classified only 1/16 exactly. It made no false allows because
unknown wording failed closed, but it made ten false denies.

Both recorded model IDs completed all 32 fresh sessions on that second
holdout. Their structured paths each classified 16/16 and made zero guard
errors, while free-text post-classification reached only 7/16 and 3/16 kind
accuracy. Replaying the structured outputs through the deny-only intersection
rule produced the same result for both models: zero false allows remained, but
ten previously correct allows became false denies, and the verifier abstained
on 12/16 cases. On the already-seen challenge, the same verifier removed
DeepSeek's one false allow without a false deny. That contrast is evidence of
challenge-specific coverage, not general safety. A lexical verifier may be
useful as a visible warning or review trigger, but this implementation is not
suitable as a default authorization gate.

The cross-model follow-up used a third, newly frozen 12-case holdout with
multi-sentence evidence boundaries, nested quotation, hedged and null effects,
counterfactuals, interval estimates, Chinese, and Spanish. DeepSeek and MiMo
each completed 24/24 fresh sessions. Their structured paths each classified
11/12 claim kinds correctly but made 12/12 correct local scope decisions.
Free-text post-classification reached 5/12 and 1/12 kind accuracy and produced
four and seven false denies.

Using the other recorded model ID as a deny-only semantic verifier changed no
scope decision and retained zero false allows/denies in both directions.
However, the models disagreed on the exact claim kind for the same two
experimental-estimate cases: one mislabeled the English interval estimate as
descriptive, and the other mislabeled the Chinese estimate as descriptive.
Because `experimental_estimate` permits both bounded effect estimates and
descriptive statements, authorization agreement concealed semantic
disagreement. An alternative exact-kind-consensus policy rejected both valid
cases in each direction, producing two false denies per direction. Therefore
cross-model scope consensus is not evidence of semantic correctness, while
strict semantic consensus can recreate the usability loss of a lexical
fail-closed verifier.

Across all three claim corpora, the two model reports cover 44 unique cases
and 88 structured calls. Treating each model as producer once yields 88
directional decisions. The baseline reports contain one false allow; the
cross-model scope intersection removes it and produces zero aggregate false
allows/denies. Exact-kind consensus instead produces four directional false
denies corresponding to two unique experimental-estimate cases.

The operational ledger changes the product interpretation. A second verifier
requires 44 additional calls. All 88 structured calls report 800,959 input
tokens and 885,353 total tokens: 424,076 input tokens for the recorded
DeepSeek ID and 376,883 for MiMo. The reconstructed visible structured prompts
sent to the additional verifier total only 28,682 UTF-8 bytes, so reported
input usage is dominated by provider/CLI context rather than claim length.
Computed serial p50 paths range from 17.2 to 27.0 seconds. If DeepSeek is the
producer and MiMo runs in parallel, computed incremental p50 is 5.2–11.0
seconds across the three corpora and incremental p95 is 26.1–32.6 seconds.
These path values combine already observed per-call timings; the serial and
parallel schedules were not themselves executed, and the original trials ran
with multiple concurrent workers. The evidence favors selective asynchronous
review over a default synchronous second-model gate.

The same reports support a lower-cost policy replay in which frozen-v3 never
changes authorization directly. It only requests second-model review when the
producer is currently allowed, v3 recognizes a claim kind, and the two kinds
conflict. Across both producer directions and all three corpora, this selects
16/88 cases (18.2%). It includes the sole baseline false allow; second-model
scope intersection removes that error without adding a false deny. Fifteen of
the sixteen selected reviews do not change authorization. The selected calls
account for 144,756 reported input tokens and 10,745 reconstructed prompt
bytes. Compared with symmetric always-on review, the policy would avoid
selecting 72/88 reviews, but those calls were actually executed in the source
experiments. The saved-call count is therefore counterfactual replay, not
realized cost or latency reduction. Because v3 was developed from the first
challenge and the captured error belongs to that challenge, prospective
generalization remains untested.

The prospective routing holdout resolves that uncertainty negatively. A new
16-case corpus was frozen before any model call and emphasized unseen
null-effect, counterfactual, source-attribution, evidence-boundary, Chinese,
and Spanish wording. The DeepSeek producer completed 16/16 responses but
misclassified `success was invariant` and `no better and no worse` as
descriptive, producing two false allows. The frozen router then selected only
one legal descriptive case (6.25%) and missed both unsafe cases. This manifest
was written before either verifier run.

The actual selected-only MiMo queue completed its one selected call, correctly
allowed the descriptive claim, and consumed 7,994 input tokens. Final routed
decisions therefore retained two false allows and zero false denies. A
separately executed 16/16 always-on MiMo shadow classified both missed
null-effect claims correctly, so intersection removed both false allows, but
the shadow also mislabeled one legal evidence-boundary claim as an effect and
introduced one false deny. It consumed 137,714 input tokens. Computed serial
path p50 was 6.06 seconds for selected-only and 27.55 seconds for always-on;
these values combine observed calls and are not direct end-to-end schedule
measurements. The result is a safety–usability–cost frontier, not evidence that
either policy dominates.

The next development candidate removes open-text matching entirely.
Authorization fragility is the fraction of alternative structured claim kinds
that would flip the current scope decision. The frozen candidate threshold is
1.0: review only an allowed claim for which both other claim kinds would be
denied. Across four corpora, two producer directions, and 120 directional
decisions, this selects 32 reviews (26.7%), captures all three observed
baseline false allows, and misses none. Routed false denies increase from one
to two, and selected reviews account for 290,659 reported input tokens.

On the latest DeepSeek-producer corpus, fragility selects 6/16 cases, captures
both false allows, and yields the same 0 false allow/1 false deny decisions as
always-on shadow while attributing 51,734 rather than 137,714 input tokens to
review. This is a post-hoc development result: the signal was proposed after
the existing failures were visible. Its contribution is a transparent,
text-independent risk feature derived from policy topology, not evidence of
prospective routing performance.

With the threshold fixed at 1.0, a new 16-case holdout stratified `none`,
`source_assertion_only`, and `experimental_estimate` scopes before model
execution. The DeepSeek producer completed 16/16 and made one false allow on
an unseen null-effect counterfactual. Fragility selected 5/16 cases (31.25%),
including that error. A deterministic seed also selected 3/11 unselected cases
for random shadow; both manifests were written before any verifier call.

The actual selected MiMo queue completed 5/5, classified all five correctly,
and reduced final decisions to zero false allows and zero false denies while
reporting 42,968 input tokens. The three-case random shadow completed 3/3 and
reported 23,918 input tokens. It found no producer false allow in its small
sample, but the shadow verifier itself misclassified one effect as
descriptive. Because shadow output had no authorization authority and the
producer had already denied that claim, the final decision remained safe.
This adds a second purpose for random shadow sampling: estimate router blind
spots and independently monitor verifier drift. The cells remain too small
for either rate estimate.

A second frozen 16-case holdout changed wording and included English,
Japanese, and French cases while keeping threshold 1.0 and using a new random
shadow seed. The producer again made one false allow. Fragility selected 5/16
cases and captured that error; selected verification ended with zero false
allows/denies. The three random shadows had no errors.

Across the two prospective holdouts, 32 cases generated ten selected reviews
and six random shadows. The router captured both observed false allows and
produced zero routed errors; random shadow found one verifier error. Selected
and shadow calls reported 85,143 and 48,639 input tokens respectively. A
predeclared product-discussion gate requires at least three holdouts, 48 cases,
five producer false allows, and twelve random-shadow cases. Current coverage
is 2/3, 32/48, 2/5, and 6/12, so every minimum remains false. These minimums
are governance gates rather than statistical power guarantees.

A third holdout was frozen before execution with more
`source_assertion_only` direct-effect negatives and Korean, Arabic, and Hindi
wording. Its DeepSeek producer completed 16/16, made one false allow, and no
false denies. Threshold-1.0 fragility selected 4/16 allowed outputs, including
the error; a new seed selected 7/12 unselected cases for random shadow.
However, both the four-case selected MiMo batch and seven-case shadow batch
completed 0 calls, and a lower-concurrency retry also completed 0, because the
verifier endpoint returned execution errors. The producer and frozen
manifests are valid intermediate evidence, but the holdout is incomplete:
there is no routed decision result, it is excluded from the cumulative
summary, and neither its case nor shadow counts satisfy a readiness gate.

### 6. Hook process startup required a different transport

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

Two consecutive unprewarmed suite runs further exposed gate variability. Both
delivered 80/80 events silently. The first failed because shell p95 was
120.4 ms, above the predeclared 100 ms threshold, although incremental p95 was
61.8 ms. The immediate repeat passed with shell p95 51.5 ms and incremental
p95 32.1 ms. Direct maxima were 836.5 ms and 429.7 ms respectively. No
controlled environmental intervention separated the runs, so this pair cannot
identify a cause. It does show that correctness and environment-sensitive
latency need separate gate classes and that a single performance pass/fail
must not be presented as deterministic reproducibility.

A third follow-up again delivered 80/80 events silently but failed with shell
p95 127.2 ms and incremental p95 98.3 ms. Its one-minute load average at start
was 7.00 on 12 logical CPUs, compared with 9.69 for the preceding failure and
10.36 for the intervening pass. In this three-run sequence, the coarsest load
average did not order latency outcomes; with only three uncontrolled runs this
is a diagnostic observation, not evidence that host load is irrelevant.

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

The 2026-07-31 follow-up audited the expanded live index after Qoder and
OpenCode evidence became visible. The privacy-safe snapshot contained 372
SkillRuns from 48 sessions and 22 Skill definitions across three adapters.
Four of seven exploratory readiness checks passed: minimum run count, at least
two adapters, at least four Finding signatures, and at least two observed
activation runs. Runtime-failure candidates, verified-outcome runs, and
human-reviewed labels all remained zero, so
`corpus_ready_for_confirmatory_evaluation=false`.

The increase from 77 to 372 runs and from one to three adapters moved the
heuristic score from 1/7 to 4/7, but the adapter distribution was 370 Codex,
one Qoder, and one OpenCode SkillRun. In addition, one Derived activation-gap
signature covered 369/372 runs. This is a useful readiness-audit correction:
adapter presence is not balanced cross-Agent coverage, and a larger corpus can
pass coarse diversity criteria while remaining dominated by one adapter and
one coverage gap. Future gates need minimum per-adapter and per-diagnostic-cell
counts, verified outcomes, explicit failures, and human labels. The before/
after aggregate populations and schemas also differed, so the observed
readiness increase cannot be attributed to any one collection or product
change.

A stricter follow-up froze a later 375-run snapshot and separated three claim
levels. Multi-Adapter presence passed 2/2 integrity checks, but descriptive
cross-Agent readiness passed 0/3 and confirmatory readiness passed 0/8. The
run distribution was 373 Codex, one Qoder, and one OpenCode, for a 373×
max/min imbalance. No Skill digest was shared across adapters, only activation
and outcome were common event stages, and the current SkillRun schema exposed
no privacy-safe paired-task alignment key. Verified outcomes, explicit failed
events, and human labels were also absent from every adapter cell.

The audit thresholds—five runs per adapter for descriptive coverage, 20 for
confirmatory coverage, a maximum 3× run-count imbalance, and minimum coverage
for shared digests, lifecycle stages, failures, verified outcomes, and
labels—are exploratory and were not preregistered. The 0/3 and 0/8 results
therefore identify concrete missing evidence rather than estimate a future
effect or rejection probability. For product design, Support, Descriptive
ready, and Confirmatory ready must remain separate states.

The latest query-only snapshot contained 405 SkillRuns from 51 sessions and
26 Skill definitions. Coarse corpus readiness remained 4/7. The corresponding
cross-Agent audit again passed 2/2 presence checks but 0/3 descriptive and 0/8
confirmatory checks: the distribution was 403 Codex, one OpenCode, and one
Qoder run; no Skill digest was shared, and verified outcomes and human labels
remained absent.

Compared with the prior 372-run snapshot, total runs increased by 33,
activation evidence-gap findings increased by 31 to 400, and unverified
outcome findings increased by 39 to 191. Observed incomplete-run findings
decreased by six to 214. Because the live population can progress and be
reconstructed between snapshots, these deltas cannot be assigned only to the
33 additional runs. They nevertheless expose two independent dimensions:
runtime completion can improve while evidence sufficient for diagnosis and
comparison remains missing. A single “complete” badge would collapse these
dimensions and overstate corpus readiness.

A follow-up fixed all 408 runs present in snapshot A as one private cohort and
matched them locally to snapshot B without emitting run keys. The observed
snapshot interval was 22.16 seconds, longer than the requested two-second wait
because snapshot loading and backup time are part of the actual capture path.
All 408 runs were retained and no new run entered the cohort. At both points,
350 runs were terminal but evidence-insufficient and 58 were nonterminal and
evidence-insufficient; no run met the strict requirement of observed Skill
activation plus either a verified outcome or an explicit failed event. No
four-state transition occurred. This single short negative pilot validates
the privacy-safe transition mechanism and provides cross-sectional state
separation, but it cannot estimate a transition rate or prove temporal
stability.

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

After the production Codex watch gates and the then-current 93-test suite
passed, the local
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

### Provenance-localized reindex drift: two boundaries are required

A privacy-safe pilot copied a transactionally consistent live database into
an isolated temporary database, ran full transcript reconstruction twice, and
reported only aggregate deltas grouped by `collection_mode`. The first run
observed zero source-mtime boundary changes while the first reconstruction
added 3 transcript-fallback raw records, 2 events, and 3 relationships.
Official-hook counts changed by zero in both reconstructions. Because this
pilot did not capture whether the live snapshot was at a completed, zero-late
checkpoint whose source watermark matched the input boundary, it localizes
the difference to transcript-fallback evidence but cannot distinguish watcher
lag from transformation instability.

The experiment was then tightened to require both boundaries: a completed
zero-failure/zero-late collection checkpoint and an exact match between its
source watermark and the reindex input. The checkpoint-aware repeat captured
a converged checkpoint, but one transcript changed during each reconstruction;
both stability comparisons were therefore explicitly non-identifiable.
Official-hook preservation and the privacy audit still passed.

These are two snapshots of one local runtime, not a failure-rate estimate or a
causal effect. The negative result is methodological: aggregate equality is a
valid reproducibility gate only when both the database checkpoint and source
boundary are bound into the manifest. Provenance grouping should precede any
record-level diff so source-specific behavior is not hidden by total counts.

### Frozen corpus: deterministic reconstruction can still lose evidence

A bounded frozen-corpus experiment selected 12 historical Codex transcripts
(2.87 MB total), all older than one hour and unchanged while copied into an
auto-deleted temporary directory. The files contained four upstream source
session identities with multiplicities 2, 3, 3, and 4. All four groups were
divergent rather than prefix chains, and the latest file contained the union
of raw line hashes in 0/4 groups.

With adapter `0.2.0`, source files sharing an upstream session ID used the same
storage primary key. The 12 successful imports therefore persisted only 4
sessions, 216 raw records, and 80 normalized events. Three repeated reindexes
were fingerprint-exact: this was deterministic overwrite, demonstrating that
repeatability alone is not a correctness criterion.

Adapter `0.3.0` now assigns a storage identity to each physical transcript
source while retaining the upstream ID as `source_session_id` and using it in
the non-destructive `correlation_key`. On the identical frozen input it
persisted 12 sessions, 802 raw records, and 300 events, with zero collapsed
source instances. Three subsequent reindexes again matched every graph-table
fingerprint exactly.

This is Experimental mechanism evidence from one bounded, selection-filtered
local corpus. It does not estimate how frequently duplicate upstream IDs occur
in other users, versions, or Agents. It does establish an exercised invariant:
physical evidence streams must remain separately addressable even when they
report the same logical session identity.

A separate lightweight audit then read at most the first 20 lines of all 135
local transcript files. All exposed an upstream identity; 55 distinct
identities were observed, 18 were shared by multiple physical sources, 80
files were above a one-to-one mapping, and the largest group contained 21
sources. The physical-to-upstream ratio was 2.45 in this one local corpus.
This Derived aggregate confirms that the identity condition is material here,
but it is not a population prevalence estimate and does not establish that
every repeated group is divergent.

After deploying adapter `0.3.0`, a full local reindex imported 135/135 sources
with zero parse failures. The live database contained 135 active transcript
sessions on `0.3.0`, plus four official-hook sessions and one retained
historical `0.2.0` source whose current transcript was unavailable. Aggregate
counts moved from the immediately pre-restart 60 sessions, 13,894 events, and
96 SkillRuns to 140 sessions, 39,896 events, and 180 SkillRuns. This is one
Observed deployment sequence, not an effect-size or failure-rate estimate; the
controlled frozen-corpus result supplies the mechanism evidence.

### Cross-Agent identity: source correlation is not experiment alignment

An eight-trial controlled mechanism experiment sent official-hook events from
Qoder, OpenCode, and Claude Code with deliberately identical upstream session,
turn, and call labels. The production hook builders, Collector normalization,
and Evidence Store retained three Agent-scoped sessions in all 8/8 trials.
All six initial event identities were distinct in every trial, and a later
Qoder event appended to the existing Qoder stream without creating a fourth
session. No cross-source causal relationship was generated.

The identical turn labels produced two repeated `(turn, event-type)` label
groups per trial across different sessions. This makes the scope rule
observable: turn and call IDs are not globally unique and must be interpreted
with the internal source-instance session. Likewise, source correlation keys
remain Agent-scoped; cross-Agent research comparisons require a separate,
explicit task/evaluation alignment key rather than reusing an upstream session
label.

The trials use synthetic payloads and repeat deterministic code paths, so they
are Experimental mechanism evidence rather than independent Agent workloads or
live schema validation. Zero implicit cross-source edges is a safety result;
the product still needs a non-causal correlation/alignment view.

### Task alignment must be explicit, scoped, and content-free

A 20-trial expanded contract experiment derived one paired-task key for each
of three synthetic Agent assignments. All 60/60 derivations converged when the opaque
task ID, study scope, and protocol version matched. Changing the task, scope,
or protocol produced a different key in 20/20 trials, and all four domain
variants were distinct in every trial. Twenty pools of 1,024 task assignments
produced 20,480 unique keys with no observed collisions; including the domain
variants, the experiment generated 20,560 keys.

The mechanism uses a random 256-bit study secret stored at 0600 and exports a
128-bit-truncated HMAC-SHA256 key. The raw opaque task ID and study secret
appeared in zero exports. Missing task IDs and prompt-only manifests failed
closed 20/20 instead of deriving identity from content. Corrupt, 0644, and
symlink secret paths also failed closed 20/20 without changing their bytes.
Agent identity, raw prompt text, semantic similarity, and time proximity are
excluded from the derivation.

This is Experimental mechanism evidence on one local filesystem with synthetic
assignments. It shows that an explicit assignment can produce a stable,
scope-separated alignment anchor; it does not show that two prompts are
semantically equivalent, solve study-secret distribution or consent, establish
cryptographic collision probability from 20,480 pool samples, or integrate the key
into production SkillRun storage. The product model should treat Task as an
explicit parent shared by runs, rather than infer Task from a run ID or
observed content.

### Verified outcomes can reconnect without exporting source session IDs

The follow-up used the 12 verified live CLI outcomes—four each from Codex,
OpenCode, and Qoder—and compared their stored source-session SHA-256 values
with hashes computed locally from the live database's adapter source-session
IDs. All 12/12 resolved to exactly one session and all 12/12 adapter labels
matched. This repaired the earlier failed attempt to hash SRI's internal
session ID: the correct join boundary is the versioned adapter source identity,
not the storage surrogate key.

An isolated temporary evidence database then imported all 12 outcomes under
one explicit paired-task key and deterministic verifier digest. The first pass
inserted 12/12 records; an identical second pass was idempotent 12/12. A missing
source digest, adapter mismatch, and conflicting outcome were rejected 3/3.
The report exports neither raw prompts nor source session IDs, and the production
database was not mutated.

This is Experimental mechanism evidence for exact live-session linkage and
safe isolated import. It does not establish semantic task equivalence, validate
production migration or consent UX, cover failed verifier outcomes, or make
the current Panorama outcome-complete. It supports using adapter-scoped source
identity as a private join input while keeping the explicit Task assignment as
the cross-Agent comparison fact.

### Alignment manifests need a comparability vector, not one boolean

A nine-case synthetic contract corpus exercised an explicit Cross-Agent
alignment manifest. All 9/9 expected classifications were exact: five cases
were comparable, two partially comparable, and two not comparable. No case
authorized causal attribution.

The contract kept lifecycle, outcome, and absolute-time comparability
independent. A 90-second clock offset masked absolute-time comparison while
retaining lifecycle and outcome comparison. Missing terminal evidence or an
unsupported outcome capability produced a partial comparison rather than a
failure. Task mismatch and uncontrolled Skill-digest mismatch blocked the
comparison. Conflicting reported outcomes remained comparable evidence with a
warning; conflicting independently verified outcomes were marked as a
verified difference, without attributing the cause to the Skill or Agent.

This is Experimental engineering evidence from synthetic cases. The
five-second clock tolerance is a chosen test policy, not an estimated optimal
threshold. The fixtures assume the validity of their verification labels and
do not establish real cross-Agent alignment accuracy or user usefulness.

An 88-evaluation sensitivity sweep then crossed 11 synthetic clock offsets
(0–89 seconds) with eight tolerance policies (0–120 seconds). Absolute-time
acceptance increased monotonically from 1/11 at zero tolerance to 11/11 at
120 seconds. All 88 evaluations preserved lifecycle and outcome comparability,
the overall comparison decision, and the prohibition on causal attribution.

This supports isolating clock policy to the absolute-time view rather than
using temporal proximity as identity or alignment evidence. It does not
support selecting a threshold: the offsets are synthetic, real clock quality
was not measured, and wider tolerance mechanically admits more pairs.

### Timestamp presence does not establish clock comparability

A privacy-safe capability audit checked seven requirements for interpreting
timestamps across Agent sources: event timestamp, timestamp origin, ingestion
timestamp, clock domain, synchronization or uncertainty, precision, and an
explicit source-versus-fallback marker. The baseline schema exposed only the
event timestamp (1/7).

Controlled production hook builders for Qoder, OpenCode, Claude Code, and
Gemini CLI preserved an explicit source timestamp in 4/4 cases and generated
a local fallback for a missing timestamp in 4/4. The baseline persisted schema
could distinguish those fallback values in 0/4 cases.

An additive implementation then introduced timestamp origin, ingestion time,
clock domain, uncertainty, and precision fields without fabricating values for
legacy rows. A migration fixture retained `unknown` origin/domain/precision
and null ingestion/uncertainty for its legacy event. The repeated controlled
audit exposed 7/7 schema capabilities, labeled fallback provenance in 4/4
profiles, and persisted 8/8 source/fallback events with ingestion, domain, and
precision labels. Known clock uncertainty remained 0/8, so
`cross_agent_absolute_time_ready=false` remained the correct gate result.

A reproducible migration audit then opened the live source database read-only,
created a consistent isolated copy, and applied the additive migration only to
that copy. It preserved 41,258/41,258 normalized events and 150/150 sessions,
added all five provenance columns, retained unknown/null values for every
legacy event, and passed SQLite `quick_check`. The report contains aggregates
only. This closes an isolated migration-integrity gate, not live deployment or
clock-quality validation.

The packaged-artifact follow-up built wheel 0.1.6 and completed another fully
isolated offline lifecycle: install, start, status, doctor, stop, and uninstall
all returned their expected codes; native prewarm passed in 459.2 ms; the
fixture project and Agent configuration remained unchanged; and product state
was removed. The packaged upgrade runner then installed that wheel into a
fresh temporary environment, opened a separate read-only snapshot copy with
41,686 events and 151 sessions, and applied migration twice. Counts were
unchanged after both passes. A controlled post-upgrade event increased the copy
to 41,687 events and 152 sessions and persisted exact source origin, ingestion
time, clock domain, 1 ms uncertainty, and second-level precision. SQLite
quick-check passed before and after the write.

This strengthens packaged-artifact, idempotency, preservation, and forward
write-path evidence on one local environment. It does not test downgrade,
concurrent live migration, crash recovery during schema change, or
cross-platform behavior.

A partial-state matrix then preconstructed every prefix of the five-column
additive migration, from zero through all five columns already present. Three
repetitions per state produced 18/18 successful recoveries. Every database
retained its legacy event as unknown/null, completed the missing columns,
survived a second idempotent open, and passed SQLite integrity checking. This
tests retryability from representable partial additive states; it does not
simulate exact process-kill timing, arbitrary corruption, or transactional
downgrade.

The process-kill follow-up used temporary WAL databases and real child
processes. Workers received `SIGKILL` before any provenance addition and after
each of the five committed DDL boundaries. Across three repetitions per
boundary, all 18/18 workers were terminated by signal and all 18/18 databases
recovered on a clean `Storage` open. Every case preserved the legacy event as
unknown/null, completed missing columns, survived a second idempotent open,
and passed SQLite integrity checking. The observed environment was
Darwin/arm64, Python 3.11.7, SQLite 3.41.2, and a one-minute load of 6.78 on
12 logical CPUs. This is committed-boundary recovery evidence; it does not
simulate termination inside SQLite atomic DDL, power loss, or filesystem
corruption.

A lock-contention follow-up held a real WAL writer transaction while a clean
process attempted migration. Two repetitions each at 50 ms, 250 ms, and one
second completed successfully within the configured five-second busy timeout.
Observed end-to-end waits ranged from 324.9 to 1,087.0 ms. A 5.5-second lock
produced the predeclared initial failure at 5,506.6 ms, after which a clean
retry completed. All 7/7 cases retained the legacy event as unknown/null and
passed SQLite integrity checking. The host one-minute load was 13.46 on
12 logical CPUs. These are environment-sensitive timing results from one lock
shape; they support bounded timeout and recovery behavior, not a general
concurrency guarantee.

A read-only follow-up removed write permission from both a temporary legacy
database and its directory before opening `Storage` in a separate process. All
3/3 attempts failed as expected, all 3/3 left the five provenance columns
absent and the single legacy event intact, and all 3/3 recovered after write
permission was restored. SQLite quick-check passed before and after recovery.
This supports non-destructive prerequisite failure on one POSIX environment;
it does not cover read-only network mounts, power loss, or mid-write I/O
failure.

An old-writer compatibility follow-up used the pre-migration column list in
three schedules: a legacy write held before migration but released within the
busy-timeout budget, a legacy write issued after migration completed, and a
legacy write held beyond the budget before clean retry. All 7/7 cases retained
both events, completed or recovered the migration, and stored the old writer's
new provenance fields as unknown/null. This supports the compatibility
mechanism created by additive columns with defaults. It does not execute a
packaged historical binary, cover multiple writers, or make legacy events
temporally comparable; compatibility prevents data loss but does not upgrade
evidence quality.

A historical-contract follow-up extracted three verified local Git commit
objects: the bootstrap Panorama snapshot, the SkillRun-core transition, and
the v0.1.0 release commit. They produced three distinct schema fingerprints
with zero timestamp-provenance columns. Across three trials per snapshot, all
9/9 current migrations retained the controlled legacy event as unknown/null,
passed a second idempotent open, and passed SQLite quick-check. This replaces
the earlier plan to describe hand-built partial states as “three historical
versions.” It is source-snapshot compatibility evidence, not proof for
published wheel artifacts or every schema ever written in the field.

The release-artifact follow-up queried the v0.1.0 GitHub release metadata,
downloaded its wheel into a temporary directory, and verified the published
SHA-256 `23b707b3...d09` before execution. With `PYTHONPATH`, `PYTHONHOME`, and
virtual-environment hints removed, the isolated install reported version
0.1.0 and all 3/3 databases migrated conservatively, including a second
idempotent open and SQLite quick-check. The repository-local wheel with the
same filename had SHA-256 `9e6200cc...ece`, so it was recorded as a comparison
artifact rather than substituted for the published release. Filename and
version strings alone are insufficient artifact identity.

An earlier pilot report from the same cycle is invalid for release-version
identity: its subprocess inherited the experiment runner's `PYTHONPATH=src`,
causing metadata discovery to observe the working tree instead of only the
installed wheel. The corrected harness removes these variables and changes
the subprocess working directory. The invalid pilot is retained as a harness
audit trail and is not counted as a release compatibility result.

The expanded v0.1 release-wheel matrix queried and downloaded v0.1.0 through
v0.1.6. All 7/7 wheels matched the GitHub release digests and their isolated
installed versions; all 21/21 controlled databases migrated with conservative
unknown/null legacy provenance, an idempotent second open, and integrity
checking. The seven releases produced one identical pre-migration schema
fingerprint. Within this bounded release family, migration-contract testing
can therefore be deduplicated by schema fingerprint while artifact digest and
installed-version identity remain per-release gates. This does not show that
runtime behavior is identical across releases or that future releases will
share the same schema.

The distribution-parity follow-up paired every v0.1.0–v0.1.6 wheel with its
release sdist. All 14/14 artifacts matched their individual release digests
and metadata versions. The sdist runner validated archive paths and proved the
resolved `storage` module was inside the extracted artifact before execution.
All 7/7 version pairs generated the same schema fingerprint within the pair,
and all 42/42 wheel-plus-sdist migration trials preserved unknown/null legacy
semantics and idempotency. This supports schema-contract parity for the
published v0.1 distributions; it does not establish complete runtime parity,
and direct source-tree execution is not the same as rebuilding the sdist into
a wheel.

The offline-rebuild follow-up rebuilt every v0.1 sdist twice with network
access disabled and the local build toolchain recorded. All 7/7 first rebuilds
matched their published wheel on selected package metadata, Python
requirements, CLI entry points, wheel tags, and schema fingerprint; all 14/14
published-plus-rebuilt migration trials passed. Byte identity was different:
0/7 rebuilt wheels matched the published digest, and only 2/7 pairs of
immediate local rebuilds matched each other. This separates semantic contract
reproducibility from byte-for-byte reproducibility. Two builds per version
cannot identify the cause of digest variation, and build isolation was
intentionally disabled to keep the run offline.

A fixed-epoch follow-up set `SOURCE_DATE_EPOCH=315532800` and rebuilt each of
the seven sdists three times. All 7/7 version groups produced one repeated
digest and preserved the selected metadata/CLI/wheel-tag contract, compared
with 2/7 repeated digest matches in the adjacent uncontrolled two-build
matrix. None matched the published wheel bytes. Across releases, the 21 common
content differences were exactly `METADATA`, `WHEEL`, and `RECORD` per
version; v0.1.3–v0.1.6 also moved one license member path in each direction.
Published wheels reported Metadata-Version 2.4 and setuptools 83.0.0, while
the local rebuilds reported Metadata-Version 2.1 and bdist_wheel 0.41.2. This
supports testing time normalization and pinned build backends as separate
factors. It does not establish that the epoch alone caused repeatability or
that the same result holds on another toolchain.

A pinned-builder follow-up used Python 3.13.11, setuptools 83.0.0, and wheel
0.46.1 with the same fixed epoch. Across all 7/7 versions, two rebuilds shared
a raw digest, member names matched the published wheel, and a normalized
content fingerprint matched after excluding only ZIP timestamps. Raw
published digests still matched 0/7 because all 249 member timestamps differed.
The normalized fingerprint retained decompressed content hashes, member names,
permissions and attributes, compression type, creator/extractor versions, and
flags. This motivates a three-layer identity model: published artifact digest
for exact provenance, normalized package-content fingerprint for explaining
container-only drift, and schema fingerprint for data-contract compatibility.
The normalized fingerprint is diagnostic evidence and must not replace the
published digest used for trust or download verification.

The Linux follow-up used the arm64 image
`python@sha256:20080e...5d0`, disabled container networking, and installed
content-recorded local wheels for setuptools 83.0.0, wheel 0.46.1, and
packaging 26.2. All 7/7 version pairs matched published normalized content,
member names, and selected contracts; each Linux pair rebuilt to one repeated
raw digest. Those Linux raw digests also matched the prior macOS
Python-3.13.11 pinned-builder report in 7/7 versions. Published raw digests
still matched 0/7 because all 249 ZIP timestamps differed. This is
cross-environment reproducibility evidence for pure-Python wheels under these
two builders, not evidence for native binaries, other architectures, or an
unrecorded dependency supply chain.

The native-sender follow-up separated published-file identity, internal
structure, symbols, and observable transport behavior. All four v0.1.6 assets
matched the recorded digest and size, and all six inspected Mach-O/ELF slices
exposed the externally required `main` entry point. Internal static helpers
were recorded only as diagnostics because optimization may inline them. On
the executable arm64 paths, the macOS and network-disabled Linux runs each
delivered 20/20 exact header-plus-payload messages, emitted no success output,
returned a silent exit 1 for a missing socket, and returned a silent exit 2
for invalid arguments. Functional execution of Darwin and Linux x86_64
remains `not_run`. The two architecture-labelled Darwin downloads had the
same digest and each contained both arm64 and x86_64 slices, showing that a
release filename can be a delivery alias rather than a sufficient statement
of internal architecture. These results establish the bounded protocol
contract on two arm64 environments; they do not establish source equivalence,
security, real-Agent end-to-end behavior, or x86_64 functionality.

The verified-source rebuild follow-up resolved tag v0.1.6 to commit
`28f146c...163f`, matched the recorded source and release-workflow digests, and
verified both selected published asset identities before compiling. A local
Apple clang universal2 build and a GCC 14.2 Linux arm64 build used the release
flags; Linux build and runtime containers were separately digest-pinned and
ran with networking disabled. Both Darwin and Linux published/rebuilt pairs
passed the external structure and exact protocol/failure contract. Across
four binary executions, 80/80 messages were delivered exactly and silently.
Raw digests and section fingerprints matched in 0/2 pairs, while full symbol
fingerprints matched in 1/2. This shows that observable contract parity can
survive build-dependent binary drift, but it does not make the rebuilt files
the published artifacts or prove source equivalence.

Two adjacent completed runs also reversed their Darwin prewarm ordering:
published versus rebuilt was approximately 270 ms versus 5.21 s in one run
and 884 ms versus 383 ms in the next. With no controlled intervention, this
cannot identify a compiler, signing, cache, or security-scanning effect. It
does show that cold-launch behavior needs a separate repeated distribution
and must not be inferred from raw, section, or protocol identity.

The path-reuse follow-up then ran three separately rebuilt, balanced
four-condition sequences. Each sequence crossed published versus rebuilt
Darwin universal binaries with a stable executable path versus a newly copied
pathname. All 144/144 missing-socket launches returned silent exit 1. Across
the three runs, stable-path p50 ranged from 23.2–47.8 ms for the published
binary and 23.4–46.6 ms for the rebuild; fresh-path-copy p50 ranged from
199.0–235.1 ms and 198.5–241.1 ms respectively. Pooled p50 was 28.2/29.9 ms
for stable paths and 213.0/220.6 ms for fresh copies. The fresh copy was slower
in 33/36 published and 34/36 rebuilt paired blocks. Both artifacts displayed
linker ad-hoc signature metadata, failed strict whole-object verification in
the recorded invocation, and carried a `com.apple.provenance` extended
attribute after copying.

This is repeated single-host path association, not a cache, signature,
provenance, or security-scanning mechanism result. A fresh pathname does not
reset the machine or establish a cold OS state, and blocks share scheduling
and cache context. The product implication is narrower: prewarm evidence
should bind to the final executable path, artifact digest, host context, and
time. Copying, replacing, or relocating the executable should invalidate that
evidence instead of inheriting a generic `prewarmed=true`.

The controlled-factor follow-up first attempted a preregistered
placement × provenance × signature pilot on temporary copies. All 8/8 launch
contracts passed, but only 4/8 factor setups passed. In every provenance-removal
cell, the deletion command returned success but the attribute was already
present again at the immediate pre-launch audit. Those four cells were rejected
as `not_identifiable`; their latency was not used as provenance-factor evidence.
This demonstrates why intervention success must be scored from the realized
postcondition rather than the mutation command's exit code.

The revised v2 matrix excluded that uncontrolled factor and retained
direct-copy versus atomic-replace placement plus original-linker versus strict
ad-hoc-resigned state. Across three balanced runs, 96/96 factor audits and
96/96 silent launch contracts passed. Placement's per-run marginal-delta p50
was +74.4, −1.1, and −44.2 ms, with exactly 4/8 positive blocks in every run.
Signature's per-run delta p50 was +3,006.0, −79.8, and −89.6 ms, with 8/8,
1/8, and 2/8 positive blocks. Thus neither factor retained a consistent
run-level direction. Pooled re-signed p50 values were lower than original,
while their p95 values retained the first run's multi-second tail; a flat pool
would conceal this phase change. The result rules out a simple stable
same-host signing penalty in this sequence, but does not explain the transient
first-run behavior.

For the product and paper, manipulation fidelity and phase boundaries must be
first-class evidence. A performance aggregate should preserve run, first-use,
artifact, path, and environment strata before displaying a pooled summary.
Otherwise a global p50 can hide precisely the nonstationarity the Doctor is
supposed to diagnose.

A phase-readiness audit then scored the same 96 raw trials without fitting a
change point to the short interleaved sequence. Raw-trial availability,
correctness, manipulation checks, run boundaries, and within-run position
balance passed; stable host identity, independent-host replication,
cross-run factor direction, established steady state, and confirmatory sample
size justification did not. The audit therefore passed its own integrity gate
at 5/10 evidence criteria while returning
`descriptive_analysis_ready=true` and `confirmatory_effect_ready=false`.
Re-signed cell run-p50 max/min ratios were 15.6–16.7×, while original-linker
cells were 1.04–1.17×. This localizes observed nonstationarity to the
manipulated state in this sequence, but still does not identify its mechanism.

The resulting protocol follows three established benchmarking lessons:
steady state must not be assumed and may require changepoint evidence
([Barrett et al.](https://arxiv.org/abs/1602.00602)); repetition levels and
uncertainty must remain explicit
([Kalibera and Jones](https://kar.kent.ac.uk/33611/)); and innocuous setup
details can bias conclusions, motivating balanced/randomized setup and bias
audits
([Mytkowicz et al.](https://sape.inf.usi.ch/publications/asplos09.html)).
These papers support the methodology, not a claim that the native sender has
the same runtime mechanism.

The host-identity follow-up tested a candidate mechanism for future
independent-run evidence without fingerprinting the machine. A local UUIDv4
secret was created atomically with 0600 permissions; exports contained only a
128-bit-truncated HMAC-SHA256 alias derived from the secret and an explicit
scope. The initial invocation used three trials with eight workers per trial.
A separate follow-up invocation increased concurrency to 12 workers across
five trials. Across both invocations, 84 concurrently started processes
converged on one alias per scope in 8/8 trials, aliases differed across all 8/8
paired scopes, and the local secret appeared in zero export payloads. Corrupt
UUID content, 0644 permissions, and symlink identity paths each failed closed
in 8/8 trials and left the underlying bytes unchanged.

A third invocation ran the same five-trial, 12-worker contract inside the
network-disabled Linux arm64 image
`python@sha256:20080e807bfc404f8450b185cf0fc95d553462673598549613735f70a5b4d5d0`.
All 5/5 Linux trials passed the same stability, separation, permission,
redaction, and fail-closed checks. Across macOS and Linux this gives 13/13
passing trials and 144 worker initializations. The container report recorded
Python 3.13.11 and Linux arm64, but reported the Git commit as unavailable
because the pinned runtime image did not contain Git; the image digest and raw
report path therefore remain necessary companion provenance.

These repeated invocations support a privacy-minimizing host-linkage mechanism
for future experiments: study runs can share an explicit study scope, while
support cases or exports use a different scope. The larger worker count and
Linux container test local initialization contention and operating-system
semantics, not additional physical hosts; they therefore do not make an alias
anonymous, test rotation or consent UX, establish independent-host
replication, or retroactively repair historical reports that omitted host
identity. Hostname, hardware serial, MAC address, and username remain forbidden
identity inputs.

This is a schema-capability result plus controlled mechanism evidence. It does
not show that any stored timestamp is wrong, measure real host clock skew, or
select a synchronization threshold. It shows that schema coverage and time
comparability must be separate gates: adding fields makes provenance
representable, while an absolute cross-Agent timeline still requires measured
or source-supported clock uncertainty. Within-stream relative order remains
independently useful.

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

## Installed-Agent black-box pilot

The 2026-07-31 controlled pilot ran one byte-identical project Skill and task
through the installed Codex 0.145.0, OpenCode 1.18.5, and Qoder CLI 0.1.26.
The design evaluates configured Agent systems, not isolated model or scaffold
effects. This follows the benchmark pattern of fixing the task, environment,
and outcome evaluator while treating the submitted AI system as the evaluated
unit; SWE-bench similarly gives systems a fixed issue/environment and evaluates
the resulting work with fail-to-pass tests
([SWE-bench](https://www.swebench.com/original.html)). OpenCode and Qoder both
document non-interactive CLI execution, so no common downloaded model or
home-built Agent loop is required for this product-level question
([OpenCode CLI](https://thdxr.dev.opencode.ai/docs/cli/),
[Qoder CLI](https://docs.qoder.com/cli/quick-start)).

Four fresh isolated trials were scheduled per Agent. Codex completed and
passed the deterministic hidden outcome check in 4/4 trials; OpenCode also
passed 4/4. All eight successful trials preserved the task-owned fixture.
Codex wall-time p50/p95 was 66.16/73.80 seconds; OpenCode was 55.35/85.14
seconds. OpenCode created Agent-owned `.opencode` dependency/runtime metadata
in 4/4 workspaces, which is now reported separately from task mutation.

The initial Qoder probe was blocked because the active CLI was not
authenticated. Browser device authorization then authenticated the Teams
account on the pinned 0.1.26 binary; the global link had auto-updated to 1.1.9
with a separate credential state, so the experiment invoked the authenticated
binary explicitly without changing that link. The authenticated batch
produced 3/4 verified outcomes and one 240-second timeout. One separately
reported retry completed in 152.77 seconds. The correct aggregate is therefore
four verified outcomes from five attempts with one timeout, not 4/4. Successful
Qoder calls ranged from 26.45 to 158.15 seconds and preserved task inputs 4/4.

The collector window added four Codex sessions and 92 normalized events but
zero Codex SkillRuns. The same window added four OpenCode sessions, 26 events,
and four Observed SkillRuns with confidence 1.0 and basis `opencode PreToolUse
official hook`. The authenticated Qoder runs added four sessions and four
minimal normalized events but zero SkillRuns. Codex outcome messages explicitly named the Skill and its tool
calls read the instructions and ran the verifier, but the privacy-safe raw
envelope retained only payload keys; no safe Skill-reference feature survived
normalization. This is Experimental evidence of adapter-dependent attribution
coverage: a successful task can coexist with a missing SkillRun.

The immediate product implication is to derive a privacy-safe Skill-reference
fingerprint at ingestion time before discarding raw command content. The UI
must also separate task mutation, Agent runtime metadata, outcome verification,
and Skill attribution. The present 4+4+4 successful outcomes establish mechanism
and expose a coverage gap; they do not estimate population success rates or
causal differences among Codex, OpenCode, and Qoder.

An additive Experimental task/outcome schema was then exercised on a
consistent copy of the live Panorama database. A deliberately invalid task
record caused the whole migration transaction to roll back, leaving zero
experimental tables. The corrected migration uses individually executed DDL
statements because Python SQLite's `executescript` implicitly commits an
active transaction; the first benchmark attempt exposed this rollback defect
before any production-schema change. The successful path inserted one
explicit paired-task assignment and 12 verified outcomes (Codex/OpenCode/Qoder
= 4/4/4); a second import was idempotent for the task and all 12 outcomes. An
invalid verifier digest was rejected, deleting the task cascaded only to the
Experimental outcomes while preserving sessions, rollback restored the
records, and downgrade removed both Experimental tables. Core-table counts
were unchanged and `PRAGMA quick_check` returned `ok` before migration, after
migration, and after downgrade. All mutation occurred on a temporary database
copy; this is Experimental migration-mechanism evidence, not production rollout
evidence. Concurrent writers, consent UX, release migrations, UI rendering,
and real failed outcomes remain untested.

The next isolated import preserved the five real unsuccessful attempts that
had previously been excluded from the success-only outcome import: four Qoder
`invalid_response` records from the unauthenticated probe and one authenticated
Qoder `execution_error` caused by the recorded 240-second timeout. The four
invalid responses had a failed deterministic response check; the timeout never
reached that check. None of the five reports carried a source-session identity,
and none resolved to a live session. The new attempt table therefore imported
5/5 as `unresolved`, repeated all five idempotently, and created zero session
outcomes. A constraint test rejected a record claiming `linked` without both a
session and source-session digest. Core counts and database integrity were
preserved through downgrade. This is Experimental evidence for a data-model
boundary: an observed process attempt is not automatically a runtime session,
and a failed attempt without session correlation must not be promoted to a
session outcome. It establishes occurrence and verifier reachability, not the
cause of failure or a Qoder failure rate.

A controlled privacy-safe attempt-correlation contract then ran 20 trials with
1,024 generated tokens per trial. Stable derivation, scope/adapter/nonce domain
separation, finite-pool collision checks, exactly-once late binding, idempotent
replay, rejection of wrong-adapter, unknown-token, and conflicting-rebind
requests, and absence of raw propagated tokens from the database dump all
passed 20/20. Across the four frozen synthetic conditions in each trial,
`authentication_failure` and `timeout_before_session` remained pending, while
`crash_after_session` and `malformed_response` bound to their controlled
sessions; every trial ended with two pending and two bound attempts. The
20,480-token collision check observed no duplicates but is not a proof of
uniqueness. W3C Trace Context likewise motivates opaque random identifiers to
reduce unintended information exposure, and OpenTelemetry span links motivate
associating asynchronously started work when its start time is not predictable
([W3C Trace Context](https://www.w3.org/TR/trace-context/),
[OpenTelemetry traces and span links](https://opentelemetry.io/docs/concepts/signals/traces/)).
Our contract is deliberately narrower: it persists only a token digest, treats
the edge as correlation evidence rather than causal authorization, and remains
Experimental synthetic mechanism evidence. No installed Agent propagated this
token, and concurrent binders or crash recovery were not tested.

The first installed-Agent propagation pilot then ran the same deterministic
fixture through OpenCode 1.18.5 four times using its official project-plugin
`session.created` and `tool.execute.before` surfaces. The raw attempt token was
read once from the parent process environment and deleted before any
model-requested child process; the hook emitted only its SHA-256 digest and the
source session identity into a temporary experiment file. All four calls
completed, passed the hidden outcome verifier, and linked the token digest to
exactly the session reported by the OpenCode JSON stream. Each trial produced
three hook records across the two expected event types and one unique session.
The scanner found the raw token in neither stdout, stderr, the temporary
evidence file, nor the isolated workspace in 4/4 trials; task-owned inputs were
unchanged 4/4. Wall-time p50/p95 was 16.69/24.17 seconds. OpenCode runtime
metadata initialization remained separate under `.opencode`.

During the same window the existing production observer advanced OpenCode from
9 to 13 sessions, 47 to 73 normalized events, and 6 to 10 Observed SkillRuns,
matching deltas of +4 sessions, +26 events, and +4 SkillRuns. The correlation
pilot itself did not write token links into the production database. These are
Experimental single-system mechanism observations: they show that one
installed OpenCode configuration can carry the minimal context through an
official hook without observed raw persistence, not that the token improves
outcomes, has zero leakage risk, or works in Codex or Qoder.

A follow-up randomized blocked ablation loaded the identical project hook in
both conditions and varied only whether a correlation token was supplied.
Eight blocks each contained one token-on and one token-off call in seeded
random order. All 16 calls completed and passed the deterministic outcome
verifier with zero task-owned input mutations. Token-on produced exact session
correlation in 8/8 cells; token-off emitted no correlation evidence in 8/8.
There were zero raw-token persistence findings. Token-on/off wall-time p50 was
16.69/20.79 seconds and p95 was 24.77/28.19 seconds. More importantly, the
within-block on-minus-off differences ranged from -13.35 to +8.10 seconds,
with mean -2.03 seconds, median -0.48 seconds, and a descriptive paired
bootstrap 95% interval of [-6.74, +2.51] seconds. The interval crosses zero and
the pair directions are mixed, so this experiment does not establish
acceleration, zero overhead, or a non-inferiority margin. The functional
non-interference gate passed; the latency-effect question remains unresolved.
The observer independently added 16 sessions, 110 events, and 16 Observed
SkillRuns during the experiment.

The post-run privacy-safe readiness audit counted 415 SkillRuns across three
adapters: Codex 408, OpenCode 6, and Qoder 1. The new OpenCode trials moved the
minimum-run descriptive check to pass for two adapters, but the descriptive
gate remained 1/3 and the confirmatory gate 0/8. There were still zero shared
Skill digests, only two shared lifecycle stages, no paired-task key, and no
`outcome.verified` events in the runtime database. The audit's label criterion
now requires independently adjudicated labels rather than human participants;
model adjudication must retain its model/prompt/sampling provenance and is
never relabeled as human evidence.

## PAI-DSW Linux replication

The repository's first formally attributable PAI-DSW result was run on
`dsw-2032100-64b9d7c65d-tg9lx`, an Ubuntu 22.04/Linux x86_64 environment with
Python 3.12.13 and one NVIDIA H20. Earlier DSW state contained only an empty
SRI workspace marker; local result bundles had no non-null
`pai_dsw_instance_id`, so prior local and container results are not relabeled
as DSW evidence.

The first suite execution passed 10/13 gates. E0 scored 13/14, E3 first-visible-
boundary readiness scored 10/11, and E5's inference-layer separation gate
failed. All three failures came from the same `reported_outcome_only` case.
The production rule correctly requires a declared verification expectation
before creating an `outcome_unverified` Finding, while the experiment fixture
expected that Finding without setting `behavior_assessment.verifier_expected`.
Running the same three scripts on macOS reproduced the exact failures, which
rules out a DSW-specific explanation for this instance of the regression.

The fixture was changed only to declare `verifier_expected=true`; the product
diagnostic rule was not relaxed. Relevant tests then passed 15/15 locally, and
the three directly affected gates returned to E0 14/14, E3 11/11, and E5
separation pass. The full DSW rerun passed 13/13 suite gates, comprising 12/12
deterministic correctness gates and the environment-sensitive Linux hook-
transport gate. The result records Git revision
`a1f2cfca6a4c7cc75e7a995ed54f48ca99c131f9` with `git_dirty=true`, because the
fixture correction was intentionally evaluated before any commit.

This run supports deterministic cross-environment reproducibility and exposes
an experiment-contract failure mode: a missing declared expectation can make
the benchmark demand behavior that the product correctly treats as neutral.
It does not evaluate an H20-hosted language model, installed Codex/OpenCode/
Qoder on Linux, native binaries on additional hardware, or a general Linux
performance distribution.

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
- Execute the published native sender on independent Darwin x86_64 and Linux
  x86_64 hosts; compare source rebuilds with the published binaries at raw,
  section, symbol, and protocol layers.
- Replicate E3 with more fresh-session sample slots and at least one additional
  model family. Keep per-model results separate, predeclare malformed-response
  handling, and do not promote the current single-model pilot to a general
  product-effect claim.
- Expand the same pinned Skill/task beyond the current four verified outcomes
  per installed Agent. Qoder required five authenticated attempts and had one
  240-second timeout; preserve this failure and stratify cold/warm execution
  before estimating latency or reliability. Do not replace installed-system
  observations with a downloaded common model because that would answer a
  different model- or scaffold-level question.
- Evaluate an evidence-citing semantic model on novel real failures; keep all
  outputs Inferred and measure calibration and unsupported-claim rate. Compare
  it with an ordered relational/graph baseline, not only flat retrieval.

## 2026-08-01 DSW transport, native, and semantic expansion

Five default Linux hook-transport runs on PAI-DSW accepted 400/400 events and
passed 5/5 integrity/performance gates. Pooled direct p50/p95/p99 were
0.462/1.163/1.574 ms; shell values were 0.901/1.739/1.986 ms. Two additional
prewarm runs and forward/reverse contention blocks also retained exact delivery
(320/320 contention events). Ratio-to-idle p95 varied up to about 22× because
the idle denominator was sub-millisecond while absolute p95 remained low. This
is single-host Experimental mechanism evidence; the five-run all-pass Wilson
interval is still approximately [0.566, 1.0].

The published v0.1.6 Linux x86_64 native sender was then executed on the same
identified DSW host. Its 16,632-byte artifact and SHA-256 matched the release
manifest, required ELF symbols were present, 40/40 socket payloads were exact,
and 40/40 successful calls were silent. Missing-socket and invalid-argument
exit/silence contracts also passed. This closes the previously unexecuted
Linux x86_64 path on one host; it is not cross-host reliability evidence.

Qwen3.6-35B-A3B provided a third E3 model family through a local vLLM server.
All 88 schema-constrained independent requests completed. Raw-view boundary
accuracy was 32/44 (72.7%) and Panorama was 44/44 (100%); unsupported causal
claims fell from 6/44 to 1/44 but did not reach zero, so the integrity gate
failed. Structured output therefore improved interface completion but did not
authorize causal language.

For E5, a consistent read-only snapshot of 463 real SkillRuns produced a
19-case de-identified holdout spanning five production-finding profiles. The
fixture contains only ordered stage states and aggregate event signatures; it
omits identifiers, content, paths, payloads, and timestamps. Its labels are
production deterministic candidates, not independent gold.

The ordered graph baseline reproduced all 19/19 candidate signatures. The
Qwen evidence-citing condition completed 19/19, cited only valid evidence IDs,
and made no causal claim, but achieved 0/19 exact and F1=0.0 while reporting
100 mean confidence. A thinking condition initially failed to emit scoreable
JSON under a 2,048-token budget; the retained 8,192-token retry completed
19/19 but remained 0/19 exact (F1=0.034), with mean confidence 97.6 and latency
p50 about 20.0 seconds versus about 1.1 seconds without thinking. Common errors
bound `run_incomplete` to the wrong stage and relabeled a relationally Derived
gap as Observed. The interface-safety gate (completion, valid citation IDs,
causal safety, and Inferred-layer separation) passed, but diagnostic agreement
did not. This supports deterministic ordered relations for known diagnoses and
restricts model assistance to separately reviewed explanations or novel-pattern
candidates. Citation-ID validity alone is insufficient; the cited evidence must
also entail the relation and evidence grade.

The installed-Agent expansion also exposed harness and observability limits.
Codex completed and verified 4/4 new trials with no workload mutation but added
no SkillRuns; OpenCode completed 2/4 and timed out twice at 120 seconds while
adding four observed SkillRuns. The runner now freezes executable version before
launch and terminates/reaps the entire process group on timeout. Qoder's pinned
authenticated binary was removed during an automatic update and the current CLI
is logged out, so the attempted expanded Qoder batch is retained as incomplete
and will not be reported as completed until authentication is restored.

Authentication was subsequently restored for Qoder CLI 1.1.10 and the frozen
four-trial expansion completed. All 4/4 calls returned the expected value,
passed the hidden verifier, and preserved both workload and runtime-metadata
digests. Wall-time p50/p95 was 18.90/22.82 seconds. The collector added exactly
four Qoder sessions, four Observed SkillRuns, and 24 events during the window.
The earlier authenticated 0.1.26 observations added sessions but no SkillRuns.
Because Agent version, authentication state, scheduling, and cold/warm state
changed together, this is a version-stratified observation rather than a causal
upgrade claim; it supports rerunning adapter capability probes after upgrades.

A fresh post-Qoder privacy-safe real-corpus audit now contains 468 SkillRuns
across 91 sessions and three adapters (Codex/OpenCode/Qoder = 427/36/5). It has 20 stage
profiles and five finding combinations, but zero verified-outcome events, zero
explicit failed events, and zero independently adjudicated labels. The real
corpus readiness check therefore passes 4/7 exploratory criteria and remains
not confirmatory-ready. Cross-Agent descriptive readiness remains 1/3 and
confirmatory readiness 2/8: there is no shared Skill digest, only two shared
lifecycle stages, no paired-task key, a 426× run imbalance including the single
Qoder run, and no verified/failure/adjudication coverage.

The dominant finding is a Derived activation evidence gap in 424/468 runs
(90.6%). This is evidence of a systematic observability/capability pattern in
the current corpus, not evidence that activation failed in 423 independent
runs. A product should group such findings by adapter/capability signature and
expose their coverage denominator before issuing run-level notifications.

Final implementation verification passed 249 repository tests with three
environment-dependent skips. The local reproducibility suite passed 13/13
gates (12 correctness and one environment-sensitive), matching the corrected
PAI-DSW 13/13 suite. These suite passes do not erase intentionally failed
research gates: Qwen E3 still contains one Panorama causal overreach, OpenCode
still has two retained 120-second timeouts, and both real-corpus readiness
audits remain below confirmatory thresholds.

The catalog-cardinality pilot was upgraded to four randomized sequential
blocks. All 12/12 Codex conditions selected the intended checksum Skill,
executed its verifier, produced the correct hidden outcome, loaded no synthetic
distractor, and preserved the workspace. Relative to zero distractors, 32
semantically disjoint distractors increased Agent-reported input tokens in all
four blocks by 4,301, 4,837, 4,910, and 4,810 tokens (mean 4,714.5, about 147
tokens per added Skill; descriptive block bootstrap interval 4,435–4,885).
The paired wall-time mean was +5.22 seconds with a descriptive interval of
+2.88 to +7.56 seconds. Sequential single-machine blocks leave time drift as a
covariate, and disjoint synthetic descriptions do not estimate semantic
collision. The result supports a catalog-footprint budget even when target
selection remains correct.

## 2026-08-01 confirmatory tranche

The remaining five confirmatory experiment classes were executed as one frozen
tranche. The reproducibility ledger is
`experiments/confirmatory_manifest_20260801.json`; every local result is bound
by SHA-256, and failed scientific gates remain failed.

### Balanced installed-Agent failures and verified outcomes

Codex, OpenCode, and Qoder each ran 20 isolated attempts under a balanced
success, execution-failure, and resource-failure schedule. All 60/60 calls
returned the nonce-bound result expected by an external verifier, preserved the
workload, and matched exactly one collected source session. Each Agent
therefore contributed 13 externally verified non-zero process failures and
seven verified successes. These are controlled real subprocess outcomes, not
naturally occurring production incidents.

The central negative result is consistent across all three adapters: zero of
the 20 exact-matched sessions per Agent contained an explicit normalized
`failed` event, even though the external verifier observed 13 failure outcomes
per Agent. OpenCode and Qoder each produced 20 SkillRuns, while Codex produced
none for the exact trial sessions. This confirms an outcome-to-telemetry
semantic gap; it does not justify synthesizing Observed failure events from an
Agent's final prose.

### Catalog 2×2×2×2 factorial

A randomized, balanced three-block Codex experiment crossed catalog
cardinality (8/32 distractors), description length (short/long), semantic
overlap (disjoint/overlap), and instruction disclosure (flat/progressive).
All 48/48 calls selected the target Skill, loaded no distractor body, executed
the hidden verifier, returned the verified outcome, and preserved the
workspace. Descriptive marginal high-minus-low differences in Agent-reported
input tokens were +3,527.75 for cardinality, +13.75 for description length,
-620.5 for semantic overlap, and +17,116 for progressive disclosure. Wall-time
differences were -0.15, -0.82, +1.06, and +6.14 seconds respectively.

The progressive condition required a second reference read; in this installed
Agent/scaffold, file layering increased rather than reduced total input tokens.
Thus progressive disclosure is a mechanism whose value depends on routing and
context-retention policy, not a synonym for lower prompt cost. The three
concurrent blocks are controlled fixture evidence, not a deployment-wide
causal estimate.

### Independent double adjudication and citation entailment

The stored Qwen thinking outputs and a fresh independent DeepSeek-v4/OpenCode
run were scored against the frozen 19-case de-identified real-run holdout. Qwen
had 19/19 citation-ID-valid cases but 0/19 relation-entailing cases. DeepSeek
completed 19/19, achieved 5/19 exact candidate-label matches and F1=0.516, kept
19/19 causal-safe, but only 3/19 cases had relation-entailing citations. The
models agreed on complete predicted finding sets in 3/19 cases, disagreed in
16/19, and produced zero cases containing a shared citation-entailed finding.

The double-adjudication gate passes only because both independent reports were
completed and the disagreement ledger was preserved. It is explicitly not an
accuracy pass. These results reject model agreement or citation existence as a
release gate for known runtime diagnoses; deterministic graph relations remain
the supported path.

### Rule-external pattern discovery

A separate preregistered controlled holdout paired anomalies and clean controls
for six relations outside the production rule set: temporal order, parent
cycles, evidence-grade escalation, reported/verifier conflict, capability
drift, and orphan references. Qwen completed 12/12 with detection F1=0.80 and
10/12 preregistered support relations valid. DeepSeek completed 12/12 with
F1=0.923 and 11/12 support relations valid. They agreed on 9/12 predictions and
both supported 9/12 cases. The three disagreements were retained.

This supports a narrow product role for models: proposing Inferred candidates
on rule-external graph patterns, followed by deterministic support checks and
review. Because the holdout is synthetic and its labels were authored with the
experiment, it measures controlled discovery behavior rather than production
incident precision or prevalence.

### Second Linux native transport environment

The hook transport benchmark was independently rerun inside a Linux arm64
container (Python 3.11.2, GCC 14.2) on the local macOS host, complementing the
remote PAI-DSW Linux x86_64 execution. Its native sender was built and executed
in that Linux environment. Direct and shell paths accepted 80/80 events with
zero exit failures and zero non-silent calls. Direct actual p95 was 2.677 ms
with incremental p95 2.354 ms; shell actual p95 was 2.842 ms with incremental
p95 1.871 ms. The prewarm failure contract and the full SLO gate passed.

This closes second-Linux-environment mechanism replication. The container
shares the local physical host, so it is not a second independent Linux
physical host. Published Linux x86_64 artifact identity/protocol evidence still
comes from the remote DSW host; cross-host reliability of the exact published
binary remains outside the supported claim.

### Confirmatory interpretation

All five planned experiment classes were executed. The results are sufficient
to support the paper's evidence-architecture claims: external outcomes and
runtime attribution are distinct, citation entailment is stricter than citation
existence, known relations favor deterministic graphs, model value is strongest
as guarded hypothesis generation, catalog cost is multi-factor, and native
transport remains non-intervening across the two tested Linux environments.

They are not sufficient to claim model-grade diagnosis accuracy, production
failure prevalence, causal Skill effectiveness, or deployment-wide native
reliability. In particular, both independent known-relation adjudicators failed
the entailment gate. That negative result is part of the paper evidence rather
than unfinished execution.

## 2026-08-01 multi-repository external-validity closure

The final confirmatory benchmark froze three tracked files at the current Git
commit of each of six real repositories, overlaid one repository-specific,
read-only audit Skill, and crossed Codex, OpenCode, and Qoder with clean plus
six controlled fault conditions. The 126-cell matrix preserved every source
worktree and exactly correlated 126/126 Agent calls to one source session. The
nonce-bound response oracle passed 122/126: Codex 42/42, OpenCode 38/42, and
Qoder 42/42. The four OpenCode response failures are retained rather than
retried. Therefore the source-correlation/read-only gate passes, while the
separate all-responses gate fails.

Reconstruction exposes a large adapter-semantic gap. Codex reconstructed no
SkillRuns. OpenCode reconstructed SkillRuns for all 42 sessions but detected
none of the 24 injected failure conditions. Qoder reconstructed all 42 and
flagged all 24 failures, yet also flagged all six clean conditions; its exact
failure-boundary rate was only 0.25. Thus event presence or apparent recall is
not boundary fidelity. Adapter capability must be reported with coverage,
specificity, and localization together.

The privacy-safe diagnostic holdout contains all 126 cases and omits raw
content, paths, and source session identifiers. It evaluates Raw model,
Panorama model, deterministic Graph-only, and Graph+Model views. On remote
PAI-DSW, Qwen completed 378/378 model calls. Raw exact diagnosis was 72/126
(0.571), Panorama 82/126 (0.651), Graph-only 126/126, and Graph+Model 125/126
(0.992). Panorama changed boundary localization from 72 to 108 cases, but
citation entailment fell from 62 to 46. The sole Graph+Model mismatch retained
the correct clean status and used boundary `outcome` rather than the frozen gold
convention `none`; it is a boundary-label sensitivity observation, not evidence
of general model-induced degradation. These results separate answer accuracy from
evidence-chain correctness and support making the deterministic graph
authoritative, with model output as a guarded, non-authoritative explanation.

A fresh local OpenCode/DeepSeek run completed only 228/378 calls: 111 timed out
and 39 returned invalid structured output. Its completed subsets were highly
accurate (Raw 69/72, Panorama 72/78, Graph+Model 76/78), but the preregistered
availability/safety gate fails; subset accuracy is not promoted to a full
cross-model confirmation. This is also a product result: deterministic graph
diagnosis must remain available under model timeout, malformed output, or
provider degradation.

This closes the experiments required for the paper's core systems and evidence-
architecture claims. The supported claim is controlled mechanism coverage across
six frozen three-file repository profiles, three installed Agent systems, seven conditions, and
two model backends. It does not establish natural-incident prevalence, human
usability, causal Skill effectiveness, or unconstrained production diagnosis
accuracy. The frozen artifact ledger is
`experiments/external_validity/confirmatory_manifest_20260801.json`.

## 2026-08-01 reviewer-driven controls

### Semantics-matched Raw control

A 126-call Qwen control retained every raw/native and auxiliary record while
adding inline lifecycle, kind, status, and evidence-grade aliases aligned with
Panorama. All 126 calls completed with valid citation IDs and causal-safe
outputs. Semantics-matched Raw scored 49/126 exact, 108/126 boundary exact,
49/126 status exact, and 26/126 citation entailment. Panorama scored 82, 108,
100, and 46 on the same metrics.

The paired semantics-matched Raw/Panorama result has identical boundary
localization on all 126 cases. At the seven-template level, Panorama/S-Raw
higher-count/equal directions are 3/1/3 for exact, 0/0/7 for boundary, 4/1/2
for status, and 3/2/2 for entailment. The result separates two mechanisms: named lifecycle semantics
account for the boundary change observed against minimally structured Raw,
while compact normalization changes status composition and evidence use. The
seven repeated templates are strongly clustered, so no case-level significance
test or population inference is reported.

A preceding natural-language semantic-legend pilot is retained. It completed
126/126 but scored only 26 exact because it over-selected verifier conflict.
This failed pilot shows that a prose legend is not an equivalent substitute for
field-level semantics and can introduce prompt priming.

### Rule-label-blinded real-trace adjudication

The 19 deidentified runtime graphs were exported without deterministic
candidate labels or label-origin fields. Qwen and Codex independently annotated
the frozen inputs before candidates were revealed. Under the clarified v2
first-boundary rubric, both completed 19/19 with valid citation IDs and causal
restraint. Their exact finding sets agreed on 11/19 cases, and all 11 strict
consensus sets matched the hidden deterministic candidate. Qwen and Codex
individually matched 11/19 and 19/19; post-hoc rubric validation passed 15/19 and
19/19 because Qwen emitted duplicate-code findings in four cases.

The earlier ambiguous-rubric pilot produced 0/19 exact agreement and is
retained. It did not specify earliest-only gap selection or the stage for
run-incomplete. This establishes that annotation protocol version is itself a
measurement instrument. The v2 result provides blinded model-consistency
support for a subset of deterministic candidates; it is not human gold,
production diagnostic accuracy, or evidence that voting upgrades an Inferred
finding. The artifact ledger is
`experiments/confirmatory_manifest_20260801.json`.

### Template-cluster and clean-case correction

The reviewer-driven re-analysis on 2026-08-02 removes all case-level McNemar
values. The 126 rows instantiate seven strongly clustered condition templates;
six of seven Panorama templates have one prediction shared by all 18
agent--repository cells. Case totals remain descriptive coverage of the frozen
matrix, while comparative directions are now reported at template level in
`template-raw-semantic-vs-panorama-20260802.json`.

The clean condition also exposes why Exact must not stand alone. Minimally
structured Raw and semantics-matched Raw emit a failure status on 18/18 clean
instantiations. Panorama emits `verified_success` on 18/18 and therefore has
0/18 failure-state false positives, but it remains 0/18 Exact because its
boundary is `outcome` rather than the frozen convention `none`. These are
different error types, and none of the clean counts estimate a production
false-positive rate.
