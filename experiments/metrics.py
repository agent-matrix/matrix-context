"""Retrieval + answer-quality metrics for the bake-off."""
from __future__ import annotations
from typing import List, Set


def recall(pack_ids: Set[str], gold: Set[str]) -> float:
    return 1.0 if not gold else len(pack_ids & gold) / len(gold)


def distractors(pack_n: int, pack_ids: Set[str], gold: Set[str]) -> int:
    return pack_n - len(pack_ids & gold)


def keyword_correct(answer: str, gold_answer: str) -> bool:
    """Cheap offline judge: majority of gold content-words present in answer."""
    a = answer.lower()
    words = [w for w in gold_answer.lower().split() if len(w) > 3]
    if not words:
        return False
    hit = sum(1 for w in words if w in a)
    return hit / len(words) >= 0.5
