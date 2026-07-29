# Security policy

## Reporting a vulnerability

Please do not disclose a suspected vulnerability in a public issue.
Send a private report to `hellogxp@gmail.com` with:

- the affected version and platform;
- reproduction steps or a minimal proof of concept;
- the expected security impact;
- any suggested mitigation.

You should receive an acknowledgement within seven days. Confirmed issues will
be coordinated privately until a fix and disclosure plan are ready.

## Product security model

Skill Runtime is read-only and local by default. It does not proxy model
requests or block Agent actions. Runtime evidence can include sensitive paths
or content, so network export is disabled unless the user explicitly enables an
endpoint. Please review Hook commands before trusting them and avoid attaching
raw runtime databases to public issues.
