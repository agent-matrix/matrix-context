"""Basic file ingestion (MVP): plain-text and markdown into document items.

Naive paragraph chunking. Richer chunking/extraction/PII live in chunk.py /
extract.py / the governance layer (v1).
"""
from __future__ import annotations
from pathlib import Path
from typing import List

from ..schema.item import ContextItem


def ingest_file(path: str, scope: str = "/", expert: str = "document",
                max_chars: int = 800) -> List[ContextItem]:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    chunks, buf = [], ""
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if len(buf) + len(para) > max_chars and buf:
            chunks.append(buf.strip()); buf = ""
        buf += para + "\n\n"
    if buf.strip():
        chunks.append(buf.strip())
    src = Path(path).name
    return [ContextItem(content=c, expert=expert, scope=scope, tags=(f"src:{src}",))
            for c in chunks]
