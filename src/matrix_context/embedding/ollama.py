"""Local Ollama embeddings client.  [v1 — stub]"""
from __future__ import annotations
import numpy as np


class OllamaEmbedder:  # pragma: no cover - [v1]
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("OllamaEmbedder is a v1 component.")

    def encode(self, text: str) -> np.ndarray:
        raise NotImplementedError
