"""Postgres + pgvector store with row-level security.  [v1 — stub]

Default server backend for v1: same logical contract as SqliteStore, with
tenant isolation via RLS and ANN vector search via pgvector (HNSW/IVFFlat).
Requires the `postgres` extra.
"""
from __future__ import annotations


class PostgresStore:  # pragma: no cover - [v1]
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("PostgresStore is a v1 component.")
