"""Context expert taxonomy and seed descriptions.

Descriptions seed each expert's centroid before any items exist (cold start).
"""
from __future__ import annotations
from ..schema.enums import EXPERTS

EXPERT_DESCRIPTIONS = {
    "session": "current conversation recent messages thread continuity",
    "profile": "user preferences identity name role settings boundaries",
    "semantic": "durable facts decisions glossary stable knowledge",
    "episodic": "past events meetings actions incidents what happened when",
    "document": "documents files manuals design docs reference material",
    "policy": "rules policy compliance allowed approval security guardrails legal",
}

assert set(EXPERT_DESCRIPTIONS) == set(EXPERTS)
