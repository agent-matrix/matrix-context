# experiments/ — algorithm bake-off for small LLMs

**Question.** Which context-retrieval algorithm produces the best answers from a
*small, local* LLM, at the lowest token cost — and does anything reliably beat
plain ChromaDB RAG?

**Hypothesis.** Small models are the most sensitive to long, noisy prompts
("lost in the middle"). So a routed, budgeted, deduplicated context (MoC-RAG)
should help small models *more* than large ones — same recall, far fewer
distractors and tokens.

## What it compares

Four algorithms, same embedder held constant (the fair lever), same token budget:

- `simple_rag`  — flat dense top-k (the ChromaDB baseline to beat)
- `bm25_rag`    — lexical only
- `hybrid_rag`  — BM25 + dense fused with RRF, no routing
- `moc_rag`     — Matrix Context: routing + hybrid + budgeted pack

## Backends (pluggable)

- Embedders: `hashing` (offline, zero-download — the CI default), `ollama`
  (e.g. `nomic-embed-text`), `sentence-transformers`.
- Stores: `memory` (offline default), `chroma` (local ChromaDB).
- Generators (optional, for answer-quality scoring): `none`, `ollama`
  (e.g. `llama3.2:1b`, `qwen2.5:0.5b`) used as both answerer and judge.

## Run it

Offline, fast, CI-safe (no downloads):
```bash
python -m experiments.runner --embedder hashing --store memory
```

Real, local, small-LLM (requires `pip install '.[experiments]'`, a running
Ollama, and the models pulled):
```bash
ollama pull nomic-embed-text && ollama pull llama3.2:1b
python -m experiments.runner --embedder ollama --store chroma --generator ollama
```

Results are written to `experiments/results/` as `summary.md` and `results.json`.

## Goal

Find the algorithm + budget that wins for small models, then promote the winning
configuration into the engine defaults. The offline run is a regression guard;
the Ollama+Chroma run is the real measurement.
