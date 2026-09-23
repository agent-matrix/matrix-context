"""Supersession primitives: retain history, mark validity changes."""
from __future__ import annotations

from ..schema.item import ContextItem


def supersede_item(store, old: ContextItem, new: ContextItem) -> ContextItem:
    if old.scope != new.scope:
        raise ValueError("supersession must remain inside the same scope")
    old_tags = tuple(t for t in old.tags if t != "active") + ("superseded", f"superseded-by:{new.id}")
    old.tags = old_tags
    store.add(old)

    new.tags = tuple(new.tags) + (f"supersedes:{old.id}", "active")
    store.add(new)
    return new


def supersede(store, old_id: str, new: ContextItem) -> ContextItem:
    old = store.get(old_id)
    if old is None:
        raise ValueError(f"unknown item: {old_id}")
    return supersede_item(store, old, new)
