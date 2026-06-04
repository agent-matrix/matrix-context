"""Minimal v1 REST surface over the engine — stdlib only, no web framework.

The package stays dependency-light (numpy-only core), so the server is built on
``http.server`` rather than FastAPI. It exposes the SDK 1:1 as JSON over HTTP.

The centerpiece is ``POST /v1/inspect``: it returns the full explainable
contract — routing scores, selected vs. unselected experts, kept and dropped
items with their score breakdown, and the final prompt-ready pack — which the
Context Console UI and the future MCP server both build on.

Endpoints (all under ``/v1``):
    GET  /v1/health      liveness + store size
    GET  /v1/experts     the typed expert taxonomy + seed descriptions
    GET  /v1/items       list stored items (?scope=&expert= filters)
    POST /v1/remember    write an item
    POST /v1/inspect     explainable routed pack (the contract)
    POST /v1/pack        prompt-ready context pack
    POST /v1/forget      delete an item by id

The dispatch is a pure function ``dispatch(service, method, path, body, query)``
returning ``(status, payload)`` so the contract is testable without sockets.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from ... import CONTRACT_VERSION, __version__
from ...manager import ContextManager, _item_dict
from ...routing.experts import EXPERT_DESCRIPTIONS
from ...schema.enums import EXPERTS

API_PREFIX = "/v1"


class HttpError(Exception):
    """Raised by handlers to return a specific status + message."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _need(body: dict, key: str, typ=str):
    if not isinstance(body, dict) or key not in body:
        raise HttpError(400, f"missing required field: {key!r}")
    val = body[key]
    if not isinstance(val, typ):
        raise HttpError(400, f"field {key!r} must be {typ.__name__}")
    return val


class RestService:
    """Pure request handlers over a ContextManager — no HTTP concerns."""

    def __init__(self, manager: ContextManager):
        self.m = manager

    # ---- GET --------------------------------------------------------------
    def health(self) -> dict:
        return {"status": "ok", "name": self.m.config.name,
                "version": __version__, "items": len(self.m.store.all_items())}

    def experts(self) -> dict:
        return {"experts": [{"name": e, "description": EXPERT_DESCRIPTIONS.get(e, "")}
                            for e in EXPERTS]}

    def list_items(self, query: Dict[str, list]) -> dict:
        scope = (query.get("scope") or [None])[0]
        expert = (query.get("expert") or [None])[0]
        items = self.m.items(scope=scope, expert=expert)
        return {"items": [_item_dict(it) for it in items], "count": len(items)}

    def version(self) -> dict:
        return {"contract_version": CONTRACT_VERSION, "implementation": "matrix-context",
                "implementation_version": __version__, "name": self.m.config.name}

    def scopes(self) -> dict:
        """Discover the scope hierarchy present in the store."""
        scopes = sorted({it.scope for it in self.m.store.all_items()})
        return {"scopes": scopes, "count": len(scopes)}

    def get_item(self, item_id: str) -> dict:
        it = self.m.store.get(item_id)
        if it is None:
            raise HttpError(404, f"item not found: {item_id}")
        return {"item": _item_dict(it)}

    # ---- POST -------------------------------------------------------------
    def remember(self, body: dict) -> dict:
        content = _need(body, "content")
        it = self.m.remember(
            content,
            expert=body.get("expert", "semantic"),
            scope=body.get("scope", "/"),
            importance=float(body.get("importance", 0.5)),
            tags=tuple(body.get("tags", ()) or ()),
            ttl=body.get("ttl"),
        )
        return {"item": _item_dict(it)}

    def inspect(self, body: dict) -> dict:
        return self.m.build_inspection(
            _need(body, "query"),
            scope=body.get("scope", "/"),
            top_experts=int(body.get("top_experts", self.m.DEFAULT_TOP_EXPERTS)),
            max_tokens=int(body.get("max_tokens", 600)),
            pin_experts=tuple(body.get("pin_experts", ()) or ()),
        )

    def pack(self, body: dict) -> dict:
        pk = self.m.build_pack(
            _need(body, "query"),
            scope=body.get("scope", "/"),
            top_experts=int(body.get("top_experts", self.m.DEFAULT_TOP_EXPERTS)),
            max_tokens=int(body.get("max_tokens", 600)),
            pin_experts=tuple(body.get("pin_experts", ()) or ()),
        )
        return {
            "tokens": pk.tokens,
            "selected_experts": pk.selected_experts,
            "routing_reason": pk.routing_reason,
            "citations": pk.citations,
            "prompt": pk.to_prompt(),
            "items": [{"id": p.item.id, "expert": p.item.expert,
                       "content": p.item.content} for p in pk.items],
        }

    def router_explain(self, body: dict) -> dict:
        """Routing decision only (the essential inspectability differentiator):
        selected vs. unselected experts and per-expert scores."""
        ins = self.m.build_inspection(
            _need(body, "query"),
            scope=body.get("scope", "/"),
            top_experts=int(body.get("top_experts", self.m.DEFAULT_TOP_EXPERTS)),
            max_tokens=int(body.get("max_tokens", 600)),
            pin_experts=tuple(body.get("pin_experts", ()) or ()),
        )
        r = ins["routing"]
        return {
            "query": ins["query"],
            "selected_experts": r["selected_experts"],
            "unselected_experts": r["unselected_experts"],
            "scores": [{"expert": e, "score": s} for e, s in
                       sorted(r["scores"].items(), key=lambda x: -x[1])],
            "widened": r["widened"],
            "reason": r["reason"],
        }

    def forget(self, body: dict) -> dict:
        item_id = _need(body, "id")
        return {"id": item_id, "deleted": self.m.forget(item_id)}


# Routing tables: path -> handler name.
_GET = {
    f"{API_PREFIX}/health": "health",
    f"{API_PREFIX}/version": "version",
    f"{API_PREFIX}/experts": "experts",
    f"{API_PREFIX}/scopes": "scopes",
    f"{API_PREFIX}/items": "list_items",
}
_POST = {
    f"{API_PREFIX}/remember": "remember",
    f"{API_PREFIX}/recall": "inspect",          # recall is inspect's routed candidates
    f"{API_PREFIX}/inspect": "inspect",
    f"{API_PREFIX}/pack": "pack",
    f"{API_PREFIX}/router/explain": "router_explain",
    f"{API_PREFIX}/forget": "forget",
}
_ALL_PATHS = set(_GET) | set(_POST)
_ITEM_PREFIX = f"{API_PREFIX}/items/"


def dispatch(service: RestService, method: str, path: str,
             body: Optional[dict] = None,
             query: Optional[Dict[str, list]] = None) -> Tuple[int, dict]:
    """Pure router: map a request to a handler and return (status, payload)."""
    method = method.upper()
    try:
        if method == "GET" and path in _GET:
            name = _GET[path]
            handler = getattr(service, name)
            return 200, (handler(query or {}) if name == "list_items" else handler())
        # GET /v1/items/{id}
        if path.startswith(_ITEM_PREFIX) and len(path) > len(_ITEM_PREFIX):
            if method != "GET":
                return 405, {"error": f"method {method} not allowed for {path}"}
            return 200, service.get_item(path[len(_ITEM_PREFIX):])
        if method == "POST" and path in _POST:
            status = 201 if path == f"{API_PREFIX}/remember" else 200
            return status, getattr(service, _POST[path])(body or {})
        if path in _ALL_PATHS:
            return 405, {"error": f"method {method} not allowed for {path}"}
        return 404, {"error": f"not found: {path}"}
    except HttpError as e:
        return e.status, {"error": e.message}
    except (ValueError, TypeError) as e:
        return 400, {"error": str(e)}


def _make_handler(service: RestService):
    class Handler(BaseHTTPRequestHandler):
        server_version = "matrix-context/" + __version__

        def log_message(self, *a):  # quiet by default
            pass

        def _send(self, status: int, payload: dict):
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _read_body(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if not length:
                return {}
            raw = self.rfile.read(length)
            try:
                parsed = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                raise HttpError(400, "invalid JSON body")
            if not isinstance(parsed, dict):
                raise HttpError(400, "JSON body must be an object")
            return parsed

        def do_GET(self):
            parsed = urlparse(self.path)
            status, payload = dispatch(service, "GET", parsed.path,
                                       query=parse_qs(parsed.query))
            self._send(status, payload)

        def do_POST(self):
            parsed = urlparse(self.path)
            try:
                body = self._read_body()
            except HttpError as e:
                self._send(e.status, {"error": e.message})
                return
            status, payload = dispatch(service, "POST", parsed.path, body=body)
            self._send(status, payload)

    return Handler


def create_app(manager: Optional[ContextManager] = None, *,
               host: str = "127.0.0.1", port: int = 8088,
               name: str = "rest", path: Optional[str] = None) -> HTTPServer:
    """Build (but do not start) the HTTP server bound to ``host:port``.

    A single-threaded server is used so the SQLite connection stays on one
    thread; it is sufficient for local use, the UI, and CI. Call
    ``server.serve_forever()`` to run, or use :func:`serve`.
    """
    if manager is None:
        manager = ContextManager.create(name, path=path or f"{name}.matrix-context.db")
    service = RestService(manager)
    return HTTPServer((host, port), _make_handler(service))


def serve(host: str = "127.0.0.1", port: int = 8088,
          manager: Optional[ContextManager] = None,
          name: str = "rest", path: Optional[str] = None) -> None:  # pragma: no cover
    server = create_app(manager, host=host, port=port, name=name, path=path)
    print(f"matrix-context REST listening on http://{host}:{port}{API_PREFIX}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
