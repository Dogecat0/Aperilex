.PHONY: help install test lint format type-check security dev clean docker-up docker-down

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	poetry install
	poetry run pre-commit install

test: ## Run tests
	poetry run pytest

test-cov: ## Run tests with coverage
	poetry run pytest --cov=src --cov-report=html --cov-report=term

lint: ## Run linting
	poetry run ruff check src tests
	poetry run black --check src tests
	poetry run isort --check-only src tests

format: ## Format code
	poetry run black src tests
	poetry run isort src tests
	poetry run ruff check --fix src tests

type-check: ## Run type checking
	poetry run mypy src

security: ## Run security checks
	poetry run bandit -r src
	poetry run safety check

pre-commit: ## Run pre-commit hooks
	poetry run pre-commit run --all-files

dev: ## Start development environment
	docker-compose up -d postgres redis
	poetry run uvicorn src.presentation.api.app:app --reload --host 0.0.0.0 --port 8000

clean: ## Clean up cache and temp files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf dist
	rm -rf build

docker-up: ## Start all services with Docker
	docker-compose up -d

docker-down: ## Stop all services
	docker-compose down

docker-logs: ## View logs
	docker-compose logs -f

docker-build: ## Build Docker image
	docker-compose build

migrate: ## Run database migrations
	poetry run alembic upgrade head

migrate-new: ## Create new migration
	@read -p "Enter migration message: " msg; \
	poetry run alembic revision --autogenerate -m "$$msg"

shell: ## Start IPython shell
	poetry run ipython