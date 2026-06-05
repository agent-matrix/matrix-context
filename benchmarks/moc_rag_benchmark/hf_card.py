"""Hugging Face dataset card + dataset_infos generation.

The card is the primary rendered documentation for a dataset on the Hub, so it
carries YAML metadata (license, tags, task categories) and explains the
contents, intended use, structure, hard negatives, and limitations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from . import __benchmark_version__
from .taxonomy import DOMAINS, EXPERTS, TYPES

_FRONTMATTER = """---
license: apache-2.0
language:
- en
pretty_name: "MoC-RAG Benchmark: Typed Context Routing for Agentic Memory"
tags:
- retrieval
- rag
- agent-memory
- context-routing
- mixture-of-contexts
task_categories:
- question-answering
- sentence-similarity
size_categories:
- 1K<n<10K
configs:
- config_name: default
  data_files:
  - split: train
    path: splits/train.jsonl
  - split: validation
    path: splits/validation.jsonl
  - split: test
    path: splits/test.jsonl
---
"""


def dataset_card(counts: Dict[str, int]) -> str:
    c = counts
    return _FRONTMATTER + f"""
# MoC-RAG Benchmark: Typed Context Routing for Agentic Memory

A benchmark for evaluating whether **routed, typed context experts**
(Mixture-of-Contexts RAG) improve retrieval and answer quality compared with
**flat RAG**, under a fixed token budget.

Version `{__benchmark_version__}`.

## Why this benchmark

Flat RAG embeds everything into one index and retrieves nearest chunks for every
query. MoC-RAG instead asks *which typed context experts should be searched
first*, retrieves inside them, and assembles a token-budgeted, explainable pack.
This dataset is built to test that claim where it should matter most: in the
presence of **hard negatives** that flat RAG is tempted by but a router should
avoid.

## Contents

| file | rows | description |
|------|-----:|-------------|
| `contexts.jsonl` | {c.get('contexts', 0)} | typed context items (the memory store) |
| `queries.jsonl`  | {c.get('queries', 0)} | queries / tasks |
| `gold.jsonl`     | {c.get('gold', 0)} | gold, acceptable, and distractor labels |
| `splits/*`       | — | train / validation / test query splits |

- **{c.get('experts', len(EXPERTS))} experts:** {", ".join(EXPERTS)}
- **{c.get('types', len(TYPES))} context types:** {", ".join(TYPES)}
- **{c.get('domains', len(DOMAINS))} domains:** {", ".join(DOMAINS)}

## Hard negatives ({c.get('hard_negatives', 5)} kinds)

Each gold fact is surrounded by:

- `same_keyword_wrong_expert` — same salient keyword, different typed expert
- `same_expert_wrong_scope` — a true fact, but for a different project/persona
- `outdated_decision` — a superseded decision (low confidence, old timestamp)
- `contradictory_memory` — a note asserting a conflicting value
- `stale_session_note` — an old session mention with nothing decided

## Query variants & robustness splits

Every gold topic is phrased **five ways** (the `variant` field on each query),
holding the gold label constant while varying lexical overlap and intent:

`direct` (keyword-aligned) · `paraphrased` · `underspecified` · `cross_expert` ·
`adversarial` (embeds a misleading term that lexically matches the contradictory
hard negative).

Beyond `train` / `validation` / `test`, three **parallel** test splits phrase the
same test topics three ways so robustness to lexical noise can be measured
directly: `test_keyword`, `test_paraphrased`, `test_adversarial`. A retriever
that scores well on `test_keyword` but degrades on `test_adversarial` is brittle
to paraphrase and misleading keywords.

## Schema

`contexts.jsonl`
```json
{{"context_id": "ctx_000000", "expert": "decision_memory", "type": "decision",
 "scope": "project:matrix-context", "content": "...", "tags": ["..."],
 "importance": 0.95, "confidence": 0.92, "source": "synthetic_gold",
 "created_at": "2026-06-04T10:00:00Z", "role": "gold"}}
```
`queries.jsonl`
```json
{{"query_id": "q_000000", "query": "...", "task_type": "architecture_recall",
 "expected_experts": ["decision_memory", "project_memory"],
 "scope": "project:matrix-context", "difficulty": "easy", "domain": "..."}}
```
`gold.jsonl`
```json
{{"query_id": "q_000000", "gold_context_ids": ["ctx_000000"],
 "acceptable_context_ids": ["ctx_000001"],
 "distractor_context_ids": ["ctx_000002", "..."],
 "gold_answer": "SQLite", "gold_citations": ["ctx_000000"]}}
```

## Intended use

Evaluate retrieval + context efficiency + answer quality for agentic memory.
Report Recall@K, Precision@K, MRR, nDCG, distractor and token counts, useful
context ratio, expert routing accuracy, and (optionally) grounded answer
quality. Compare flat / BM25 / hybrid / metadata-filtered / reranked RAG against
MoC-RAG with `top_experts in {{1, 2, 3, all}}`.

## Limitations and bias

The dataset is **synthetic** (template-generated, deterministic) and English
only. It is designed to exercise the routing mechanism and tooling rigorously,
not to make a strong general claim about real corpora; the roadmap is to grow it
toward human-reviewed, real long-horizon memory. Synthetic facts about named
projects are illustrative, not authoritative.

## License

Apache-2.0.

## Conformance

The reference implementation passes the **MoC Contract v1** conformance suite and
is `MoC API v1 Compatible` / `MoC Inspect v1 Compatible`. See
`moc_contract/` in the software repository and run
`python -m moc_contract.conformance`.

## Citation

Please cite the software via its `CITATION.cff`
(`github.com/agent-matrix/matrix-context`). A dataset/software **DOI is
forthcoming** (Zenodo deposit on tagged release, after manuscript review); this
card will be updated with the DOI when minted. Until then, cite as:

```
@software{{moc_rag_benchmark,
  title  = {{MoC-RAG Benchmark: Typed Context Routing for Agentic Memory}},
  author = {{Magana Vsevolodovna, Ruslan}},
  year   = {{2026}},
  note   = {{Independent Researcher, Genova, Italy. DOI forthcoming.}},
  url    = {{https://huggingface.co/datasets/ruslanmv/moc-rag-benchmark}}
}}
```
"""


def write_card(path: Path, counts: Dict[str, int]) -> None:
    path.write_text(dataset_card(counts))
