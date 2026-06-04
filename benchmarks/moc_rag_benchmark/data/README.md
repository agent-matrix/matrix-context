---
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

# MoC-RAG Benchmark: Typed Context Routing for Agentic Memory

A benchmark for evaluating whether **routed, typed context experts**
(Mixture-of-Contexts RAG) improve retrieval and answer quality compared with
**flat RAG**, under a fixed token budget.

Version `0.1.0`.

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
| `contexts.jsonl` | 1000 | typed context items (the memory store) |
| `queries.jsonl`  | 600 | queries / tasks |
| `gold.jsonl`     | 600 | gold, acceptable, and distractor labels |
| `splits/*`       | — | train / validation / test query splits |

- **8 experts:** user_memory, project_memory, document_rag, code_context, session_memory, decision_memory, policy_rules, tool_history
- **10 context types:** fact, preference, goal, decision, rule, document, code, episode, summary, tool_result, profile
- **6 domains:** project_architecture, user_persona, code_context, policy_rules, tool_session, document_rag

## Hard negatives (5 kinds)

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
{"context_id": "ctx_000000", "expert": "decision_memory", "type": "decision",
 "scope": "project:matrix-context", "content": "...", "tags": ["..."],
 "importance": 0.95, "confidence": 0.92, "source": "synthetic_gold",
 "created_at": "2026-06-04T10:00:00Z", "role": "gold"}
```
`queries.jsonl`
```json
{"query_id": "q_000000", "query": "...", "task_type": "architecture_recall",
 "expected_experts": ["decision_memory", "project_memory"],
 "scope": "project:matrix-context", "difficulty": "easy", "domain": "..."}
```
`gold.jsonl`
```json
{"query_id": "q_000000", "gold_context_ids": ["ctx_000000"],
 "acceptable_context_ids": ["ctx_000001"],
 "distractor_context_ids": ["ctx_000002", "..."],
 "gold_answer": "SQLite", "gold_citations": ["ctx_000000"]}
```

## Intended use

Evaluate retrieval + context efficiency + answer quality for agentic memory.
Report Recall@K, Precision@K, MRR, nDCG, distractor and token counts, useful
context ratio, expert routing accuracy, and (optionally) grounded answer
quality. Compare flat / BM25 / hybrid / metadata-filtered / reranked RAG against
MoC-RAG with `top_experts in {1, 2, 3, all}`.

## Limitations and bias

The dataset is **synthetic** (template-generated, deterministic) and English
only. It is designed to exercise the routing mechanism and tooling rigorously,
not to make a strong general claim about real corpora; the roadmap is to grow it
toward human-reviewed, real long-horizon memory. Synthetic facts about named
projects are illustrative, not authoritative.

## License

Apache-2.0.

## Citation

```
@software{moc_rag_benchmark,
  title = {MoC-RAG Benchmark: Typed Context Routing for Agentic Memory},
  author = {Magana Vsevolodovna, Ruslan},
  year = {2026},
  url = {https://github.com/agent-matrix/matrix-context}
}
```
