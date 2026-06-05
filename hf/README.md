---
title: Matrix Context Console
emoji: 🟢
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
short_description: Inspectable, typed memory for AI agents — live control plane
---

# Matrix Context — Console (live demo)

A live, self-contained control plane / admin UI for **Matrix Context**, the
inspectable, typed memory layer for AI agents. One container serves both the
operator console (Overview · Inspector · Ingest · Memory · Experts · Routing ·
Benchmarks · MoC Contract · Settings) **and** the live **MoC Contract v1** API
under `/v1`. A small demo memory set is seeded on startup.

- Code & docs: https://github.com/agent-matrix/matrix-context
- The UI is wired to the same-origin `/v1` API; the Ingest wizard runs in
  Compatible Mode (client-side chunking → `POST /v1/remember`).

## How this Space is built

This directory (`hf/`) holds the Hugging Face packaging — the `Dockerfile`,
this card, and `deploy.py`. The deploy step assembles the build context
(`pyproject.toml` + `src/` + `frontend/`) so the image installs the backend and
serves the `frontend/` UI. The `frontend/` app is the single source of truth; it
is not duplicated here.

Reproduce locally:

```bash
docker build -f hf/Dockerfile -t matrix-context-console .
docker run -p 7860:7860 matrix-context-console   # http://127.0.0.1:7860
```
