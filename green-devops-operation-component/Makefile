.PHONY: help setup install dev test lint format clean run train docker-build docker-up docker-down

help:
	@echo "Green DevOps Operation Component"
	@echo "Available commands:"
	@echo "  make setup              - Setup development environment"
	@echo "  make install            - Install dependencies"
	@echo "  make dev                - Run development server"
	@echo "  make test               - Run tests"
	@echo "  make lint               - Run linters"
	@echo "  make format             - Format code"
	@echo "  make clean              - Clean cache and logs"
	@echo "  make train              - Train cold-start models"
	@echo "  make docker-build       - Build Docker image"
	@echo "  make docker-up          - Start docker-compose stack"
	@echo "  make docker-down        - Stop docker-compose stack"

setup:
	python -m venv venv
	venv/Scripts/pip install --upgrade pip
	venv/Scripts/pip install -e .[dev]
	cp .env.example .env
	@echo "Setup complete. Activate with: venv/Scripts/activate"

install:
	pip install -e .[dev]

dev:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v --cov=src --cov-report=html

lint:
	flake8 src tests --max-line-length=100
	mypy src --ignore-missing-imports

format:
	black src tests --line-length=100

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov
	rm -rf logs/*.log

train:
	python scripts/train_cold_start_models.py

docker-build:
	docker build -f infrastructure/docker/Dockerfile -t green-devops-operation:latest .

docker-up:
	docker-compose -f infrastructure/docker/docker-compose.yaml up -d

docker-down:
	docker-compose -f infrastructure/docker/docker-compose.yaml down
