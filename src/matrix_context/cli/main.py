"""``matrix-context`` / ``mc`` CLI entry point.

The CLI is organized around the simplest possible workflow::

    mc init demo
    mc add "We use SQLite as the default backend" --expert semantic
    mc ask "what backend do we use?"
    mc inspect "what backend do we use?"

Beginner commands (init, add, ask, inspect, list, forget, serve, ui, doctor)
sit at the top level; the original verbs (remember, ingest, recall, pack) and
the advanced tooling (benchmark, contract, eval, adapters) remain available.
Both ``matrix-context`` and the short ``mc`` invoke this same parser.
"""
from __future__ import annotations

import argparse
import sys

from . import commands


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mc",
        description="Matrix Context — a local-first, inspectable memory plane for agents.",
        epilog="Quickstart:  mc init demo  ->  mc add \"...\"  ->  mc ask \"...\"  ->  mc inspect \"...\"",
    )
    p.add_argument("--db", default=None,
                   help="SQLite path (overrides project discovery / .matrix-context/)")
    sub = p.add_subparsers(dest="cmd", required=True)

    # -- beginner workflow --------------------------------------------------- #
    sp = sub.add_parser("init", help="create a local project (.matrix-context/)")
    sp.add_argument("name", nargs="?", default=None, help="project name")

    sp = sub.add_parser("add", help="remember text, or ingest a file/dir/URL")
    sp.add_argument("text", help="literal text, or a path / http(s) URL to ingest")
    sp.add_argument("--expert", default=None,
                    help="target expert (default: semantic for text, document for files)")
    sp.add_argument("--scope", default=None, help="scope/tenant (default: project scope)")
    sp.add_argument("--importance", type=float, default=0.5)
    sp.add_argument("--tag", action="append", help="tag (repeatable)")

    sp = sub.add_parser("ask", help="build a context pack for a query (prompt-ready)")
    _query_opts(sp)
    sp.add_argument("--prompt", action="store_true",
                    help="print only the prompt-ready pack (default)")
    sp.add_argument("--json", action="store_true", help="print the structured pack as JSON")

    sp = sub.add_parser("inspect", help="explain why memory was selected for a query")
    _query_opts(sp)
    sp.add_argument("--json", action="store_true", help="print the full inspection as JSON")

    sp = sub.add_parser("list", help="list stored memory items")
    sp.add_argument("--expert", default=None)
    sp.add_argument("--scope", default=None)
    sp.add_argument("--tag", default=None)
    sp.add_argument("--limit", type=int, default=50)

    sp = sub.add_parser("forget", help="delete a memory item by id (or id prefix)")
    sp.add_argument("id")
    sp.add_argument("--yes", "-y", action="store_true", help="skip the confirmation prompt")

    sp = sub.add_parser("serve", help="run the REST API (v1) + Console UI, or MCP server")
    _serve_opts(sp)
    sp.add_argument("--ui", action="store_true", help="open the Console UI in a browser")

    sp = sub.add_parser("ui", help="open the Playground (Console UI) in a browser")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8088)

    sub.add_parser("doctor", help="check the install, store, config and server")
    sub.add_parser("experts", help="list the typed context experts")
    sub.add_parser("scopes", help="list scopes present in the store")
    sub.add_parser("version", help="print the package and MoC Contract versions")

    # -- original verbs (kept, backward compatible) -------------------------- #
    sp = sub.add_parser("remember", help="write a memory item (alias of `add` for text)")
    sp.add_argument("content")
    sp.add_argument("--expert", default="semantic")
    sp.add_argument("--scope", default="/")
    sp.add_argument("--importance", type=float, default=0.5)

    sp = sub.add_parser("ingest", help="ingest a text/markdown file")
    sp.add_argument("path")
    sp.add_argument("--scope", default="/")

    for name in ("recall", "pack"):
        sp = sub.add_parser(name, help=f"{name} context for a query")
        _query_opts(sp)

    # -- advanced tooling (delegates to the dev modules) --------------------- #
    sp = sub.add_parser("benchmark", help="MoC-RAG benchmark (build / compare)")
    sp.add_argument("rest", nargs=argparse.REMAINDER)
    sp = sub.add_parser("contract", help="MoC Contract v1 conformance suite")
    sp.add_argument("rest", nargs=argparse.REMAINDER)
    sp = sub.add_parser("eval", help="routing evaluation harness")
    sp.add_argument("rest", nargs=argparse.REMAINDER)
    sub.add_parser("adapters", help="list the built-in agent adapters")

    return p


def _query_opts(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("query")
    sp.add_argument("--scope", default=None)
    sp.add_argument("--max-tokens", type=int, default=600)
    sp.add_argument("--top-experts", type=int, default=2)


def _serve_opts(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--transport", default="rest", choices=["rest", "stdio", "http"])
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8088)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return commands.dispatch(args)


if __name__ == "__main__":
    sys.exit(main())
