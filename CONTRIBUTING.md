# Contributing

```bash
pip install -e ".[dev]"
ruff check src eval tests
mypy src
pytest -q
python -m eval.harness
```

Stage discipline: build `[MVP]` first (engine, real embedder, eval, HomePilot
bridge). `[v1]` wraps the proven engine. `[v2]` is scale. Don't promote a stub
to real until the eval harness shows it helps.
