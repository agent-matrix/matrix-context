"""Executable MoC Contract v1 conformance suite.

A server is *MoC v1 compatible* if it passes these checks. The suite is
implementation-agnostic: it drives a target purely through a ``call`` function
``call(method, path, body=None, query=None) -> (status, payload)`` and validates
every response against the frozen JSON Schemas (shape) plus a set of behavioural
invariants (routing, budget, inspectability, error semantics).

    # against the bundled reference (in-process Matrix Context)
    python -m moc_contract.conformance

    # against a running server
    python -m moc_contract.conformance --url http://127.0.0.1:8088
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Callable, List, Tuple

from . import CONTRACT_VERSION
from .loader import validate

Call = Callable[..., Tuple[int, dict]]
PREFIX = "/v1"


@dataclass
class Report:
    checks: List[Tuple[str, bool, str]] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = ""):
        self.checks.append((name, ok, detail))

    def shape(self, name: str, schema: str, payload) -> bool:
        errs = validate(schema, payload)
        self.add(f"shape:{name} ⊨ {schema}", not errs, "; ".join(errs[:3]))
        return not errs

    @property
    def passed(self) -> int:
        return sum(1 for _, ok, _ in self.checks if ok)

    @property
    def failed(self) -> int:
        return sum(1 for _, ok, _ in self.checks if not ok)

    @property
    def ok(self) -> bool:
        return self.failed == 0


def run(call: Call) -> Report:
    r = Report()

    # --- version / health ----------------------------------------------------
    st, ver = call("GET", f"{PREFIX}/version")
    r.add("GET /version status 200", st == 200, str(st))
    if r.shape("version", "version_response", ver):
        r.add("version.contract_version == 1.x",
              ver.get("contract_version", "").split(".")[0] == "1",
              ver.get("contract_version", ""))
    st, h = call("GET", f"{PREFIX}/health")
    r.add("GET /health status 200", st == 200, str(st))
    r.shape("health", "health_response", h)

    # --- experts / scopes ----------------------------------------------------
    r.shape("experts", "experts_response", call("GET", f"{PREFIX}/experts")[1])

    # --- remember (seed data via the API) -----------------------------------
    st, rem = call("POST", f"{PREFIX}/remember", {
        "content": "Decision: use OAuth 2.1 with PKCE for MCP HTTP clients",
        "expert": "policy", "importance": 0.9})
    r.add("POST /remember status 201", st == 201, str(st))
    r.shape("remember", "remember_response", rem)
    item_id = rem.get("item", {}).get("id", "")
    for c, e in [("The user prefers local-first tools", "profile"),
                 ("Decision: SQLite is the default backend", "semantic"),
                 ("On 2026-05-02 we deferred Milvus to v2", "episodic")]:
        call("POST", f"{PREFIX}/remember", {"content": c, "expert": e})

    # --- items list + by id --------------------------------------------------
    st, items = call("GET", f"{PREFIX}/items")
    r.shape("items", "items_response", items)
    r.add("items count >= 4", items.get("count", 0) >= 4, str(items.get("count")))
    st, one = call("GET", f"{PREFIX}/items/{item_id}")
    r.add("GET /items/{id} status 200", st == 200, str(st))
    r.shape("item", "item_response", one)
    st, _ = call("GET", f"{PREFIX}/items/does-not-exist")
    r.add("GET /items/{missing} status 404", st == 404, str(st))

    st, sc = call("GET", f"{PREFIX}/scopes")
    r.shape("scopes", "scopes_response", sc)

    # --- inspect (the inspectability contract) -------------------------------
    st, ins = call("POST", f"{PREFIX}/inspect",
                   {"query": "what did we decide about MCP auth", "max_tokens": 100})
    r.add("POST /inspect status 200", st == 200, str(st))
    if r.shape("inspect", "inspect_response", ins):
        routing, pack = ins["routing"], ins["pack"]
        sel, unsel = set(routing["selected_experts"]), set(routing["unselected_experts"])
        r.add("inspect: selected experts non-empty", bool(sel))
        r.add("inspect: selected ∩ unselected == ∅", not (sel & unsel))
        r.add("inspect: every score has a known expert",
              set(routing["selected_experts"]) | set(routing["unselected_experts"])
              >= set(routing["scores"]))
        r.add("inspect: pack within token budget", pack["tokens"] <= 100,
              str(pack["tokens"]))
        r.add("inspect: kept items carry a score breakdown",
              all(set(p.get("breakdown", {})) ==
                  {"relevance", "importance", "recency", "redundancy"}
                  for p in pack["items"]))

    # --- pack ----------------------------------------------------------------
    st, pk = call("POST", f"{PREFIX}/pack", {"query": "MCP auth decision", "max_tokens": 80})
    if r.shape("pack", "pack_response", pk):
        r.add("pack: prompt is prompt-ready", pk["prompt"].startswith("Relevant context:"))
        r.add("pack: within token budget", pk["tokens"] <= 80, str(pk["tokens"]))

    # --- router/explain ------------------------------------------------------
    st, re_ = call("POST", f"{PREFIX}/router/explain", {"query": "policy on secrets"})
    if r.shape("router_explain", "router_explain_response", re_):
        scores = [s["score"] for s in re_["scores"]]
        r.add("router/explain: scores ranked descending", scores == sorted(scores, reverse=True))

    # --- pinned experts are always injectable --------------------------------
    st, pinned = call("POST", f"{PREFIX}/inspect",
                      {"query": "an unrelated query", "pin_experts": ["profile"],
                       "max_tokens": 200})
    r.add("inspect: pin_experts honoured",
          "profile" in pinned.get("routing", {}).get("selected_experts", []))

    # --- forget --------------------------------------------------------------
    st, fg = call("POST", f"{PREFIX}/forget", {"id": item_id})
    if r.shape("forget", "forget_response", fg):
        r.add("forget: deleted existing == true", fg["deleted"] is True)
    st, fg2 = call("POST", f"{PREFIX}/forget", {"id": item_id})
    r.add("forget: deleting missing == false", fg2.get("deleted") is False)

    # --- error contract ------------------------------------------------------
    st, err = call("GET", f"{PREFIX}/nope")
    r.add("unknown route status 404", st == 404, str(st))
    r.shape("error(404)", "error", err)
    st, err = call("POST", f"{PREFIX}/inspect", {})
    r.add("missing required field status 400", st == 400, str(st))
    r.shape("error(400)", "error", err)
    st, _ = call("GET", f"{PREFIX}/remember")
    r.add("method not allowed status 405", st == 405, str(st))

    return r


# --------------------------------------------------------------------------- #
# Clients
# --------------------------------------------------------------------------- #
def in_process_client() -> Call:
    """Reference client: the in-process Matrix Context REST service."""
    from matrix_context import ContextManager
    from matrix_context.serve.rest.app import RestService, dispatch

    service = RestService(ContextManager.create("conformance", path=":memory:"))

    def call(method, path, body=None, query=None):
        return dispatch(service, method, path, body=body, query=query)

    return call


def http_client(base_url: str) -> Call:  # pragma: no cover - network
    """Client for a running server (requires httpx)."""
    import httpx

    base = base_url.rstrip("/")

    def call(method, path, body=None, query=None):
        params = {k: v[0] for k, v in (query or {}).items()}
        resp = httpx.request(method, base + path, json=body, params=params, timeout=10)
        try:
            return resp.status_code, resp.json()
        except ValueError:
            return resp.status_code, {}

    return call


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="MoC Contract v1 conformance suite")
    p.add_argument("--url", default="", help="target server base URL (default: in-process)")
    args = p.parse_args(argv)

    call = http_client(args.url) if args.url else in_process_client()
    report = run(call)
    target = args.url or "in-process matrix-context"
    print(f"MoC Contract v{CONTRACT_VERSION} conformance — target: {target}\n")
    for name, ok, detail in report.checks:
        mark = "PASS" if ok else "FAIL"
        line = f"  [{mark}] {name}"
        if detail and not ok:
            line += f"  -> {detail}"
        print(line)
    print(f"\n{report.passed} passed, {report.failed} failed")
    if report.ok:
        print("RESULT: MoC API v1 Compatible ✓")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
