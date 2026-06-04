"""MoC-RAG Benchmark — typed context routing for agentic memory.

A reproducible benchmark + evaluation suite that tests whether routed, typed
context experts (Mixture-of-Contexts RAG) improve retrieval and answer quality
over flat RAG. It ships:

* a deterministic generator (`generate.py`) producing typed context items,
  queries, gold labels, and *hard negatives* across six agentic-memory domains;
* baseline runners (`runners.py`): BM25, dense, hybrid, metadata-filtered,
  reranked, and MoC-RAG with `top_experts in {1, 2, 3, all}`;
* retrieval + context-efficiency + answer-quality metrics (`metrics.py`);
* JSON/Markdown reporting (`report.py`) and a Hugging Face dataset card +
  Hub push script (`hf_card.py`, `push_to_hub.py`).

Everything runs offline single-node with the hashing embedder (CI guard); the
real ranking appears with a competent embedder (`--embedder st`).
"""
from .taxonomy import DOMAINS, EXPERTS, TYPES

__all__ = ["EXPERTS", "TYPES", "DOMAINS"]
__benchmark_version__ = "0.1.0"
