"""Reciprocal Rank Fusion of the lexical and dense channels.

RRF is rank-based, so it needs no score calibration between channels — which is
why it is robust when one channel is a stub and the other a real model.
"""
from __future__ import annotations
from typing import Dict, List, Tuple

import numpy as np

from ..schema.item import ContextItem
from .dense import dense_rank
from .lexical import bm25_rank


def rrf(rank_lists: List[List[Tuple[str, float]]], k: int = 60) -> Dict[str, float]:
    fused: Dict[str, float] = {}
    for rl in rank_lists:
        for rank, (item_id, _score) in enumerate(rl):
            fused[item_id] = fused.get(item_id, 0.0) + 1.0 / (k + rank + 1)
    return fused


def hybrid_retrieve(query: str, query_emb: np.ndarray,
                    items: List[ContextItem]) -> Dict[str, float]:
    return rrf([bm25_rank(query, items), dense_rank(query_emb, items)])
