"""Deterministic keyword rules — the transparent MVP routing prior.

Cheap signals that nudge the router toward obvious partitions. Combined with the
centroid gate in router.py; never the sole decision.
"""
from __future__ import annotations
from typing import List

_RULES = [
    (("policy", "allowed", "approval", "compliance", "rule", "secret"), "policy"),
    (("prefer", "preference", "my name", "i like", "profile"), "profile"),
    (("decided", "decision", "glossary", "definition"), "semantic"),
    (("when", "happened", "meeting", "incident", "yesterday"), "episodic"),
    (("document", "doc", "manual", "section", "file"), "document"),
]


def keyword_experts(query: str) -> List[str]:
    q = query.lower()
    hits = [expert for terms, expert in _RULES if any(t in q for t in terms)]
    return list(dict.fromkeys(hits))  # de-dup, preserve order
