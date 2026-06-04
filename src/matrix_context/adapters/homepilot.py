"""HomePilot adapter (MVP) — the first consumer.

Turns HomePilot's local memory into Matrix Context items so the synthetic eval
becomes live gold signal. Maps profile fields -> profile expert, persona
memories -> semantic/episodic, device/persona state -> (live_state, v1).
"""
from __future__ import annotations
from typing import Dict, Iterable

from ..manager import ContextManager


class HomePilotAdapter:
    def __init__(self, ctx: ContextManager, scope: str = "/homepilot"):
        self.ctx, self.scope = ctx, scope

    def load_profile(self, profile: Dict[str, str]) -> int:
        n = 0
        for key, value in profile.items():
            self.ctx.remember(f"{key}: {value}", expert="profile",
                              scope=f"{self.scope}/profile", importance=0.9)
            n += 1
        return n

    def load_memories(self, memories: Iterable[str], expert: str = "semantic") -> int:
        n = 0
        for m in memories:
            self.ctx.remember(m, expert=expert, scope=f"{self.scope}/memory")
            n += 1
        return n
