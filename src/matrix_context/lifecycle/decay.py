"""Recency decay + TTL — the MVP slice of the dual-engine memory model.

Basic engine: TTL + caps (deterministic). Adaptive engine [v1]: decay +
reinforcement + consolidation. This module provides the shared time math.
"""
from __future__ import annotations
import math
import time
from typing import Optional

from ..schema.item import ContextItem


def recency_decay(item: ContextItem, now: Optional[float] = None,
                  half_life_days: float = 30.0) -> float:
    now = now if now is not None else time.time()
    age_days = (now - item.created_at) / 86400.0
    return math.pow(0.5, age_days / half_life_days)


def is_expired(item: ContextItem, now: Optional[float] = None) -> bool:
    return not item.is_live(now)
