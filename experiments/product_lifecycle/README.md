# Packaged product lifecycle smoke

Installs the built wheel into a temporary virtual environment and exercises
`install`, `start`, `status`, `doctor`, `stop`, and `uninstall` with an isolated
`HOME`, state root, project, Agent-session root, and random localhost port.

The release download URL is redirected to a closed localhost port so the run
is offline and exercises the packaged native-source build fallback. The gate
requires:

- successful offline wheel installation and lifecycle commands;
- successful one-time native-sender prewarm during installation;
- a healthy managed runtime before stop and an absent runtime afterward;
- `doctor` to truthfully report that live official evidence is not ready;
- unchanged project content;
- no Agent configuration created outside or inside the isolated home; and
- complete removal of the isolated product state.

This is a packaged-product smoke test, not evidence that live Agent hooks were
connected.

The current-host native sender contract verifies one manifest-selected
published artifact against its byte size and SHA-256, confirms host OS and
architecture, fingerprints binary sections/symbols, and executes exact local
Unix-socket delivery plus silent failure semantics:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/native_sender_host_contract_benchmark.py \
  --artifact /path/to/skill-runtime-hook-native-linux-x86_64 \
  --repetitions 40
```

A passing run is host-specific Experimental mechanism evidence. It does not
establish cross-host reliability or hosted-builder reproducibility.

Audit an additive schema upgrade from the built wheel against a consistent
copy of the live local database:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/run_upgrade_migration.py \
  --wheel dist/skill_runtime_intelligence-0.1.6-py3-none-any.whl \
  --database .sri/panorama.db
```

The source database is opened read-only. The wheel is installed offline into a
temporary virtual environment, the migration is applied twice to verify
idempotency, and one controlled post-upgrade event exercises the new write
path. Only aggregate counts and integrity status are reported. Legacy
provenance remains unknown/null rather than being reconstructed.

Exercise every prefix of the five-column additive migration:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/migration_partial_state_benchmark.py \
  --trials 3
```

The six preconstructed states represent zero through five already-applied
columns. Each state is opened twice and must preserve the legacy row as
unknown/null while completing the schema and passing SQLite integrity checks.
This tests retryability from partial additive states, not process-kill timing
or arbitrary database corruption.

Kill a real migration worker after each committed DDL boundary:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/migration_kill_recovery_benchmark.py \
  --trials 3
```

The worker uses WAL mode and receives `SIGKILL` before any column and after
each of the five committed additions. A clean process must then complete the
migration twice, retain unknown/null legacy semantics, and pass SQLite
integrity checking. This does not simulate termination inside atomic DDL,
power loss, or filesystem corruption.

Exercise migration under transient and over-budget SQLite writer locks:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/migration_lock_contention_benchmark.py
```

Transient locks at 50 ms, 250 ms, and one second must complete within the
configured five-second busy timeout. A 5.5-second lock must produce an initial
bounded failure and then recover cleanly after release. Every case must retain
legacy unknown/null semantics and pass SQLite integrity checking. Lock timing
is environment-sensitive and remains outside the deterministic suite.

Verify a read-only migration attempt fails without partially mutating evidence:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/migration_readonly_recovery_benchmark.py \
  --trials 3
```

The temporary database and its directory are made read-only before a separate
process opens `Storage`. The attempt must fail, leave the legacy schema and row
intact, and recover after write permission is restored. POSIX permissions do
not model power loss or a mid-write I/O failure.

Exercise an old column-list writer before and after the additive migration:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/migration_old_writer_compatibility_benchmark.py
```

The fixture writes through the legacy column list while holding a transaction
before migration, after migration has completed, and beyond the five-second
busy-timeout budget. The gate requires every legacy write to survive, retain
unknown/null timestamp provenance, and remain recoverable. This is a raw
SQLite compatibility fixture, not execution of a packaged historical binary.

Create databases with three verified repository-history snapshots and migrate
them with the current working-tree implementation:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/migration_historical_schema_contract_benchmark.py \
  --trials 3
```

The snapshots cover the bootstrap Panorama, the SkillRun-core transition, and
the v0.1.0 release commit. The report records full commit identities and
schema fingerprints, then requires every controlled legacy event to survive
the current additive migration with unknown/null provenance and an idempotent
second open. Historical sources are executed directly from local verified Git
objects; this is not a wheel-install compatibility claim.

Verify a downloaded historical release wheel by its published SHA-256 before
using it to create migration fixtures:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/migration_release_artifact_contract_benchmark.py \
  --artifact /tmp/skill_runtime_intelligence-0.1.0-py3-none-any.whl \
  --expected-sha256 23b707b3de8cd8561e07285e6904cf5b25ad68b0910a8d7c4e38e68826825d09 \
  --expected-version 0.1.0 \
  --source-url https://github.com/hellogxp/skill-runtime-intelligence/releases/download/v0.1.0/skill_runtime_intelligence-0.1.0-py3-none-any.whl
```

The benchmark installs the artifact offline into an isolated virtual
environment only after its digest matches, creates a database with that
installed code, and applies the current migration twice. An optional
`--comparison-artifact` records whether a same-named local file has the same
identity, but does not treat filename equality as release provenance.

Run the identity and migration contract across every wheel in the observed
v0.1 release manifest:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/migration_release_matrix_benchmark.py \
  --artifact-directory /tmp/sri-v0.1-release-wheels \
  --trials 3
```

`release_wheel_manifest_v0.1.json` records release API timestamps, URLs, sizes,
and SHA-256 identities for v0.1.0 through v0.1.6. Every artifact is installed
in a separate isolated environment. Missing downloads are reported as
`not_run/artifact_missing`; they are not converted into migration failures.

Compare each v0.1 wheel with its identity-verified source distribution:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/migration_distribution_parity_benchmark.py \
  --artifact-directory /tmp/sri-v0.1-release-distributions \
  --trials 3
```

The sdist source is extracted with path validation and imported only after the
resolved module path is proven to be inside that artifact. Each version pair
must match release digests and metadata, generate the same schema fingerprint,
and migrate conservatively. Schema parity is not runtime-behavior parity.

Rebuild every v0.1 sdist into a wheel with network access disabled, then
compare it with the published wheel:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/migration_sdist_rebuild_benchmark.py \
  --artifact-directory /tmp/sri-v0.1-release-distributions \
  --build-repetitions 2 \
  --migration-trials 1
```

The contract gate compares package name/version, Python requirement, CLI entry
points, wheel tags, schema fingerprints, and conservative migration. Rebuilt
byte digests are reported separately: byte mismatch is not automatically a
behavior-contract failure. The offline build uses the recorded host
setuptools/wheel toolchain with build isolation disabled.

Measure fixed-epoch rebuild repeatability and classify file-level drift:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/sdist_rebuild_determinism_benchmark.py \
  --artifact-directory /tmp/sri-v0.1-release-distributions \
  --source-date-epoch 315532800 \
  --build-repetitions 3
```

The gate requires repeated offline builds to share a digest and preserve the
selected metadata/CLI/wheel-tag contract. Published-byte equality is reported
separately. The file audit distinguishes member-name, decompressed-content,
and ZIP-metadata differences; a fixed-epoch association is not a causal claim.

Compare published wheels with fixed-epoch rebuilds from a pinned builder while
normalizing only ZIP member timestamps:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/wheel_normalized_content_benchmark.py \
  --artifact-directory /tmp/sri-v0.1-release-distributions \
  --builder-python /tmp/sri-python313-setuptools83/bin/python \
  --source-date-epoch 315532800 \
  --build-repetitions 2
```

The normalized fingerprint keeps member names, decompressed content hashes,
permissions/attributes, compression type, creator/extractor versions, and
flags. It excludes only ZIP timestamps. It is a diagnostic equivalence signal,
not a replacement for the published artifact digest.

Repeat normalized-content reconstruction in a digest-pinned Linux container:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/linux_pinned_wheel_benchmark.py \
  --artifact-directory /tmp/sri-v0.1-release-distributions \
  --dependency-directory /tmp/sri-linux-builder-deps \
  --shared-temp-parent /Users/example/.codex \
  --image-ref python@sha256:20080e807bfc404f8450b185cf0fc95d553462673598549613735f70a5b4d5d0 \
  --builder-requirement setuptools==83.0.0 \
  --builder-requirement wheel==0.46.1 \
  --builder-requirement packaging==26.2 \
  --comparison-report experiments/product_lifecycle/results/normalized-wheel-content-<timestamp>.json
```

The container runs with `--network none`; builder dependency wheels are
mounted read-only. The report records image ID/digest, Linux architecture,
toolchain versions, repeated raw digests, normalized content, and timestamp
drift. A Docker-shared parent is explicit because desktop runtimes may not
mount the host's `/tmp` contents. The optional comparison report tests whether
the Linux rebuild digest also matches a prior pinned-builder environment.

Audit published native senders at raw, section, symbol, and protocol layers:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/native_sender_contract_benchmark.py \
  --artifact-directory /tmp/sri-native-v0.1.6 \
  --linux-image-ref python@sha256:20080e807bfc404f8450b185cf0fc95d553462673598549613735f70a5b4d5d0 \
  --shared-temp-parent /Users/example/.codex \
  --repetitions 20
```

All four Darwin/Linux arm64/x86_64 assets receive digest, section, and symbol
evidence. Only the externally required entry point gates symbol compatibility;
optimization-sensitive static helper symbols remain diagnostic. Protocol
delivery and silent failure behavior run only for Darwin arm64 and Linux arm64
in this environment; x86_64 functional status remains `not_run`, not a failure
or inferred pass.

Rebuild the identity-verified v0.1.6 native source with release-matching flags
and compare observable contracts:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/native_sender_rebuild_parity_benchmark.py \
  --artifact-directory /tmp/sri-native-v0.1.6 \
  --linux-build-image-ref gcc@sha256:<resolved-multiarch-digest> \
  --linux-runtime-image-ref python@sha256:20080e807bfc404f8450b185cf0fc95d553462673598549613735f70a5b4d5d0 \
  --shared-temp-parent /Users/example/.codex \
  --repetitions 20
```

The benchmark verifies the Git tag, commit, source, workflow, and published
asset identities before building. Linux build and runtime containers run with
networking disabled. Raw, section, and symbol fingerprints remain visible
diagnostics; the gate covers external structure and exact protocol/failure
parity. Matching flags do not recreate the original hosted runner identity.

Measure launch sensitivity to executable path reuse on macOS:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/native_sender_path_launch_benchmark.py \
  --artifact-directory /tmp/sri-native-v0.1.6 \
  --shared-temp-parent /Users/example/.codex \
  --repetitions 12
```

Four balanced cells cross published/rebuilt binaries with a stable executable
path or a fresh pathname copy. Exit 1 and silence on a missing socket form the
correctness gate. Latency has no pass threshold and remains descriptive: a new
pathname does not guarantee a fresh OS cache, scan, or machine. Code-sign and
extended-attribute metadata are recorded but not manipulated.

Aggregate at least three completed path-launch reports:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/summarize_native_path_launch_reports.py \
  experiments/product_lifecycle/results/native-path-launch-*.json
```

The summary pools correctness and descriptive latency, reports the range of
per-run medians, and counts paired direction by block. Repeated runs on one
host are not independent-machine replications and do not identify a cause.

Run the preregistered temporary-copy launch-factor matrix:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/native_sender_launch_factor_benchmark.py \
  --artifact-directory /tmp/sri-native-v0.1.6 \
  --shared-temp-parent /Users/example/.codex
```

The v2 four-cell matrix crosses direct copy/atomic replace and original
linker/ad-hoc re-signed states. Only temporary copies are changed. Provenance
xattr removal is excluded because the v1 pilot observed the attribute present
again before launch in all four removal cells despite successful deletion
commands. Every retained factor application is audited before execution and
the correctness gate remains silent exit 1 on a missing socket. Latency uses
the preregistered endpoint but has no pass threshold; within-block marginal
contrasts are descriptive until repeated across runs and hosts.

Aggregate three valid v2 factor reports while preserving run boundaries:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/summarize_native_launch_factor_reports.py \
  <three-v2-report-paths>
```

The summary records per-run factor-delta medians and direction before pooled
cell statistics. This prevents a transient first-run phase from being hidden
inside a seemingly stable pooled result.

Audit whether repeated launch-factor data is ready for effect claims:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/native_launch_phase_readiness_audit.py \
  --summary <three-run-summary.json> \
  <three-v2-report-paths>
```

The audit can pass its own integrity gate while still returning
`confirmatory_effect_ready=false`. It does not infer a change point from the
short interleaved sequence; it records which evidence dimensions are missing.

Audit a privacy-safe scoped host identity contract:

```bash
PYTHONPATH=src python3 \
  experiments/product_lifecycle/host_identity_contract_benchmark.py \
  --trials 3 \
  --workers 8
```

The local identity is random rather than derived from hardware or user data.
Concurrent initialization must converge on one 0600 secret, exported aliases
must be stable within a scope and distinct across scopes, and corrupt,
over-permissive, or symlink identities must fail closed without replacement.
