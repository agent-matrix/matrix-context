"""matrix-context CLI entry point."""
from __future__ import annotations
import argparse
import sys

from . import commands


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="matrix-context",
                                description="Local-first context plane for agents.")
    p.add_argument("--db", default="matrix-context.db", help="SQLite path")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="initialize a local store")

    sp = sub.add_parser("remember", help="write a memory item")
    sp.add_argument("content")
    sp.add_argument("--expert", default="semantic")
    sp.add_argument("--scope", default="/")
    sp.add_argument("--importance", type=float, default=0.5)

    sp = sub.add_parser("ingest", help="ingest a text/markdown file")
    sp.add_argument("path"); sp.add_argument("--scope", default="/")

    for name in ("recall", "pack", "inspect"):
        sp = sub.add_parser(name, help=f"{name} context for a query")
        sp.add_argument("query")
        sp.add_argument("--scope", default="/")
        sp.add_argument("--max-tokens", type=int, default=600)
        sp.add_argument("--top-experts", type=int, default=3)

    sp = sub.add_parser("serve", help="run as an MCP server [v1]")
    sp.add_argument("--transport", default="stdio", choices=["stdio", "http"])
    sp.add_argument("--host", default="127.0.0.1"); sp.add_argument("--port", type=int, default=8088)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return commands.dispatch(args)


if __name__ == "__main__":
    sys.exit(main())
