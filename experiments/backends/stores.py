"""Vector stores: in-memory (offline) and ChromaDB (local). Same interface."""
from __future__ import annotations
from typing import List, Tuple

import numpy as np


def get_store(name: str, dim: int):
    if name == "memory":
        return MemoryStore(dim)
    if name == "chroma":
        return ChromaStore(dim)
    raise ValueError(f"unknown store: {name}")


class MemoryStore:
    def __init__(self, dim: int):
        self.dim = dim
        self._ids: List[str] = []
        self._emb: List[np.ndarray] = []

    def add(self, item_id: str, embedding: np.ndarray):
        self._ids.append(item_id); self._emb.append(embedding)

    def query(self, embedding: np.ndarray, k: int) -> List[Tuple[str, float]]:
        if not self._emb:
            return []
        mat = np.vstack(self._emb)
        sims = mat @ embedding
        order = np.argsort(-sims)[:k]
        return [(self._ids[i], float(sims[i])) for i in order]


class ChromaStore:
    """Local ChromaDB collection. Requires `pip install '.[experiments]'`."""
    def __init__(self, dim: int):
        import chromadb  # lazy
        self.dim = dim
        self._client = chromadb.Client()
        try:
            self._client.delete_collection("experiments")
        except Exception:
            pass
        self._col = self._client.create_collection(
            "experiments", metadata={"hnsw:space": "cosine"})

    def add(self, item_id: str, embedding: np.ndarray):
        self._col.add(ids=[item_id], embeddings=[embedding.tolist()])

    def query(self, embedding: np.ndarray, k: int):
        r = self._col.query(query_embeddings=[embedding.tolist()], n_results=k)
        ids = r["ids"][0]
        dists = r.get("distances", [[0.0] * len(ids)])[0]
        return [(i, 1.0 - d) for i, d in zip(ids, dists)]  # cosine distance -> sim
