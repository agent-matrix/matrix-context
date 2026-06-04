"""Two-tier context router — the centerpiece (cf. MODE / ExpertRAG / MixRAG).

Tier 1: fast centroid gate. Each expert has a running centroid of its items'
embeddings blended with a description embedding; score = cosine(query, centroid).
Tier 2: ambiguity fallback. On low confidence or an indecisive margin, WIDEN
selection rather than guess. This is the exact seam where a v1 LLM classifier
plugs in (see llm_gate.py). Every decision is returned with scores + reason so
`inspect()` can explain why an expert fired.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from ..embedding.base import Embedder, cosine
from ..schema.item import ContextItem
from .experts import EXPERT_DESCRIPTIONS


@dataclass
class RoutingDecision:
    selected: List[str]
    scores: Dict[str, float]
    widened: bool
    reason: str


class ContextRouter:
    def __init__(self, embedder: Embedder,
                 confident: float = 0.18, decisive_gap: float = 0.05):
        self.embedder = embedder
        self.confident = confident
        self.decisive_gap = decisive_gap
        self._desc = {e: embedder.encode(d) for e, d in EXPERT_DESCRIPTIONS.items()}

    def _centroid(self, expert: str, items: List[ContextItem]) -> Optional[np.ndarray]:
        embs = [it.embedding for it in items
                if it.expert == expert and it.embedding is not None]
        base = self._desc.get(expert)
        if not embs:
            return base
        c = np.mean(embs, axis=0)
        if base is not None:
            c = 0.7 * c + 0.3 * base
        n = np.linalg.norm(c)
        return c / n if n > 0 else c

    def route(self, query: str, items: List[ContextItem],
              top_experts: int = 3) -> RoutingDecision:
        q = self.embedder.encode(query)
        experts = sorted(set(list(EXPERT_DESCRIPTIONS) + [it.expert for it in items]))
        scores = {e: (cosine(q, c) if (c := self._centroid(e, items)) is not None else 0.0)
                  for e in experts}
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top = ranked[:top_experts]
        top_score = top[0][1] if top else 0.0
        gap = (top[0][1] - top[1][1]) if len(top) > 1 else 1.0

        if top_score < self.confident or gap < self.decisive_gap:
            widened = ranked[:top_experts + 2]
            return RoutingDecision(
                selected=[e for e, _ in widened], scores=scores, widened=True,
                reason=(f"ambiguous (top={top_score:.3f} < {self.confident} or "
                        f"gap={gap:.3f} < {self.decisive_gap}); widened — v1 "
                        f"would invoke the LLM gate here"))
        return RoutingDecision(
            selected=[e for e, _ in top], scores=scores, widened=False,
            reason=f"confident: top={top_score:.3f}, gap={gap:.3f}")
