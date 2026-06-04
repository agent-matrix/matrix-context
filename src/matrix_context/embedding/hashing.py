"""Zero-download, offline, deterministic embedder — the local-first default.

A hashing vectorizer over word unigrams + character 3-grams, L2-normalized.
It runs anywhere with no model files and no network. It is a STAND-IN for
semantic quality, not a model; the benchmark shows routing on this stub does
not beat flat RAG. Use a real Embedder in production.
"""
from __future__ import annotations
import hashlib
import re
from typing import List

import numpy as np

_TOKEN = re.compile(r"[a-z0-9]+")


class HashingEmbedder:
    def __init__(self, dim: int = 512):
        self.dim = dim

    def _features(self, text: str) -> List[str]:
        words = _TOKEN.findall(text.lower())
        feats = list(words)
        for w in words:
            padded = f"#{w}#"
            feats += [padded[i:i + 3] for i in range(len(padded) - 2)]
        return feats

    def encode(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        for f in self._features(text):
            h = int(hashlib.md5(f.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0 if (h >> 8) & 1 else -1.0
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec
