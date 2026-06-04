# MoC Contract — MCP mapping

REST is the source-of-truth contract; MCP is the interop binding. An MCP server
maps the same v1 wire objects into JSON-RPC 2.0 tools and resources (over `stdio`
or Streamable HTTP) **without inventing parallel semantics**. The same
`schemas/*.json` validate the tool inputs/outputs.

## Tools (model-controlled)

| MCP tool | REST equivalent | Input schema | Output schema |
|----------|-----------------|--------------|---------------|
| `context.remember`        | `POST /v1/remember`       | `remember_request` | `remember_response` |
| `context.recall`          | `POST /v1/recall`         | `query_request`    | `inspect_response`  |
| `context.pack`            | `POST /v1/pack`           | `query_request`    | `pack_response`     |
| `context.inspect`         | `POST /v1/inspect`        | `query_request`    | `inspect_response`  |
| `context.router.explain`  | `POST /v1/router/explain` | `query_request`    | `router_explain_response` |
| `context.forget`          | `POST /v1/forget`         | `forget_request`   | `forget_response`   |

## Resources (application-controlled)

| MCP resource | REST equivalent | Output schema |
|--------------|-----------------|---------------|
| `context://experts` | `GET /v1/experts` | `experts_response` |
| `context://scopes`  | `GET /v1/scopes`  | `scopes_response`  |
| `context://items/{id}` | `GET /v1/items/{id}` | `item_response` |
| `context://version` | `GET /v1/version` | `version_response` |

## Notes

- **Inspectability is normative.** `context.inspect` / `context.router.explain`
  must return the same routing scores, selected/unselected experts, kept/dropped
  items, and score breakdowns as the REST surface — the explanation is part of
  the contract, not a debug extra.
- **Transports.** Follow the MCP spec for `stdio` and Streamable HTTP, including
  the spec's origin-validation, localhost-binding, and authentication guidance
  for HTTP transports.
- **Versioning.** Advertise `contract_version` (e.g. via the `context://version`
  resource) so clients can negotiate compatibility.
