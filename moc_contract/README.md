# MoC Contract v1

The **standard**, separate from any one implementation: a frozen, versioned wire
contract for typed agent-memory recall, routed retrieval, budgeted context
packing, and **inspectable** routing explanations. It is designed to sit above
many storage engines, embedders, and agent frameworks — the value is a stable,
inspectable contract, not a particular vector store.

```
moc_contract/
├── schemas/            JSON Schema 2020-12 wire objects (single source of truth)
├── openapi.yaml        OpenAPI 3.1 description of the HTTP surface
├── mcp-mapping.md      MCP (tools/resources) binding of the same objects
├── compatibility.md    SemVer compatibility + deprecation policy
├── loader.py           load schemas + build a validation registry
└── conformance.py      executable conformance suite (shape + behaviour)
```

## The contract at a glance

HTTP surface (`/v1`): `GET health, version, experts, scopes, items, items/{id}`;
`POST remember, recall, pack, inspect, router/explain, forget`. The
load-bearing, differentiating object is the **inspect** response: selected vs.
unselected experts, per-expert routing scores, kept items with a per-item score
breakdown, dropped items with reasons, and the final prompt-ready pack.

## Conformance

A server is **MoC API v1 Compatible** when it passes the suite, which drives the
target purely through HTTP/JSON and validates every response against the schemas
plus behavioural invariants (routing disjointness, token budget, inspect
completeness, pin semantics, error contract):

```bash
# bundled reference (in-process Matrix Context)
python -m moc_contract.conformance

# a running server
matrix-context serve --transport rest --port 8088
python -m moc_contract.conformance --url http://127.0.0.1:8088
```

Requires the `conformance` extra: `pip install "matrix-context[conformance]"`
(`jsonschema`).

## Versioning

`CONTRACT_VERSION` follows [SemVer](https://semver.org) independently of the
implementation's package version; see `compatibility.md`. Implementations
advertise the contract version they target via `GET /v1/version`.

## Status

v1.0.0 is frozen against the `matrix-context` reference implementation, which
passes the full suite. Additional implementations that pass `moc_contract.conformance`
may claim `MoC API v1 Compatible`.
