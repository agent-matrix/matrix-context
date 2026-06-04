"""ContextManager — the small public facade that wires the whole engine.

    ctx = ContextManager.create("my-agent")
    ctx.remember("The user prefers local-first tools", expert="profile", importance=0.9)
    pack = ctx.build_pack("How should I design this agent?", max_tokens=400)
    print(pack.to_prompt())
    print(ctx.inspect("How should I design this agent?"))
"""
from __future__ import annotations
from typing import Optional

from .config import Config
from .context.assembler import assemble_pack
from .embedding.base import Embedder
from .embedding.hashing import HashingEmbedder
from .retrieval.fusion import hybrid_retrieve
from .routing.router import ContextRouter
from .schema.item import ContextItem
from .schema.pack import ContextPack
from .schema.query import RecallQuery
from .store.sqlite import SqliteStore


def _make_embedder(name: str) -> Embedder:
    if name in ("hashing", "", None):
        return HashingEmbedder()
    if name in ("sentence-transformers", "st"):
        from .embedding.sentence_transformers import SentenceTransformerEmbedder
        return SentenceTransformerEmbedder()
    raise ValueError(f"unknown embedder: {name}")


class ContextManager:
    def __init__(self, store: SqliteStore, router: ContextRouter, embedder: Embedder,
                 config: Optional[Config] = None):
        self.store, self.router, self.embedder = store, router, embedder
        self.config = config or Config()

    @classmethod
    def create(cls, name: str = "default", path: Optional[str] = None,
               embedder: Optional[Embedder] = None) -> "ContextManager":
        embedder = embedder or HashingEmbedder()
        store = SqliteStore(path or f"{name}.matrix-context.db", embedder)
        return cls(store, ContextRouter(embedder), embedder, Config(name=name))

    @classmethod
    def from_env(cls) -> "ContextManager":
        cfg = Config.from_env()
        emb = _make_embedder(cfg.embedder)
        store = SqliteStore(cfg.path or f"{cfg.name}.matrix-context.db", emb)
        return cls(store, ContextRouter(emb), emb, cfg)

    def remember(self, content: str, expert: str = "semantic", scope: str = "/",
                 importance: float = 0.5, tags=(), ttl: Optional[float] = None) -> ContextItem:
        return self.store.add(ContextItem(content=content, expert=expert, scope=scope,
                                          importance=importance, tags=tuple(tags), ttl=ttl))

    # Default expert fan-out. The bake-off (embedder=sentence-transformers,
    # store=memory) measured moc_rag winning at top_experts=2 — fewer distractors
    # and tokens at equal recall — so 2 is the promoted engine default.
    DEFAULT_TOP_EXPERTS = 2

    def _route_and_score(self, query: str, scope: str, top_experts: int,
                         pin_experts: tuple = ()):
        decision = self.router.route(query, self.store.all_items(), top_experts)
        # Pinned experts are always injectable (e.g. profile), regardless of the
        # routing decision — appended without disturbing the ranked order.
        selected = list(decision.selected)
        for e in pin_experts:
            if e not in selected:
                selected.append(e)
        decision.selected = selected
        cands = self.store.candidates(selected, scope)
        by_id = {it.id: it for it in cands}
        scores = hybrid_retrieve(query, self.embedder.encode(query), cands) if cands else {}
        return decision, scores, by_id

    def build_pack(self, query: str, scope: str = "/", top_experts: int = DEFAULT_TOP_EXPERTS,
                   max_tokens: int = 600, pin_experts: tuple = ()) -> ContextPack:
        decision, scores, by_id = self._route_and_score(query, scope, top_experts,
                                                        pin_experts)
        return assemble_pack(scores, by_id, decision.selected, decision.reason,
                             max_tokens=max_tokens)

    def recall(self, query: RecallQuery) -> ContextPack:
        return self.build_pack(query.text, scope=query.scopes[0],
                               top_experts=query.top_experts, max_tokens=query.max_tokens)

    def inspect(self, query: str, scope: str = "/", top_experts: int = DEFAULT_TOP_EXPERTS,
                max_tokens: int = 600, pin_experts: tuple = ()) -> str:
        decision, scores, by_id = self._route_and_score(query, scope, top_experts,
                                                        pin_experts)
        pack = assemble_pack(scores, by_id, decision.selected, decision.reason,
                             max_tokens=max_tokens)
        lines = [f"ROUTING: {decision.reason}",
                 "  scores: " + ", ".join(f"{e}={s:.3f}" for e, s in
                 sorted(decision.scores.items(), key=lambda x: -x[1])),
                 f"  selected experts: {decision.selected}",
                 f"PACK ({pack.tokens} tokens, {len(pack.items)} items):"]
        for p in pack.items:
            lines.append(f"  [{p.item.expert}] score={p.final_score} {p.breakdown} "
                         f":: {p.item.content[:60]}")
        for d in pack.dropped:
            lines.append(f"  DROPPED [{d['expert']}] {d['reason']}")
        return "\n".join(lines)
