# Praetor. `make install` once, then the rest. Stubs print TODO(owner) until that terminal wires them.
PY ?= .venv/bin/python
.PHONY: install dev test test-fast e2e bench build up lint

install: $(PY)
$(PY):  # auto-built on first use, so fresh worktrees just work
	uv venv -p 3.11 .venv
	uv pip install -p $(PY) -e ".[dev]"

dev:  ## API with reload (T5) — UI dev server lives in apps/web (T6)
	@if [ -f apps/api/main.py ]; then $(PY) -m uvicorn apps.api.main:app --reload --port 8000; \
	else echo "TODO(T5): apps/api/main.py not built yet"; fi

test: $(PY)
	$(PY) -m pytest -q

test-fast: $(PY)  ## <30s, no network
	$(PY) -m pytest -q -m "not network and not slow"

lint: $(PY)
	$(PY) -m ruff check core apps tests

e2e: $(PY)  ## offline gate: build_twin -> personas -> attacks -> score on pat-example-01
	$(PY) scripts/e2e.py

bench:  ## numbers for README (T4/T8)
	@echo "TODO(T4): bench"

build:  ## docker image (T5)
	@if [ -f Dockerfile ]; then docker build -t praetor .; else echo "TODO(T5): Dockerfile"; fi

up:  ## run image locally (T5)
	@if [ -f Dockerfile ]; then docker run --rm -p 8000:8000 --env-file .env praetor; else echo "TODO(T5): Dockerfile"; fi
