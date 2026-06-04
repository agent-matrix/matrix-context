"""Load the experiment items + queries."""
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Tuple

from matrix_context.schema.item import ContextItem

_DIR = Path(__file__).parent


def _read(name: str) -> List[dict]:
    return [json.loads(l) for l in (_DIR / name).read_text().splitlines() if l.strip()]


def load() -> Tuple[List[ContextItem], List[dict]]:
    items = [ContextItem(id=r["id"], content=r["content"], expert=r["expert"],
                         importance=r["importance"]) for r in _read("items.jsonl")]
    queries = _read("queries.jsonl")
    return items, queries
