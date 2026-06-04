"""Optional cross-encoder reranker.  [v1 — stub]

Off by default to preserve the local-first promise. When enabled, reranks the
fused top-N before pack assembly.
"""
from __future__ import annotations
from typing import Dict, List

from ..schema.item import ContextItem


def rerank(query: str, items: List[ContextItem],
           scores: Dict[str, float]) -> Dict[str, float]:  # pragma: no cover - [v1]
    raise NotImplementedError("Cross-encoder reranking is a v1 component.")
