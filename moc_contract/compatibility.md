# MoC Contract — compatibility and versioning policy

The MoC Contract has its own version (`CONTRACT_VERSION`, currently **1.0.0**),
independent of any implementation's package version. It follows
[Semantic Versioning](https://semver.org): the *public API* is the set of wire
objects in `schemas/`, the HTTP surface in `openapi.yaml`, and their documented
semantics.

## What is covered

The frozen v1 public surface is:

- **Objects** (`schemas/*.json`): `MemoryItem`, `ScoreBreakdown`, `PackedItem`,
  `DroppedItem`, `ExpertScore`, `Error`, the request bodies, and the per-endpoint
  responses (`HealthResponse`, `VersionResponse`, `ExpertsResponse`,
  `ScopesResponse`, `ItemsResponse`, `ItemResponse`, `RememberResponse`,
  `PackResponse`, `InspectResponse`, `RouterExplainResponse`, `ForgetResponse`).
- **Endpoints** (`openapi.yaml`): `GET /v1/{health,version,experts,scopes,items,items/{id}}`
  and `POST /v1/{remember,recall,pack,inspect,router/explain,forget}`.

## Compatibility rules

| Change | Bump |
|--------|------|
| New optional response field | MINOR |
| New optional endpoint | MINOR |
| New expert type behind a feature flag (default semantics unchanged) | MINOR |
| New optional request field with a backward-compatible default | MINOR |
| Renaming or removing a field | MAJOR |
| Making an optional field required | MAJOR |
| Changing the meaning of a score, or routing semantics, in a way that breaks clients | MAJOR |
| Documentation fix or implementation bugfix with no wire change | PATCH |

Schemas use `additionalProperties` permissively so that MINOR additions do not
break strict validators. Clients **must** ignore unknown fields.

## Deprecation

A field or endpoint slated for removal is marked deprecated in `openapi.yaml`
(and noted here) for at least one MINOR release before a MAJOR removal. The
`GET /v1/version` response advertises the `contract_version` an implementation
targets so clients can negotiate.

## Conformance

An implementation is **MoC API v1 Compatible** when it passes
`python -m moc_contract.conformance` (shape validation against these schemas plus
behavioural invariants). Badges: `MoC API v1 Compatible`, `MoC Inspect v1
Compatible`, `MoC MCP v1 Compatible`.
