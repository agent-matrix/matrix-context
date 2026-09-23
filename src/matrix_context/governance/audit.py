"""Append-only, hash-chained audit events for memory lifecycle operations."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    action: str
    actor_id: str
    scope: str
    item_id: Optional[str]
    timestamp: float
    previous_hash: Optional[str]
    payload_hash: str
    event_hash: str


def make_event(action: str, actor_id: str, scope: str, payload: Dict[str, Any],
               *, item_id: str | None = None, previous_hash: str | None = None) -> AuditEvent:
    ts = time.time()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    payload_hash = hashlib.sha256(canonical.encode()).hexdigest()
    seed = f"{action}|{actor_id}|{scope}|{item_id}|{ts}|{previous_hash}|{payload_hash}"
    event_hash = hashlib.sha256(seed.encode()).hexdigest()
    return AuditEvent(
        event_id=event_hash[:20], action=action, actor_id=actor_id, scope=scope,
        item_id=item_id, timestamp=ts, previous_hash=previous_hash,
        payload_hash=payload_hash, event_hash=event_hash,
    )


def audit(*args, **kwargs):
    return asdict(make_event(*args, **kwargs))
