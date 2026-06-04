"""Row schemas for the benchmark dataset (contexts, queries, gold).

These are plain dataclasses with JSON (de)serialization so the dataset is a set
of ``.jsonl`` files that render on the Hugging Face Hub. A ``ContextRow`` carries
the typed metadata the benchmark needs (expert, type, scope, importance,
confidence, source, created_at) plus internal bookkeeping (``topic``, ``role``,
``negative_kind``) used to build gold labels and analyze hard negatives.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class ContextRow:
    context_id: str
    expert: str
    type: str
    scope: str
    content: str
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5
    confidence: float = 0.9
    source: str = "synthetic"
    created_at: str = "2026-06-04T10:00:00Z"
    # Internal bookkeeping (kept in-file so the benchmark is self-describing).
    topic: str = ""
    role: str = "gold"            # gold | acceptable | distractor | filler
    negative_kind: Optional[str] = None  # set for hard negatives


@dataclass
class QueryRow:
    query_id: str
    query: str
    task_type: str
    expected_experts: List[str]
    scope: str
    difficulty: str = "medium"
    domain: str = ""
    topic: str = ""
    variant: str = "direct"   # direct | paraphrased | underspecified | cross_expert | adversarial


@dataclass
class GoldRow:
    query_id: str
    gold_context_ids: List[str]
    acceptable_context_ids: List[str] = field(default_factory=list)
    distractor_context_ids: List[str] = field(default_factory=list)
    gold_answer: str = ""
    gold_citations: List[str] = field(default_factory=list)


def write_jsonl(rows: Iterable, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(asdict(r) if hasattr(r, "__dataclass_fields__") else r))
            f.write("\n")
            n += 1
    return n


def read_jsonl(path: Path) -> List[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_contexts(path: Path) -> List[ContextRow]:
    return [ContextRow(**r) for r in read_jsonl(path)]


def load_queries(path: Path) -> List[QueryRow]:
    return [QueryRow(**r) for r in read_jsonl(path)]


def load_gold(path: Path) -> List[GoldRow]:
    return [GoldRow(**r) for r in read_jsonl(path)]
