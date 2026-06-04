# Changelog

## [0.1.0] — unreleased
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
### Scaffolded (staged for v1/v2)
- MCP server (tools/resources/prompts), REST API, governance plane, memory
  lifecycle, Postgres/pgvector and Milvus backends, framework adapters.
