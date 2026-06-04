"""Real semantic embedder via sentence-transformers (extra: `embeddings`).

This is the regime the benchmark shows actually beats flat RAG. Lazy import so
the package stays dependency-light when the stub is used.
"""
from __future__ import annotations
import numpy as np


class SentenceTransformerEmbedder:
    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "Install the embeddings extra: pip install 'matrix-context[embeddings]'"
            ) from e
        self._model = SentenceTransformer(model)
        self.dim = self._model.get_sentence_embedding_dimension()

    def encode(self, text: str) -> np.ndarray:
        v = self._model.encode(text, normalize_embeddings=True)
        return np.asarray(v, dtype=np.float32)
