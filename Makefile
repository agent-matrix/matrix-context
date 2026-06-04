.PHONY: install test lint eval serve clean
install:
	pip install -e ".[dev]"
test:
	pytest -q
lint:
	ruff check src eval tests && mypy src
eval:
	python -m eval.harness
serve:
	matrix-context serve --transport stdio
clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache .mypy_cache *.db
