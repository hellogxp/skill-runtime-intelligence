# Research and competitive landscape

Snapshot date: 2026-07-28

## 1. Reliable findings

### Agent Skills use progressive disclosure

The Agent Skills specification defines a directory containing `SKILL.md` and optional `scripts/`, `references/`, and `assets/`. Metadata supports discovery, full instructions load on activation, and resources load as needed.

Source: [Agent Skills specification](https://agentskills.io/specification)

### Skill availability does not guarantee value

SkillsBench evaluates thousands of trajectories across diverse tasks. Curated Skills improve average performance, but effects vary substantially and some tasks regress. Self-generated Skills do not provide average benefit.

Source: [SkillsBench, arXiv:2602.12670](https://arxiv.org/abs/2602.12670)

### Software-engineering Skill gains are narrow

SWE-Skills-Bench reports that most evaluated public SWE Skills provide no pass-rate gain, some add substantial token overhead, and version-mismatched guidance can reduce performance.

Source: [SWE-Skills-Bench, arXiv:2603.15401](https://arxiv.org/abs/2603.15401)

### Runtime trust is a real concern

Third-party Skills can combine instructions, scripts, resources, and privileged tools. Runtime behavior may differ from static appearance.

Sources:

- [AgentTrap, arXiv:2605.13940](https://arxiv.org/abs/2605.13940)
- [Snyk ToxicSkills research](https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/)

Security is relevant context, but security enforcement is not the MVP.

## 2. Existing products and projects

| Project | Primary focus | Relevant overlap | Remaining distinction |
|---|---|---|---|
| Langfuse | General LLM observability and evaluation | traces, metrics, evals | Not Skill-lifecycle-first |
| Observal | Agent/component registry, analytics, session replay | Skill usage and cross-agent traces | Broad control plane, heavier deployment |
| SkillScope CLI | Claude Code transcript usage and token reports | activation counts, dead Skills, cost | CLI analytics, Claude-specific, limited run panorama |
| SkillScope flowchart | Static `SKILL.md` visualization and scoring | trigger/step flowchart | Static design, not runtime reconstruction |
| agent-skills-eval | Paired with/without evaluation | effect measurement and reports | Evaluation harness, not passive runtime panorama |
| Microsoft SkillLens | Skill lifecycle research framework | generation and consumption analysis | Research framework rather than local runtime UX |
| OpenSkillEval | Ecosystem evaluation research | cross-model and cross-framework quality | Benchmarking rather than developer run inspection |

Links:

- [Langfuse](https://github.com/langfuse/langfuse)
- [Observal](https://github.com/Observal/Observal)
- [SkillScope CLI](https://github.com/notsointresting/skillscope)
- [SkillScope flowchart](https://github.com/silvesterdivas/skillscope)
- [agent-skills-eval](https://github.com/darkrishabh/agent-skills-eval)
- [Microsoft SkillLens](https://github.com/microsoft/SkillLens)
- [OpenSkillEval](https://arxiv.org/abs/2605.23657)

## 3. Corrected market interpretation

It is inaccurate to claim that Skill quality, security, or observability is entirely empty. Existing projects cover pieces of all three.

The narrower opportunity is:

> A local-first, cross-source, Skill-lifecycle runtime panorama with explicit evidence attribution and a later path to controlled effect evaluation.

The product must be more than:

- another generic span viewer;
- static `SKILL.md` flowchart generation;
- counts of how often a Skill fired;
- a general agent component registry;
- an opaque quality score.

## 4. Strategic decision

Do not launch a broad “Skill Trust Stack” containing lint, trace, eval, scan, registry, and runtime.

Start with one sharp product:

> Reconstruct what a Skill did in a real agent session.

Reasons:

- immediately understandable user question;
- strong fit with a visual product;
- low-intrusion adoption;
- existing local session data provides a feasible starting point;
- evidence discipline creates differentiation;
- later diagnosis and paired evaluation extend the same data model.

## 5. Working positioning

### Product category

**Agent Skill Runtime Intelligence**

### Core interface

**Skill Run Panorama**

### Core technical capability

**Evidence Attribution**

### User outcome

**Runtime Debugging**

### One-line message

> See how every Skill was discovered, activated, executed, and connected to its observable results.

## 6. Naming constraints

Do not use `SkillScope` or `SkillLens`; both names already have closely related active projects.

The repository uses a descriptive working title until a dedicated name search covers:

- GitHub organizations and repositories;
- package registries;
- domains;
- trademarks;
- confusingly similar developer tools.

