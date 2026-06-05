"""Shared helper for the framework tutorials: download a real document from the
internet and ingest it into Matrix Context, then expose a queryable store.

Used by ``langchain_demo.py``, ``langgraph_demo.py`` and ``crewai_demo.py``.
Dependency-free (only ``matrix_context``); the document is cached under ``data/``
so the demos also run offline after the first download.

    python tutorials/integrations/mc_ingest.py      # download + ingest + sample query
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from matrix_context import ContextManager

DATA = Path(__file__).parent / "data"
DOC = DATA / "postgresql.txt"
SCOPE = "doc:postgresql"
_UA = {"User-Agent": "matrix-context-tutorial/0.1 (+https://github.com/agent-matrix/matrix-context)"}
_WIKI = ("https://en.wikipedia.org/w/api.php?action=query&prop=extracts"
         "&explaintext=1&format=json&redirects=1&titles=PostgreSQL")


def download_document(path: Path = DOC, url: str = _WIKI, max_chars: int = 12000) -> str:
    """Download a public document (Wikipedia → PostgreSQL) and cache it locally."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    text = next(iter(data["query"]["pages"].values()))["extract"][:max_chars]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return text


def chunk(text: str, min_len: int = 80, max_chunks: int = 60) -> list[str]:
    """Split into paragraph-sized chunks (simple, dependency-free)."""
    out = []
    for line in text.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) >= min_len:          # keep paragraphs, drop headings/blank lines
            out.append(line)
    return out[:max_chunks]


def build_context(name: str = "frameworks-demo", scope: str = SCOPE) -> ContextManager:
    """Download → chunk → ingest → return a queryable ContextManager."""
    ctx = ContextManager.create(name, path=":memory:")
    for c in chunk(download_document()):
        ctx.remember(c, expert="document", scope=scope, importance=0.6, tags=["postgresql"])
    return ctx


def retrieve(ctx: ContextManager, query: str, max_tokens: int = 400, scope: str = SCOPE) -> str:
    """The one call every framework wraps: routed, budgeted, prompt-ready context."""
    return ctx.build_pack(query, scope=scope, max_tokens=max_tokens).to_prompt()


if __name__ == "__main__":
    ctx = build_context()
    n = len(ctx.store.all_items())
    print(f"Ingested {n} chunks of the PostgreSQL document into Matrix Context.\n")
    for q in ["What is PostgreSQL?", "What license is PostgreSQL released under?",
              "What does ACID mean in PostgreSQL?"]:
        print(f"Q: {q}")
        print(retrieve(ctx, q, max_tokens=180))
        print()
    print("=== inspect (why) ===")
    print(ctx.inspect("What license is PostgreSQL released under?", scope=SCOPE, max_tokens=180))
