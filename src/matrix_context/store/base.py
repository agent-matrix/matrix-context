"""Store contract. SQL is the governance plane; vectors are an accelerator.
The logical contract here is identical across sqlite/postgres/milvus backends.
"""
from __future__ import annotations
from typing import List, Optional, Protocol

from ..schema.item import ContextItem


class Store(Protocol):
    def add(self, item: ContextItem) -> ContextItem: ...
    def candidates(self, experts: List[str], scope: str,
                   now: Optional[float] = None) -> List[ContextItem]: ...
    def all_items(self) -> List[ContextItem]: ...
