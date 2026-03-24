.PHONY: setup test lint run-learn run-serve

setup:
	uv sync
	uv run python -m spacy download en_core_web_sm

test:
	uv run pytest tests/ -v --tb=short

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

run-learn:
	uv run mycelium learn --calls 50

run-serve:
	uv run mycelium serve
