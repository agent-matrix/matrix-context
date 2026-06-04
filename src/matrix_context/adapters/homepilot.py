"""HomePilot adapter (MVP) — the first real consumer.

HomePilot keeps two distinctions that already work, and this adapter preserves
both rather than replacing HomePilot's memory:

* **Profile vs. learned memory.** Profile fields (persona identity, preferences,
  device facts) map to the ``profile`` expert and are *always injectable* — they
  ride along regardless of the routing decision. Persona memories map to the
  ``semantic`` / ``episodic`` experts and are recalled by routing.

* **Two engines.** ``Mode.BASIC`` is deterministic: a TTL on each memory and a
  per-scope cap (newest-wins). ``Mode.ADAPTIVE`` leans on the engine's recency
  decay and importance weighting (the assembler already scores both);
  consolidation is deferred to the v1 lifecycle module.

Compact-injection discipline is respected: :meth:`build_pack` defaults to a low
hundreds-of-tokens budget. Device / persona live state is exposed through a
``live_state`` expert seam that activates when the live-state expert lands in v1.

The framing is that HomePilot treats Matrix Context as an externalized,
inspectable context plane it can hand off to other agents or reach over MCP —
not a black box that replaces what already works. Every selection is explainable
via :meth:`explain` (``inspect()``).
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Iterable, List

from ..manager import ContextManager
from ..schema.pack import ContextPack

# Profile is always injectable; live_state is the v1 seam for device/persona state.
PINNED_EXPERTS = ("profile",)
LIVE_STATE_EXPERT = "live_state"  # [v1] activates when the live-state expert lands

# Profile-shaped persona fields are identity, not learned memory.
PROFILE_FIELDS = ("id", "label", "category", "psychology_approach",
                  "name", "timezone", "location", "language")


class Mode(str, Enum):
    BASIC = "basic"        # deterministic: TTL + per-scope cap
    ADAPTIVE = "adaptive"  # recency decay + importance weighting


class HomePilotAdapter:
    def __init__(self, ctx: ContextManager, scope: str = "/homepilot",
                 mode: Mode = Mode.ADAPTIVE,
                 basic_ttl_seconds: float = 7 * 86400.0,
                 basic_cap: int = 200):
        self.ctx = ctx
        self.scope = scope
        self.mode = Mode(mode)
        self.basic_ttl_seconds = basic_ttl_seconds
        self.basic_cap = basic_cap

    # ----------------------------------------------------------------- scopes
    def _scope(self, kind: str) -> str:
        return f"{self.scope}/{kind}"

    # -------------------------------------------------------------- profile in
    def load_profile(self, profile: Dict[str, str]) -> int:
        """Map profile fields -> profile expert (always-injectable identity)."""
        n = 0
        for key, value in profile.items():
            if value is None:
                continue
            self.ctx.remember(f"{key}: {value}", expert="profile",
                              scope=self._scope("profile"), importance=0.9)
            n += 1
        return n

    def load_persona(self, persona: Dict) -> Dict[str, int]:
        """Split a HomePilot persona definition into profile + learned memory.

        Profile-shaped fields become always-injectable profile facts; the rest
        of the persona's descriptive text (system prompt, techniques, behaviors)
        becomes semantic memory recalled by routing.
        """
        prof = {k: persona[k] for k in PROFILE_FIELDS if persona.get(k)}
        counts = {"profile": self.load_profile(prof), "memory": 0}

        memories: List[str] = []
        if persona.get("system_prompt"):
            memories.append(f"persona style: {persona['system_prompt']}")
        for k in ("key_techniques", "unique_behaviors", "affirmations"):
            for v in persona.get(k, []) or []:
                memories.append(f"{k[:-1] if k.endswith('s') else k}: {v}")
        counts["memory"] = self.load_memories(memories, expert="semantic")
        return counts

    # --------------------------------------------------------------- memory in
    def load_memories(self, memories: Iterable[str], expert: str = "semantic",
                      importance: float = 0.5) -> int:
        """Map persona memories -> semantic/episodic experts (routed at recall)."""
        ttl = self.basic_ttl_seconds if self.mode is Mode.BASIC else None
        n = 0
        for m in memories:
            self.ctx.remember(m, expert=expert, scope=self._scope("memory"),
                              importance=importance, ttl=ttl)
            n += 1
        if self.mode is Mode.BASIC:
            self._enforce_cap(self._scope("memory"))
        return n

    def remember_turn(self, text: str, expert: str = "episodic",
                      importance: float = 0.5) -> None:
        """Record one conversational turn (Basic applies TTL + cap)."""
        ttl = self.basic_ttl_seconds if self.mode is Mode.BASIC else None
        self.ctx.remember(text, expert=expert, scope=self._scope("memory"),
                          importance=importance, ttl=ttl)
        if self.mode is Mode.BASIC:
            self._enforce_cap(self._scope("memory"))

    def _enforce_cap(self, scope: str) -> None:
        """Basic-engine cap: keep only the newest ``basic_cap`` items in scope."""
        items = [it for it in self.ctx.store.all_items()
                 if it.scope == scope]
        if len(items) <= self.basic_cap:
            return
        items.sort(key=lambda it: it.created_at, reverse=True)
        for it in items[self.basic_cap:]:
            self.ctx.store.delete(it.id)

    # ------------------------------------------------------------------ recall
    def build_pack(self, query: str, max_tokens: int = 220,
                   top_experts: int = 2) -> ContextPack:
        """Compact, profile-pinned context pack for one turn.

        Profile is always injectable; learned memory is recalled by routing. The
        default budget keeps per-turn injection in the low hundreds of tokens.
        """
        return self.ctx.build_pack(query, scope=self.scope, top_experts=top_experts,
                                   max_tokens=max_tokens, pin_experts=PINNED_EXPERTS)

    def explain(self, query: str, max_tokens: int = 220,
                top_experts: int = 2) -> str:
        """Inspect why each item was selected (externalized & inspectable)."""
        return self.ctx.inspect(query, scope=self.scope, top_experts=top_experts,
                                max_tokens=max_tokens, pin_experts=PINNED_EXPERTS)

    # ------------------------------------------------------- live state (v1 seam)
    def load_live_state(self, state: Dict[str, str]) -> int:
        """Device / persona live state -> live_state expert (always injectable).

        The live-state expert is a v1 component; until then these are stored and
        pinned like profile so device facts ride along with each pack.
        """
        n = 0
        for key, value in state.items():
            if value is None:
                continue
            self.ctx.remember(f"{key}: {value}", expert=LIVE_STATE_EXPERT,
                              scope=self._scope("state"), importance=0.8)
            n += 1
        return n
