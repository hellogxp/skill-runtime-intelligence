# Observability platform setup

Skill Runtime exports normalized, Skill-specific evidence as standard
OTLP/HTTP JSON traces. Export is opt-in, fail-open, checkpointed, and excludes
raw prompts, raw tool payloads, credentials, and Skill resource contents.

This connection is independent from where SRI runs. A developer-workstation or
self-hosted remote deployment can operate without any observability export;
either placement may explicitly connect an OTLP/HTTP destination. The export
destination is outside the SRI deployment boundary and is always opt-in.

## Recommended production path

Send Skill Runtime to an OpenTelemetry Collector, then route the same stream to
one or more observability backends:

```text
Skill Runtime
    → OTLP/HTTP JSON
    → OpenTelemetry Collector / Grafana Alloy
    → Phoenix / Grafana Cloud / Datadog / another OTLP backend
```

This keeps credentials and vendor routing outside the Skill Runtime
configuration. Start a Collector with
[`examples/otel-collector.yaml`](../examples/otel-collector.yaml), then:

```bash
skill-runtime config --set network_export.endpoint=http://127.0.0.1:4318
skill-runtime config --set network_export.enabled=true
skill-runtime restart
```

Use `OTEL_EXPORTER_OTLP_HEADERS` for secrets. Skill Runtime never writes those
headers to its JSON configuration or process arguments.

## Direct endpoints

The endpoint may be a base OTLP URL or a complete `/v1/traces` URL. Skill
Runtime appends `/v1/traces` when it is absent.

| Destination | Endpoint guidance | Headers |
|---|---|---|
| OpenTelemetry Collector | `http://127.0.0.1:4318` | normally none on loopback |
| Phoenix self-hosted | `http://127.0.0.1:6006/v1/traces` | optional `authorization`, `x-project-name` |
| Phoenix Cloud | use the Phoenix OTLP HTTP endpoint | `authorization` |
| Grafana Cloud | copy the OTLP gateway base URL from the OpenTelemetry tile | `Authorization=Basic …` from the tile |
| Datadog Agent | enable local OTLP/HTTP ingestion and use `http://127.0.0.1:4318` | normally none on loopback |
| Datadog direct intake | use the site-specific OTLP traces intake URL | `dd-api-key`, optional `compute_stats=true` |
| Langfuse | use the project’s OpenTelemetry traces endpoint | project authentication headers and `x-langfuse-ingestion-version=4` where required |

Vendor endpoint formats and authentication can change. Copy the current values
from the destination’s own connection page rather than guessing a region or
tenant URL.

## Verification

Check local delivery state:

```bash
skill-runtime status
skill-runtime doctor
```

The Settings page reports destination, last attempt, last success, exported
count, pending state, and the redacted last error. A 2xx response advances the
per-destination checkpoint; timeout, transport error, or non-2xx response keeps
the batch pending for retry.

Run the repository interoperability test:

```bash
PYTHONPATH=src python3 -m unittest tests.test_otlp_exporter -v
```

It starts a real local OTLP/HTTP capture endpoint, exports a redacted Skill
event, verifies the `/v1/traces` payload and Skill attributes, confirms
idempotent checkpoints, injects a failed endpoint, and verifies recovery.

## Evidence mapping

Each normalized event is exported as one span. Important attributes include:

| Attribute | Meaning |
|---|---|
| `skill.runtime.name` | Skill identity when known |
| `skill.runtime.run_id` | SkillRun identity |
| `skill.runtime.event` | normalized event type |
| `skill.runtime.stage` | lifecycle stage |
| `skill.runtime.evidence.grade` | Observed, Derived, Inferred, or Experimental |
| `skill.runtime.evidence.confidence` | calibrated confidence from the source record |
| `skill.runtime.source.adapter` | versioned Agent adapter |
| `skill.runtime.status` | event status |

Generic traces remain generic traces in the destination. Skill Runtime does not
claim that an observability backend natively understands the Skill lifecycle.
The canonical diagnosis stays in the local evidence model and UI.

## Primary references

- [OpenTelemetry OTLP exporter specification](https://opentelemetry.io/docs/specs/otel/protocol/exporter/)
- [Phoenix endpoint documentation](https://arize.com/docs/phoenix/learn/faqs/what-is-my-phoenix-endpoint)
- [Grafana Cloud OTLP endpoint](https://grafana.com/docs/grafana-cloud/send-data/otlp/send-data-otlp/)
- [Datadog OTLP intake](https://docs.datadoghq.com/opentelemetry/setup/otlp_ingest/)
- [Langfuse Public API and OTLP ingestion](https://langfuse.com/docs/api-and-data-platform/features/public-api)
