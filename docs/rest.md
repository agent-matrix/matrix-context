# REST API (v1)

The minimal v1 REST surface exposes the engine over HTTP as JSON. It is built on
the Python standard library (`http.server`) so the package stays dependency-light
— no FastAPI required. The centerpiece is **`POST /v1/inspect`**, which returns
the full *explainable* routed-pack contract that the Context Console UI and the
future MCP server both build on.

## Run

```bash
matrix-context serve --transport rest --port 8088
# matrix-context REST listening on http://127.0.0.1:8088/v1
```

Or from Python:

```python
from matrix_context.serve.rest import create_app
create_app(host="127.0.0.1", port=8088).serve_forever()
```

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/v1/health`   | liveness + store size |
| GET  | `/v1/experts`  | typed expert taxonomy + seed descriptions |
| GET  | `/v1/items`    | list items (`?scope=` / `?expert=` filters) |
| POST | `/v1/remember` | write an item → `201` |
| POST | `/v1/inspect`  | **explainable routed pack (the contract)** |
| POST | `/v1/pack`     | prompt-ready context pack |
| POST | `/v1/forget`   | delete an item by id |

## The inspect contract

`POST /v1/inspect` with `{"query": "...", "max_tokens": 100}` returns:

```jsonc
{
  "query": "what did we decide about MCP auth",
  "routing": {
    "selected_experts":   ["policy", "semantic"],
    "unselected_experts": ["document", "episodic", "profile", "session"],
    "scores":   { "policy": 0.59, "semantic": 0.23, "...": 0.07 },
    "widened":  false,
    "reason":   "confident: top=0.599, gap=0.371"
  },
  "pack": {
    "tokens": 8,
    "max_tokens": 100,
    "selected_experts": ["policy", "semantic"],
    "routing_reason": "confident: top=0.599, gap=0.371",
    "items": [
      { "id": "ctx_…", "expert": "policy", "content": "Decision: …",
        "final_score": 1.23,
        "breakdown": { "relevance": 1.0, "importance": 0.2,
                       "recency": 0.3, "redundancy": 0.0 } }
    ],
    "dropped": [ { "id": "ctx_…", "expert": "semantic",
                   "reason": "exceeds token budget" } ],
    "citations": ["ctx_…"],
    "prompt": "Relevant context:\n\n1. [policy] Decision: …"
  }
}
```

This single response carries everything a UI needs to explain a selection:
selected vs. non-selected experts, the routing scores and reason, the kept items
with their score breakdown, the dropped items with the reason they were dropped,
and the final prompt-ready pack.

The same structure backs the SDK's `ContextManager.build_inspection()` and the
human-readable `ContextManager.inspect()` string, so REST, SDK, and (next) MCP
stay in lockstep.
