"""Context pack result types."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

from .item import ContextItem


@dataclass
class PackedItem:
    item: ContextItem
    final_score: float
    breakdown: Dict[str, float]


@dataclass
class ContextPack:
    items: List[PackedItem] = field(default_factory=list)
    selected_experts: List[str] = field(default_factory=list)
    routing_reason: str = ""
    tokens: int = 0
    dropped: List[Dict] = field(default_factory=list)

    def to_prompt(self) -> str:
        lines = ["Relevant context:", ""]
        for i, p in enumerate(self.items, 1):
            lines.append(f"{i}. [{p.item.expert}] {p.item.content}")
        return "\n".join(lines)

    @property
    def citations(self) -> List[str]:
        return [p.item.id for p in self.items]
