"""Milvus vector accelerator.  [v2 — stub]

Optional high-scale dense+sparse+hybrid backend. Never the source of truth —
scopes, policy, approvals and audit always remain in SQL. Requires `milvus`.
"""
from __future__ import annotations


class MilvusStore:  # pragma: no cover - [v2]
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("MilvusStore is a v2 component.")
