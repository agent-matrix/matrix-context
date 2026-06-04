# Matrix Context

**A local-first, inspectable context layer for agents — a Python library and (v1) MCP server that routes across typed memories and assembles a token-budgeted context pack, so any agent retrieves the right context, in less of it, and you can see exactly why.**

Part of the [Agent-Matrix](https://github.com/agent-matrix) ecosystem. Matrix Hub catalogs and installs; agent-generator generates; HomePilot proves local-first memory. Matrix Context is the missing runtime layer that turns scattered memory and knowledge into the right prompt-sized context, on demand, with governance.

## Why it exists

Classic RAG dumps one flat index into every prompt. Matrix Context implements **Mixture-of-Contexts (MoC-RAG)**: it routes each query to the smallest useful subset of typed *context experts* (session, profile, semantic, episodic, document, policy), retrieves with a hybrid lexical + dense fusion inside them, and packs the result into a token budget that weighs relevance, importance, recency and diversity. Every selection is explainable through `inspect()`.

## Install

```bash
pip install matrix-context                 # core, zero model download
pip install "matrix-context[embeddings]"   # real semantic embedder (recommended)
pip install "matrix-context[all]"          # + mcp, postgres, milvus
```

## Quickstart

```python
from matrix_context import ContextManager

ctx = ContextManager.create("my-agent")
ctx.remember("The user prefers local-first AI tools", expert="profile", importance=0.9)
ctx.remember("Decision: SQLite is the default backend", expert="semantic", importance=0.8)

pack = ctx.build_pack("How should I design this agent?", max_tokens=400)
print(pack.to_prompt())
print(ctx.inspect("How should I design this agent?"))   # why each item won
```

## CLI

```bash
matrix-context init
matrix-context remember "Decision: use Postgres for audit logs" --expert semantic
matrix-context pack "what did we decide about audit logs" --max-tokens 600
matrix-context inspect "what did we decide about audit logs"
```

## The benchmark, honestly

`python -m eval.harness` compares the engine against classic flat RAG on a typed memory set. The finding that drives the roadmap: with the **offline hashing-stub embedder, routing does not beat flat RAG** — the gate can't discriminate. With a **competent gate (a real embedding model), the engine matches flat RAG's recall while cutting distractor noise ~60% and roughly halving tokens.** The whole payoff is gated on embedding quality, so that is the first investment.

The larger **[MoC-RAG Benchmark](benchmarks/README.md)** (`huggingface.co/datasets/ruslanmv/moc-rag-benchmark`) sharpens the claim to *robustness*: across keyword / paraphrased / adversarial query splits, BM25 collapses on adversarial phrasing (−36%) while MoC-RAG holds and **overtakes BM25 by ~+15 points on the adversarial split**, carrying roughly half the hard distractors of dense RAG at 95–100% routing accuracy. Live leaderboard: `huggingface.co/spaces/ruslanmv/moc-rag-leaderboard`.

## The standard: MoC Contract v1

Matrix Context is positioned as a **protocol and inspectability standard**, not just an engine. [`moc_contract/`](moc_contract/README.md) freezes a versioned public wire contract — 20 JSON Schema (2020-12) objects, an OpenAPI 3.1 description, an MCP mapping, and a SemVer compatibility policy — so any storage engine, embedder, or framework can implement the same inspectable recall behaviour. The differentiating object is the **inspect** response: selected vs. unselected experts, routing scores, kept items with score breakdowns, dropped items with reasons, and the prompt-ready pack.

```bash
matrix-context serve --transport rest --port 8088
python -m moc_contract.conformance --url http://127.0.0.1:8088   # -> MoC API v1 Compatible ✓
```

## Status

`0.1.0` ships the engine (routing, hybrid retrieval, budgeted packing, inspect), SQLite, the SDK and CLI, the eval harness, a **v1 REST surface** implementing **MoC Contract v1** (`/v1/health|version|experts|scopes|items|items/{id}|remember|recall|pack|inspect|router/explain|forget`) with an executable conformance suite, the **agent-generator** and **HomePilot** adapters, and the **MoC-RAG Benchmark**. The MCP server, governance, lifecycle (dedup/contradiction/consolidation), and Postgres/pgvector are scaffolded and staged for v1; Milvus and the learned router for v2. See `PROJECT_STRUCTURE` for the staged tree, and `RELEASE.md` for the release/DOI process.

## License

Apache-2.0.
