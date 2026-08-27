.PHONY: help install dev lint format test coverage clean build

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	poetry install

dev:  ## Install with dev dependencies (same as install for Poetry)
	poetry install

lint:  ## Run linters (ruff + mypy)
	poetry run ruff check src/ tests/ examples/
	poetry run mypy src/indexforge --ignore-missing-imports

format:  ## Format code with black
	poetry run black src/ tests/ examples/

format-check:  ## Check formatting without making changes
	poetry run black --check --diff src/ tests/ examples/

test:  ## Run tests
	poetry run pytest tests/ -v

coverage:  ## Run tests with coverage report
	poetry run pytest tests/ -v --cov=indexforge --cov-report=term-missing --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +

build:  ## Build the package
	poetry build

lock:  ## Update poetry.lock
	poetry lock

update:  ## Update dependencies
	poetry update

shell:  ## Activate poetry shell
	poetry shell

all: format lint test  ## Run format, lint, and test
