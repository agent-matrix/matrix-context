"""Embedding contract. This protocol is the seam the whole payoff depends on:
swap HashingEmbedder for a real model and routing quality (and therefore the
product's advantage over flat RAG) jumps. See eval/ for the measured effect.
"""
from __future__ import annotations
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    dim: int
    def encode(self, text: str) -> np.ndarray: ...


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))  # inputs are expected L2-normalized
