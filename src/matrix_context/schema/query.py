"""Recall query model."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RecallQuery:
    text: str
    scopes: List[str] = field(default_factory=lambda: ["/"])
    experts: Optional[List[str]] = None      # None = let the router decide
    top_experts: int = 3
    top_k: int = 8
    max_tokens: int = 600
