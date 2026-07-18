# Sexta-Feira OS — dev shortcuts. Run from the repo root.
# The kernel lives in backend-core/; most targets operate there.

VENV := backend-core/.venv
# Cross-platform venv paths: Linux/Mac uses bin/, Windows uses Scripts/
ifeq ($(OS),Windows_NT)
  PY := $(VENV)/Scripts/python
  PIP := $(VENV)/Scripts/pip
else
  PY := $(VENV)/bin/python
  PIP := $(VENV)/bin/pip
endif

.PHONY: help setup install run test lint fmt migrate revision brain clean

help:
	@echo "Sexta-Feira OS — comandos:"
	@echo "  make setup     - cria venv, instala deps, prepara .env"
	@echo "  make run       - sobe o kernel (http://127.0.0.1:8000)"
	@echo "  make test      - roda a suite de testes"
	@echo "  make lint      - ruff check"
	@echo "  make fmt       - ruff format + autofix"
	@echo "  make migrate   - aplica migrações do banco (alembic upgrade head)"
	@echo "  make revision m=\"msg\" - cria nova migração autogerada"
	@echo "  make brain     - baixa os modelos locais no Ollama"

setup:
	cd backend-core && python3 -m venv .venv && $(PIP) install -q -U pip -r requirements.txt ruff
	@test -f .env || cp .env.template .env
	@echo "OK. Edite .env (OWNER_*/DEVICE_PAIRING_CODE) e rode: make brain && make run"

install:
	$(PIP) install -q -U pip -r backend-core/requirements.txt ruff

run:
	cd backend-core && ./.venv/bin/python -m app.main

test:
	cd backend-core && ./.venv/bin/python -m pytest

lint:
	cd backend-core && ./.venv/bin/ruff check app tests

fmt:
	cd backend-core && ./.venv/bin/ruff check --fix app tests && ./.venv/bin/ruff format app tests

migrate:
	cd backend-core && ./.venv/bin/alembic upgrade head

revision:
	cd backend-core && ./.venv/bin/alembic revision --autogenerate -m "$(m)"

brain:
	ollama pull llama3.2 && ollama pull nomic-embed-text

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend-core/.pytest_cache backend-core/.ruff_cache
