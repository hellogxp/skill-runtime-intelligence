# E3 — Model-Agent diagnostic usefulness

`prepare_study.py` creates a deterministic, counterbalanced model-session study
packet for Raw versus Skill Run Panorama diagnosis. It audits condition
balance, evidence citations, and whether the first visible finding matches the
earliest gold lifecycle boundary.

`run_model_study.py` executes each assigned trial in a fresh `opencode --pure`
session, requests a bounded JSON answer, and records exact model/CLI identity,
prompt digest, correctness, confidence, unsupported causal claims, latency,
and a one-way session identity digest. Prompts use stdin, while per-trial
model data/config/cache/state is redirected to temporary storage and deleted
after the response.

`summarize_model_studies.py` recomputes metrics from trial rows, verifies that
reports share one immutable dataset, and preserves per-model effects instead
of pooling heterogeneous model behavior.

`analyze_model_failure_modes.py` performs a post-hoc descriptive audit by gold
finding family and lifecycle stage. Invalid responses count as incorrect, and
model strata remain separate.

`causal_scope_contract_benchmark.py` verifies that deterministic single-Run
findings permit descriptive wording but deny Skill-to-outcome effect claims,
that the full scope/claim policy matrix is exact, and that unknown inputs fail
closed.

`causal_claim_classifier_benchmark.py` evaluates an experiment-only,
fail-closed phrase classifier over negation, quotation, conditional, hedged,
negative-effect, and experimental-estimate wording. The corpus is a
development contract, not a generalization benchmark. A separate post-freeze
challenge exposes synonym, counterfactual, nested-quotation, and multilingual
failures. `fail-closed-v2` abstains on unrecognized wording; it is measured for
false allows and false denies rather than promoted to the product.
`fail-closed-v3` is frozen from those known failures and evaluated without
retuning on `causal_claim_holdout_v2.jsonl`.

`run_claim_output_mode_study.py` runs the same challenge through fresh
schema-constrained and free-text model sessions. Structured `allowed` output
is never trusted directly: the local causal-scope validator recomputes the
decision and records model/guard disagreement.

`summarize_claim_output_studies.py` keeps model strata separate while
aggregating only safety-event counts and replication direction.

`analyze_deny_only_hybrid.py` replays completed structured trials with an
intersection rule: the model-derived scope guard and frozen phrase verifier
must both allow. It reports the safety/usability tradeoff and cannot expand
authorization.

`summarize_prospective_fragility_studies.py` retains per-holdout reports,
stratifies results by scope and expected kind, and enforces predeclared minimum
evidence counts before the threshold can be discussed for product promotion.

`analyze_cross_model_semantic_guard.py` symmetrically replays two distinct
recorded model IDs over the same immutable corpus. Each direction treats one
structured output as producer and the other as a deny-only semantic verifier;
missing responses fail closed and remain in the intention-to-treat denominator.

`summarize_cross_model_guard_studies.py` keeps accuracy by corpus and latency by
producer/verifier direction while aggregating call count, reported token usage,
minimum reconstructed prompt bytes, and safety events. Serial/parallel latency
paths are labeled as computed replays rather than directly executed schedules.

`analyze_semantic_review_router.py` replays frozen-v3 as a cheap conflict
router, never as an authorization source. A second model is consulted only
when the producer is currently allowed and the known local kind disagrees;
the report records review rate, captured errors, and tokens attributable to
the selected reviews.

`run_structured_claim_study.py` executes only schema-constrained trials so a
prospective routing study does not pay for an unused free-text arm.
`prepare_prospective_review_queue.py` freezes the selected-case manifest after
producer completion and before either selected-only or always-on shadow
verifier execution.

`analyze_prospective_review_study.py` verifies those digests and compares the
actually selected-only queue with a separately executed always-on shadow. It
reports missed/captured false allows, false denies, actual verifier tokens,
visible prompt bytes, and computed serial path latency separately.

`analyze_contract_fragility_router.py` evaluates a text-independent routing
signal. It reviews an allowed claim only when both alternative structured
claim kinds would flip the local scope decision; the frozen threshold is a
development candidate for a later prospective holdout.

`prepare_fragility_review_queue.py` freezes threshold-selected reviews and a
deterministic random sample of unselected claims in one pre-verifier manifest,
so prospective blind-spot auditing cannot be chosen after verifier results.

`analyze_prospective_fragility_study.py` validates those manifest/report
digests, evaluates the selected-only final decisions, and reports random-shadow
semantic disagreement and guard errors without letting shadow output affect
authorization.

Passing the preparation gate means the model study is ready to run. Passing a
pilot integrity gate means only that all planned model responses were valid,
session-isolated, and causally guarded. Neither gate is human usability
evidence, and repeated sessions from one model are not independent model
families.
