"""Pluggable embedders. Hashing is offline/CI; ollama & ST are real, lazy."""
from __future__ import annotations
import numpy as np


def get_embedder(name: str):
    if name == "hashing":
        from matrix_context.embedding.hashing import HashingEmbedder
        return HashingEmbedder()
    if name in ("sentence-transformers", "st"):
        from matrix_context.embedding.sentence_transformers import SentenceTransformerEmbedder
        return SentenceTransformerEmbedder()
    if name == "ollama":
        return OllamaEmbedder()
    raise ValueError(f"unknown embedder: {name}")


class OllamaEmbedder:
    """Local Ollama embeddings (e.g. nomic-embed-text). Requires a running server."""
    def __init__(self, model: str = "nomic-embed-text"):
        import ollama  # lazy
        self._ollama = ollama
        self.model = model
        self.dim = len(self.encode("dimension probe"))

    def encode(self, text: str) -> np.ndarray:
        r = self._ollama.embeddings(model=self.model, prompt=text)
        v = np.asarray(r["embedding"], dtype=np.float32)
        n = np.linalg.norm(v)
        return v / n if n > 0 else v
