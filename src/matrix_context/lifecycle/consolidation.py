"""Consolidate stale low-importance episodes into procedural memory.

The default reducer is deterministic and loss-preserving: it never deletes source
items. Callers may supply a summarizer later, but consolidation itself remains
auditable.
"""
from __future__ import annotations

import time
from collections.abc import Callable, Iterable

from ..schema.item import ContextItem


def consolidate(
    items: Iterable[ContextItem],
    *,
    scope: str = "/",
    older_than_s: float = 7 * 86400,
    max_importance: float = 0.55,
    summarizer: Callable[[list[str]], str] | None = None,
) -> ContextItem | None:
    now = time.time()
    eligible = [
        item
        for item in items
        if item.scope == scope
        and item.expert == "episodic"
        and (now - item.created_at) >= older_than_s
        and item.importance <= max_importance
        and item.is_live(now)
        and "superseded" not in item.tags
    ]
    if len(eligible) < 2:
        return None

    texts = [item.content for item in sorted(eligible, key=lambda item: item.created_at)]
    content = (
        summarizer(texts)
        if summarizer
        else "Reusable lesson from prior episodes:
- " + "
- ".join(texts)
    )
    return ContextItem(
        content=content,
        expert="procedural",
        scope=scope,
        importance=max(item.importance for item in eligible),
        tags=("consolidated",) + tuple(f"source:{item.id}" for item in eligible),
    )
