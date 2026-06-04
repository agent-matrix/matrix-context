"""Lexical-only BM25 retrieval."""
from __future__ import annotations
from matrix_context.retrieval.lexical import bm25_rank
from .base import Algorithm, Context


class BM25RAG(Algorithm):
    name = "bm25_rag"

    def build_context(self, query, max_tokens) -> Context:
        ranked = [i for i, _ in bm25_rank(query, self.items)]
        return self._pack_by_rank(ranked, self.by_id, max_tokens)
