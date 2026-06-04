"""v1 REST route table (documentation) — implemented in app.py.

The minimal v1 contract mirrors the SDK. POST /v1/inspect is the centerpiece:
it returns the full explainable routed-pack contract the UI and MCP build on.
Governance routes (approve, audit, ingest) follow once the engine surface is
stable.
"""
ROUTES = [
    ("GET", "/v1/health"),
    ("GET", "/v1/experts"),
    ("GET", "/v1/items"),
    ("POST", "/v1/remember"),
    ("POST", "/v1/inspect"),
    ("POST", "/v1/pack"),
    ("POST", "/v1/forget"),
]
