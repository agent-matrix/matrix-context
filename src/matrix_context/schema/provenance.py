from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Provenance:
    source_type: str
    source_id: str
    actor_id: str
    run_id: str | None = None
    evidence_ids: tuple[str, ...] = ()
    parent_item_ids: tuple[str, ...] = ()
