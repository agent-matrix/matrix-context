"""Configuration model. from_env reads MATRIX_CONTEXT_* variables."""
from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass
class Config:
    name: str = "default"
    backend: str = "sqlite"          # sqlite | postgres(v1) | milvus(v2)
    path: str = ""                   # sqlite file path
    embedder: str = "hashing"        # hashing | sentence-transformers | watsonx(v1)
    max_tokens: int = 600
    top_experts: int = 2            # promoted from the bake-off (moc_rag winner)

    @classmethod
    def from_env(cls) -> "Config":
        g = os.environ.get
        return cls(
            name=g("MATRIX_CONTEXT_NAME", "default"),
            backend=g("MATRIX_CONTEXT_BACKEND", "sqlite"),
            path=g("MATRIX_CONTEXT_PATH", ""),
            embedder=g("MATRIX_CONTEXT_EMBEDDER", "hashing"),
            max_tokens=int(g("MATRIX_CONTEXT_MAX_TOKENS", "600")),
            top_experts=int(g("MATRIX_CONTEXT_TOP_EXPERTS", "2")),
        )
