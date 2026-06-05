# Matrix Context — Solution Design & Feasibility Proposal (0.1.0)

This proposal sits on top of the executive report. It does not repeat the architecture, API surface, or roadmap, all of which are sound. Its job is narrower and more useful: to define the smallest version that is actually shippable, to prove the hard core works with running code, and to name the one thing that decides whether the whole product succeeds. A working reference engine and a benchmark accompany this document; the numbers below come from running it, not from estimating it.

## What the report got right, and what it left open

The report converged on the correct shape. Package-first with an optional MCP server, typed context items, hybrid retrieval, a staged router, SQL as the governance plane with vectors as an accelerator, local-first SQLite by default, and the HomePilot dual-engine memory model — all of that is the right design and I would not change it. The framework-neutral, MCP-native, governance-aware positioning is a real wedge against Mem0, Zep, and the framework-locked memory in CrewAI and LangGraph, because none of them is naturally Agent-Matrix-native and inspectable at the same time.

What the report leaves open is the thing every memory product actually lives or dies on, and it is not the plumbing. It is whether routing to a typed subset of memory genuinely produces better context than dumping a flat index into the prompt — and if so, under what conditions. That question cannot be answered by a design document. It has to be measured. So I built the core and measured it.

## The engine is real and it is small

The accompanying `matrix_context` package is a working reference implementation of the part the report treated as the centerpiece: route, then hybrid-retrieve inside the selected experts, then assemble a token-budgeted context pack. It is roughly four hundred lines across seven modules, depends only on numpy and the standard library, runs entirely offline with no model download, and persists to a single SQLite file. It includes the two-tier router (a fast centroid gate with an ambiguity fallback that is the exact seam where a v1 LLM classifier plugs in), BM25-plus-dense retrieval fused with reciprocal rank fusion, and a context-pack assembler that scores each candidate by relevance, importance, recency decay, and a redundancy penalty before solving a greedy knapsack under the budget. It also exposes `inspect()`, which returns which experts fired with what scores and why each item won or was dropped — the explainability that the funded competitors structurally do not offer.

That the engine exists, runs, and is this small is the first feasibility result: the core is a one-to-two-week build, not a research project, and the report's twelve-to-sixteen-week estimate for a production v1 is realistic precisely because the genuinely hard piece is already de-risked here.

## The benchmark, and the finding that matters

I ran the engine against classic flat RAG on a small typed-memory set — the same memories, the same tight token budget per query — under three conditions. The result is honest rather than flattering, and the honesty is the point.

| System | Gold recall | Distractors in pack | Reading |
|---|---|---|---|
| **STUB** — MoC with the offline hashing-stub embedder, as it ships with zero dependencies | 78% | 39 | The gate cannot discriminate, so it widens and floods the pack with the same noise flat RAG has. **No win.** |
| **CMPT** — MoC with a competent gate (the regime a real embedding model unlocks) | 100% | 16 | Same answers as flat RAG, **62% fewer distractors**, and roughly **half the token spend** — once it is in the right partition it stops filling the budget with junk. |
| **FLAT** — classic RAG: one flat index, dense top-k to budget | 100% | 42 | Finds the gold, but spends the entire budget, most of it on off-partition distractors. |

The finding is this. With the naive offline embedder, Matrix Context does not beat flat RAG — it ties it at best, because a hashing vectorizer cannot tell the policy partition from the session partition, so the router widens its selection and the typing buys nothing. The moment the gate can actually route, which is what a real embedding model delivers, the same engine matches flat RAG's recall while cutting distractor noise by nearly two thirds and roughly halving the tokens it spends to do it. That is the product's value proposition, quantified: not better recall, but the *same* answers in far less context, with every selection explainable.

So the entire payoff is gated on one thing — embedding and routing quality — and nothing else on the critical path matters until that is solved. This is the most important sentence in the proposal. It means the make-or-break investment is a real embedder plus a router evaluation harness, and that the SQLite schema, the MCP transports, the CLI, the governance fields, and the framework adapters are all comparatively safe, deferrable work. Building those first would be building the safe 80% while leaving the risky 20% untested.

## The ruthless MVP cut

The report's MVP is still v1-heavy: eighteen-field items, nine experts, REST plus MCP plus SDK plus CLI, governance, redaction. For 0.1.0 I would cut harder, because the only goal of the first release is to prove the routed-pack advantage holds with a real model on real data.

Keep, because it is the thing under test: typed items (ten fields, not eighteen), six experts (not nine), the two-tier router, hybrid retrieval with RRF, the budgeted pack assembler, `inspect()`, SQLite, the Python SDK, and a real embedding model behind the existing `Embedder` seam. Add the router eval harness as a first-class deliverable, not a QA afterthought — it is the instrument that tells you whether you have a product.

Defer everything else to v1 with a clear conscience: Postgres and pgvector, the MCP server wrapper, Streamable HTTP, approval flows and redaction, the REST API, the CrewAI and LangGraph adapters, and the admin UI. The MCP wrapper is thin and strategically important for distribution, but it wraps an engine that must first be proven; wrap it the moment the eval turns green, not before. Milvus, the graph expert, and the learned router stay in v2 exactly as the report says.

## The first integration is the validation

The fastest way to make the eval real rather than synthetic is to wire 0.1.0 into HomePilot as consumer number one within the first month. HomePilot already has persistent local memory, the profile-versus-memory split, and real usage, so it supplies real queries and real gold context that the synthetic benchmark cannot. Dogfooding inside a product you control turns the abstract "does routing help" question into a concrete "did the assistant recall the right thing" signal, and it is the one validation path the funded competitors cannot copy. GitPilot and the agent-generator templates follow once the HomePilot numbers hold.

## Recommended sequence

Build the engine core and the real embedder first and prove the routed-pack advantage on a held-out set — this is the gate that everything else waits behind, roughly three to four weeks including the eval harness. Then wire it into HomePilot to replace synthetic gold with live signal, about one week. Only then add the MCP server wrapper over stdio so Claude Desktop, Cursor, and the rest of the 500-plus-server ecosystem can reach it, about a week. Postgres, governance, and the framework adapters become the back half of the report's v1 timeline, unchanged. The net is the same twelve-to-sixteen-week v1 the report proposed, reordered so the risk is retired in week four instead of week thirteen.

## The one-line product, restated to match what ships

Matrix Context is a local-first, inspectable context layer — a Python library and MCP server that routes across typed memories and assembles a token-budgeted context pack, so any agent retrieves the right context, in less of it, and you can see exactly why. The benchmark says that sentence is true the day the embedder is real, and not before.
