# Changelog

## [0.1.0] — 2026-06-04
### Added
- MoC-RAG engine: two-tier context router, BM25 + dense retrieval with RRF fusion,
  token-budgeted context-pack assembler with importance/recency/MMR scoring.
- `inspect()` explainability for routing and pack selection.
- SQLite local-first store, Python SDK, and CLI.
- Feasibility/impact eval harness comparing the engine to classic flat RAG.
- **Measured routing win:** with a real embedder (`sentence-transformers`,
  `all-MiniLM-L6-v2`) the bake-off makes `moc_rag` the winner (100% recall,
  fewest distractors and tokens) and the eval's live router hits 7/7 routing
  accuracy — the competent-gate result is now measured, not simulated. See
  `experiments/results/MEASURED_FINDINGS.md`. Winning config promoted into the
  engine defaults (`top_experts=2`).
- **agent-generator adapter** (`emit_template`): emits a wired Matrix Context
  memory layer (in-process SQLite client or MCP `serve --transport stdio` config),
  framework-aware for react/crewai/langgraph.
- **HomePilot adapter**: profile-pinned compact packs, Basic (TTL + cap) and
  Adaptive (decay + importance) engines, and a `live_state` v1 seam.
- `eval.harness --embedder` flag and `ContextManager.build_pack(pin_experts=...)`
  for always-injectable experts; `SqliteStore.delete`.
- **v1 REST API** (`serve/rest`, stdlib `http.server`, no web-framework dep):
  `GET /v1/{health,experts,items}` and `POST /v1/{remember,inspect,pack,forget}`.
  The centerpiece `POST /v1/inspect` returns the full explainable contract —
  routing scores, selected vs. unselected experts, kept/dropped items with score
  breakdown, and the prompt-ready pack — backed by the new
  `ContextManager.build_inspection()`. Launch with
  `matrix-context serve --transport rest` (default port 8088).
- **MoC-RAG Benchmark** (`benchmarks/moc_rag_benchmark`): a reproducible,
  Hugging-Face-ready benchmark + harness. Deterministic generator (1000 contexts,
  300 queries, 8 experts, 10 types, 6 domains, 5 hard-negative kinds,
  train/val/test); runners for BM25 / dense / hybrid / metadata-filtered /
  reranked RAG and MoC-RAG (`top_experts ∈ {1,2,3,all}`) with a **hybrid router**
  (centroid + keyword + type + scope + activity priors); retrieval +
  context-efficiency + routing + answer-quality metrics; JSON/Markdown reports;
  dataset card + Hub push script. Finding: MoC-RAG cuts packed hard distractors
  ~50% vs the dense/hybrid/metadata/reranked baselines at 95–100% routing
  accuracy (`benchmarks/moc_rag_benchmark/results/FINDINGS.md`).
- **Benchmark robustness layer**: paraphrased/adversarial query generator — each
  gold topic phrased five ways (direct/paraphrased/underspecified/cross_expert/
  adversarial) with gold held constant; parallel `test_keyword` /
  `test_paraphrased` / `test_adversarial` splits and a `compare` command that
  reports recall + hard distractors by query type. Result: BM25 drops −36% from
  keyword to adversarial while MoC-RAG overtakes it by +15 points on adversarial
  queries and carries ~half the hard distractors of dense RAG.
- **MoC Contract v1** (`moc_contract/`): a frozen, versioned public wire contract
  — 20 JSON Schema (2020-12) objects, an OpenAPI 3.1 description, an MCP mapping,
  and a SemVer compatibility policy. `CONTRACT_VERSION = "1.0.0"`. New REST
  endpoints to match the contract: `GET /v1/version`, `GET /v1/scopes`,
  `GET /v1/items/{id}`, `POST /v1/recall`, `POST /v1/router/explain`.
- **Executable conformance suite** (`python -m moc_contract.conformance`):
  implementation-agnostic shape + behaviour checks; the matrix-context reference
  server passes all 35 (`MoC API v1 Compatible`). Runs in CI and as the
  previously-skipped conformance QA layer (now real).
### Scaffolded (staged for v1/v2)
- MCP server (tools/resources/prompts), governance plane, memory lifecycle,
  Postgres/pgvector and Milvus backends.
