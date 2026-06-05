"""v1 REST contract tests.

Covers the dispatch contract for every endpoint (no sockets) plus one real
HTTP round-trip proving the app runs and POST /v1/inspect returns the full
explainable contract. The inspect response is the load-bearing one: the UI and
the future MCP server depend on its exact shape.
"""
import json
import threading
import urllib.request

import pytest

from matrix_context import ContextManager
from matrix_context.serve.rest.app import RestService, create_app, dispatch


@pytest.fixture
def service():
    m = ContextManager.create("rest-test", path=":memory:")
    m.remember("Decision: use OAuth 2.1 with PKCE for MCP HTTP clients",
               expert="policy", importance=0.9)
    m.remember("The user prefers local-first tools", expert="profile", importance=0.9)
    m.remember("Decision: SQLite is the default backend", expert="semantic", importance=0.8)
    m.remember("On 2026-05-02 we agreed to defer Milvus to v2", expert="episodic")
    return RestService(m)


# --------------------------------------------------------------- GET endpoints
def test_health(service):
    status, body = dispatch(service, "GET", "/v1/health")
    assert status == 200
    assert body["status"] == "ok" and body["items"] == 4 and "version" in body


def test_experts_lists_taxonomy(service):
    status, body = dispatch(service, "GET", "/v1/experts")
    assert status == 200
    names = {e["name"] for e in body["experts"]}
    assert {"session", "profile", "semantic", "episodic", "document", "policy"} == names
    assert all(e["description"] for e in body["experts"])


def test_items_list_and_filter(service):
    _, all_body = dispatch(service, "GET", "/v1/items")
    assert all_body["count"] == 4
    _, pol = dispatch(service, "GET", "/v1/items", query={"expert": ["policy"]})
    assert pol["count"] == 1 and pol["items"][0]["expert"] == "policy"
    assert "embedding" not in pol["items"][0]  # embeddings never serialized


# -------------------------------------------------------------- POST endpoints
def test_remember_stores_item(service):
    status, body = dispatch(service, "POST", "/v1/remember",
                            body={"content": "Decision: ship the REST API",
                                  "expert": "semantic", "importance": 0.7})
    assert status == 201
    item = body["item"]
    assert item["content"] == "Decision: ship the REST API" and item["id"]
    # It is now retrievable.
    _, listing = dispatch(service, "GET", "/v1/items")
    assert listing["count"] == 5


def test_inspect_returns_full_contract(service):
    status, body = dispatch(service, "POST", "/v1/inspect",
                            body={"query": "what did we decide about MCP auth",
                                  "max_tokens": 100})
    assert status == 200
    routing, pack = body["routing"], body["pack"]

    # Routing: selected, non-selected, scores, explanation.
    assert routing["selected_experts"]
    assert "unselected_experts" in routing
    selset, unselset = set(routing["selected_experts"]), set(routing["unselected_experts"])
    assert selset and not (selset & unselset)               # disjoint
    assert isinstance(routing["scores"], dict) and routing["scores"]
    assert isinstance(routing["reason"], str) and routing["reason"]
    assert "widened" in routing

    # Pack: kept items with score breakdown, dropped items, prompt-ready text.
    assert pack["tokens"] <= 100
    assert isinstance(pack["items"], list) and pack["items"]
    for it in pack["items"]:
        assert set(it["breakdown"]) == {"relevance", "importance", "recency", "redundancy"}
        assert "final_score" in it and it["content"]
    assert "dropped" in pack
    assert pack["prompt"].startswith("Relevant context:")
    assert pack["citations"]


def test_pack_returns_prompt_ready(service):
    status, body = dispatch(service, "POST", "/v1/pack",
                            body={"query": "MCP auth decision", "max_tokens": 80})
    assert status == 200
    assert body["prompt"].startswith("Relevant context:")
    assert body["tokens"] <= 80 and body["selected_experts"]


# --------------------------------------------------------- v1 contract endpoints
def test_version_advertises_contract(service):
    from matrix_context import CONTRACT_VERSION
    status, body = dispatch(service, "GET", "/v1/version")
    assert status == 200
    assert body["contract_version"] == CONTRACT_VERSION
    assert body["implementation"] == "matrix-context"


def test_scopes_discovers_hierarchy(service):
    status, body = dispatch(service, "GET", "/v1/scopes")
    assert status == 200 and "/" in body["scopes"]


def test_get_item_by_id_and_404(service):
    _, listing = dispatch(service, "GET", "/v1/items")
    target = listing["items"][0]["id"]
    status, body = dispatch(service, "GET", f"/v1/items/{target}")
    assert status == 200 and body["item"]["id"] == target
    status, _ = dispatch(service, "GET", "/v1/items/missing-id")
    assert status == 404


def test_router_explain_scores_ranked(service):
    status, body = dispatch(service, "POST", "/v1/router/explain",
                            body={"query": "what is the policy on secrets"})
    assert status == 200
    assert body["selected_experts"] and "scores" in body
    scores = [s["score"] for s in body["scores"]]
    assert scores == sorted(scores, reverse=True)
    assert set(body["selected_experts"]) & set(  # disjoint from unselected
        body["unselected_experts"]) == set()


def test_forget_deletes_item(service):
    _, listing = dispatch(service, "GET", "/v1/items")
    target = listing["items"][0]["id"]
    status, body = dispatch(service, "POST", "/v1/forget", body={"id": target})
    assert status == 200 and body["deleted"] is True
    _, after = dispatch(service, "GET", "/v1/items")
    assert after["count"] == 3
    # Forgetting a missing id is a no-op, reported as deleted=False.
    _, again = dispatch(service, "POST", "/v1/forget", body={"id": target})
    assert again["deleted"] is False


# --------------------------------------------------------------- error contract
def test_unknown_route_404(service):
    status, body = dispatch(service, "GET", "/v1/nope")
    assert status == 404 and "error" in body


def test_method_not_allowed_405(service):
    status, _ = dispatch(service, "GET", "/v1/remember")
    assert status == 405


def test_missing_required_field_400(service):
    status, body = dispatch(service, "POST", "/v1/inspect", body={})
    assert status == 400 and "query" in body["error"]


# ----------------------------------------------------------- real HTTP round-trip
def test_server_runs_and_serves_inspect_over_http():
    m = ContextManager.create("rest-http", path=":memory:")
    m.remember("Decision: use OAuth 2.1 with PKCE for MCP HTTP clients",
               expert="policy", importance=0.9)
    server = create_app(m, host="127.0.0.1", port=0)  # ephemeral port
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        base = f"http://{host}:{port}/v1"
        with urllib.request.urlopen(f"{base}/health", timeout=5) as r:
            assert r.status == 200
            assert json.loads(r.read())["status"] == "ok"

        req = urllib.request.Request(
            f"{base}/inspect",
            data=json.dumps({"query": "MCP auth", "max_tokens": 100}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            payload = json.loads(r.read())
        assert payload["routing"]["selected_experts"]
        assert payload["pack"]["prompt"].startswith("Relevant context:")
    finally:
        server.shutdown()
        server.server_close()


def test_inspector_ui_is_served_at_root():
    """The Context Inspector UI is served as HTML at / and /ui."""
    import threading
    import urllib.request

    from matrix_context.serve.rest.app import inspector_html

    html = inspector_html()
    assert "Context Inspector" in html
    assert '"/inspect"' in html and "/v1" in html   # calls the inspect endpoint

    m = ContextManager.create("rest-ui", path=":memory:")
    server = create_app(m, host="127.0.0.1", port=0)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        for path in ("/", "/ui"):
            with urllib.request.urlopen(f"http://{host}:{port}{path}", timeout=5) as r:
                assert r.status == 200
                assert r.headers.get_content_type() == "text/html"
                assert "Context Inspector" in r.read().decode()
    finally:
        server.shutdown()
        server.server_close()


def test_console_asset_is_path_safe():
    from matrix_context.serve.rest.app import console_asset
    assert console_asset("index.html") is not None
    assert console_asset("api.js")[1].startswith("application/javascript")
    assert console_asset("console.css")[1].startswith("text/css")
    # traversal / nested / unknown are rejected
    assert console_asset("../app.py") is None
    assert console_asset("nope.js") is None
    assert console_asset("sub/x.js") is None


def test_console_spa_is_served_live():
    """The Context Console (Phase 0) is served same-origin at /console; existing
    routes and the contract are untouched."""
    import threading
    import urllib.error
    import urllib.request

    m = ContextManager.create("rest-console", path=":memory:")
    server = create_app(m, host="127.0.0.1", port=0)
    host, port = server.server_address
    base = f"http://{host}:{port}"
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    def get(path):
        try:
            with urllib.request.urlopen(base + path, timeout=5) as r:
                return r.status, r.headers.get_content_type(), r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get_content_type(), ""

    try:
        st, ct, body = get("/console")
        assert st == 200 and ct == "text/html" and "Matrix Context" in body
        st, ct, body = get("/console/api.js")
        assert st == 200 and "window.MC" in body and "/inspect" in body  # the live adapter
        st, ct, body = get("/console/app.js")
        assert st == 200 and "viewInspector" in body
        assert get("/console/console.css")[1] == "text/css"
        assert get("/console/missing.js")[0] == 404
        # existing surfaces still work, contract unchanged
        assert get("/")[1] == "text/html"
        with urllib.request.urlopen(base + "/v1/version", timeout=5) as r:
            import json
            assert json.loads(r.read())["contract_version"] == "1.0.0"
    finally:
        server.shutdown()
        server.server_close()


def test_default_rest_port_is_8088():
    # Acceptance: the app is meant to run on localhost:8088 by default.
    import inspect as _inspect

    from matrix_context.serve.rest.app import serve
    assert _inspect.signature(serve).parameters["port"].default == 8088
