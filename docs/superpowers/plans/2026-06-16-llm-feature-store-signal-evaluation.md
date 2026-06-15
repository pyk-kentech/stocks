# LLM Feature Store Signal Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit-local-JSON-only LLM feature store and deterministic future-outcome evaluation layer.

**Architecture:** New pure models, fixture loaders, and evaluator consume only validated signal and outcome fixtures. A service layer coordinates exact local JSON output and optional append-only SQLite audit; CLI and system smoke remain offline and advisory-only.

**Tech Stack:** Python 3.11, Pydantic, SQLite, argparse, pytest

---

### Task 1: Strict Signal And Outcome Fixtures

**Files:**
- Create: `src/stock_risk_mcp/llm_feature_models.py`
- Create: `src/stock_risk_mcp/llm_feature_fixture.py`
- Create: `tests/test_llm_feature_fixture.py`

- [ ] Write failing tests for strict schemas, timestamps, versions, normalized
  lists, duplicate keys, false safety flags, safe runtime metadata, outcome
  consistency, and lookahead rejection.
- [ ] Run focused tests and confirm missing modules fail.
- [ ] Implement strict models and exact local JSON loaders.
- [ ] Run focused fixture tests and confirm they pass.

### Task 2: Pure Feature Store And Signal Evaluation

**Files:**
- Create: `src/stock_risk_mcp/llm_signal_evaluation.py`
- Create: `tests/test_llm_signal_evaluation.py`
- Create: `tests/test_llm_feature_safety.py`

- [ ] Write failing tests for feature-store output, 1D/3D/5D evaluations,
  confidence/risk buckets, directional outcomes, missing data, positive
  baseline, spillover, version metrics, minimum samples, and forbidden core
  dependencies.
- [ ] Run focused tests and confirm missing evaluator fails.
- [ ] Implement deterministic evaluation and aggregate reporting.
- [ ] Run focused evaluator and safety tests and confirm they pass.

### Task 3: Optional Audit Service, CLI, And System Smoke

**Files:**
- Create: `src/stock_risk_mcp/llm_feature_service.py`
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Modify: `src/stock_risk_mcp/cli.py`
- Modify: `src/stock_risk_mcp/system_smoke.py`
- Create: `tests/test_llm_feature_service.py`
- Create: `tests/test_llm_feature_cli.py`
- Modify: `tests/test_system_smoke.py`

- [ ] Write failing tests for default DB-free service, optional append-only
  safe audit, CLI run/evaluate/show, JSON-safe errors, and offline smoke.
- [ ] Run focused tests and confirm missing service, commands, tables, and
  smoke checks fail.
- [ ] Implement service-layer-only persistence, CLI, and temporary local
  fixture smoke integration.
- [ ] Run focused service, CLI, and smoke tests and confirm they pass.

### Task 4: Documentation, Full Validation, And Commit

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document fixture contracts, evaluation metrics, optional audit,
  commands, and advisory-only safety boundary.
- [ ] Run `python3.11 -m pytest -q`.
- [ ] Run `python3.11 -m compileall -q src`.
- [ ] Run `git diff --check`.
- [ ] Run `python3.11 -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`.
- [ ] Confirm offline smoke and clean staged scope.
- [ ] Commit with `Add LLM feature store signal evaluation`.
- [ ] Do not create a v3.4 tag.
