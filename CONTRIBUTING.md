# Contributing

Thank you for improving Skill Runtime Intelligence.

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Keep integrations behind versioned adapters and preserve raw source events
separately from normalized and inferred records. New behavior must strengthen
the Skill-specific run panorama or diagnosis workflow.

## Public repository boundary

This repository and every published release contain public material only. Do
not commit private infrastructure URLs, organization-only installation or
distribution instructions, credentials, employee identity data, or other
non-public content.

Run the same fail-closed check used by CI before opening a pull request:

```bash
python scripts/check_public_boundary.py
```

The release workflow repeats this check against both the source tree and the
contents of packaged archives before uploading any asset.

## Pull requests

1. Open an issue for substantial behavior or event-model changes.
2. Add tests for observable behavior and evidence-grade boundaries.
3. Run the complete test suite and JavaScript syntax checks.
4. Explain privacy, compatibility, and non-interference implications.
5. Do not include session transcripts, tokens, credentials, or private data.

By contributing, you agree that your contribution is licensed under
Apache-2.0.
