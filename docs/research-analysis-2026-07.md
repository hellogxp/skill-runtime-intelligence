# Research Analysis: Industry Pain Points, Competitive Landscape, and Product Positioning Refinement

Date: 2026-07-28  
Author: Research synthesis  
Status: Working document for team discussion

---

## 1. Executive Summary

This document synthesizes findings from academic literature search, competitive product analysis, and project-internal documentation to evaluate and refine the product positioning of **Agent Skill Runtime Intelligence**.

**Core finding**: The product occupies a genuine gap that no existing paper or product fills — a **local-first, cross-harness, Skill-lifecycle-first runtime panorama with explicit evidence grading**. The gap is validated by at least six 2026 papers that address adjacent problems (evidence tracing, harness effects, Skill effectiveness, Skill compilation) but none that provide a runtime reconstruction and diagnosis tool specifically for the Skill lifecycle.

**Key recommendation**: Sharpen the product into a **diagnosis-first** experience with a shareable **Skill Health Report**, open-source the event model as a community standard, and build the paper around the **evidence-graded Skill lifecycle reconstruction** with a benchmark dataset. GPU resources enable large-scale paired evaluation experiments that no existing Skill benchmark has done at this granularity.

---

## 2. Industry Pain Points (Evidence-Backed)

### 2.1 Silent Skill Lifecycle Failures

**The problem**: Agent Skills use progressive disclosure — metadata for discovery, full instructions loaded on activation, resources loaded on demand. Each boundary can fail silently. A developer sees a plausible final answer but cannot determine whether the Skill was discovered, activated, fully loaded, or executed correctly.

**Evidence**:

- **SkillsBench** (arXiv:2602.12670, 2026): Curated Skills raise average pass rate from 33.9% to 50.5% (+16.6pp), but effects vary substantially across configurations (+4.1 to +25.7pp). Some tasks regress. Self-generated Skills provide no average benefit. This means a significant fraction of Skill runs produce no measurable value, and the developer has no way to know why.

- **SWE-Skills-Bench** (arXiv:2603.15401, 2026): Most evaluated public SWE Skills provide no pass-rate gain. Some add substantial token overhead. Version-mismatched guidance can reduce performance. The developer cannot distinguish "Skill didn't help" from "Skill wasn't loaded" from "Skill was loaded but instructions were stale."

- **Skill-as-Pseudocode / SaP** (arXiv:2605.27955, 2026): Documents a "confused → re-retrieve → still confused" loop where the agent issues a partially-correct action, receives uninformative environment feedback, and re-retrieves the same prose. This is a runtime behavior invisible to both the agent and the developer.

**Implication for our product**: The #1 pain point is not "did the Skill help" (that's evaluation, which is deferred) but "did the Skill actually run as intended" (that's reconstruction + diagnosis, which is our MVP).

### 2.2 The Harness, Not the Model, Is the Binding Constraint

**The problem**: Agent execution reliability depends more on the infrastructure layer (harness) wrapping the model than on the model itself. The same Skill produces materially different lifecycle behavior across harnesses.

**Evidence**:

- **Agent Harness Survey** (preprints 202604.0428, 2026): "The harness, not the model, is the binding constraint for real-world agent system performance." Defines a six-component completeness matrix: Execution environment, Tool integration, Context management, Scope negotiation, Loop management, Verification.

- **Harness-Bench** (arXiv:2605.27922, 2026): "Agent capability should be reported at the model-harness configuration level rather than attributed to the base model alone." Identifies "execution-alignment failures, where plausible reasoning becomes decoupled from tool feedback, workspace state, evidence, or verifiable output contracts." 5,194 trajectories show substantial variation in completion, process quality, efficiency, and failure behavior across model-harness pairings.

**Implication**: Our product's cross-harness adapter architecture is directly validated. Nobody else provides a Skill-specific view that works across harnesses.

### 2.3 The Evidence/Provenance Gap

**The problem**: Final-answer accuracy cannot explain how an output was produced, which evidence supported each claim, whether tool calls were justified, or where execution failures originated.

**Evidence**:

- **"From Agent Traces to Trust: Evidence Tracing and Execution Provenance in LLM Agents"** (arXiv:2606.04990, 2026): A systematic review establishing evidence tracing and execution provenance as a research area. Introduces a taxonomy covering trace sources, evidence units, provenance relations, tracing granularity, representation forms, and trust functions. Identifies open challenges including "unified trace schemas, claim-level and semantic provenance, provenance-aware safety mechanisms, realistic execution-trace benchmarks, recovery-oriented evaluation, and privacy-aware audit infrastructure."

- **DAIRA** (Zenodo 2026): "Dynamic Observability" — equipping agents with "Perspective Glasses" to mitigate blind exploration. Integrates dynamic analysis into the agent decision loop. Validates that runtime observability changes agent effectiveness.

- **AGENTSAFE** (arXiv:2512.03180, 2025): Governance framework with "semantic telemetry, dynamic authorization, anomaly detection, and interruptibility mechanisms" and "cryptographic tracing."

**Implication**: Evidence tracing is an active research frontier. Our four-grade evidence model (Observed/Derived/Inferred/Experimental) is more concrete and actionable than the conceptual taxonomies in these papers. We can be the first system to operationalize it for Skills.

### 2.4 Skill Portability and Format Sensitivity

**The problem**: The same Skill produces different behavior across agent frameworks due to prompt formatting sensitivity. Skills are authored once as format-agnostic Markdown but behave differently everywhere.

**Evidence**:

- **SkCC** (arXiv:2605.03353, 2026): "Agent frameworks are highly sensitive to prompt formatting, leading to a large performance variation for the same skill." Pass rates vary from 21.1% to 35.1% for the same Skills across Claude Code vs Kimi CLI. Introduces a compiler with a strongly-typed IR (SkIR) to decouple skill semantics from framework-specific formatting.

- **AgentTrap** (arXiv:2605.13940, 2026): Runtime behavior may differ from static appearance. Third-party Skills can combine instructions, scripts, resources, and privileged tools in ways not visible from static inspection.

**Implication**: Our product should explicitly support cross-harness comparison (v0.2 roadmap) and can serve as the observability layer that makes SkCC-like compilation verifiable.

### 2.5 Skill Effectiveness Is Not Activation Frequency

**The problem**: Developers and teams measure Skill "usage" (how often a Skill fires) as a proxy for value. This is a poor proxy.

**Evidence**:

- **SkillsBench**: Activation frequency says nothing about whether a Skill helped. Some frequently-activated Skills regress task performance.

- **Harness-Bench**: "execution-alignment failures" — plausible reasoning decoupled from tool feedback. An agent can "use" a Skill and still produce wrong outcomes.

**Implication**: Our product's path from execution attribution (single run) to controlled effect evaluation (paired trials) is the correct research trajectory. The H4 hypothesis ("Skill activation frequency is a poor proxy for Skill effectiveness") is directly testable with GPU resources.

---

## 3. Competitive Landscape (Updated)

### 3.1 GitHub Ecosystem Snapshot (Web Search, 2026-07-28)

A GitHub search reveals a stark contrast: **Skill collections have massive adoption, but Skill observability tools are nearly nonexistent**.

| Repo | Stars | What it is |
|---|---|---|
| anthropics/skills | 164,707 | Official Anthropic Agent Skills repository |
| obra/superpowers | 262,417 | Agentic skills framework & methodology |
| VoltAgent/awesome-agent-skills | 29,097 | 1000+ agent skills collection |
| addyosmani/agent-skills | 80,701 | Production-grade engineering skills |
| Shubhamsaboo/awesome-llm-apps | 128,250 | 100+ AI agents, skills, and RAG apps |

**vs. Skill observability tools:**

| Repo | Stars | What it does | Our remaining distinction |
|---|---|---|---|
| **SkillPulse** (HarryFunn/skillpulse) | 3 | Runtime reliability: degradation detection, root-cause attribution, offline replay, canary validation. Integrates Langfuse/Phoenix. Python+SQLite, CLI-only. | No visual panorama, no evidence grading, no cross-harness adapters, no lifecycle model; focused on reliability management not diagnosis |
| **claude-token-lens** (wassimbensalem) | 4 | Per-skill/per-tool/per-MCP token attribution for Claude Code. Real-time terminal dashboard. | Only Claude Code; only token cost, not lifecycle; no evidence grades |
| **SkillScope CLI** (notsointresting) | 1 | Which Claude Code skills fire, what they cost, which are dead weight. CLI analytics. | Claude-specific; no panorama DAG; no evidence grades; no lifecycle reconstruction |
| **SkillScope flowchart** (silvesterdivas) | 13 | Static SKILL.md visualization as interactive flowchart. | Static design-time, not runtime reconstruction |
| **agent-skills-eval** (darkrishabh) | 637 | Test runner for agentskills.io-style skills. | Pre-deployment evaluation, not runtime observation; complementary not competitive |
| **Observal** (Observal/Observal) | 2,246 | Control plane & system of record for internal AI components. Registry, discovery, session replay, usage analytics. Supports Claude Code/Cursor/Kiro/Copilot/Codex/OpenCode. | Broader control plane, not Skill-lifecycle-first; heavier deployment; includes registry/governance (we explicitly exclude); no evidence grading |
| **Shepherd** (shepherd-agents) | 1,576 | Runtime substrate: reversible Git-like execution traces. Meta-agents observe, fork, replay, revert. Copy-on-write fork, ~95% KV-cache reuse. Paper: arXiv:2605.10913. | Agent framework/runtime that takes over execution (violates our read-only principle); no Skill lifecycle model; no evidence grading |
| **Sail Skills** (sailresearchco) | 1 | Sail plugin with `sail-voyage` (tracing for long-horizon runs) and `sail-voyage-debugging`. | Sail-specific plugin, not general-purpose; no Skill lifecycle model |

**Key insight**: The Skill ecosystem has hundreds of thousands of users (anthropics/skills: 164k stars) but Skill observability tools have single-digit adoption (SkillPulse: 3 stars). This is the market gap — not because there's no demand, but because nobody has built the right tool yet.

### 3.2 Academic Systems

| System/Paper | What it does | Overlap | Our remaining distinction |
|---|---|---|---|
| SkillsBench (2602.12670) | Paired with/without Skill evaluation across 87 tasks × 18 configs | Effect measurement | Not runtime reconstruction; doesn't diagnose WHERE failure occurred; doesn't reconstruct lifecycle |
| SkCC (2605.03353) | Skill compiler with typed IR for cross-framework portability + security | Cross-framework Skill quality | Static compilation, not runtime observation; no evidence grading |
| Skill-as-Pseudocode (2605.27955) | Markdown→pseudocode conversion with quality control | Skill format quality | Pre-execution optimization, not runtime diagnosis |
| "From Agent Traces to Trust" (2606.04990) | Survey of evidence tracing & execution provenance | Conceptual taxonomy | Survey, not a system; no Skill-lifecycle model; no local tool |
| Agent Harness Survey (2026) | Survey of agent harness as research object | Harness-as-constraint thesis | Survey, not a tool; no Skill-specific lifecycle |
| Harness-Bench (2605.27922) | Benchmark for harness effects across models | Cross-model-harness variation | Benchmark, not a developer diagnosis tool; not Skill-specific |
| AGENTSAFE (2512.03180) | Governance framework for agentic AI | Runtime telemetry, audit | Policy enforcement focus, not observation; not Skill-specific |
| DAIRA (2026) | Dynamic observability for issue resolution agents | Runtime observability | Coding-agent focus, not Skill lifecycle; not cross-harness |
| Agent-as-a-Judge (2601.05111) | Agentic evaluation systems survey | Evaluation methodology | Evaluation, not runtime reconstruction |
| LLM-as-a-Judge survey (2026) | Comprehensive survey of LLM evaluation | Evaluation reliability | Evaluation, not runtime diagnosis |
| **Shepherd** (shepherd-agents, 1576*) | Reversible Git-like execution traces; meta-agent supervision | Runtime trace inspection | Agent framework that takes over execution; no Skill lifecycle; no evidence grading; paper arXiv:2605.10913 |
| **SkillPulse** (HarryFunn, 3*) | Degradation detection, root-cause attribution, canary validation | Runtime reliability | No panorama, no evidence grading, no cross-harness; CLI-only; reads from Langfuse/Phoenix |
| **claude-token-lens** (4*) | Per-skill token attribution | Token cost | Only Claude Code; only tokens; no lifecycle model |
| **Observal** (2246*) | Control plane for AI components: registry, discovery, replay | Component analytics | Broad control plane, not Skill-lifecycle-first; no evidence grading; includes registry/governance |

### 3.3 Commercial/Open-Source Products (from project docs, already known)

| Product | What it does | Overlap | Our remaining distinction |
|---|---|---|---|
| Langfuse | General LLM observability (traces, metrics, evals) | Trace/span ingestion | Not Skill-lifecycle-first; session/trace is primary entity, not SkillRun |
| LangSmith | LLM observability + evaluation | Trace ingestion | Same; no Skill lifecycle model |
| Phoenix (Arize) | OpenInference spans over OTLP | OTLP ingestion | Same; no Skill semantic layer |
| W&B Weave | Call-level tracing + evaluation | Call ingestion | Same; no Skill lifecycle |
| Datadog LLM Obs | LLM observability in APM platform | Span ingestion | Same; enterprise-scale, not local-first |
| Observal | Agent component registry + analytics | Skill usage, cross-agent traces | Broader control plane, heavier; not evidence-graded |
| SkillScope CLI | Claude Code transcript analytics | Activation counts, dead Skills | CLI analytics, Claude-specific; no panorama DAG; no evidence grades |
| SkillScope flowchart | Static SKILL.md visualization | Trigger/step flowchart | Static design, not runtime reconstruction |
| agent-skills-eval | Paired with/without evaluation | Effect measurement | Evaluation harness, not passive panorama |
| Microsoft SkillLens | Skill lifecycle research framework | Generation/consumption analysis | Research framework, not local runtime UX |

### 3.4 The Gap We Fill

No existing paper or product provides all of:

1. **Skill lifecycle as the primary domain model** (discovery → activation → loading → execution → artifacts → outcome) — SkillPulse measures outcomes, not lifecycle; Shepherd traces execution but not Skill-specific lifecycle; Observal tracks usage but not lifecycle boundaries
2. **Cross-source evidence reconstruction** (Skill files + runtime events + transcripts + workspace state) — SkillPulse only reads observability platform data; claude-token-lens only reads Claude Code session files
3. **Explicit evidence grading** (Observed / Derived / Inferred / Experimental) — **No competitor has this at all.** This is our strongest differentiator. SkillPulse does statistical degradation detection (closest to "Experimental") but has no Observed/Derived/Inferred distinction.
4. **Local-first, read-only, no cloud dependency** — Shepherd wraps the agent; Observal requires a server; SkillPulse integrates with cloud observability platforms
5. **Cross-harness adapters** (Claude Code, Codex, with extensibility) — Observal supports multiple harnesses but as a registry, not for lifecycle observation; SkillPulse reads from Langfuse/Phoenix (indirect)
6. **A path from runtime attribution to controlled effect evaluation** — SkillsBench does evaluation but not runtime; SkillPulse does canary but not paired evaluation; nobody connects runtime evidence to measured effectiveness
7. **A visual Skill Run Panorama** as the primary interface — SkillPulse is CLI-only; claude-token-lens is terminal TUI; Shepherd has traces but not a Skill-specific panorama; Observal has session replay but not Skill lifecycle DAG

**The single sharpest differentiator**: Our **evidence grading model** (Observed/Derived/Inferred/Experimental) is completely unique. No competitor, no paper, no product has this four-grade taxonomy operationalized for Skill runtime claims. "From Agent Traces to Trust" (arXiv:2606.04990) has a conceptual provenance taxonomy, but it's a survey, not a system with concrete correlation precedence rules and UI constraints.

---

## 4. Product Positioning Refinement

### 4.0 Market Timing Analysis

The web research reveals a critical timing signal:

**Skill adoption is exploding, but observability tooling hasn't caught up:**

| Signal | Data point | Implication |
|---|---|---|
| anthropics/skills | 164,707 stars | Official Skills repo — massive adoption |
| obra/superpowers | 262,417 stars | Skills framework — even bigger |
| VoltAgent/awesome-agent-skills | 29,097 stars, 1000+ skills | Community curation at scale |
| SkillsBench paper (2602.12670) | 87 tasks × 18 configs | Academic benchmarking is happening |
| SkCC paper (2605.03353) | Cross-framework compiler | Infrastructure is being built |
| Skill-as-Pseudocode (2605.27955) | Format optimization | Skill quality is a research topic |
| Agent Skills specification | agentskills.io | Standardization is underway |
| **SkillPulse** | 3 stars (created July 17, 2026) | Closest competitor is 11 days old |
| **SkillScope CLI** | 1 star | Minimal adoption |
| **claude-token-lens** | 4 stars | Minimal adoption |

**Conclusion**: We are entering a market where (a) the substrate (Skills) has massive adoption, (b) academic infrastructure (benchmarks, compilers, format standards) is being built, but (c) the runtime observability/diagnosis layer is almost completely empty. The window is open now.

### 4.1 Current Positioning

> Agent Skill Runtime Intelligence — local-first, read-only developer tool for understanding Agent Skill runs.

**Core interface**: Skill Run Panorama  
**Core capability**: Evidence Attribution  
**User outcome**: Runtime Debugging

### 4.2 Recommended Refinements

#### 4.2.1 Sharpen the one-liner

**Current**: "See how every Skill was discovered, activated, executed, and connected to its observable results."

**Proposed**: **"See exactly what your Skill did — and where it failed silently."**

Rationale: The current one-liner is accurate but doesn't convey the urgency. Developers don't search for "Skill lifecycle observability"; they search for "why didn't my Skill work." The pain point is silent failure, not lack of observability.

#### 4.2.2 Add a diagnosis-first entry point

The MVP opens on a runs list. But the highest-value user moment is **diagnosis**: "where is the first failed step?" The product should lead with diagnosis, not just a list.

Proposed: Add a **"Diagnose"** quick-action on the runs list that jumps directly to the first failed or missing lifecycle boundary. The panorama remains the detailed view, but diagnosis is the entry point that makes the product viral — developers share "here's where my Skill broke."

#### 4.2.3 Add a shareable "Skill Health Report"

A one-page, exportable summary per run that includes:

- Skill identity and version
- Lifecycle status (discovered? activated? loaded? executed? produced?)
- First failure boundary (if any)
- Evidence grades for key claims
- Duration, token overhead, artifact count
- A "diagnosis" sentence in plain language
- A permalink-safe redacted version

This is the artifact that spreads. Developers paste it in PRs, Slack, GitHub issues. It makes the product's value visible without requiring someone to install it.

#### 4.2.4 Open-source the event model as a community standard

The normalized event model (Skill lifecycle events, evidence grades, correlation precedence) should be published as an open specification, separate from the tool implementation. This creates:

- **A community standard** that other tools can adopt
- **A citation target** for the paper
- **A vendor-neutral interoperability layer** that positions the product as the reference implementation
- **A moat through ecosystem adoption** — even if competitors build tools, they'll use our event model

#### 4.2.5 Positioning against nearest competitors

Given the web research findings, here's how we position against each direct competitor:

**vs SkillPulse (closest competitor)**:
- They do: statistical degradation detection, canary validation, root-cause attribution to 4 causes
- We do: **lifecycle reconstruction** (what happened step by step), **evidence grading** (Observed/Derived/Inferred), **visual panorama**, **cross-harness adapters**
- Their weakness: reads from Langfuse/Phoenix (requires external observability platform); CLI-only; no lifecycle model; no evidence grading
- Our message: "SkillPulse tells you a Skill degraded. We show you exactly where in the lifecycle it broke and why."

**vs Observal (biggest competitor by stars)**:
- They do: registry, discovery, session replay, usage analytics across harnesses
- We do: **Skill-lifecycle-first runtime reconstruction**, **evidence grading**, **local-first read-only diagnosis**
- Their weakness: broad control plane (heavier); not Skill-lifecycle-first; no evidence grading; includes governance/registry (we explicitly exclude)
- Our message: "Observal is your component registry. We are your Skill diagnosis microscope."

**vs Shepherd (most academically credible)**:
- They do: reversible execution traces, meta-agent supervision, copy-on-write fork/replay
- We do: **passive observation** (never takes over the agent), **Skill-specific lifecycle**, **evidence grading**
- Their weakness: wraps the agent execution (violates read-only principle); no Skill lifecycle model; requires Python 3.11+ and OS-level sandboxing
- Our message: "Shepherd runs your agent. We observe what your agent already did — without touching it."

**vs claude-token-lens**:
- They do: real-time per-skill token attribution
- We do: **full lifecycle reconstruction** (not just tokens), **evidence-graded claims**, **cross-harness**
- Our message: "Token attribution tells you what it cost. We tell you what it did and where it failed."

**vs agent-skills-eval (637 stars, complementary)**:
- They do: pre-deployment test runner for Skills
- We do: **runtime reconstruction** of real sessions, **post-deployment diagnosis**
- Our message: "agent-skills-eval tests before you ship. We diagnose after you run." These are complementary, not competitive — we should recommend both in a workflow.

#### 4.2.6 Target two developer personas for rapid spread

**Persona A: The frustrated Skill author** (primary)
- Wrote a Skill, installed it, ran the agent, got a bad result
- Doesn't know if the Skill was even loaded
- Will install the tool, run it against their session, see the first failure boundary, and fix it
- Will share the Skill Health Report in the Skill's GitHub issue

**Persona B: The agent platform maintainer** (secondary)
- Maintains Skills across multiple agent products (Claude Code, Codex, etc.)
- Needs to know how the same Skill behaves across harnesses
- Will use the comparison/diff feature (v0.2) to show behavioral changes
- Will cite the paper and event model in their platform docs

#### 4.2.7 Sequence the roadmap for viral spread

| Phase | Feature | Why it spreads |
|---|---|---|
| v0.1 | Run panorama + diagnosis | "I can finally see what my Skill did" |
| v0.1+ | Skill Health Report (exportable) | Developers share it in issues/PRs |
| v0.2 | Cross-run/version comparison | "Skill v2 broke this — here's the diff" |
| v0.2 | Why-not-triggered diagnosis | "My Skill wasn't even discovered — here's why" |
| v0.3 | Controlled paired evaluation | "This Skill doesn't help — here's the evidence" |
| v0.3 | Skill conflict matrix | "Two Skills are fighting — here's the overlap" |

The key insight: **each phase produces a shareable artifact** that demonstrates the product's value to someone who hasn't installed it yet.

---

## 5. Paper Plan

### 5.1 Research Question

> How can dynamically loaded Agent Skill behavior be reconstructed and attributed across heterogeneous agent harnesses while distinguishing direct observation, deterministic derivation, uncertain inference, and experimentally measured effect?

### 5.2 Why This Paper Is Needed Now

1. **"From Agent Traces to Trust"** (2606.04990) establishes evidence tracing as a research area but provides no system or benchmark.
2. **SkillsBench** establishes that Skill effectiveness varies but doesn't diagnose why.
3. **Harness-Bench** establishes that the harness matters but doesn't reconstruct Skill lifecycle.
4. **Agent Harness Survey** formalizes the harness but not the Skill lifecycle.
5. Nobody has published a **Skill lifecycle event model** or an **evidence-graded reconstruction benchmark**.

The gap is real and timable.

### 5.3 Candidate Contributions (Prioritized)

| # | Contribution | Novelty | Evidence of gap |
|---|---|---|---|
| 1 | **Skill lifecycle event model** — normalized representation of discovery, activation, instruction loading, resource loading, tool execution, artifacts, outcomes | No existing paper defines this. Agent Harness Survey defines harness components, not Skill lifecycle. "From Agent Traces to Trust" defines provenance taxonomy, not Skill-specific lifecycle. | High |
| 2 | **Evidence attribution taxonomy** (Observed/Derived/Inferred/Experimental) for Skill runtime claims | "From Agent Traces to Trust" has a conceptual taxonomy; ours is operationalized with concrete correlation precedence rules and UI constraints. | Medium-High |
| 3 | **Cross-harness adapters** with explicit capability/observability matrices | Harness-Bench measures effects; nobody maps which lifecycle signals each harness can observe. | High |
| 4 | **Reconstruction evaluation benchmark** — labeled sessions measuring event recall, relationship precision, uncertainty calibration | Nobody has this. "From Agent Traces to Trust" calls it an open challenge. | High |
| 5 | **Empirical study of silent Skill failures** — characterization of where lifecycle failures occur | SkillsBench measures effectiveness; nobody diagnoses WHERE failure occurs. | High |
| 6 | **Controlled effect evaluation** connecting runtime evidence to measured effectiveness | SkillsBench does paired evaluation but doesn't connect it to runtime evidence. | Medium |

### 5.4 Hypotheses (Refined)

| ID | Hypothesis | How to test | GPU role |
|---|---|---|---|
| H1 | Skill lifecycle failures are not limited to non-activation; resource loading and execution boundaries contribute substantial silent failure | Run 100+ Skill sessions, label first-failure boundary | GPU runs the agent sessions |
| H2 | Cross-source reconstruction identifies more Skill behavior than transcript-only analysis | Compare reconstruction from transcript-only vs transcript+files+workspace | Label ground truth manually |
| H3 | Explicit evidence grading reduces unsupported attribution claims without making the interface unusable | User study: developers diagnose with/without evidence grades | — |
| H4 | Skill activation frequency is a poor proxy for Skill effectiveness | Correlate activation frequency with paired evaluation delta across many runs | GPU runs paired trials |
| H5 | The same Skill produces materially different lifecycle behavior across agent harnesses and versions | Run same Skill×task across Claude Code, Codex, and multiple versions | GPU runs cross-harness |
| H6 | Focused Skills (≤3 modules) produce fewer silent failures than exhaustive Skill bundles | Categorize Skills by module count, run paired evaluation | GPU runs paired trials |

### 5.5 Evaluation Dimensions

#### Reconstruction quality
- Event precision and recall (vs labeled ground truth)
- Parent/child relationship precision
- Artifact attribution precision
- Missing-telemetry detection rate
- Inference calibration (Brier score / ECE)

#### System quality
- Collection overhead (latency added to agent)
- Indexing throughput
- Storage cost per session
- Adapter robustness across harness versions
- Privacy/redaction effectiveness

#### Human usefulness
- Time to diagnose a failed Skill run (with vs without the tool)
- Accuracy of developer explanations
- Usability compared with raw transcripts
- Trust calibration between observed and inferred claims

#### Skill effectiveness (v0.3)
- Paired success-rate delta (with/without Skill)
- Token and latency overhead
- Variance across models and harnesses
- Regressions across Skill versions

### 5.6 Paper Targeting

Based on the user's prior research context (EMNLP 2026 via ARR was targeted for a different paper):

**Primary target**: A systems/SE venue that values tool building + evaluation:
- **ICSE** (Software Engineering) — if framed as "Skill debugging infrastructure"
- **FSE** (Foundations of Software Engineering) — if framed as "runtime reconstruction for extensible agents"
- **ASE** (Automated Software Engineering) — tool track

**Alternative**: A venues that values agent infrastructure:
- **NeurIPS Datasets & Benchmarks** — if the reconstruction benchmark is the primary contribution
- **ACL/EMNLP (System Demonstrations)** — if the tool is the primary contribution
- **COLM** (Conference on Language Modeling) — if Skill lifecycle modeling is the focus

**Recommended**: NeurIPS D&B for the benchmark + ICSE/FSE for the system, or a combined paper at COLM/ICLR.

### 5.7 Artifact Plan

The research artifact would contain:
1. Normalized event schema (JSON Schema + spec document)
2. Adapter capability matrix (Claude Code, Codex)
3. Sanitized session fixtures (100+ labeled runs)
4. Reconstruction benchmark (ground-truth labels)
5. Evaluation scripts (precision/recall/calibration)
6. Reproducible figures and tables
7. The local panorama UI (open-source tool)
8. Paired evaluation results (with/without Skills across models)

---

## 6. GPU Experiment Plan

### 6.1 Available Resources

- PAI-DSW server: 121.41.193.56, GPU available, `/mnt/workspace` working directory
- GitHub repos for code sync: skill-research, skillweaver, compositional-skill-routing

### 6.2 Experiment Phases

#### Phase 1: Reconstruction Benchmark Construction (2-3 weeks)

**Goal**: Build a labeled dataset of 100+ Skill runs for reconstruction evaluation.

**Steps**:
1. Select 20-30 representative Skills across domains (coding, document processing, data analysis, research)
2. Run each Skill against 3-5 tasks on 2 harnesses (Claude Code, Codex) × 2-3 models
3. Manually label ground truth: which lifecycle events occurred, which resources were loaded, which tools fired, which artifacts were produced, where failures occurred
4. Run our reconstruction pipeline against each session
5. Compute: event precision/recall, relationship precision, missing-telemetry detection rate, inference calibration

**Output**: A labeled reconstruction benchmark.

#### Phase 2: Silent Failure Characterization (1-2 weeks)

**Goal**: Test H1 — where do Skill lifecycle failures actually occur?

**Steps**:
1. From the Phase 1 dataset, categorize each run's first-failure boundary
2. Compute the distribution: discovery failures, activation failures, loading failures, execution failures, outcome failures
3. Compare with SkillsBench's effectiveness data to see if ineffective Skills have diagnosable lifecycle failures
4. Produce the empirical findings table

**Output**: Distribution of silent failure points across the lifecycle.

#### Phase 3: Cross-Harness Behavior Comparison (1-2 weeks)

**Goal**: Test H5 — do the same Skills behave differently across harnesses?

**Steps**:
1. Run the same Skill×task pairs across Claude Code and Codex
2. Compare lifecycle event coverage, activation modes, resource loading patterns
3. Identify signals that are observable in one harness but not the other
4. Produce the adapter capability matrix comparison

**Output**: Cross-harness behavior comparison table.

#### Phase 4: Controlled Effect Evaluation (2-3 weeks)

**Goal**: Test H4 — is activation frequency a poor proxy for effectiveness?

**Steps**:
1. Select 10-15 Skills from Phase 1
2. For each Skill, run 20 matched task pairs (with/without Skill) across 3 models
3. Compute: paired success-rate delta, token overhead, latency overhead
4. Correlate activation frequency with effectiveness delta
5. Produce the correlation analysis

**Output**: Effectiveness vs activation frequency scatter plot + statistics.

#### Phase 5: Skill Module Count Analysis (1 week)

**Goal**: Test H6 — do focused Skills fail less silently?

**Steps**:
1. Categorize Skills by module count (1, 2-3, 4+)
2. From Phase 1+4 data, compute silent failure rate and effectiveness per category
3. Produce the comparison table

**Output**: Module count vs failure rate vs effectiveness.

### 6.3 Total Timeline

| Phase | Duration | Depends on | Output |
|---|---|---|---|
| 1. Reconstruction benchmark | 2-3 weeks | MVP v0.1 | Labeled dataset |
| 2. Silent failure characterization | 1-2 weeks | Phase 1 | Empirical findings |
| 3. Cross-harness comparison | 1-2 weeks | Phase 1 | Capability matrix |
| 4. Controlled effect evaluation | 2-3 weeks | Phase 1 | Effectiveness data |
| 5. Module count analysis | 1 week | Phase 1+4 | Module count comparison |
| **Total** | **8-11 weeks** | | **Paper-ready results** |

### 6.4 Compute Budget Estimate

- Phase 1: 100 runs × ~2 min each = ~3.3 hours GPU
- Phase 4: 15 Skills × 20 pairs × 3 models × ~2 min = ~30 hours GPU
- Buffer: 50% overhead for retries, debugging
- **Total: ~50 hours GPU** — well within typical PAI-DSW availability

---

## 7. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Agent transcript formats change mid-experiment | Medium | Adapter versioning; fixtures captured at experiment time |
| Ground truth labeling is subjective | High | Two annotators + adjudication; report inter-annotator agreement |
| Too few Skills/tasks for statistical power | Medium | Use SkillsBench's 87 tasks as a starting pool; supplement with community Skills |
| Reconstruction quality depends on adapter completeness | High | Report results per-adapter; be explicit about unsupported signals |
| "Effectiveness" requires deterministic verifiers | Medium | Reuse SkillsBench verifiers where available; define custom verifiers for new tasks |
| Paper venue mismatch | Low | Target D&B track (dataset) or system demo track first; full paper second |

---

## 8. Immediate Next Steps

1. **Finalize MVP v0.1** — ensure Claude Code adapter works alongside Codex adapter
2. **Create the Skill Health Report** — the shareable artifact that makes the product viral
3. **Start Phase 1 experiments** — select Skills, run sessions, begin labeling
4. **Draft the event model specification** as a standalone document for open-source release
5. **Write a short position paper** (2-3 pages) for rapid community feedback — "Skill Lifecycle Observability: Why Activation Is Not Effectiveness"
6. **Update the competitive landscape doc** with the new papers found in this research

### 8.1 Positioning Decisions to Make Now

Based on the research, here are the key positioning decisions that need team alignment:

| Decision | Options | Recommendation |
|---|---|---|
| Product name | "Agent Skill Runtime Intelligence" (working) vs. shorter brandable name | Keep working title; launch a name search after MVP |
| Primary user entry | Runs list vs. Diagnose-first | **Diagnose-first**: lead with "where did it break?" not "here's a list of runs" |
| Viral artifact | None vs. Skill Health Report | **Skill Health Report**: exportable one-page summary that developers paste in GitHub issues |
| Event model | Internal vs. open specification | **Open specification**: publish as a standalone spec for community adoption |
| Relationship with Observal | Compete vs. complement | **Complement**: Observal is the registry; we are the diagnosis microscope. Consider integration. |
| Relationship with Shepherd | Compete vs. complement | **Complement**: Shepherd wraps the agent; we observe from outside. Different philosophy, different use cases. |
| Relationship with agent-skills-eval | Compete vs. complement | **Complement**: They test before shipping; we diagnose after running. Recommend both in workflow. |
| Paper venue | EMNLP vs. ICSE/FSE vs. NeurIPS D&B | **NeurIPS D&B** (benchmark) or **ICSE/FSE** (system) — depends on which contribution leads |
| GPU experiment priority | All 5 phases vs. priority | **Phase 1 + Phase 2 first** (reconstruction benchmark + silent failure characterization) — these produce the paper's core contribution |

---

## 9. Key Papers for Citation

| Paper | arXiv | Relevance |
|---|---|---|
| SkillsBench | 2602.12670 | Skill effectiveness benchmark; our H4 |
| SWE-Skills-Bench | 2603.15401 | SE Skill effectiveness; silent failure |
| SkCC | 2605.03353 | Skill compilation; cross-framework variation |
| Skill-as-Pseudocode | 2605.27955 | Skill format quality; confused loop |
| From Agent Traces to Trust | 2606.04990 | Evidence tracing survey; our conceptual basis |
| Agent Harness Survey | preprints 202604.0428 | Harness as binding constraint |
| Harness-Bench | 2605.27922 | Harness effects benchmark |
| AGENTSAFE | 2512.03180 | Agent governance framework |
| Agent-as-a-Judge | 2601.05111 | Agentic evaluation survey |
| LLM-as-a-Judge survey | (2026) | Evaluation reliability |
| AgentTrap | 2605.13940 | Skill runtime trust |
| Agentic Skill Discovery | 2405.15019 | Skill emergence (robotics) |
| A Survey on LLM-based Autonomous Agents | (2024) | Agent survey background |
| Shepherd | 2605.10913 | Reversible execution traces; meta-agent supervision |

---

## 10. Summary

The product is well-positioned. The gap is real, validated by recent literature, and not filled by any existing system. The path to a paper is clear: operationalize evidence-graded Skill lifecycle reconstruction, build a benchmark, and produce empirical findings about silent failures. GPU resources enable the paired evaluation that SkillsBench started but at a finer granularity. The product can spread rapidly through shareable Skill Health Reports and an open event model specification.
