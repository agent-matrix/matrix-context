# Governance (v1)

First-class axis: PII redaction before embedding, sensitivity labels,
approval-required writes for profile/policy/pinned memory, append-only audit,
and tenant/scope checks on every read and write. SQL (with row-level security
on Postgres) is the source of truth; vectors never hold governance state.
