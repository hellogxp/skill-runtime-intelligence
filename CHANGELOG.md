# Changelog

All notable changes to Agent Skill Runtime Intelligence are documented here.
The project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Authenticated self-hosted remote deployment with independent read-only
  viewer and write-only Collector credentials.
- Direct TLS or loopback-behind-HTTPS-proxy transport enforcement, secure
  credential initialization, and fail-open remote queue relay.

### Changed

- Non-loopback service binding now fails closed unless explicit remote access
  policy is configured.
- The UI identifies the selected deployment boundary and disables local data
  mutations for remote viewer sessions.

## [0.3.0] - 2026-07-31

### Added

- Skill behavior checks that extract conservative, inspectable constraints from
  the current `SKILL.md` and match them to runtime evidence.
- Concrete instruction, resource, execution, artifact, and outcome inventories
  in each SkillRun, with paths and evidence records available for inspection.
- An evidence-bounded run assessment that separates observable failures,
  declared verification expectations, and adapter limitations.
- Explicit causal-scope metadata for diagnostic findings.
- Localized diagnostic and activity surfaces across all supported UI locales.

### Changed

- Runtime Overview separates systemic telemetry blind spots from run-specific
  findings instead of repeating the same adapter limitation as many alerts.
- SkillRun list summaries are loaded in one batched query, avoiding one
  lifecycle query per row.
- Release metadata, community files, and tag/version consistency are validated
  before publishing.

### Fixed

- Realtime export cursors remain stable when an in-progress transcript is
  refreshed.
- The cross-Agent Qoder experiment uses the current non-interactive permission
  flag.
- Historical distribution tests use the published artifact filename and skip
  clearly when verified fixtures have not been fetched.

## [0.2.1] - 2026-07-31

- Preserved realtime export cursors across session refreshes.

## [0.2.0] - 2026-07-30

- Added live fail-open collection, four versioned Agent adapters, Runtime
  Overview, first-boundary diagnosis, Compare, Inferred Analysis, and OTLP
  interoperability.

[Unreleased]: https://github.com/hellogxp/skill-runtime-intelligence/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/hellogxp/skill-runtime-intelligence/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/hellogxp/skill-runtime-intelligence/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/hellogxp/skill-runtime-intelligence/releases/tag/v0.2.0
