"""Retrieval, context-efficiency, and routing metrics for the benchmark.

Each runner returns, per query, a :class:`RunResult`: the full ranked candidate
list (best first), the kept pack ids, the pack token count, the selected experts
(for routed methods), and latency. :func:`aggregate` turns a list of those plus
the gold labels into the reported metric table.

Relevance convention: ``relevant = gold ∪ acceptable``. ``distractors`` are kept
items that are not relevant; ``hard_distractors`` are kept items in the query's
labeled hard-negative set — the cases the benchmark is specifically about.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set


@dataclass
class RunResult:
    query_id: str
    ranked_ids: List[str]                      # full ranked candidate list, best first
    kept_ids: List[str] = field(default_factory=list)   # items in the assembled pack
    tokens: int = 0
    selected_experts: Optional[List[str]] = None
    latency_ms: float = 0.0


# ---- ranking metrics (on the ranked candidate list) ----------------------- #
def recall_at_k(ranked: Sequence[str], relevant: Set[str], k: int) -> float:
    if not relevant:
        return 1.0
    return len(set(ranked[:k]) & relevant) / len(relevant)


def precision_at_k(ranked: Sequence[str], relevant: Set[str], k: int) -> float:
    topk = ranked[:k]
    if not topk:
        return 0.0
    return len(set(topk) & relevant) / len(topk)


def reciprocal_rank(ranked: Sequence[str], relevant: Set[str]) -> float:
    for i, item_id in enumerate(ranked):
        if item_id in relevant:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(ranked: Sequence[str], relevant: Set[str], k: int) -> float:
    dcg = sum((1.0 / math.log2(i + 2)) for i, item_id in enumerate(ranked[:k])
              if item_id in relevant)
    ideal_n = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_n))
    return dcg / idcg if idcg > 0 else 0.0


# ---- aggregate ------------------------------------------------------------ #
def aggregate(results: List[RunResult], gold_by_qid: Dict[str, dict],
              expected_by_qid: Dict[str, List[str]], k: int = 8) -> Dict[str, float]:
    """Mean metrics over all queries. ``gold_by_qid[qid]`` carries the relevance
    sets; ``expected_by_qid[qid]`` the expected experts for routing accuracy."""
    n = len(results) or 1
    agg = {m: 0.0 for m in (
        "recall_at_k", "precision_at_k", "mrr", "ndcg_at_k",
        "distractors", "hard_distractors", "dropped_relevant",
        "tokens", "useful_context_ratio", "latency_ms")}
    routed = 0
    routing_hits = 0

    for r in results:
        g = gold_by_qid[r.query_id]
        relevant = set(g["gold_context_ids"]) | set(g.get("acceptable_context_ids", []))
        hard = set(g.get("distractor_context_ids", []))

        agg["recall_at_k"] += recall_at_k(r.ranked_ids, relevant, k)
        agg["precision_at_k"] += precision_at_k(r.ranked_ids, relevant, k)
        agg["mrr"] += reciprocal_rank(r.ranked_ids, relevant)
        agg["ndcg_at_k"] += ndcg_at_k(r.ranked_ids, relevant, k)

        kept = set(r.kept_ids)
        kept_relevant = kept & relevant
        agg["distractors"] += len(kept) - len(kept_relevant)
        agg["hard_distractors"] += len(kept & hard)
        # relevant items that were available as candidates but dropped by budget
        agg["dropped_relevant"] += len((set(r.ranked_ids) & relevant) - kept)
        agg["tokens"] += r.tokens
        agg["useful_context_ratio"] += (len(kept_relevant) / len(kept)) if kept else 0.0
        agg["latency_ms"] += r.latency_ms

        if r.selected_experts is not None:
            routed += 1
            expected = set(expected_by_qid.get(r.query_id, []))
            if expected and set(r.selected_experts) & expected:
                routing_hits += 1

    out = {
        "recall_at_k": round(agg["recall_at_k"] / n, 4),
        "precision_at_k": round(agg["precision_at_k"] / n, 4),
        "mrr": round(agg["mrr"] / n, 4),
        "ndcg_at_k": round(agg["ndcg_at_k"] / n, 4),
        "distractors": int(agg["distractors"]),
        "hard_distractors": int(agg["hard_distractors"]),
        "dropped_relevant": int(agg["dropped_relevant"]),
        "tokens": int(agg["tokens"]),
        "useful_context_ratio": round(agg["useful_context_ratio"] / n, 4),
        "latency_ms": round(agg["latency_ms"] / n, 3),
        # Context-efficiency: recall earned per 1k tokens spent.
        "context_efficiency": round(
            (agg["recall_at_k"] / n) / ((agg["tokens"] / n / 1000.0) or 1.0), 4),
        "routing_accuracy": round(routing_hits / routed, 4) if routed else None,
    }
    return out
