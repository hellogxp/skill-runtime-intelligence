# Contributing to Skill Runtime Intelligence

Thank you for improving Skill Runtime Intelligence.

## Before you start

Substantial changes to the event model, evidence semantics, privacy boundary,
or Agent adapters should begin with an issue. Bug fixes and focused
documentation improvements can go directly to a pull request.

Read these product contracts before changing behavior:

- `docs/product-definition.md`
- `docs/mvp-specification.md`
- `docs/runtime-event-model.md`
- `docs/ui-information-architecture.md`

## Local development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
node --check src/skill_runtime_intelligence/web/app.js
node --check src/skill_runtime_intelligence/web/i18n.js
node --check src/skill_runtime_intelligence/web/locale-packs.js
git diff --check
```

Keep integrations behind versioned adapters and preserve raw source events
separately from normalized and inferred records. New behavior must strengthen
the Skill-specific run panorama or diagnosis workflow.

Historical release compatibility tests use checksum-pinned public artifacts.
They are skipped in the ordinary local suite when those fixtures are absent.
To run them explicitly:

```bash
.venv/bin/python scripts/fetch_release_fixtures.py --version 0.1.0
.venv/bin/python -m unittest -v \
  tests.test_migration_sdist_rebuild_benchmark \
  tests.test_sdist_rebuild_determinism_benchmark
```

Before changing release metadata, run:

```bash
.venv/bin/python scripts/check_release.py
```

## Evidence and privacy requirements

- Preserve raw source envelopes separately from normalized and inferred data.
- Label claims as Observed, Derived, Inferred, or Experimental.
- Never turn a missing signal into proof that an action did not occur.
- Never infer causal Skill effectiveness from one run.
- Keep integrations versioned, bounded, fail-open, and observation-only.
- Do not commit prompts, transcripts, credentials, private paths, or runtime
  databases. Use synthetic fixtures with explicit provenance.

## Pull requests

1. Keep the change focused and explain the user-visible outcome.
2. Add tests for observable behavior and evidence-grade boundaries.
3. Run the complete test suite and relevant experiment contract checks.
4. Update English and Simplified Chinese source documentation when behavior
   changes; generated locale files must remain structurally synchronized.
5. Explain privacy, compatibility, and non-interference implications.
6. Include screenshots only when they contain synthetic or intentionally
   public data.

By contributing, you agree that your contribution is licensed under
Apache-2.0.
