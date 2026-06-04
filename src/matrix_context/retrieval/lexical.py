"""BM25 lexical retrieval over the candidate set.

Pure-Python for inspectability and zero deps. FTS5 (SQLite) / Postgres text
search are the production swap-ins behind the same call signature.
"""
from __future__ import annotations
import math
import re
from collections import Counter
from typing import List, Tuple

from ..schema.item import ContextItem

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(s: str) -> List[str]:
    return _TOKEN.findall(s.lower())


def bm25_rank(query: str, items: List[ContextItem],
              k1: float = 1.5, b: float = 0.75) -> List[Tuple[str, float]]:
    docs = [tokenize(it.content) for it in items]
    if not docs:
        return []
    avgdl = sum(len(d) for d in docs) / len(docs)
    df: Counter = Counter()
    for d in docs:
        for term in set(d):
            df[term] += 1
    N = len(docs)
    q_terms = tokenize(query)
    scored = []
    for it, d in zip(items, docs):
        tf = Counter(d)
        score = 0.0
        for term in q_terms:
            if term not in tf:
                continue
            idf = math.log(1 + (N - df[term] + 0.5) / (df[term] + 0.5))
            denom = tf[term] + k1 * (1 - b + b * len(d) / avgdl)
            score += idf * (tf[term] * (k1 + 1)) / denom
        scored.append((it.id, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
