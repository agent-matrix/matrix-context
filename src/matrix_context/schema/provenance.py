from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class Provenance:
    source_type: str
    source_id: str
    actor_id: str
    run_id: Optional[str] = None
    evidence_ids: Tuple[str, ...] = ()
    parent_item_ids: Tuple[str, ...] = ()
