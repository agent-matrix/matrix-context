"""Matrix Context: routing -> hybrid retrieval -> budgeted, scored pack."""
from __future__ import annotations
from matrix_context import ContextManager
from .base import Algorithm, Context


class MoCRAG(Algorithm):
    name = "moc_rag"

    def prepare(self, items):
        super().prepare(items)
        self.ctx = ContextManager.create("exp", path=":memory:", embedder=self.embedder)
        for it in items:
            self.ctx.remember(it.content, expert=it.expert, importance=it.importance)

    def build_context(self, query, max_tokens) -> Context:
        pack = self.ctx.build_pack(query, top_experts=2, max_tokens=max_tokens)
        return Context(contents=[p.item.content for p in pack.items],
                       tokens=pack.tokens,
                       meta={"experts": pack.selected_experts})
