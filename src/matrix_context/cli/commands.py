"""CLI command handlers."""
from __future__ import annotations

from ..manager import ContextManager
from ..ingest.files import ingest_file


def _mgr(args) -> ContextManager:
    return ContextManager.create("cli", path=args.db)


def dispatch(args) -> int:
    ctx = _mgr(args)
    if args.cmd == "init":
        print(f"initialized store at {args.db}"); return 0
    if args.cmd == "remember":
        it = ctx.remember(args.content, expert=args.expert, scope=args.scope,
                          importance=args.importance)
        print(f"remembered {it.id} [{it.expert}]"); return 0
    if args.cmd == "ingest":
        items = ingest_file(args.path, scope=args.scope)
        for it in items:
            ctx.store.add(it)
        print(f"ingested {len(items)} chunks from {args.path}"); return 0
    if args.cmd in ("recall", "pack"):
        pack = ctx.build_pack(args.query, scope=args.scope,
                              top_experts=args.top_experts, max_tokens=args.max_tokens)
        print(pack.to_prompt()); return 0
    if args.cmd == "inspect":
        print(ctx.inspect(args.query, scope=args.scope,
                          top_experts=args.top_experts, max_tokens=args.max_tokens)); return 0
    if args.cmd == "serve":
        from ..serve.mcp.server import serve
        serve(transport=args.transport, host=args.host, port=args.port); return 0
    return 1
