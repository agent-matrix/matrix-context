"""CLI command handlers for ``matrix-context`` / ``mc``.

Every handler receives the parsed args plus a resolved :class:`Project` and a
:class:`ContextManager`. The beginner verbs (add, ask, inspect, list, forget)
mirror the beginner SDK (:mod:`matrix_context.simple`) one-to-one.
"""
from __future__ import annotations

import sys
from pathlib import Path

from ..ingest.files import ingest_file
from ..manager import ContextManager
from . import project as _project

_TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".rst", ".text"}


# --------------------------------------------------------------------------- #
# wiring
# --------------------------------------------------------------------------- #
def _resolve(args) -> _project.Project:
    return _project.load(getattr(args, "db", None))


def _manager(proj: _project.Project) -> ContextManager:
    proj.db.parent.mkdir(parents=True, exist_ok=True)
    embedder = None
    if proj.embedder not in ("hashing", "", None):
        from ..manager import _make_embedder
        embedder = _make_embedder(proj.embedder)
    return ContextManager.create(proj.name, path=str(proj.db), embedder=embedder)


def _looks_like_url(s: str) -> bool:
    return s.startswith(("http://", "https://"))


def dispatch(args) -> int:
    # `version` is side-effect free — don't open/create a store for it.
    if args.cmd == "version":
        return cmd_version()

    proj = _resolve(args)

    # Advanced tooling delegates to the dev modules; no manager needed.
    if args.cmd == "benchmark":
        return _passthrough("benchmarks.moc_rag_benchmark.run", "benchmark", args.rest)
    if args.cmd == "contract":
        return _passthrough("moc_contract.conformance", "contract", args.rest)
    if args.cmd == "eval":
        return _passthrough("eval.harness", "eval", args.rest)
    if args.cmd == "adapters":
        return cmd_adapters()

    ctx = _manager(proj)
    handlers = {
        "init": lambda: cmd_init(args, proj),
        "add": lambda: cmd_add(ctx, proj, args),
        "ask": lambda: cmd_ask(ctx, proj, args),
        "inspect": lambda: cmd_inspect(ctx, proj, args),
        "list": lambda: cmd_list(ctx, args),
        "forget": lambda: cmd_forget(ctx, args),
        "serve": lambda: cmd_serve(ctx, args),
        "ui": lambda: cmd_ui(ctx, args),
        "doctor": lambda: cmd_doctor(ctx, proj),
        "experts": lambda: cmd_experts(ctx),
        "scopes": lambda: cmd_scopes(ctx),
        # original verbs
        "remember": lambda: cmd_remember(ctx, args),
        "ingest": lambda: cmd_ingest(ctx, args),
        "recall": lambda: cmd_pack(ctx, proj, args),
        "pack": lambda: cmd_pack(ctx, proj, args),
    }
    handler = handlers.get(args.cmd)
    return handler() if handler else 1


# --------------------------------------------------------------------------- #
# beginner workflow
# --------------------------------------------------------------------------- #
def cmd_init(args, proj: _project.Project) -> int:
    created = _project.init(args.name)
    print(f"Initialized Matrix Context project '{created.name}'")
    print(f"  store:  {created.db}")
    print(f"  config: {created.root / _project.PROJECT_DIR / _project.CONFIG_NAME}")
    print("\nNext:")
    print('  mc add "The team uses Postgres for production."')
    print('  mc ask "What database do we use?"')
    print('  mc inspect "What database do we use?"')
    return 0


def cmd_add(ctx: ContextManager, proj: _project.Project, args) -> int:
    target = args.text
    scope = args.scope or proj.scope
    tags = tuple(args.tag or ())

    if _looks_like_url(target):
        items = _ingest_url(ctx, target, scope, args.expert or "document")
        print(f"Added {len(items)} chunk(s) from {target}")
        return 0

    path = Path(target)
    if path.is_file():
        items = ingest_file(str(path), scope=scope, expert=args.expert or "document")
        for it in items:
            ctx.store.add(it)
        print(f"Added {len(items)} chunk(s) from file {path.name}")
        return 0
    if path.is_dir():
        total = 0
        for f in sorted(path.rglob("*")):
            if f.is_file() and f.suffix.lower() in _TEXT_SUFFIXES:
                items = ingest_file(str(f), scope=scope, expert=args.expert or "document")
                for it in items:
                    ctx.store.add(it)
                total += len(items)
        print(f"Added {total} chunk(s) from directory {path}")
        return 0

    it = ctx.remember(target, expert=args.expert or "semantic", scope=scope,
                      importance=args.importance, tags=tags)
    print(f"Added {it.id} [{it.expert}] scope={it.scope}")
    return 0


def _ingest_url(ctx: ContextManager, url: str, scope: str, expert: str):
    import tempfile
    import urllib.request

    req = urllib.request.Request(
        url, headers={"User-Agent": "matrix-context-cli/0.1 (+https://github.com/agent-matrix/matrix-context)"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (explicit http(s) only)
        data = resp.read().decode("utf-8", errors="ignore")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write(data)
        tmp = fh.name
    items = ingest_file(tmp, scope=scope, expert=expert)
    for it in items:
        it.tags = tuple(t for t in it.tags if not t.startswith("src:")) + (f"src:{url}",)
        ctx.store.add(it)
    return items


def cmd_ask(ctx: ContextManager, proj: _project.Project, args) -> int:
    scope = args.scope or proj.scope
    if getattr(args, "json", False):
        import json
        print(json.dumps(ctx.build_inspection(args.query, scope=scope,
              top_experts=args.top_experts, max_tokens=args.max_tokens), indent=2))
        return 0
    pack = ctx.build_pack(args.query, scope=scope,
                          top_experts=args.top_experts, max_tokens=args.max_tokens)
    print(pack.to_prompt())
    return 0


def cmd_inspect(ctx: ContextManager, proj: _project.Project, args) -> int:
    scope = args.scope or proj.scope
    if getattr(args, "json", False):
        import json
        print(json.dumps(ctx.build_inspection(args.query, scope=scope,
              top_experts=args.top_experts, max_tokens=args.max_tokens), indent=2))
        return 0
    print(ctx.inspect(args.query, scope=scope,
                      top_experts=args.top_experts, max_tokens=args.max_tokens))
    return 0


def cmd_list(ctx: ContextManager, args) -> int:
    items = ctx.items(scope=args.scope, expert=args.expert)
    if args.tag:
        items = [it for it in items if args.tag in it.tags]
    shown = items[: args.limit] if args.limit else items
    if not shown:
        print("(no items)")
        return 0
    for it in shown:
        preview = it.content.replace("\n", " ")[:60]
        print(f"  {it.id:20} {it.expert:9} {it.scope:14} imp={it.importance:.2f}  {preview}")
    extra = f" (showing {len(shown)})" if len(shown) < len(items) else ""
    print(f"\n{len(items)} item(s){extra}")
    return 0


def cmd_forget(ctx: ContextManager, args) -> int:
    matches = [it for it in ctx.store.all_items()
               if it.id == args.id or it.id.startswith(args.id)]
    if not matches:
        print(f"No item matching '{args.id}'")
        return 1
    if len(matches) > 1:
        print(f"'{args.id}' is ambiguous ({len(matches)} matches) — use a longer id")
        return 1
    it = matches[0]
    if not args.yes:
        preview = it.content.replace("\n", " ")[:50]
        ans = input(f"Forget {it.id} [{it.expert}] '{preview}'? [y/N] ").strip().lower()
        if ans not in ("y", "yes"):
            print("Cancelled")
            return 0
    ctx.forget(it.id)
    print(f"Forgot {it.id}")
    return 0


def cmd_serve(ctx: ContextManager, args) -> int:
    if args.transport == "rest":
        from ..serve.rest.app import serve as serve_rest
        if getattr(args, "ui", False):
            _open_browser_soon(f"http://{args.host}:{args.port}/ui")
        serve_rest(host=args.host, port=args.port, manager=ctx)
        return 0
    from ..serve.mcp.server import serve
    serve(transport=args.transport, host=args.host, port=args.port)
    return 0


def cmd_ui(ctx: ContextManager, args) -> int:
    from ..serve.rest.app import serve as serve_rest
    url = f"http://{args.host}:{args.port}/ui"
    print(f"Opening the Matrix Context Playground at {url}")
    print("(Ctrl-C to stop the server)")
    _open_browser_soon(url)
    serve_rest(host=args.host, port=args.port, manager=ctx)
    return 0


def _open_browser_soon(url: str, delay: float = 1.0) -> None:
    import threading
    import webbrowser
    threading.Timer(delay, lambda: webbrowser.open(url)).start()


# --------------------------------------------------------------------------- #
# diagnostics & discovery
# --------------------------------------------------------------------------- #
def cmd_doctor(ctx: ContextManager, proj: _project.Project) -> int:
    from .. import CONTRACT_VERSION, __version__
    rows: list[tuple[str, str, str]] = [
        ("package", "ok", f"matrix-context {__version__}"),
    ]
    try:
        n = len(ctx.store.all_items())
        rows.append(("store", "ok", f"{proj.db} ({n} item(s))"))
    except Exception as e:  # pragma: no cover - defensive
        rows.append(("store", "fail", str(e)))
    if proj.discovered:
        rows.append(("project", "ok", f"{proj.root / _project.PROJECT_DIR}"))
    else:
        rows.append(("project", "warn", "no .matrix-context/ (run `mc init`); using cwd defaults"))
    rows.append(("contract", "ok", f"MoC Contract v{CONTRACT_VERSION}"))
    import importlib.util
    if importlib.util.find_spec("sentence_transformers") is not None:
        rows.append(("embeddings", "ok", "hashing (default); sentence-transformers also available"))
    else:
        rows.append(("embeddings", "ok",
                     "hashing (default, zero-download); pip install 'matrix-context[embeddings]' for ST"))
    try:
        from ..serve.rest.app import serve  # noqa: F401
        rows.append(("server", "ok", "REST /v1 + Console UI importable"))
    except Exception as e:  # pragma: no cover - defensive
        rows.append(("server", "fail", str(e)))

    glyph = {"ok": "✓", "warn": "!", "fail": "✗"}
    for name, status, detail in rows:
        print(f"  {glyph.get(status, '?')} {name:11} {detail}")
    ok = all(s != "fail" for _, s, _ in rows)
    print("\n" + ("All checks passed." if ok else "Some checks FAILED."))
    return 0 if ok else 1


def cmd_experts(ctx: ContextManager) -> int:
    from ..routing.experts import EXPERT_DESCRIPTIONS
    counts: dict[str, int] = {}
    for it in ctx.store.all_items():
        counts[it.expert] = counts.get(it.expert, 0) + 1
    for expert, desc in EXPERT_DESCRIPTIONS.items():
        print(f"  {expert:9} ({counts.get(expert, 0):3})  {desc}")
    return 0


def cmd_scopes(ctx: ContextManager) -> int:
    counts: dict[str, int] = {}
    for it in ctx.store.all_items():
        counts[it.scope] = counts.get(it.scope, 0) + 1
    if not counts:
        print("(no scopes yet)")
        return 0
    for scope in sorted(counts):
        print(f"  {scope:24} {counts[scope]} item(s)")
    return 0


def cmd_version() -> int:
    from .. import CONTRACT_VERSION, __version__
    print(f"matrix-context {__version__}  (MoC Contract v{CONTRACT_VERSION})")
    return 0


# --------------------------------------------------------------------------- #
# original verbs (backward compatible)
# --------------------------------------------------------------------------- #
def cmd_remember(ctx: ContextManager, args) -> int:
    it = ctx.remember(args.content, expert=args.expert, scope=args.scope,
                      importance=args.importance)
    print(f"remembered {it.id} [{it.expert}]")
    return 0


def cmd_ingest(ctx: ContextManager, args) -> int:
    items = ingest_file(args.path, scope=args.scope)
    for it in items:
        ctx.store.add(it)
    print(f"ingested {len(items)} chunks from {args.path}")
    return 0


def cmd_pack(ctx: ContextManager, proj: _project.Project, args) -> int:
    scope = args.scope or proj.scope
    pack = ctx.build_pack(args.query, scope=scope,
                          top_experts=args.top_experts, max_tokens=args.max_tokens)
    print(pack.to_prompt())
    return 0


# --------------------------------------------------------------------------- #
# advanced tooling
# --------------------------------------------------------------------------- #
def _passthrough(module: str, label: str, rest) -> int:
    import importlib.util
    top = module.split(".")[0]
    # `python -m <module>` (the subprocess) adds cwd to sys.path, so a repo-local
    # dev module resolves even when the installed `mc` script's path does not.
    available = (importlib.util.find_spec(top) is not None
                 or (Path.cwd() / top).is_dir())
    if not available:
        print(f"`mc {label}` needs the developer checkout (module '{top}' not found).")
        print("Clone the repo and run from source, or `pip install -e \".[dev]\"`.")
        return 1
    import subprocess
    rest = [a for a in (rest or []) if a != "--"]
    return subprocess.call([sys.executable, "-m", module, *rest])


def cmd_adapters() -> int:
    import pkgutil
    from .. import adapters as adapters_pkg
    print("Built-in agent adapters (matrix_context.adapters):")
    for mod in pkgutil.iter_modules(adapters_pkg.__path__):
        print(f"  - {mod.name}")
    print("\nExample:  from matrix_context.adapters.langgraph import ...")
    return 0
