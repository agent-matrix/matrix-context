"""Eval metrics: recall@budget, distractor rate, token cost, routing accuracy."""
from __future__ import annotations
from typing import List, Set


def gold_recall(pack_contents: List[str], gold: Set[str]) -> float:
    if not gold:
        return 1.0
    return len(gold & set(pack_contents)) / len(gold)


def distractor_count(pack_contents: List[str], gold: Set[str]) -> int:
    return len(pack_contents) - len(gold & set(pack_contents))


def routing_hit(selected_experts: List[str], target_expert: str) -> bool:
    return target_expert in selected_experts
