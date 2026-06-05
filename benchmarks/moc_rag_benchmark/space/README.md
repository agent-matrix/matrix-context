---
title: MoC-RAG Benchmark Leaderboard
emoji: 🧭
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: 5.50.0
app_file: app.py
pinned: false
license: apache-2.0
---

# MoC-RAG Benchmark Leaderboard

A public viewer for the [MoC-RAG Benchmark](https://huggingface.co/datasets/ruslanmv/moc-rag-benchmark):
does routed, typed context (Mixture-of-Contexts RAG) beat flat RAG for agentic
memory?

The Space renders two tables from bundled result artifacts:

- **Robustness by query type** — Recall@K and hard distractors across the
  parallel `keyword` / `paraphrased` / `adversarial` test splits. This is the
  headline: BM25 collapses on adversarial phrasing while MoC-RAG holds and
  overtakes it.
- **Single-split leaderboard** — full retrieval + context-efficiency + routing
  metrics on the mixed test split.

Switch embedder (`hashing` offline guard vs `st` = sentence-transformers) with
the dropdown. Reproduce locally:

```bash
python -m benchmarks.moc_rag_benchmark.run build
python -m benchmarks.moc_rag_benchmark.run compare --embedder st --groundedness
```
