# E4 — Cross-Agent/export-profile comparability

The local gate feeds semantically equivalent parent/child Skill traces through
the OTel, Phoenix, LangSmith, Langfuse, Weave, and Datadog export profiles. It
checks only fields that the profiles can represent equivalently and audits
parent references for dangling IDs.

This is a canonicalization test. Live same-Skill comparisons across independent
Agents remain a stronger experiment tier.

