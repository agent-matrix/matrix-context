"""End-to-end workflow test — the product spine in one place.

Walks the full happy path so `make install && make test` gives real confidence
the whole thing works together:

    SDK (remember -> build_pack -> inspect)
      -> REST server over real HTTP (the full v1 contract + the Inspector UI)
      -> MoC Contract v1 conformance ("MoC API v1 Compatible")
      -> framework adapters (agent-generator emits runnable memory code; HomePilot)

Runs fully offline with the hashing embedder.
"""
import json
import threading
import urllib.error
import urllib.request

from matrix_context import CONTRACT_VERSION, ContextManager
from matrix_context.serve.rest.app import create_app, inspector_html

SEED = [
    ("Decision: use SQLite as the default storage backend", "semantic", 0.9),
    ("The user prefers local-first tools over cloud services", "profile", 0.9),
    ("Policy: never store API keys or PII in durable memory", "policy", 0.9),
    ("On 2026-05-02 we deferred Milvus support to v2", "episodic", 0.6),
]


# --------------------------------------------------------------------------- #
# 1. SDK end to end
# --------------------------------------------------------------------------- #
def test_sdk_remember_pack_inspect():
    ctx = ContextManager.create("e2e-sdk", path=":memory:")
    for content, expert, importance in SEED:
        ctx.remember(content, expert=expert, importance=importance)

    pack = ctx.build_pack("what is the default storage backend?", max_tokens=120)
    assert pack.tokens <= 120 and pack.selected_experts
    assert any("SQLite" in p.item.content for p in pack.items)
    assert pack.to_prompt().startswith("Relevant context:")

    ins = ctx.build_inspection("what is the default storage backend?", max_tokens=120)
    assert ins["routing"]["selected_experts"]
    assert set(ins["routing"]["selected_experts"]) & \
        set(ins["routing"]["unselected_experts"]) == set()
    for item in ins["pack"]["items"]:
        assert set(item["breakdown"]) == {"relevance", "importance", "recency", "redundancy"}

    text = ctx.inspect("what is the default storage backend?")
    assert "ROUTING:" in text and "PACK" in text


# --------------------------------------------------------------------------- #
# 2. REST server over real HTTP — the full v1 workflow + UI
# --------------------------------------------------------------------------- #
def _http(base, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def test_rest_server_full_workflow_over_http():
    server = create_app(ContextManager.create("e2e-http", path=":memory:"),
                        host="127.0.0.1", port=0)
    host, port = server.server_address
    base = f"http://{host}:{port}"
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        # version advertises the frozen contract
        st, ver = _http(base, "GET", "/v1/version")
        assert st == 200 and ver["contract_version"] == CONTRACT_VERSION

        # remember the seed set
        ids = []
        for content, expert, importance in SEED:
            st, body = _http(base, "POST", "/v1/remember",
                             {"content": content, "expert": expert, "importance": importance})
            assert st == 201
            ids.append(body["item"]["id"])

        # discovery
        assert _http(base, "GET", "/v1/experts")[1]["experts"]
        assert "/" in _http(base, "GET", "/v1/scopes")[1]["scopes"]
        assert _http(base, "GET", "/v1/items")[1]["count"] == len(SEED)
        assert _http(base, "GET", f"/v1/items/{ids[0]}")[1]["item"]["id"] == ids[0]

        # inspect: routing + budgeted, explainable pack
        st, ins = _http(base, "POST", "/v1/inspect",
                        {"query": "default storage backend?", "max_tokens": 120})
        assert st == 200 and ins["routing"]["selected_experts"]
        assert any("SQLite" in p["content"] for p in ins["pack"]["items"])

        # pack: prompt-ready
        st, pk = _http(base, "POST", "/v1/pack", {"query": "backend decision", "max_tokens": 80})
        assert pk["prompt"].startswith("Relevant context:") and pk["tokens"] <= 80

        # router/explain: ranked scores
        st, re_ = _http(base, "POST", "/v1/router/explain", {"query": "policy on secrets"})
        scores = [s["score"] for s in re_["scores"]]
        assert scores == sorted(scores, reverse=True)

        # forget
        assert _http(base, "POST", "/v1/forget", {"id": ids[0]})[1]["deleted"] is True

        # error contract
        assert _http(base, "GET", "/v1/nope")[0] == 404
        assert _http(base, "POST", "/v1/inspect", {})[0] == 400

        # the Context Inspector UI is served at /
        with urllib.request.urlopen(f"{base}/", timeout=5) as r:
            assert r.status == 200 and "Context Inspector" in r.read().decode()
    finally:
        server.shutdown()
        server.server_close()

    assert "Context Inspector" in inspector_html()


# --------------------------------------------------------------------------- #
# 3. MoC Contract v1 conformance
# --------------------------------------------------------------------------- #
def test_reference_passes_conformance():
    import pytest
    pytest.importorskip("jsonschema")
    from moc_contract.conformance import in_process_client, run

    report = run(in_process_client())
    assert report.ok, [c for c in report.checks if not c[1]]


# --------------------------------------------------------------------------- #
# 4. Framework adapters: generated memory code runs; HomePilot recalls
# --------------------------------------------------------------------------- #
def test_agent_generator_emitted_code_runs(tmp_path):
    from matrix_context.adapters.agent_generator import emit_template

    t = emit_template("Research assistant", framework="react",
                      store_path=str(tmp_path / "gen.matrix-context.db"))
    ns: dict = {}
    exec(compile(t.code, "matrix_memory.py", "exec"), ns)
    ns["bootstrap"]()
    ns["record_turn"]("The user prefers Postgres for audit logs.", "Noted.")
    assert "Postgres" in ns["build_context"]("what database for audit logs?")


def test_homepilot_adapter_recalls_profile_and_memory():
    from matrix_context.adapters.homepilot import HomePilotAdapter

    ctx = ContextManager.create("e2e-hp", path=":memory:")
    hp = HomePilotAdapter(ctx)
    hp.load_persona({"id": "coach", "label": "Coach",
                     "system_prompt": "You are a motivational coach."})
    hp.load_memories(["The user is training for a marathon in October."])
    pack = hp.build_pack("what is the user training for?")
    experts = {p.item.expert for p in pack.items}
    contents = " ".join(p.item.content for p in pack.items)
    assert "profile" in experts          # profile always injectable
    assert "marathon" in contents        # routed memory recalled
    assert "ROUTING:" in hp.explain("what is the user training for?")
