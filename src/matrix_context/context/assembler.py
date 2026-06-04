"""Budgeted context-pack assembler — where the real value is.

score(item) = wR*relevance + wI*importance + wT*recency_decay - wD*redundancy(MMR)
solved greedily under a token budget. The redundancy term dedups near-identical
memories at read time without a separate pass.
"""
from __future__ import annotations
import time
from typing import Dict, List, Optional

import numpy as np

from ..embedding.base import cosine
from ..lifecycle.decay import recency_decay
from ..schema.item import ContextItem
from ..schema.pack import ContextPack, PackedItem


def assemble_pack(candidate_scores: Dict[str, float],
                  items_by_id: Dict[str, ContextItem],
                  selected_experts: List[str], routing_reason: str,
                  max_tokens: int = 600,
                  wR: float = 1.0, wI: float = 0.4, wT: float = 0.3, wD: float = 0.6,
                  now: Optional[float] = None) -> ContextPack:
    now = now if now is not None else time.time()
    mx = max(candidate_scores.values()) if candidate_scores else 1.0
    mx = mx or 1.0
    pool = [items_by_id[i] for i in candidate_scores]
    pack = ContextPack(selected_experts=selected_experts, routing_reason=routing_reason)
    chosen: List[np.ndarray] = []

    while pool:
        best: Optional[ContextItem] = None
        best_s: float = -1e9
        best_bd: Dict[str, float] = {}
        for it in pool:
            rel = candidate_scores[it.id] / mx
            rec = recency_decay(it, now)
            red = (max((cosine(it.embedding, e) for e in chosen), default=0.0)
                   if it.embedding is not None else 0.0)
            s = wR * rel + wI * it.importance + wT * rec - wD * red
            if s > best_s:
                best, best_s, best_bd = it, s, {
                    "relevance": round(wR * rel, 3),
                    "importance": round(wI * it.importance, 3),
                    "recency": round(wT * rec, 3),
                    "redundancy": round(-wD * red, 3)}
        assert best is not None  # pool is non-empty, so a best is always chosen
        pool.remove(best)
        if pack.tokens + best.approx_tokens() > max_tokens:
            pack.dropped.append({"id": best.id, "expert": best.expert,
                                 "reason": "exceeds token budget"})
            continue
        pack.items.append(PackedItem(best, round(best_s, 3), best_bd))
        pack.tokens += best.approx_tokens()
        if best.embedding is not None:
            chosen.append(best.embedding)
    return pack
