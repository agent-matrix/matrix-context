# Production memory lifecycle

Matrix Context is the memory plane; it does not act.

This change adds deterministic lifecycle primitives needed by Matrix OS:

- near-duplicate suppression,
- supersession without deleting history,
- procedural-memory consolidation,
- explicit provenance type,
- hash-chained audit events,
- a first-class `procedural` expert.

## Memory classes

- **episodic** — what happened,
- **procedural** — reusable strategies/lessons,
- **semantic** — durable facts,
- **policy** — constraints,
- existing session/profile/document experts remain.

## Integration

Matrix OS should use `POST /v1/recall` for inspectable retrieval and
`POST /v1/remember` or the SDK lifecycle-aware write path for durable outcomes.

A later storage migration can persist provenance/audit fields directly in SQL;
the lifecycle semantics introduced here are backend-independent.
