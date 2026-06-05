"""Matrix Context — frontend / control-plane server.

A self-contained, Hugging-Face-deployable launcher that serves:
  * the static control-plane UI in ``frontend/app/`` (Overview, Inspector,
    Builder, Memory, Experts, Routing, Benchmarks, Standard, Settings), and
  * the live MoC Contract v1 API under ``/v1`` — by reusing the published
    backend's ``RestService`` / ``dispatch``.

This is **additive and non-destructive**: it imports ``matrix_context`` and the
existing REST app; it does not modify them. A small demo memory set is seeded on
startup so the Space is useful immediately.

    python frontend/server.py            # local  -> http://127.0.0.1:7860
    PORT=7860 HOST=0.0.0.0 python ...     # container / Hugging Face Space
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from matrix_context import ContextManager
from matrix_context.serve.rest.app import RestService, dispatch

APP_DIR = Path(__file__).parent / "app"
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "7860"))
DB_PATH = os.environ.get("MATRIX_CONTEXT_PATH", ":memory:")

_CONTENT_TYPES = {".html": "text/html; charset=utf-8",
                  ".js": "application/javascript; charset=utf-8",
                  ".css": "text/css; charset=utf-8",
                  ".svg": "image/svg+xml", ".json": "application/json",
                  ".png": "image/png", ".ico": "image/x-icon"}

# Demo seed — a small, typed, multi-scope memory set so every view is populated.
SEED = [
    ("Decision: use SQLite as the default storage backend; vectors accelerate, SQL is the source of truth.",
     "semantic", "project:matrix-context", 0.95, ["backend", "sqlite", "type:decision"]),
    ("Matrix Context exposes both a Python SDK and an MCP server so agents and operators share one memory plane.",
     "semantic", "project:matrix-context", 0.9, ["mcp", "sdk", "type:decision"]),
    ("Policy: the agent must never store API keys, tokens, or PII in durable memory.",
     "policy", "project:matrix-context", 0.95, ["security", "pii", "type:rule"]),
    ("Decision: defer Milvus support to v2; pgvector lands in v1.",
     "episodic", "project:matrix-context", 0.8, ["milvus", "roadmap", "type:decision"]),
    ("The user prefers local-first tools over cloud services by default.",
     "profile", "user:42", 0.9, ["preference", "type:preference"]),
    ("The user prefers concise, direct answers with code first.",
     "profile", "user:42", 0.8, ["preference", "tone", "type:preference"]),
    ("The whitepaper reports that routed typed context cuts distractors at equal recall.",
     "document", "project:matrix-context", 0.7, ["whitepaper", "type:document"]),
    ("Decision: ship the REST API and Context Console before the MCP server.",
     "semantic", "project:acme", 0.85, ["rest", "console", "type:decision"]),
    ("Policy in project:acme — audit-log every write to profile or policy memory.",
     "policy", "project:acme", 0.88, ["audit", "governance", "type:rule"]),
    ("In the last session we agreed the demo should run on Hugging Face Spaces.",
     "episodic", "project:acme", 0.65, ["session", "demo", "type:episode"]),
]


def build_service() -> RestService:
    mgr = ContextManager.create("matrix-context-demo", path=DB_PATH)
    if not mgr.store.all_items():
        for content, expert, scope, importance, tags in SEED:
            mgr.remember(content, expert=expert, scope=scope,
                         importance=importance, tags=tags)
    return RestService(mgr)


def _static(path: str):
    """Resolve a static asset under APP_DIR (path-traversal safe)."""
    rel = path.lstrip("/") or "index.html"
    target = (APP_DIR / rel).resolve()
    if APP_DIR.resolve() not in target.parents and target != APP_DIR.resolve():
        return None
    if not target.is_file():
        return None
    ctype = _CONTENT_TYPES.get(target.suffix, "application/octet-stream")
    return target.read_bytes(), ctype


def make_handler(service: RestService):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send_json(self, status, payload):
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_bytes(self, data, ctype, status=200):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _read_body(self):
            n = int(self.headers.get("Content-Length") or 0)
            if not n:
                return {}
            try:
                obj = json.loads(self.rfile.read(n) or b"{}")
                return obj if isinstance(obj, dict) else {}
            except json.JSONDecodeError:
                return {}

        def do_GET(self):
            p = urlparse(self.path)
            if p.path.startswith("/v1"):
                st, payload = dispatch(service, "GET", p.path, query=parse_qs(p.query))
                self._send_json(st, payload)
                return
            asset = _static("index.html" if p.path == "/" else p.path)
            if asset:
                self._send_bytes(*asset)
            else:
                self._send_json(404, {"error": f"not found: {p.path}"})

        def do_POST(self):
            p = urlparse(self.path)
            if p.path.startswith("/v1"):
                st, payload = dispatch(service, "POST", p.path, body=self._read_body())
                self._send_json(st, payload)
            else:
                self._send_json(404, {"error": f"not found: {p.path}"})

    return Handler


def main() -> int:
    service = build_service()
    httpd = HTTPServer((HOST, PORT), make_handler(service))
    n = len(service.m.store.all_items())
    print(f"Matrix Context control plane on http://{HOST}:{PORT}  ({n} seeded items)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
