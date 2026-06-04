"""watsonx.ai embedding client.  [v1 — stub]

Wraps ibm-watsonx-ai Embeddings behind the Embedder protocol. Implement once a
watsonx endpoint/credentials path is wired through config.
"""
from __future__ import annotations
import numpy as np


class WatsonxEmbedder:  # pragma: no cover - [v1]
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("WatsonxEmbedder is a v1 component.")

    def encode(self, text: str) -> np.ndarray:
        raise NotImplementedError
