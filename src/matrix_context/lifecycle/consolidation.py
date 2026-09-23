"""Consolidate stale low-importance episodes into procedural memory.

The default reducer is deterministic and loss-preserving: it never deletes source
items. Callers may supply a summarizer later, but consolidation itself remains
auditable.
"""
from __future__ import annotations

import time
from typing import Callable, Iterable, List

from ..schema.item import ContextItem


def consolidate(items: Iterable[ContextItem], *, scope: str = "/",
                older_than_s: float = 7 * 86400, max_importance: float = 0.55,
                summarizer: Callable[[List[str]], str] | None = None) -> ContextItem | None:
    now = time.time()
    eligible = [
        i for i in items
        if i.scope == scope and i.expert == "episodic"
        and (now - i.created_at) >= older_than_s
        and i.importance <= max_importance and i.is_live(now)
        and "superseded" not in i.tags
    ]
    if len(eligible) < 2:
        return None
    texts = [i.content for i in sorted(eligible, key=lambda x: x.created_at)]
    content = summarizer(texts) if summarizer else "Reusable lesson from prior episodes:\n- " + "\n- ".join(texts)
    return ContextItem(
        content=content,
        expert="procedural",
        scope=scope,
        importance=max(i.importance for i in eligible),
        tags=("consolidated",) + tuple(f"source:{i.id}" for i in eligible),
    )
