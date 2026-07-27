# Task runner for Linux/macOS/CI (Windows users: use .\tasks.ps1 instead).
PY ?= python

.PHONY: setup fmt lint type test itest check run up down seed eval help

help:
	@echo "Tasks: setup fmt lint type test itest check run up down seed eval"

setup:            ## install dev deps + git hooks
	$(PY) -m pip install -r requirements-dev.txt
	$(PY) -m pre_commit install

fmt:              ## auto-format + auto-fix
	$(PY) -m ruff format app tests
	$(PY) -m ruff check --fix app tests

lint:             ## lint (no changes) — same as CI
	$(PY) -m ruff check app tests
	$(PY) -m ruff format --check app tests

type:             ## static type check
	$(PY) -m mypy app

test:             ## fast unit tests
	$(PY) -m pytest -q -m "not integration"

itest:            ## integration tests (needs docker compose up)
	$(PY) -m pytest -q -m integration

check: lint type test  ## everything CI runs

run:              ## run the API locally
	$(PY) -m uvicorn app.api.main:app --reload

up:               ## start Neo4j + Qdrant + API
	docker compose up -d

down:
	docker compose down

seed:             ## ingest corpus into Neo4j + Qdrant
	$(PY) -m app.ingest

eval:             ## run RAGAS eval
	$(PY) -m app.eval.run_eval
