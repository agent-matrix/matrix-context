# Matrix Context — developer tasks.  Quickstart: `make install && make test`
PYTHON ?= python

.PHONY: install test e2e lint conformance badges eval benchmark paper check serve ui clean

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest -q

e2e:
	$(PYTHON) -m pytest tests/e2e -q

lint:
	$(PYTHON) -m ruff check src eval tests moc_contract && $(PYTHON) -m mypy src

conformance:
	$(PYTHON) -m moc_contract.conformance

badges:
	$(PYTHON) -m moc_contract.badges

eval:
	$(PYTHON) -m eval.harness

benchmark:
	$(PYTHON) -m benchmarks.moc_rag_benchmark.run build
	$(PYTHON) -m benchmarks.moc_rag_benchmark.run compare --embedder hashing --groundedness

paper:
	$(MAKE) -C docs/paper/latex all

# Everything CI runs, locally.
check: lint test eval conformance

serve:
	matrix-context serve --transport rest --port 8088

ui: serve   # the Context Inspector UI is served at http://127.0.0.1:8088/

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache .mypy_cache *.db
