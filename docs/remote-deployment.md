# Self-hosted remote deployment

Skill Runtime Intelligence separates **deployment placement** from
**observability interoperability**. The service can run on a developer
workstation or on a self-managed remote host. Importing traces from, or
exporting normalized evidence to, another observability platform is optional
in either topology.

Remote mode remains observational. It does not proxy model requests, take over
the Agent loop, or turn collection failure into an Agent failure.

## Security contract

Remote mode is explicit and fail-closed:

- a non-loopback bind is rejected unless `--remote` is present;
- remote mode requires separate viewer and Collector credentials;
- the viewer credential can read the UI and APIs but cannot ingest events,
  change settings, or delete indexed runs;
- the Collector credential is a write-only Bearer token accepted only by
  `/api/events`;
- token files must be regular, non-symlinked files inaccessible to group and
  other users;
- remote traffic must use direct TLS or a loopback backend behind an HTTPS
  reverse proxy;
- failed Hook deliveries remain in the permission-restricted local queue and
  never block the Agent decision path.

This is a self-hosted deployment mode, not a multi-tenant SaaS or organization
governance service.

## 1. Initialize credentials on the service host

```bash
skill-runtime remote-init
```

The command creates two `0600` files under
`~/.skill-runtime/secrets/` and prints only their paths. It never prints token
values and never replaces existing credentials.

## 2A. Recommended: loopback backend behind HTTPS

Start the SRI backend on loopback:

```bash
skill-runtime serve \
  --remote \
  --behind-https-proxy \
  --host 127.0.0.1 \
  --port 4317
```

Expose it through an HTTPS reverse proxy. A minimal Caddy site is:

```caddyfile
sri.example.com {
    reverse_proxy 127.0.0.1:4317
}
```

The proxy must preserve the `Authorization` header. Open the HTTPS URL in a
browser, use `sri` as the username, and use the contents of
`remote-viewer.token` as the password.

## 2B. Direct TLS

When the service has a certificate and private key, it can terminate TLS
itself:

```bash
skill-runtime serve \
  --remote \
  --host 0.0.0.0 \
  --port 4317 \
  --tls-cert /etc/sri/tls/fullchain.pem \
  --tls-key /etc/sri/tls/privkey.pem
```

Use a service manager for restarts and resource limits. Direct-TLS remote mode
runs in the foreground by design; secrets are referenced by file path rather
than copied into process arguments.

## 3. Connect an Agent host

Copy only the ingest token to a `0600` file on the Agent host through an
approved secret-distribution channel. Then set these variables in the
environment that launches the Agent:

```bash
export SKILL_RUNTIME_COLLECTOR_ENDPOINT=https://sri.example.com/api/events
export SKILL_RUNTIME_COLLECTOR_TOKEN_FILE="$HOME/.skill-runtime/secrets/remote-ingest.token"
```

Installed fail-open Hooks use those values for direct delivery. Run the relay
alongside the Agent to replay any events queued during network or service
outages:

```bash
skill-runtime relay \
  --endpoint "$SKILL_RUNTIME_COLLECTOR_ENDPOINT" \
  --token-file "$SKILL_RUNTIME_COLLECTOR_TOKEN_FILE"
```

`relay --once` performs one bounded replay and exits. The network request is
made without holding the queue lock, so a slow remote service cannot extend the
Hook critical section. Duplicate replay is safe because normalized event IDs
are idempotent.

## 4. Verify the boundary

An unauthenticated health request returns only product/version/deployment
metadata. It does not return database counts or indexed evidence:

```bash
curl https://sri.example.com/api/health
```

Use browser Basic authentication for the read-only UI/API. Collector requests
must use the separate ingest token. Swapping the two credentials is rejected.

Remote placement does not require OTLP export. If interoperability is desired,
configure [observability import/export](observability-platform-setup.md)
independently.
