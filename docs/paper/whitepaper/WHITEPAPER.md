# Matrix Context: A Local-First, Inspectable Mixture-of-Contexts Layer for Agent Memory

**Ruslan Magana Vsevolodovna** · Agent-Matrix · ruslanmv.com
Version 0.1.0 · Apache-2.0 · `github.com/agent-matrix/matrix-context`

## Abstract

Retrieval-augmented generation has largely settled into a single pattern: embed everything into one flat index and retrieve the nearest chunks for every query. That pattern is simple, but it spends the prompt budget indiscriminately and offers no account of why a given piece of context was chosen. Matrix Context proposes a different shape, which we call Mixture-of-Contexts retrieval. Rather than retrieving from one undifferentiated store, it routes each query to the smallest useful subset of typed context partitions — session, profile, semantic, episodic, document, and policy memory — retrieves with a hybrid lexical and dense fusion inside them, and assembles the result into a token-budgeted pack scored by relevance, importance, recency and diversity. Every selection is explainable. This paper describes the design, reports an honest benchmark against classic flat retrieval, and states plainly where the approach helps and where it does not. The central empirical finding is that the architecture's advantage is real but conditional: it depends entirely on the quality of the routing signal, which in turn depends on the embedding model. With a weak embedder the approach ties flat retrieval; with a competent one it matches flat retrieval's recall while cutting distractor noise by roughly sixty percent and halving the tokens spent to do it.

## 1. The context bottleneck

A language model with no memory begins every interaction from zero. The common remedy is to store past interactions and documents in a vector index and retrieve the top matches into each prompt. This works in demonstrations and degrades in production for reasons that are by now well understood: the prompt grows, latency rises, the model loses facts buried in the middle of a long window, and sending tens of thousands of tokens of history to produce a short answer becomes expensive. The deeper problem is that a flat index treats a user's stable preference, a one-off chat aside, a compliance rule, and a paragraph from a manual as interchangeable, ranked only by surface similarity to the query. When the budget is tight, similarity alone is a poor guide to usefulness, and the system has no way to explain or audit what it chose.

## 2. From routing experts to routing memory

The idea that motivates Matrix Context is sparse routing, the same principle that lets mixture-of-experts models grow in capacity without growing proportionally in compute: present many specialists, but activate only the few that a given input needs. This thesis — that sparse routing scales from model experts upward to whole models and to agents — is the argument I developed in *From Mixture of Experts to Mixture of Agents*. Matrix Context extends it one layer further, to context itself. The memory store becomes a set of context experts, and a router selects only the relevant few per query.

Honesty about the mechanism matters here, because the name invites a misunderstanding. These context experts are not learned mixture-of-experts modules with jointly trained gates and gradient-shaped specialization. They are typed memory partitions, and the router is a retrieval-time policy rather than a trained network. The approach therefore belongs to a recognized and active line of work on query-routed retrieval — for example clustering documents into topical experts and routing by centroid, gating whether to retrieve at all, and routing across specialized retrievers — rather than to a novel learning algorithm. Positioning it this way is not a weakness; it places the contribution where it actually lies, which is in the product shape and the explainability, not in a new training objective.

## 3. Architecture

Matrix Context is organized as four planes — ingest, store, route, and serve — with a deliberate asymmetry between them: structured metadata and governance always live in SQL, while vector search is treated as an accelerator that can be swapped or omitted. This keeps a single-file local deployment viable while leaving a clear path to a multi-user server.

The unit of memory is a typed context item carrying its content, its expert partition, a hierarchical scope, an author-set importance, optional time-to-live, and an embedding. Typing the item is what allows the system to route by meaning and, in later versions, to govern by policy, rather than ranking by similarity alone.

Routing proceeds in two tiers. A fast centroid gate scores the query against each expert's running centroid, blended with a short description of that expert so the system behaves sensibly before any items exist. When the gate is confident and decisive, it selects the top experts and stops. When it is not — a low top score or a narrow margin between the leading experts — it widens its selection rather than guessing. That widening point is the exact seam where a stronger language-model classifier belongs in a later version; in the present release it is a transparent rule, so the system needs no model to run.

Inside the selected experts, retrieval combines a lexical channel and a dense channel and fuses them with reciprocal rank fusion. Rank fusion needs no score calibration between the two channels, which is precisely why it stays robust when one channel is strong and the other weak. The fused candidates then pass to the part of the system where most of the value sits and where most memory libraries simply stop: the context-pack assembler. Selecting the nearest k items is easy; packing the most useful, non-redundant set into a fixed token budget is a small optimization. Each candidate is scored as a weighted sum of its fused relevance, its importance, an exponential recency decay, and a penalty for redundancy against what has already been chosen, and items are added greedily until the budget is exhausted. The redundancy term deduplicates near-identical memories at read time without a separate pass.

Finally, the system can explain itself. An inspection call returns which experts fired and with what scores, which items entered the pack and the contribution of each scoring term, and which items were dropped and why. This is the trait that the funded incumbents structurally lack, and it is the one most likely to matter for trust and for any future governance story.

## 4. What we measured

We compared three systems on the same typed memory set under the same tight token budget. The first is classic flat retrieval: one index, dense top-k packed to the budget. The second is Matrix Context running with its zero-dependency offline embedder, a hashing vectorizer that requires no model download. The third is Matrix Context with a competent gate — the regime that a real embedding model unlocks — which we isolate by routing each query to its correct partition. The set is small and synthetic and the offline embedder is a deliberate stand-in, so these numbers illustrate the mechanism rather than claim a leaderboard position.

| System | Mean gold recall | Distractors in packs | Pack tokens |
|---|---|---|---|
| Flat retrieval (classic RAG) | 100% | 42 | 613 |
| Matrix Context, offline stub gate | 79% | 39 | — |
| Matrix Context, competent gate | 100% | 16 | 308 |

The finding is the point, and it is not flattering to the naive version. With the offline stub embedder the router cannot tell the policy partition from the session partition, so it widens, inherits the same noise that flat retrieval has, and wins nothing. The moment the gate can actually route, the same engine matches flat retrieval's recall while cutting distractor noise from forty-two items to sixteen and roughly halving the tokens it spends. In other words the product's value is not better recall but the same answers in far less context, with every choice explainable — and that entire payoff is gated on embedding and routing quality. The practical consequence is that the first investment is a real embedding model and a routing evaluation, not the surrounding plumbing. Building the storage, the transports, and the adapters before the routing is proven would be building the safe part of the system and leaving the risky part untested.

## 5. Positioning

The agent-memory category is crowded and well funded. Several mature systems already cover personalization, temporal knowledge graphs, operating-system-style memory management for long-running agents, and graph reasoning for private corpora, and the framework ecosystems ship their own scoped memory. Matrix Context does not try to outscore any of them on their own benchmarks, and a paper that claimed otherwise would not survive contact with the literature. Its defensible position is a narrower combination that those systems do not bundle together: a local-first default that runs with no model download and no network, a typed and inspectable routing layer where the reason for every retrieval is visible, and native fit inside the Agent-Matrix ecosystem so that the same context layer sits underneath generated agents, local assistants, and a control plane at once. Transparency and local-first are the wedge, not benchmark supremacy.

## 6. Implementation and availability

The 0.1.0 release implements the engine described above — the two-tier router, hybrid retrieval with rank fusion, the budgeted pack assembler, and the inspection interface — over a single-file SQLite store, with a small Python SDK, a command-line interface, and the evaluation harness that produced the numbers above. The remaining components from the architecture — the standards-compliant MCP server, a REST surface, the governance plane, the memory lifecycle of deduplication, contradiction handling and consolidation, the Postgres and Milvus backends, and the framework adapters — are present as documented scaffolds and are staged for later versions, so the repository is structurally complete without pretending that untested code works. The project is distributed under Apache-2.0 at `github.com/agent-matrix/matrix-context`, and the benchmark is reproducible with a single command.

## 7. Limitations and future work

The honest limitations are the roadmap. The benchmark is synthetic and the default embedder is a stand-in, so the next step is to rerun the comparison with a real embedding model on an established long-horizon memory benchmark, turning the competent-gate column from a simulated result into a measured one. The memory lifecycle — keeping memory clean and correct as facts accumulate and contradict one another over months — is the genuinely hard part of this category and is deferred to the next version, where it should be designed against the same evaluation harness rather than by intuition. The routing itself remains a heuristic gate; promoting it to a learned router is worthwhile only once there is logged acceptance data to train on. And the strongest external validation will not come from a synthetic set at all but from wiring the layer into a real assistant and measuring whether it recalls the right thing in use.

## Appendix: reproducing the benchmark

```bash
git clone https://github.com/agent-matrix/matrix-context
cd matrix-context && pip install -e ".[dev]"
python -m eval.harness
```

## Related work and acknowledgements

The routing thesis is developed in the author's essay *From Mixture of Experts to Mixture of Agents*. The query-routed retrieval direction draws on published work including Mixture-of-Document-Experts routing, retrieval-gating mixtures of experts, and mixture-of-experts graph retrieval. The agent-memory landscape referenced in the positioning section reflects the state of the field as surveyed in early 2026.
