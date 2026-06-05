# Changelog

## [0.1.0] — 2026-06-04
### Added
- **Control plane / admin UI** (`frontend/`, single source of truth): a
  self-contained console (Overview · Inspector · Ingest · Memory · Experts ·
  Routing · Benchmarks · MoC Contract · Settings) in the emerald-glass MatrixHub
  aesthetic. `frontend/server.py` serves the wired UI **and** the live `/v1` API
  by reusing the backend's dispatch, and seeds a demo memory set. Additive —
  imports the package, modifies nothing; the Cloud tab is omitted (pre-launch).
- **Hugging Face Space packaging** (`hf/`): a best-practice Docker `Dockerfile`
  (slim, non-root, healthcheck) + Space card + `deploy.py` that builds the Space
  from `frontend/` + `src/` (no UI duplication). Published at
  `huggingface.co/spaces/ruslanmv/matrix-context-console`. CI workflow
  `deploy-hf-space.yml` publishes on push when the `HF_TOKEN` secret is set.
- **Chatbot guide** (`docs/CHATBOT_GUIDE.md`): build a memory-backed chatbot via
  the SDK or REST (`build_pack` before each turn, `remember` after), with
  Anthropic/Ollama examples and production tips (scopes, importance, TTL, inspect).
- **Context Console (Phase 0)**: a same-origin, zero-dependency operator console
  served at `/console` (Overview · Ingest wizard · Memory · Inspector · Experts).
  A live `console/api.js` adapter drives the real `/v1` API in Compatible Mode
  (client-side chunking → `POST /v1/remember`, metadata encoded as tags); it maps
  the response shapes (`remember.item`, `inspect.routing/.pack`,
  `version.contract_version`, string scopes). Additive only — existing `/`,
  `/ui`, `/inspector`, `/v1/*` routes and the frozen MoC Contract v1 are
  unchanged. See `docs/CONSOLE_INTEGRATION.md`.
- **End-to-end workflow test** (`tests/e2e/test_workflow.py`): one happy-path
  walk through the product spine — SDK (remember → build_pack → inspect), the
  REST server over real HTTP (full v1 contract + the Inspector UI), MoC Contract
  v1 conformance, and the agent-generator/HomePilot adapters. `make install &&
  make test`. The Makefile gained `e2e`, `conformance`, `badges`, `benchmark`,
  `paper`, and `check` targets.
- **Context Inspector UI**: a single-file, dependency-free web inspector served
  by the REST server at `/` (and `/ui`). Run a query and see selected vs.
  unselected experts, routing scores, kept items with score breakdowns, dropped
  items with reasons, and the final prompt-ready pack. `matrix-context serve
  --transport rest` → open `http://127.0.0.1:8088/`.
- **Release-candidate hardening**: README 5-minute quickstart, a benchmark smoke
  step in CI, and `docs/RELEASE_CANDIDATE.md` (the RC checklist; DOI deferred
  until manuscript review).
- **Conformance badges** (`python -m moc_contract.badges`): generates
  self-contained SVG badges + `status.json` for `MoC API v1`, `MoC Inspect v1`,
  and `MoC MCP v1` from ground truth (reference passes API + Inspect; MCP is
  `pending` until a conformant MCP server ships). README displays them.
- **Benchmark published** to `huggingface.co/datasets/ruslanmv/moc-rag-benchmark`
  (private): dataset card with usage + DOI-ready citation, splits, and result
  artifacts for BM25/dense/hybrid/metadata/reranked RAG and MoC-RAG.
- **`paper` CI workflow**: on LaTeX/result changes, regenerates figures/tables
  and compiles the manuscript, uploading the PDF as a build artifact.
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
