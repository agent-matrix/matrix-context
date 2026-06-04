"""Dense (vector) retrieval."""
from __future__ import annotations
from typing import List, Tuple

import numpy as np

from ..embedding.base import cosine
from ..schema.item import ContextItem


def dense_rank(query_emb: np.ndarray,
               items: List[ContextItem]) -> List[Tuple[str, float]]:
    scored = [(it.id, cosine(query_emb, it.embedding)) for it in items
              if it.embedding is not None]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
