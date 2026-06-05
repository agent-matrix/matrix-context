"""The frontend control-plane server serves the UI + a live /v1, and is additive.

Loads frontend/server.py (a standalone launcher, not part of the package), checks
it seeds demo memory and serves both static assets and the real API by reusing
the backend's dispatch.
"""
import importlib.util
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "frontend" / "server.py"


@pytest.fixture(scope="module")
def fe():
    spec = importlib.util.spec_from_file_location("fe_server", SERVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _serve(fe):
    service = fe.build_service()
    httpd = fe.HTTPServer(("127.0.0.1", 0), fe.make_handler(service))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    host, port = httpd.server_address
    return httpd, service, f"http://{host}:{port}"


def _get(base, p):
    try:
        with urllib.request.urlopen(base + p, timeout=5) as r:
            return r.status, r.headers.get_content_type(), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get_content_type(), e.read()


def test_seeds_and_serves_ui_and_live_api(fe):
    httpd, service, base = _serve(fe)
    try:
        assert len(service.m.store.all_items()) >= 8        # demo seed present

        st, ct, body = _get(base, "/")
        assert st == 200 and ct == "text/html" and "Matrix Context" in body.decode()
        for path, frag in [("/app.js", "vInspector"), ("/api.js", "window.MC")]:
            st, ct, body = _get(base, path)
            assert st == 200 and ct.startswith("application/javascript") and frag in body.decode()
        assert _get(base, "/styles.css")[1] == "text/css"
        assert _get(base, "/assets/logo.svg")[1] == "image/svg+xml"

        # live /v1 through the reused backend dispatch
        req = urllib.request.Request(base + "/v1/inspect",
                                     data=json.dumps({"query": "default storage backend?",
                                                      "max_tokens": 120}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            ins = json.loads(r.read())
        assert ins["routing"]["selected_experts"] and "SQLite" in ins["pack"]["prompt"]
        with urllib.request.urlopen(base + "/v1/version", timeout=5) as r:
            assert json.loads(r.read())["contract_version"] == "1.0.0"

        # path-traversal is refused
        assert _get(base, "/../pyproject.toml")[0] == 404
    finally:
        httpd.shutdown()
        httpd.server_close()
