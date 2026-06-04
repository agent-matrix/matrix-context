"""The typed context item — the unit the engine routes, scores and packs.

Lean by design (10 MVP fields). Governance/provenance fields (tenant_id,
sensitivity, approval_state, provenance, embedding_ref ...) arrive in v1 once
the multi-tenant store and approval flow exist.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np

from ..utils.ids import new_id
from ..utils.tokens import approx_tokens


@dataclass
class ContextItem:
    content: str
    expert: str
    scope: str = "/"
    importance: float = 0.5                  # 0..1, author-set (learned in v2)
    tags: Tuple[str, ...] = ()
    id: str = field(default_factory=new_id)
    created_at: float = field(default_factory=time.time)
    ttl: Optional[float] = None              # seconds; None = no expiry
    embedding: Optional[np.ndarray] = None   # filled by the store on write

    def is_live(self, now: Optional[float] = None) -> bool:
        if self.ttl is None:
            return True
        now = now if now is not None else time.time()
        return (now - self.created_at) <= self.ttl

    def approx_tokens(self) -> int:
        return approx_tokens(self.content)
