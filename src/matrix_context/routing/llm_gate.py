"""LLM classifier for the ambiguous-routing fallback.  [v1 — stub]

Invoked only when the centroid gate is not confident/decisive (~5-15% of
queries). Returns the chosen experts plus a rationale string for inspect().
"""
from __future__ import annotations
from typing import List


def classify(query: str, candidate_experts: List[str]) -> List[str]:  # pragma: no cover - [v1]
    raise NotImplementedError("LLM gate is a v1 component.")
