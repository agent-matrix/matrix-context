# matrix-context — Full Project Tree

Canonical repo `agent-matrix/matrix-context` · dist `matrix-context` · import `matrix_context` · CLI `matrix-context`.

Stage tags drive build order, and they follow the feasibility finding: the router + embedder + eval are the make-or-break path, so they are `[MVP]`. Everything that wraps a proven engine is `[v1]`. Scale and learned components are `[v2]`.

```text
matrix-context/
├── README.md                          # what it is, quickstart, the one-line pitch
├── LICENSE                            # Apache-2.0
├── CHANGELOG.md
├── CONTRIBUTING.md
├── pyproject.toml                     # [MVP] hatchling, extras: embeddings/mcp/postgres/milvus/all
├── llms.txt                           # ecosystem discoverability (matches your other repos)
├── .gitignore
├── .pre-commit-config.yaml            # ruff + mypy gate
├── Makefile                           # install / test / lint / eval / serve shortcuts
│
├── src/
│   └── matrix_context/
│       ├── __init__.py                # [MVP] public API exports + __version__
│       ├── config.py                  # [MVP] env/file config model (backend, paths, weights)
│       ├── manager.py                 # [MVP] ContextManager facade — wires the whole engine
│       │
│       ├── schema/                    # the typed data model
│       │   ├── __init__.py
│       │   ├── item.py                # [MVP] ContextItem (lean 10-field MVP; full fields in v1)
│       │   ├── pack.py                # [MVP] ContextPack / PackedItem
│       │   ├── query.py               # [MVP] RecallQuery
│       │   └── enums.py               # [MVP] experts, scopes, sensitivity, approval_state
│       │
│       ├── embedding/                 # the seam the whole payoff depends on
│       │   ├── __init__.py
│       │   ├── base.py                # [MVP] Embedder protocol + cosine
│       │   ├── hashing.py             # [MVP] zero-download offline stub (default, local-first)
│       │   ├── sentence_transformers.py  # [MVP] real semantic embedder (the regime that wins)
│       │   ├── watsonx.py             # [v1] watsonx.ai embedding client
│       │   └── ollama.py              # [v1] local Ollama embeddings
│       │
│       ├── store/                     # SQL = governance plane; vectors = accelerator
│       │   ├── __init__.py
│       │   ├── base.py                # [MVP] Store protocol (add/get/candidates/all_items)
│       │   ├── sqlite.py              # [MVP] default local backend (+ FTS5 in v1)
│       │   ├── postgres.py            # [v1] Postgres + pgvector + row-level security
│       │   └── milvus.py              # [v2] optional high-scale vector accelerator
│       │
│       ├── retrieval/                 # hybrid lexical + dense + fusion
│       │   ├── __init__.py
│       │   ├── lexical.py             # [MVP] BM25 (pure-py now; FTS5/pg text-search in v1)
│       │   ├── dense.py               # [MVP] vector similarity ranking
│       │   ├── fusion.py              # [MVP] reciprocal rank fusion
│       │   └── rerank.py              # [v1] optional cross-encoder reranker
│       │
│       ├── routing/                   # the centerpiece — MODE/ExpertRAG-style routing
│       │   ├── __init__.py
│       │   ├── router.py              # [MVP] two-tier router + RoutingDecision
│       │   ├── experts.py             # [MVP] expert taxonomy + descriptions + centroids
│       │   ├── rules.py               # [MVP] deterministic keyword/metadata rules
│       │   ├── llm_gate.py            # [v1] LLM classifier for the ambiguous fallback
│       │   └── learned.py             # [v2] router trained on logged acceptance signals
│       │
│       ├── context/                   # pack assembly + scoring
│       │   ├── __init__.py
│       │   ├── assembler.py           # [MVP] budgeted knapsack: relevance/importance/recency/MMR
│       │   └── compress.py            # [v1] summarize/compress to fit tighter budgets
│       │
│       ├── lifecycle/                 # the moat — keeps memory good over months
│       │   ├── __init__.py
│       │   ├── dedup.py               # [v1] write-time near-duplicate detection
│       │   ├── contradiction.py       # [v1] supersede stale facts (light validity window)
│       │   ├── consolidation.py       # [v1] summarize stale low-importance items
│       │   └── decay.py               # [MVP] TTL + recency decay (Basic vs Adaptive engines)
│       │
│       ├── governance/                # first-class axis, not post-processing
│       │   ├── __init__.py
│       │   ├── identity.py            # [v1] tenant/scope resolution
│       │   ├── policy.py              # [v1] read/write policy enforcement
│       │   ├── approval.py            # [v1] transient / candidate / approved writes
│       │   ├── redaction.py           # [v1] PII redaction before embedding
│       │   └── audit.py               # [v1] append-only audit events
│       │
│       ├── ingest/                    # raw input -> typed items
│       │   ├── __init__.py
│       │   ├── normalize.py           # [v1] messages/files/records -> common shape
│       │   ├── chunk.py               # [v1] document chunking
│       │   ├── extract.py             # [v1] fact/entity extraction
│       │   └── files.py               # [MVP] basic file ingestion (pdf/txt/md)
│       │
│       ├── serve/                     # the interoperability surfaces
│       │   ├── __init__.py
│       │   ├── mcp/                   # the strategic differentiator
│       │   │   ├── __init__.py
│       │   │   ├── server.py          # [v1] MCP server entry (after engine is proven)
│       │   │   ├── tools.py           # [v1] remember/recall/pack/forget/approve/router.explain
│       │   │   ├── resources.py       # [v1] URI-addressable scope/item/audit views
│       │   │   ├── prompts.py         # [v1] compose_context_pack / propose_memory_write
│       │   │   └── transports.py      # [v1] stdio + Streamable HTTP
│       │   └── rest/
│       │       ├── __init__.py
│       │       ├── app.py             # [v1] FastAPI app
│       │       ├── routes.py          # [v1] /v1/context/* endpoints (mirror the SDK)
│       │       └── auth.py            # [v1] OAuth 2.1 / PKCE, audience validation
│       │
│       ├── adapters/                  # meet each framework where it already is
│       │   ├── __init__.py
│       │   ├── crewai.py              # [v1] MCP tool server + Memory-semantics mapping
│       │   ├── langgraph.py           # [v1] store adapter (thread->session, ns->semantic)
│       │   ├── react.py               # [v1] minimal recall/pack/remember tools
│       │   ├── homepilot.py           # [MVP] first consumer — turns synthetic eval into live signal
│       │   └── agent_generator.py     # [v1] --context-provider matrix-context templates
│       │
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py                # [MVP] entry point (matrix-context ...)
│       │   └── commands.py            # [MVP] init/remember/recall/pack/ingest/serve/approve/audit
│       │
│       └── utils/
│           ├── __init__.py
│           ├── ids.py                 # [MVP] id generation
│           └── tokens.py              # [MVP] token estimation
│
├── eval/                              # FIRST-CLASS — the instrument that decides product viability
│   ├── harness.py                     # [MVP] route/recall/pack vs flat-RAG, three regimes
│   ├── datasets/
│   │   ├── synthetic_typed.jsonl      # [MVP] the seeded set (ships now)
│   │   └── homepilot_gold.jsonl       # [MVP] live gold from the first integration
│   ├── baselines.py                   # [MVP] flat dense top-k comparator
│   ├── metrics.py                     # [MVP] recall@budget, distractor rate, tokens, routing acc
│   └── report.py                      # [MVP] renders the comparison table
│
├── tests/                            # the report's four QA layers
│   ├── unit/                          # [MVP] schema, retrieval, router, assembler
│   ├── integration/                   # [v1] end-to-end manager flows per backend
│   ├── conformance/                   # [v1] MCP tools/list, resources/read, prompts/get
│   ├── governance/                    # [v1] redaction, approval-bypass, scope-escape
│   └── performance/                   # [v1] p95 recall/pack latency, ingest throughput
│
├── docs/                              # MkDocs (matches your blog/workshop tooling)
│   ├── index.md
│   ├── quickstart.md
│   ├── architecture.md                # four planes, expert taxonomy, scoring contract
│   ├── routing.md
│   ├── mcp.md
│   ├── governance.md
│   └── adapters/
│       ├── crewai.md
│       ├── langgraph.md
│       └── homepilot.md
│
├── deploy/
│   ├── Dockerfile                     # [v1]
│   ├── docker-compose.yml             # [v1] HTTP + Postgres (+ optional Milvus sidecar)
│   ├── compose.milvus.yml             # [v2]
│   └── helm/                          # [v2] chart for k8s
│       ├── Chart.yaml
│       └── values.yaml
│
├── examples/
│   ├── quickstart.py                  # [MVP] library usage
│   ├── mcp_client.json                # [v1] MCP server config snippet
│   ├── crewai_crew.py                 # [v1]
│   └── langgraph_app.py               # [v1]
│
└── .github/
    └── workflows/
        ├── ci.yml                     # [MVP] ruff + mypy + pytest + run eval/harness.py
        └── publish.yml                # [v1] build + publish to PyPI on tag
```

## How the existing reference core maps in

The 8 modules already built and benchmarked map directly into `src/matrix_context/`: `schema.py → schema/item.py`, `embedding.py → embedding/{base,hashing}.py`, `store.py → store/sqlite.py`, `retrieval.py → retrieval/{lexical,dense,fusion}.py`, `router.py → routing/{router,experts}.py`, `pack.py → context/assembler.py`, `manager.py → manager.py`, and `eval_moc.py → eval/harness.py`. Nothing is thrown away; the flat MVP becomes the spine of the src-layout.

## Reading the tree as a build order

Build every `[MVP]` node first — that is the engine, the real embedder, the HomePilot bridge, and the eval harness, and it is the only work that retires the product's central risk. Add `[v1]` once the eval turns green with a real model: MCP and REST surfaces, governance, lifecycle, Postgres, and the framework adapters. Leave `[v2]` for scale: Milvus, the learned router, Helm. The discipline the report calls for — package-first, router-first, SQL metadata first, vector backend optional, graph optional, UI deferred — is encoded in the tags, so following the tree top-to-MVP-first is following the plan.
