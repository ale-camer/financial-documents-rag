# ============================================================
# Makefile — Financial Documents RAG System
# ============================================================
.DEFAULT_GOAL := help
PYTHON := python3
VENV := .venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy

.PHONY: help install test lint format type-check up down logs clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Create .venv and install all dependencies
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@echo "✅ Virtual environment ready. Run: source $(VENV)/bin/activate"

test: ## Run test suite with coverage
	$(PYTEST) tests/ -v

lint: ## Run ruff linter
	$(RUFF) check src/ tests/

format: ## Auto-format code with ruff
	$(RUFF) check src/ tests/ --fix
	$(RUFF) format src/ tests/

type-check: ## Run mypy type checker
	$(MYPY) src/ tests/

check: lint type-check ## Run all checks (lint + type-check)

up: ## Start PostgreSQL + pgvector via docker-compose
	docker compose up -d
	@echo "✅ PostgreSQL with pgvector running on port 5432"

down: ## Stop all docker-compose services
	docker compose down

logs: ## Tail docker-compose logs
	docker compose logs -f db

clean: ## Remove .venv, caches, and build artifacts
	rm -rf $(VENV) __pycache__ .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned up"
