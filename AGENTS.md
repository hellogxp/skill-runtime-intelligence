# Project instructions

## Product

This repository builds a local-first Agent Skill runtime intelligence tool. Its first outcome is an evidence-graded Skill Run Panorama.

Read these documents before changing product behavior:

1. `docs/product-definition.md`
2. `docs/mvp-specification.md`
3. `docs/runtime-event-model.md`
4. `docs/ui-information-architecture.md`

## Non-negotiable principles

- Observe agent runs; do not take over or orchestrate them.
- Default to read-only collection and local storage.
- Do not proxy model requests.
- Do not block agent actions in the default product.
- Never store secrets or raw sensitive content unnecessarily.
- Label evidence as Observed, Derived, Inferred, or Experimental.
- Never claim causal Skill effectiveness from one run.
- Preserve raw source events separately from normalized and inferred records.
- Keep each agent integration behind a versioned adapter.

## Scope discipline

The MVP is not a Skill marketplace, registry, security gate, universal runtime, or general LLM observability platform. New features must strengthen the Skill-specific run panorama or diagnosis workflow.

## Verification and UI

- Do not use, inspect, invoke, or depend on StateSeal in this repository.
- Do not require StateSeal receipts or StateSeal verification for development,
  experiments, delivery, or release reporting.
