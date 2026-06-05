# Matrix Context — frontend (control plane / admin UI)

The **single source of truth** for the web UI. A self-contained, zero-dependency
operator console (Overview · Inspector · Ingest · Memory · Experts · Routing ·
Benchmarks · MoC Contract · Settings) wired to the live **MoC Contract v1** API.
Used both for native/local runs and as the app inside the Hugging Face Space
(`../hf/`, which builds from this folder — the UI is not duplicated).

```
frontend/
├── server.py        # launcher: serves app/ + the live /v1 API (reuses the backend), seeds demo data
└── app/             # the SPA (no React/Babel/CDN for logic; fonts from Google Fonts)
    ├── index.html   # shell + matrix-rain canvas
    ├── styles.css   # emerald-glass theme
    ├── api.js       # live /v1 adapter (maps backend shapes for the UI)
    ├── app.js       # the views
    └── assets/      # logo
```

## Run (native / local)

```bash
pip install -e ".[dev]"            # from the repo root
python frontend/server.py         # -> http://127.0.0.1:7860
```

Environment: `HOST` (default `127.0.0.1`), `PORT` (default `7860`),
`MATRIX_CONTEXT_PATH` (default `:memory:`).

## Hugging Face

The Space packaging (Dockerfile + card + deploy) lives in [`../hf/`](../hf) and
builds from this folder. Deploy with `python hf/deploy.py --repo <user>/<space>`.

## How it talks to the backend

The UI calls the same-origin `/v1` surface; the Ingest wizard runs in Compatible
Mode (client-side chunking → `POST /v1/remember`, metadata stored as tags). It is
additive — `server.py` imports the published backend and serves the existing
`dispatch`; nothing in the engine is modified.
