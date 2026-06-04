"""Benchmark runners: the baselines and MoC-RAG variants.

All methods share one budgeted packer so the comparison isolates *retrieval and
routing quality* rather than packer tricks: each runner returns a ranked
candidate list and the common packer fills the token budget greedily. MoC-RAG's
advantage therefore has to come from routing the *right* typed experts into the
candidate pool — exactly the claim under test.

Registered algorithms (see ``ALGORITHMS``):
    bm25_rag, dense_rag, hybrid_rag, metadata_rag, reranked_rag,
    moc_rag_e1, moc_rag_e2, moc_rag_e3, moc_rag_all
"""
from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from matrix_context.embedding.base import cosine
from matrix_context.retrieval.dense import dense_rank
from matrix_context.retrieval.lexical import bm25_rank, tokenize
from matrix_context.retrieval.fusion import rrf
from matrix_context.schema.item import ContextItem
from matrix_context.utils.tokens import approx_tokens

from .metrics import RunResult
from .schema import ContextRow, QueryRow
from .taxonomy import (EXPERT_DESCRIPTIONS, EXPERTS, KEYWORD_PRIORS, TYPE_TO_EXPERT)

RECENT_PREFIX = "2026"  # created_at recency heuristic


# --------------------------------------------------------------------------- #
# Corpus preparation
# --------------------------------------------------------------------------- #
class Corpus:
    """Items with embeddings + the per-id benchmark metadata runners need."""

    def __init__(self, contexts: List[ContextRow], embedder):
        self.embedder = embedder
        self.meta: Dict[str, ContextRow] = {c.context_id: c for c in contexts}
        self.items: List[ContextItem] = []
        for c in contexts:
            it = ContextItem(id=c.context_id, content=c.content, expert=c.expert,
                             scope=c.scope, importance=c.importance)
            it.embedding = embedder.encode(c.content)
            self.items.append(it)
        self.by_id: Dict[str, ContextItem] = {it.id: it for it in self.items}
        self._by_expert: Dict[str, List[ContextItem]] = {}
        for it in self.items:
            self._by_expert.setdefault(it.expert, []).append(it)
        self._centroids = self._build_centroids()

    def _build_centroids(self) -> Dict[str, np.ndarray]:
        out: Dict[str, np.ndarray] = {}
        for e in EXPERTS:
            desc = self.embedder.encode(EXPERT_DESCRIPTIONS[e])
            embs = [it.embedding for it in self._by_expert.get(e, [])]
            c = np.mean(embs, axis=0) if embs else desc
            c = 0.7 * c + 0.3 * desc if embs else desc
            nrm = np.linalg.norm(c)
            out[e] = c / nrm if nrm > 0 else c
        return out

    def expert_items(self, experts: List[str]) -> List[ContextItem]:
        out: List[ContextItem] = []
        for e in experts:
            out.extend(self._by_expert.get(e, []))
        return out

    def scope_items(self, scope: str) -> List[ContextItem]:
        pref = scope.rstrip("/")
        return [it for it in self.items if it.scope == scope or it.scope.startswith(pref)]


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #
def _minmax(scores: Dict[str, float]) -> Dict[str, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-9:
        return {k: 0.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def _rank_from_scores(scores: Dict[str, float]) -> List[str]:
    return [i for i, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)]


def _hybrid_scores(query: str, q_emb: np.ndarray,
                   items: List[ContextItem]) -> Dict[str, float]:
    return rrf([bm25_rank(query, items), dense_rank(q_emb, items)])


def _rerank_scores(query: str, q_emb: np.ndarray, corpus: Corpus,
                   items: List[ContextItem]) -> Dict[str, float]:
    """Lightweight local reranker (cross-encoder seam): dense + bm25 +
    importance + confidence + recency, each normalized to [0, 1]."""
    dense = _minmax({i: s for i, s in dense_rank(q_emb, items)})
    bm = _minmax({i: s for i, s in bm25_rank(query, items)})
    out: Dict[str, float] = {}
    for it in items:
        m = corpus.meta[it.id]
        recency = 1.0 if m.created_at.startswith(RECENT_PREFIX) else 0.4
        out[it.id] = (0.45 * dense.get(it.id, 0.0) + 0.30 * bm.get(it.id, 0.0)
                      + 0.10 * it.importance + 0.10 * m.confidence + 0.05 * recency)
    return out


def _pack(ranked_ids: List[str], corpus: Corpus, budget: int) -> Tuple[List[str], int]:
    """Common greedy budgeted packer used by every method."""
    kept: List[str] = []
    tokens = 0
    for item_id in ranked_ids:
        t = approx_tokens(corpus.by_id[item_id].content)
        if tokens + t > budget:
            continue
        kept.append(item_id)
        tokens += t
    return kept, tokens


# --------------------------------------------------------------------------- #
# Hybrid router (the heart of MoC-RAG)
# --------------------------------------------------------------------------- #
# query token -> context type (cheap intent classifier for the type prior)
_TYPE_HINTS = {
    "decide": "decision", "decision": "decision", "default": "decision",
    "why": "decision", "prefer": "preference", "tone": "profile",
    "respond": "profile", "where": "code", "implement": "code", "file": "code",
    "policy": "rule", "store": "rule", "allowed": "rule", "result": "tool_result",
    "ran": "tool_result", "session": "episode", "last": "episode",
    "whitepaper": "document", "say": "document", "interfaces": "fact",
}


class MoCRouter:
    """Hybrid expert router:

        score = 0.40*centroid + 0.25*keyword + 0.15*type + 0.10*scope + 0.10*activity

    With a low-confidence/indecisive fallback that WIDENS selection (graceful
    degradation) rather than guessing.
    """

    def __init__(self, corpus: Corpus, confident: float = 0.15, gap: float = 0.03):
        self.corpus = corpus
        self.confident = confident
        self.gap = gap
        total = len(corpus.items) or 1
        self._activity = {e: sum(1 for it in corpus._by_expert.get(e, [])
                                 if corpus.meta[it.id].created_at.startswith(RECENT_PREFIX))
                          / total for e in EXPERTS}
        self._scopes = {e: {it.scope for it in corpus._by_expert.get(e, [])}
                        for e in EXPERTS}

    def score(self, query: QueryRow, q_emb: np.ndarray) -> Dict[str, float]:
        q_tokens = set(tokenize(query.query))
        detected_types = {_TYPE_HINTS[t] for t in q_tokens if t in _TYPE_HINTS}
        type_experts = {TYPE_TO_EXPERT[t] for t in detected_types}
        scores: Dict[str, float] = {}
        for e in EXPERTS:
            centroid = cosine(q_emb, self.corpus._centroids[e])
            kp = KEYWORD_PRIORS.get(e, [])
            keyword = (sum(1 for w in kp if w in query.query.lower()) / len(kp)) if kp else 0.0
            type_prior = 1.0 if e in type_experts else 0.0
            scope_prior = 1.0 if query.scope in self._scopes.get(e, set()) else 0.0
            activity = self._activity.get(e, 0.0)
            scores[e] = (0.40 * max(centroid, 0.0) + 0.25 * keyword
                         + 0.15 * type_prior + 0.10 * scope_prior + 0.10 * activity)
        return scores

    def route(self, query: QueryRow, q_emb: np.ndarray, top_experts) -> Tuple[List[str], Dict[str, float], bool]:
        scores = self.score(query, q_emb)
        ranked = _rank_from_scores(scores)
        if top_experts == "all":
            return ranked, scores, False
        k = int(top_experts)
        top = ranked[:k]
        top_score = scores[top[0]] if top else 0.0
        margin = (scores[ranked[0]] - scores[ranked[1]]) if len(ranked) > 1 else 1.0
        if top_score < self.confident or margin < self.gap:
            return ranked[:k + 2], scores, True   # widen on uncertainty
        return top, scores, False


# --------------------------------------------------------------------------- #
# Runners
# --------------------------------------------------------------------------- #
class Runner:
    name = "base"
    routed = False

    def __init__(self, corpus: Corpus, budget: int = 200):
        self.corpus = corpus
        self.budget = budget

    def run(self, query: QueryRow) -> RunResult:
        t0 = time.perf_counter()
        ranked, selected = self._rank(query)
        kept, tokens = _pack(ranked, self.corpus, self.budget)
        dt = (time.perf_counter() - t0) * 1000
        return RunResult(query_id=query.query_id, ranked_ids=ranked, kept_ids=kept,
                         tokens=tokens, selected_experts=selected, latency_ms=dt)

    def _rank(self, query: QueryRow) -> Tuple[List[str], Optional[List[str]]]:
        raise NotImplementedError


class BM25Runner(Runner):
    name = "bm25_rag"

    def _rank(self, query):
        return [i for i, _ in bm25_rank(query.query, self.corpus.items)], None


class DenseRunner(Runner):
    name = "dense_rag"

    def _rank(self, query):
        q = self.corpus.embedder.encode(query.query)
        return [i for i, _ in dense_rank(q, self.corpus.items)], None


class HybridRunner(Runner):
    name = "hybrid_rag"

    def _rank(self, query):
        q = self.corpus.embedder.encode(query.query)
        return _rank_from_scores(_hybrid_scores(query.query, q, self.corpus.items)), None


class MetadataRunner(Runner):
    """Metadata-filtered hybrid RAG — the key 'isn't this just filtering?'
    baseline. Filters candidates by the query scope, then hybrid-retrieves."""
    name = "metadata_rag"

    def _rank(self, query):
        q = self.corpus.embedder.encode(query.query)
        items = self.corpus.scope_items(query.scope) or self.corpus.items
        return _rank_from_scores(_hybrid_scores(query.query, q, items)), None


class RerankedRunner(Runner):
    """Dense top-N then local rerank (dense+bm25+importance+confidence+recency)."""
    name = "reranked_rag"

    def __init__(self, corpus, budget: int = 200, top_n: int = 40):
        super().__init__(corpus, budget)
        self.top_n = top_n

    def _rank(self, query):
        q = self.corpus.embedder.encode(query.query)
        pool_ids = [i for i, _ in dense_rank(q, self.corpus.items)[:self.top_n]]
        pool = [self.corpus.by_id[i] for i in pool_ids]
        return _rank_from_scores(_rerank_scores(query.query, q, self.corpus, pool)), None


class MoCRunner(Runner):
    """MoC-RAG: hybrid route -> retrieve within selected experts -> rerank."""

    def __init__(self, corpus, budget: int = 200, top_experts="2", rerank: bool = True):
        super().__init__(corpus, budget)
        self.router = MoCRouter(corpus)
        self.top_experts = top_experts
        self.rerank = rerank
        self.name = f"moc_rag_e{top_experts}"
        self.routed = True

    def _rank(self, query):
        q = self.corpus.embedder.encode(query.query)
        selected, _scores, _widened = self.router.route(query, q, self.top_experts)
        items = self.corpus.expert_items(selected)
        if not items:
            items = self.corpus.items
        if self.rerank:
            scored = _rerank_scores(query.query, q, self.corpus, items)
        else:
            scored = _hybrid_scores(query.query, q, items)
        return _rank_from_scores(scored), selected


# Registry: name -> factory(corpus, budget) -> Runner
ALGORITHMS: Dict[str, Callable[..., Runner]] = {
    "bm25_rag": BM25Runner,
    "dense_rag": DenseRunner,
    "hybrid_rag": HybridRunner,
    "metadata_rag": MetadataRunner,
    "reranked_rag": RerankedRunner,
    "moc_rag_e1": lambda c, budget=200: MoCRunner(c, budget, top_experts="1"),
    "moc_rag_e2": lambda c, budget=200: MoCRunner(c, budget, top_experts="2"),
    "moc_rag_e3": lambda c, budget=200: MoCRunner(c, budget, top_experts="3"),
    "moc_rag_all": lambda c, budget=200: MoCRunner(c, budget, top_experts="all"),
}
