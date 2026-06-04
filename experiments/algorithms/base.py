"""Algorithm contract. Every strategy indexes the same items with the same
embedder, then returns a budgeted context for a query. The differences between
them — routing, fusion, scoring — are exactly what the bake-off measures.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

from matrix_context.schema.item import ContextItem


@dataclass
class Context:
    contents: List[str] = field(default_factory=list)
    tokens: int = 0
    meta: Dict = field(default_factory=dict)

    def text(self) -> str:
        return "\n".join(f"- {c}" for c in self.contents)


class Algorithm:
    name = "base"

    def __init__(self, embedder, store_name: str = "memory"):
        self.embedder = embedder
        self.store_name = store_name
        self.items: List[ContextItem] = []
        self.by_id: Dict[str, ContextItem] = {}

    def prepare(self, items: List[ContextItem]) -> None:
        self.items = items
        self.by_id = {it.id: it for it in items}

    def build_context(self, query: str, max_tokens: int) -> Context:
        raise NotImplementedError

    @staticmethod
    def _pack_by_rank(ranked_ids, by_id, max_tokens) -> Context:
        ctx = Context()
        for item_id in ranked_ids:
            it = by_id[item_id]
            if ctx.tokens + it.approx_tokens() > max_tokens:
                continue
            ctx.contents.append(it.content); ctx.tokens += it.approx_tokens()
        return ctx
