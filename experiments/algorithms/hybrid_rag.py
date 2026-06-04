"""BM25 + dense fused with RRF, packed to budget — no routing, no MMR scoring.
Isolates the value of routing+packing when compared against moc_rag."""
from __future__ import annotations
from matrix_context.retrieval.lexical import bm25_rank
from matrix_context.retrieval.dense import dense_rank
from matrix_context.retrieval.fusion import rrf
from .base import Algorithm, Context


class HybridRAG(Algorithm):
    name = "hybrid_rag"

    def prepare(self, items):
        super().prepare(items)
        for it in items:
            if it.embedding is None:
                it.embedding = self.embedder.encode(it.content)

    def build_context(self, query, max_tokens) -> Context:
        q = self.embedder.encode(query)
        fused = rrf([bm25_rank(query, self.items), dense_rank(q, self.items)])
        ranked = [i for i, _ in sorted(fused.items(), key=lambda x: -x[1])]
        return self._pack_by_rank(ranked, self.by_id, max_tokens)
