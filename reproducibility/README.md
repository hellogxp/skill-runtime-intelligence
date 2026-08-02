# Reproducibility archive

This directory preserves the de-identified experiment evidence used by the SRI
paper and anticipated artifact or rebuttal checks. It complements the runnable
experiment implementations under `experiments/`; it is not a production
telemetry corpus and does not contain raw Agent sessions, credentials, model
weights, or private source code.

## What is included

- all retained JSON/JSONL experiment reports from the working tree;
- source and published SHA-256 digests in `manifest.json`;
- a flat checksum ledger in `CHECKSUMS.sha256`;
- the exact PAI-DSW environment fingerprint used for the Linux and Qwen runs;
- the 16,632-byte Linux x86_64 native sender artifact used by the host contract
  experiment;
- deterministic experiment, analysis, and test code in the main repository.

Machine-local path prefixes in published result copies are replaced with
`${REPO_ROOT}`, `${LOCAL_HOME}`, `${PAI_WORKSPACE}`, or `${PAI_HOME}`. The
builder records both the source and published digest and does not modify
metrics, labels, predictions, timings, or model responses.

## Verify the frozen evidence

```bash
python3 scripts/verify_reproducibility_bundle.py
shasum -a 256 -c reproducibility/CHECKSUMS.sha256
```

## Re-run deterministic experiments

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python experiments/run_suite.py --output /tmp/sri-reproduction.json
```

The deterministic correctness core is expected to pass. The transport gate is
environment-sensitive and reports its mechanism explicitly. Live Agent and
model-backed experiments require the named external Agent/CLI or an
OpenAI-compatible model endpoint; they are intentionally not hidden inside the
deterministic command.

## Maintainer rebuild

Rebuilding requires the complete source result directories from the private
working archive. Those machine-local source copies are intentionally not
published; reviewers should use the verification commands above.

```bash
python3 scripts/build_reproducibility_bundle.py
python3 scripts/verify_reproducibility_bundle.py
```

See `experiments/confirmatory_manifest_20260801.json` and
`experiments/external_validity/confirmatory_manifest_20260801.json` for frozen
claims, planned/completed counts, failed gates, and inference boundaries.
