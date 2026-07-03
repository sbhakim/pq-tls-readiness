# Common developer commands. Run `make help` to list them.

.DEFAULT_GOAL := help
PY := python3

.PHONY: help install install-dev lint typecheck test pilot clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

install: ## Install the package
	$(PY) -m pip install -e .

install-dev: ## Install with dev tools (pytest, ruff, mypy)
	$(PY) -m pip install -e ".[dev]"

lint: ## Static lint
	ruff check src tests

typecheck: ## Type check
	mypy src

test: ## Run unit tests
	pytest

pilot: ## Run a small pilot over 150 domains
	pqreadiness run --config config/default.yaml --limit 150

clean: ## Remove caches and build artifacts
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
