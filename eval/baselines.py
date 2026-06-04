"""Baseline: classic flat RAG — one flat index, dense top-k packed to budget."""
from __future__ import annotations
from typing import List, Tuple

from matrix_context.embedding.base import Embedder
from matrix_context.retrieval.dense import dense_rank
from matrix_context.schema.item import ContextItem


def flat_rag(query: str, embedder: Embedder, items: List[ContextItem],
             budget: int) -> Tuple[List[str], int]:
    by_id = {it.id: it for it in items}
    ranked = dense_rank(embedder.encode(query), items)
    picked, tokens = [], 0
    for item_id, _ in ranked:
        it = by_id[item_id]
        if tokens + it.approx_tokens() > budget:
            continue
        picked.append(it.content); tokens += it.approx_tokens()
    return picked, tokens
