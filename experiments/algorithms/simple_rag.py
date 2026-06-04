"""Flat dense top-k — the classic ChromaDB RAG baseline to beat."""
from __future__ import annotations
from .base import Algorithm, Context
from ..backends.stores import get_store


class SimpleRAG(Algorithm):
    name = "simple_rag"

    def prepare(self, items):
        super().prepare(items)
        self.store = get_store(self.store_name, self.embedder.dim)
        for it in items:
            if it.embedding is None:
                it.embedding = self.embedder.encode(it.content)
            self.store.add(it.id, it.embedding)

    def build_context(self, query, max_tokens) -> Context:
        q = self.embedder.encode(query)
        ranked = [i for i, _ in self.store.query(q, k=len(self.items))]
        ctx = self._pack_by_rank(ranked, self.by_id, max_tokens)
        ctx.meta = {"store": self.store_name}
        return ctx
