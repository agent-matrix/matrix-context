# Changelog

## [0.1.0] — unreleased
### Added
- MoC-RAG engine: two-tier context router, BM25 + dense retrieval with RRF fusion,
  token-budgeted context-pack assembler with importance/recency/MMR scoring.
- `inspect()` explainability for routing and pack selection.
- SQLite local-first store, Python SDK, and CLI.
- Feasibility/impact eval harness comparing the engine to classic flat RAG.
### Scaffolded (staged for v1/v2)
- MCP server (tools/resources/prompts), REST API, governance plane, memory
  lifecycle, Postgres/pgvector and Milvus backends, framework adapters.
