# MoC-RAG Benchmark

A reproducible benchmark + evaluation suite that tests whether **routed, typed
context experts** (Mixture-of-Contexts RAG) beat **flat RAG** for agentic memory
— not by assertion, but with a dataset and harness anyone can run.

> The point is not to *say* MoC-RAG is better. It is to publish the benchmark
> where that claim can be tested by anyone.

## Quickstart

```bash
# 1. Generate the dataset (deterministic): 1000 contexts, 300 queries,
#    8 experts, 10+ types, 6 domains, 5 hard-negative kinds, train/val/test.
python -m benchmarks.moc_rag_benchmark.run build

# 2. Run every method on the test split (offline, hashing embedder = CI guard).
python -m benchmarks.moc_rag_benchmark.run run --split test --embedder hashing --groundedness

# 3. The real reading, with a competent embedder.
pip install -e ".[experiments]"
python -m benchmarks.moc_rag_benchmark.run run --split test --embedder st --groundedness

# 4. Robustness by query type — the key result. Runs every method across the
#    parallel keyword / paraphrased / adversarial test splits.
python -m benchmarks.moc_rag_benchmark.run compare --embedder st --groundedness

# 5. Answer quality with a small local LLM (optional).
ollama pull qwen2.5:0.5b
python -m benchmarks.moc_rag_benchmark.run run --split test --embedder st --generator ollama
```

## Query variants (the robustness layer)

Each gold topic is phrased five ways — `direct`, `paraphrased`,
`underspecified`, `cross_expert`, `adversarial` — with the gold label held
constant. The `adversarial` phrasing embeds a misleading term that lexically
matches the contradictory hard negative, so a flat retriever is genuinely
tempted. Three **parallel** test splits (`test_keyword`, `test_paraphrased`,
`test_adversarial`) phrase the *same* test topics three ways, so `compare`
attributes any metric change to query style rather than topic leakage.

Headline (real embedder): BM25 drops −36% from keyword to adversarial, while
MoC-RAG holds within ~17 points, **overtakes BM25 by +15 points on the
adversarial split**, and carries ~half the hard distractors of dense RAG. See
[`results/FINDINGS.md`](moc_rag_benchmark/results/FINDINGS.md).

Reports are written to `benchmarks/moc_rag_benchmark/results/` as `summary.md`
(publication table), `results.json`, and one `<algorithm>.json` artifact each.

## What it measures

**Methods** — `bm25_rag`, `dense_rag`, `hybrid_rag`, `metadata_rag` (the
"isn't this just filtering?" baseline), `reranked_rag`, and MoC-RAG with
`top_experts ∈ {1, 2, 3, all}`.

**Metrics** — Recall@K, Precision@K, MRR, nDCG@K; packed distractors and **hard
distractors** (labeled hard negatives); token count; useful-context ratio;
context efficiency (recall per 1k tokens); expert routing accuracy; latency; and
optional answer correctness / groundedness / citation support.

**Hard negatives** — every gold fact is surrounded by five kinds flat RAG is
tempted by: `same_keyword_wrong_expert`, `same_expert_wrong_scope`,
`outdated_decision`, `contradictory_memory`, `stale_session_note`.

## The algorithm under test

```
query → hybrid route → retrieve in selected experts → rerank → budgeted pack → explain
```

The **hybrid router** scores experts with
`0.40·centroid + 0.25·keyword + 0.15·type + 0.10·scope + 0.10·activity`, with a
low-confidence fallback that widens selection (graceful degradation). See
`runners.py:MoCRouter`.

## Results

Two reference runs (hashing, sentence-transformers) — each with a mixed-split
table (`summary.md`) and a robustness-by-query-type table
(`variants_summary.md`) — plus an honest interpretation are archived in
[`moc_rag_benchmark/results/FINDINGS.md`](moc_rag_benchmark/results/FINDINGS.md).
Short version: MoC-RAG cuts packed hard distractors ~50% versus the
dense/hybrid/metadata/reranked baselines at 95–100% routing accuracy, and — the
robustness result — **overtakes BM25 by +15 points on adversarial queries** where
BM25's lexical advantage collapses (−36%).

## Publishing to Hugging Face

```bash
python -m benchmarks.moc_rag_benchmark.run push-results \
  --repo agent-matrix/moc-rag-benchmark --dataset
python -m benchmarks.moc_rag_benchmark.run push-results \
  --repo agent-matrix/moc-rag-benchmark --results benchmarks/moc_rag_benchmark/results/st
```

`build` writes a Hugging Face dataset card to `data/README.md`; the push uses
`huggingface_hub` (install separately) and `HF_TOKEN`.
