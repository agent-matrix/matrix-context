# Matrix Context: A Local-First, Inspectable Mixture-of-Contexts Layer for Agent Memory

**Author.** Ruslan Magana Vsevolodovna (Independent Researcher, Genova, Italy; ruslanmv.com). ORCID: _[add at deposit]_.
**Version.** 0.1.0 · **Date.** 2026 · **License.** Apache-2.0 (software) / CC-BY-4.0 (this manuscript).
**Software.** https://github.com/agent-matrix/matrix-context · **DOI.** _[minted by Zenodo on deposit]_

## Abstract

Most retrieval-augmented generation systems embed all available knowledge into a single index and retrieve the nearest passages for every query. This is simple but indiscriminate: it spends a fixed prompt budget without regard to the type or usefulness of what it retrieves, and it cannot explain its choices. We present Matrix Context, a local-first context layer that reframes retrieval as routing over typed memory. Each query is directed to a small subset of typed context experts — session, profile, semantic, episodic, document, and policy memory — retrieved with a hybrid lexical and dense fusion within those experts, and composed into a token-budgeted context pack scored by relevance, importance, recency, and diversity, with every selection exposed for inspection. We describe the architecture, report a reproducible benchmark against classic flat retrieval, and characterize the conditions under which routing helps. Our principal finding is that the advantage of the approach is real but conditional on the quality of the routing signal: with a weak embedder the method ties flat retrieval, whereas with a competent embedder it matches flat retrieval's recall while reducing distractor content by roughly sixty percent and approximately halving the tokens consumed. We release the engine, a command-line tool, and the evaluation harness under an open-source license.

**Keywords.** agent memory; retrieval-augmented generation; mixture of contexts; query routing; model context protocol; local-first.

## 1. Introduction

Stateless language models begin each interaction without history. The prevailing remedy stores prior interactions and documents in a vector index and retrieves top matches into each prompt. This degrades in deployment for compounding reasons: the prompt lengthens, time-to-first-token rises, salient facts are lost within long windows, and transmitting large histories to produce short answers is costly. The underlying issue is representational. A flat index treats a stable user preference, an incidental remark, a compliance rule, and a paragraph of reference material as interchangeable, ranked only by surface similarity, and offers no account of why any item was selected. We argue that retrieval for agent memory should instead be organized around typed partitions and an explicit routing decision, and that doing so yields the same answers in substantially less context while making the system auditable.

## 2. Approach

The organizing principle is sparse routing: expose many specialists but activate only the few a given input requires. This is the mechanism by which mixture-of-experts models scale capacity without proportional compute, and the author has argued elsewhere that the same principle extends upward from model experts to whole models and to agents. Matrix Context extends it to context, treating the memory store as a set of context experts selected per query.

We are precise about the mechanism to avoid overstating novelty. The context experts here are typed memory partitions, not learned mixture-of-experts modules with jointly trained gates; the router is a retrieval-time policy rather than a trained network. The contribution therefore belongs to the established line of query-routed retrieval — routing to clustered document experts, gating whether to retrieve, and routing across specialized retrievers — and lies in the product shape, the budgeted composition, and the explainability rather than in a new learning objective.

## 3. Architecture

The system comprises four planes — ingest, store, route, and serve — with structured metadata and governance held in SQL and vector search treated as an accelerator. The unit of memory is a typed context item carrying content, an expert partition, a hierarchical scope, an author-set importance, an optional time-to-live, and an embedding; typing the item is what enables routing by meaning and, in later versions, governance by policy.

Routing proceeds in two tiers. A fast centroid gate scores the query against each expert's running centroid blended with a seed description, so the system behaves sensibly before any items exist. When the gate is confident and decisive it selects the leading experts; when it is not, it widens its selection rather than guessing, and that widening point is the seam at which a language-model classifier belongs in a later version. Within the selected experts, a lexical channel and a dense channel are fused by reciprocal rank fusion, which requires no calibration between channels and is therefore robust when one channel is strong and the other weak. The fused candidates are composed by a context-pack assembler that scores each item as a weighted sum of relevance, importance, an exponential recency decay, and a redundancy penalty against already-selected items, adding items greedily until a token budget is reached; the redundancy term deduplicates near-identical memories at read time. Finally, an inspection interface reports which experts fired and with what scores, which items entered the pack with the contribution of each scoring term, and which items were dropped and why.

## 4. Evaluation

We compare four systems on a typed memory set under an identical token budget: classic flat retrieval (one index, dense top-k packed to budget); Matrix Context with its zero-dependency offline hashing embedder; Matrix Context with a **live router** driven by a real embedding model (`sentence-transformers`, `all-MiniLM-L6-v2`), which earns its routing decisions rather than assuming them; and the competent-gate oracle, isolated by routing each query to its correct partition to bound the achievable ceiling. The set is small and synthetic, so the results illustrate the mechanism rather than assert a leaderboard position; the competent-gate regime, however, is now **measured with a real embedder rather than simulated**.

| System | Mean gold recall | Distractors in packs | Pack tokens |
|---|---|---|---|
| Flat retrieval (classic RAG) | 100% | 42 | 613 |
| Matrix Context, offline stub gate | 79% | 39 | — |
| Matrix Context, **live router** (real embedder, measured) | 100% | 38 | — |
| Matrix Context, competent gate (oracle ceiling) | 100% | 16 | 308 |

With the offline embedder the router cannot distinguish partitions, widens its selection, inherits the distractor noise that flat retrieval carries, and gains nothing (routing accuracy 6/7). With a real embedding model the live router routes correctly on every query (7/7), reaches flat retrieval's recall while already carrying fewer distractors (38 versus 42), and the oracle bounds the ceiling — reducing distractor content from forty-two to sixteen items and approximately halving token usage. The accompanying bake-off (`experiments/`) reproduces the flip end to end: `simple_rag` wins under the hashing stub while `moc_rag` trails at 79% recall, and `moc_rag` becomes the outright winner once the real embedder is supplied (100% recall, fewest distractors and tokens). The value delivered is therefore not higher recall but equivalent answers in less context, with every choice explainable, and the entire effect is gated on embedding and routing quality. The practical implication is that a real embedding model and a routing evaluation are the first investment; the storage, transport, and adapter layers are comparatively safe and should follow proven routing rather than precede it. The full run is archived in `experiments/results/MEASURED_FINDINGS.md`.

### 4.1 Robustness benchmark

To address the objection that a keyword-aligned fixture flatters lexical retrieval, we release a larger public benchmark, the MoC-RAG Benchmark (Hugging Face dataset `ruslanmv/moc-rag-benchmark`): 1,000 typed context items and 600 queries across six agentic-memory domains, eight typed experts, and five hard-negative kinds (same-keyword/wrong-expert, true-fact/wrong-scope, superseded decision, contradictory note, stale session). Each gold fact is queried in five styles — direct, paraphrased, underspecified, cross-expert, and adversarial (the last embedding a misleading term that lexically matches the contradictory negative) — and the same test topics are phrased into parallel `keyword`, `paraphrased`, and `adversarial` splits so a score change is attributable to query style, not topic leakage. Methods compared: BM25, dense, hybrid, metadata-filtered, and reranked RAG, and MoC-RAG with a hybrid router (centroid + keyword + type + scope + activity priors) at `top_experts ∈ {1,2,3,all}`.

Measured with `sentence-transformers/all-MiniLM-L6-v2`, BM25 recall falls from 100% on keyword queries to 64% on adversarial queries (−36 points), whereas MoC-RAG holds within ~17 points (96%→79%) and overtakes BM25 on the adversarial split by ~15 points, while carrying roughly half the hard distractors of the dense/hybrid/metadata/reranked baselines (48–62 versus 91–103) at 95–100% routing accuracy. The benchmark thus supports the stronger and more defensible claim: routed typed context is markedly more robust than flat retrieval when context is typed, distractor-heavy, and lexical matching is unreliable. The same flip is visible offline with the hashing embedder, indicating the gain is driven by the typed-routing priors rather than embedding quality alone. Reference runs are archived in `benchmarks/moc_rag_benchmark/results/`.

## 5. Related work

The routing thesis is developed in the author's essay *From Mixture of Experts to Mixture of Agents*. The query-routed retrieval direction is supported by recent work on mixture-of-document-experts routing, retrieval-gating mixtures of experts, and mixture-of-experts graph retrieval. The contemporary agent-memory landscape — covering personalization, temporal knowledge graphs, operating-system-style memory management, and graph reasoning over private corpora — reflects the state of the field in early 2026, against which Matrix Context positions itself not by benchmark supremacy but by combining a local-first default, typed and inspectable routing, and native fit within a single agent ecosystem.

## 6. Availability and reproducibility

Version 0.1.0 implements the engine, a Python SDK, a command-line interface, a SQLite store, and the evaluation harness, distributed under Apache-2.0. The benchmark in Section 4 is reproduced by installing the package and running the harness:

```bash
git clone https://github.com/agent-matrix/matrix-context
cd matrix-context && pip install -e ".[dev]"
python -m eval.harness
```

The MCP server, REST surface, governance plane, memory lifecycle, Postgres and Milvus backends, and framework adapters are provided as documented scaffolds and are staged for subsequent versions.

## 7. Limitations

The benchmark is synthetic; although the competent-gate result is now measured with a real embedding model, the immediate next step is to rerun the comparison on an established long-horizon memory benchmark and against a small generator's answer quality, growing the synthetic fixture toward live gold signal (the HomePilot adapter is the path to it). Memory lifecycle — maintaining cleanliness and consistency as facts accumulate and contradict over time — is the hardest part of the category and is deferred to a subsequent version, to be designed against the same evaluation rather than by intuition. The router is presently a heuristic gate; a learned router is warranted only once logged acceptance data exists. The strongest external validation will come from integration into a working assistant rather than from a synthetic set.

## How to cite

Magana Vsevolodovna, R. (2026). *Matrix Context: A Local-First, Inspectable Mixture-of-Contexts Layer for Agent Memory* (Version 0.1.0) [Software and manuscript]. Zenodo. DOI: _[minted on deposit]_.

A machine-readable citation is provided in `CITATION.cff` in the repository.
