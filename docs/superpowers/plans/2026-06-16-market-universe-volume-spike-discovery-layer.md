# Market Universe Volume Spike Discovery Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit-local-JSON-or-CSV-only pure market discovery scanner that produces deterministic advisory candidates.

**Architecture:** Keep strict normalized fixture/result models, CSV/JSON loading, and fixed discovery scoring in new pure modules without persistence or strategy/order integration. A local-file service and CLI coordinate exact input/output while system smoke verifies offline discovery.

**Tech Stack:** Python 3.11, Pydantic, argparse, csv, pytest

---

### Task 1: Strict Fixture Models And Loaders

**Files:**
- Create: `src/stock_risk_mcp/market_discovery_models.py`
- Create: `src/stock_risk_mcp/market_discovery_fixture.py`
- Create: `tests/test_market_discovery_fixture.py`

- [ ] Write failing tests for strict JSON/CSV schemas, exact headers, repeated
  CSV config, timezone-aware timestamps, as-of boundaries, duplicate tickers,
  finite numerics, positive baselines, and exact-file loading.
- [ ] Run focused tests and confirm missing modules fail.
- [ ] Implement strict normalized models and exact-path JSON/CSV loading.
- [ ] Run focused tests and confirm they pass.

### Task 2: Deterministic Discovery Scoring And Service

**Files:**
- Create: `src/stock_risk_mcp/market_discovery_scoring.py`
- Create: `src/stock_risk_mcp/market_discovery_service.py`
- Create: `tests/test_market_discovery_scoring.py`
- Create: `tests/test_market_discovery_safety.py`

- [ ] Write failing tests for evidence calculations, fixed component scoring,
  hard filters, `DISCOVER`/`WATCH`/`EXCLUDE`, stable ranking, candidate limit,
  JSON/CSV equivalence, result output, and forbidden dependencies.
- [ ] Run focused tests and confirm missing scoring/service modules fail.
- [ ] Implement pure scoring and exact local result JSON read/write.
- [ ] Run focused scoring and safety tests and confirm they pass.

### Task 3: CLI And Offline System Smoke

**Files:**
- Modify: `src/stock_risk_mcp/cli.py`
- Modify: `src/stock_risk_mcp/system_smoke.py`
- Create: `tests/test_market_discovery_cli.py`
- Modify: `tests/test_system_smoke.py`

- [ ] Write failing tests for run/show commands, optional output, JSON-safe
  errors, strict result validation, and offline system-smoke discovery.
- [ ] Run focused tests and confirm commands and smoke check fail.
- [ ] Add CLI dispatch and temporary local JSON discovery fixture smoke run.
- [ ] Run focused CLI and smoke tests and confirm they pass.

### Task 4: Documentation, Full Validation, And Commit

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document strict fixture contracts, fixed scoring/classification/ranking,
  commands, advisory-only boundary, and explicit exclusions.
- [ ] Run `python3.11 -m pytest -q`.
- [ ] Run `python3.11 -m compileall -q src`.
- [ ] Run `git diff --check`.
- [ ] Run `python3.11 -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`.
- [ ] Confirm completed offline smoke and clean staged scope.
- [ ] Commit with `Add market universe volume spike discovery`.
- [ ] Do not create a v3.3 tag.
