# Windows task runner (there is no `make` on stock Windows).
# Usage:  .\tasks.ps1 <task>
#   setup | fmt | lint | type | test | check | run | up | down | seed | eval
param([Parameter(Position = 0)][string]$Task = "help")

$ErrorActionPreference = "Stop"
$py = ".\venv\Scripts\python.exe"

switch ($Task) {
    "setup" { & $py -m pip install -r requirements-dev.txt; & $py -m pre_commit install }
    "fmt"   { & $py -m ruff format app tests; & $py -m ruff check --fix app tests }
    "lint"  { & $py -m ruff check app tests; & $py -m ruff format --check app tests }
    "type"  { & $py -m mypy app }
    "test"  { & $py -m pytest -q -m "not integration" }
    "itest" { & $py -m pytest -q -m integration }
    "check" { & $py -m ruff check app tests; & $py -m mypy app; & $py -m pytest -q -m "not integration" }
    "run"   { & $py -m uvicorn app.api.main:app --reload }
    "up"    { docker compose up -d }
    "down"  { docker compose down }
    "seed"  { & $py -m app.ingest }
    "eval"  { & $py -m app.eval.run_eval }
    default { Write-Host "Tasks: setup fmt lint type test itest check run up down seed eval" }
}
