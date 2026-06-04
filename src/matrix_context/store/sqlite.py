"""SQLite store — the local-first default. Single file, real persistence.

Metadata + content live in SQL; embeddings are float32 blobs. In production the
lexical channel becomes FTS5; the vector channel can move to pgvector/Milvus.
"""
from __future__ import annotations
import sqlite3
import time
from typing import List, Optional

import numpy as np

from ..embedding.base import Embedder
from ..schema.item import ContextItem


class SqliteStore:
    def __init__(self, path: str, embedder: Embedder):
        self.embedder = embedder
        self.db = sqlite3.connect(path)
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY, content TEXT, expert TEXT, scope TEXT,
                importance REAL, tags TEXT, created_at REAL, ttl REAL, embedding BLOB
            )"""
        )
        self.db.commit()

    def add(self, item: ContextItem) -> ContextItem:
        if item.embedding is None:
            item.embedding = self.embedder.encode(item.content)
        self.db.execute(
            "INSERT OR REPLACE INTO items VALUES (?,?,?,?,?,?,?,?,?)",
            (item.id, item.content, item.expert, item.scope, item.importance,
             ",".join(item.tags), item.created_at, item.ttl,
             item.embedding.astype(np.float32).tobytes()),
        )
        self.db.commit()
        return item

    def _row(self, r) -> ContextItem:
        return ContextItem(
            id=r[0], content=r[1], expert=r[2], scope=r[3], importance=r[4],
            tags=tuple(t for t in r[5].split(",") if t), created_at=r[6], ttl=r[7],
            embedding=np.frombuffer(r[8], dtype=np.float32) if r[8] else None,
        )

    def candidates(self, experts: List[str], scope: str,
                   now: Optional[float] = None) -> List[ContextItem]:
        now = now if now is not None else time.time()
        q = (f"SELECT * FROM items WHERE expert IN "
             f"({','.join('?' * len(experts))}) AND scope LIKE ?")
        rows = self.db.execute(q, (*experts, scope.rstrip('/') + '%')).fetchall()
        return [it for it in (self._row(r) for r in rows) if it.is_live(now)]

    def all_items(self) -> List[ContextItem]:
        return [self._row(r) for r in self.db.execute("SELECT * FROM items")]

    def get(self, item_id: str) -> Optional[ContextItem]:
        r = self.db.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        return self._row(r) if r else None
