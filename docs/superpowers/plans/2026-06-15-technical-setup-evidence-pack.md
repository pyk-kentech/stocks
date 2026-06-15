# Technical Setup Evidence Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit-local-JSON-only pure technical evidence pack that computes deterministic OHLCV features and advisory setup grades.

**Architecture:** Keep strict fixture/result models, indicator calculations, and setup scoring in new pure modules with no existing indicator/setup behavior changes or persistence. A local-file service and CLI coordinate exact JSON input/output while system smoke verifies offline calculation.

**Tech Stack:** Python, Pydantic, argparse, pytest

---

### Task 1: Strict Fixture And Result Models

**Files:**
- Create: `src/stock_risk_mcp/technical_evidence_models.py`
- Create: `src/stock_risk_mcp/technical_evidence_fixture.py`
- Create: `tests/test_technical_evidence_fixture.py`

- [ ] Write failing tests for strict schema, timezone-aware timestamps,
  increasing points, OHLC relationships, as-of boundary, duplicate tickers,
  and exact-file loading.
- [ ] Run focused tests and confirm missing modules fail.
- [ ] Implement strict fixture and result models plus exact-path JSON loading.
- [ ] Run focused tests and confirm they pass.

### Task 2: Pure Technical Feature Calculators

**Files:**
- Create: `src/stock_risk_mcp/macd_features.py`
- Create: `src/stock_risk_mcp/rsi_features.py`
- Create: `src/stock_risk_mcp/ma_trend_features.py`
- Create: `src/stock_risk_mcp/hma_features.py`
- Create: `src/stock_risk_mcp/atr_features.py`
- Create: `src/stock_risk_mcp/volume_features.py`
- Create: `src/stock_risk_mcp/divergence_features.py`
- Create: `tests/test_technical_feature_calculators.py`

- [ ] Write failing known-value and insufficient-data tests for every approved
  feature family.
- [ ] Run focused tests and confirm missing calculators fail.
- [ ] Implement deterministic fixed-period calculations from strict OHLCV
  points only.
- [ ] Run focused calculator tests and confirm they pass.

### Task 3: Evidence Scoring And Local Service

**Files:**
- Create: `src/stock_risk_mcp/setup_evidence_scoring.py`
- Create: `src/stock_risk_mcp/technical_evidence_service.py`
- Create: `tests/test_setup_evidence_scoring.py`
- Create: `tests/test_technical_evidence_safety.py`

- [ ] Write failing tests for taxonomy, component scores, hard blocks, grade
  thresholds/caps, deterministic result output, and forbidden dependencies.
- [ ] Run focused tests and confirm missing scoring/service modules fail.
- [ ] Implement advisory evidence scoring and exact local JSON result
  read/write without persistence or strategy/order integration.
- [ ] Run focused scoring and safety tests and confirm they pass.

### Task 4: CLI And System Smoke

**Files:**
- Modify: `src/stock_risk_mcp/cli.py`
- Modify: `src/stock_risk_mcp/system_smoke.py`
- Create: `tests/test_technical_evidence_cli.py`
- Modify: `tests/test_system_smoke.py`

- [ ] Write failing tests for run/show commands, optional output file,
  JSON-safe errors, strict result validation, and offline system smoke.
- [ ] Run focused tests and confirm commands and smoke check fail.
- [ ] Add CLI dispatch and temporary local OHLCV fixture smoke calculation.
- [ ] Run focused CLI and smoke tests and confirm they pass.

### Task 5: Documentation, Full Validation, And Commit

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document fixture, calculations, advisory grading, commands, safety
  boundary, and future exclusions.
- [ ] Run `python3.11 -m pytest -q`.
- [ ] Run `python3.11 -m compileall -q src`.
- [ ] Run `git diff --check`.
- [ ] Run `python3.11 -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`.
- [ ] Confirm completed offline smoke and clean staged scope.
- [ ] Commit with `Add technical setup evidence pack`.
- [ ] Do not create a v3.2 tag.
