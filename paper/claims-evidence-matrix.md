# Paper claims and evidence matrix

This file is the authoring guardrail for the paper. A failed scientific gate is
a result, not missing data, and may not be rewritten as a pass.

| ID | Permitted claim | Primary evidence | Prohibited expansion |
|---|---|---|---|
| C1 | All 126 final benchmark calls preserved the workload and correlated to exactly one source session | `experiments/external_validity/results/multirepo-agent-confirmatory.json` | The agents are equally observable or reliable |
| C2 | Current versioned adapters exhibit materially different SkillRun and failure-event semantics | Agent matrix plus reconstruction report | One Agent is intrinsically better than another |
| C3 | Under the controlled fault contract, Codex reconstructed 0/42 SkillRuns, OpenCode emitted failure-like events in 0/24 operational failure cells, and Qoder emitted failure-like events in 24/24 operational failure cells and 6/6 clean cells, with 6/24 exact injected boundaries | `multirepo-reconstruction-confirmatory.json` | Qoder detected or was nonce-attributed to every injected failure; these are production incident rates |
| C4 | On the frozen 126-case controlled holdout, Qwen Panorama had 82 exact diagnoses and 108 exact boundaries versus Raw's 72 and 72; a semantics-matched Raw control reached 108 boundaries, 49 exact diagnoses, and 49 correct statuses. At the seven-template level, Panorama/S-Raw exact-count directions were 3 higher/1 lower/3 equal, and boundary counts were equal in all seven templates. Both Raw views emitted a failure status in all 18 clean instantiations, while Panorama emitted none | Qwen primary report, `multirepo-diagnostic-qwen36-raw-semantic-inline-20260801.json`, and `template-raw-semantic-vs-panorama-20260802.json` | Case counts are population estimates; normalization or semantic aliases generally cause better diagnosis across users or models; the two components are fully isolated causal effects; clean counts estimate a production false-positive rate |
| C5 | Citation entailment changed from 62 Raw to 46 Panorama cases while boundary localization changed from 72 to 108 | Qwen diagnostic report and paired analysis | Citations or normalization are generally harmful |
| C6 | The known-rule graph conformed to 126/126 contract-generated labels; Graph+Model had one clean-case boundary-label mismatch (`outcome` rather than gold `none`) while retaining the correct `verified_success` status | Qwen diagnostic report | This is independent diagnostic accuracy; the single mismatch proves model augmentation generally reduces accuracy; deterministic rules solve unknown/natural failures perfectly |
| C7 | DeepSeek completed 228/378 requested calls; its completeness/safety gate failed | `multirepo-diagnostic-deepseek-confirmatory.json` | Completed-subset accuracy estimates full service reliability |
| C8 | Native and hook collection preserved tested inputs/outputs and achieved low millisecond latency in the named environments | Hook-transport confirmatory reports and experiment summary | Negligible overhead on all machines or workflows |
| C9 | The evidence architecture has controlled mechanism coverage across six frozen three-file repository profiles, three installed Agents, and seven conditions | External-validity manifest and repository profile table | Repository-scale comprehension, natural-incident prevalence, or unrestricted production accuracy |
| C10 | The design supports a deterministic authoritative diagnosis layer with model output stored as Inferred | C4--C7 and system contract | Models should never be used for novel-pattern discovery |
| C11 | On a rule-label-blinded 19-trace v2 adjudication, Qwen and Codex completed 19/19; exact finding-set agreement was 11/19 and all 11 strict consensus sets matched the hidden deterministic candidate; individual candidate agreement was 11/19 and 19/19, with Qwen protocol-valid on 15/19 | blinded holdout, Qwen/Codex v2 reports, and `blinded-real-trace-double-adjudication-v2-20260801.json` | These rule candidates are independent human gold, the 19 traces estimate production accuracy, or two models establish correctness by voting |
| C12 | On six controlled rule-external anomaly/clean pairs, Qwen and DeepSeek achieved support-valid relations in 10/12 and 11/12 cases with three disagreements | novel-pattern model and cross-model reports | This estimates unknown-fault accuracy or natural incident prevalence |

## Required wording conventions

- Use “observed,” “derived,” “inferred,” and “experimental” according to the
  runtime evidence contract.
- Use “controlled fault,” not “production incident,” for the seven-condition
  benchmark.
- Use “one execution per cell,” not a population error rate.
- Report both the Agent integrity gate and the stricter response gate.
- Report DeepSeek timeout and structured-output failures alongside completed
  subset accuracy.
- State that the known-rule graph evaluates contract conformance over
  preregistered relations; graph and gold share the frozen fault contract.
- Do not report case-level significance tests for the diagnostic matrix. The
  corpus instantiates seven strongly clustered condition templates; report
  descriptive case counts and template-stratified directions.
- Do not claim human diagnostic utility: no human participants were used.
- Do not claim causal Skill effectiveness from any single run.
