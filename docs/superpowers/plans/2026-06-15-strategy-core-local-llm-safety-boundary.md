# Strategy Core And Local LLM Safety Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fixture-only deterministic strategy recommendation layer, disabled local LLM advisory boundary, auditable SQLite records, and draft-only OrderIntent conversion.

**Architecture:** Keep the strategy engine pure and dependent only on strict strategy models. Put explicit JSON fixture loading, persistence orchestration, disabled advisory review, and OrderIntent draft conversion in separate modules so source-level tests can enforce the safety boundaries.

**Tech Stack:** Python, Pydantic, SQLite, argparse, pytest

---

### Task 1: Strategy Models And Deterministic Engine

**Files:**
- Create: `src/stock_risk_mcp/strategy_core.py`
- Create: `tests/test_strategy_core.py`

- [ ] Write failing tests for strict models, deterministic BUY/SELL/WATCH,
  missing-data, high-risk, and forbidden candidate decisions.
- [ ] Run `pytest -q tests/test_strategy_core.py` and confirm the missing module
  causes failure.
- [ ] Implement the strict strategy models, protocol, reason/status enums, and
  minimal deterministic baseline engine.
- [ ] Run `pytest -q tests/test_strategy_core.py` and confirm it passes.

### Task 2: Explicit Fixture And Disabled Advisor

**Files:**
- Create: `src/stock_risk_mcp/strategy_fixture.py`
- Create: `src/stock_risk_mcp/strategy_advisor.py`
- Create: `tests/test_strategy_fixture.py`
- Create: `tests/test_strategy_advisor.py`
- Create: `tests/test_strategy_safety.py`

- [ ] Write failing tests for exact JSON-file loading, strict validation,
  broken references, disabled health, advisory-only review, and forbidden
  source dependencies.
- [ ] Run the focused tests and confirm missing modules fail.
- [ ] Implement the exact-path JSON loader and disabled advisor without DB,
  environment, credential, token, network, broker, Kiwoom, account, or order
  dependencies.
- [ ] Run the focused tests and confirm they pass.

### Task 3: SQLite Audit And Strategy Run Service

**Files:**
- Create: `src/stock_risk_mcp/strategy_service.py`
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Create: `tests/test_strategy_repository.py`
- Create: `tests/test_strategy_service.py`

- [ ] Write failing tests for the five audit tables, model round trips,
  deterministic persisted runs, disabled advisory behavior, and no reads from
  existing signal/realtime tables.
- [ ] Run the focused tests and confirm missing schema and service fail.
- [ ] Add append-only audit tables and repository methods, then implement the
  fixture-to-decision orchestration service.
- [ ] Run the focused tests and confirm they pass.

### Task 4: Draft OrderIntent Conversion

**Files:**
- Create: `src/stock_risk_mcp/strategy_order_intent_draft.py`
- Create: `tests/test_strategy_order_intent_draft.py`

- [ ] Write failing tests proving eligible BUY/SELL decisions create only
  `CREATED` drafts, SELL requires later sell-safety, and MARKET or forbidden
  exposure creates no intent.
- [ ] Run the focused tests and confirm the missing module fails.
- [ ] Implement draft conversion and persistence without gate evaluation,
  execution, broker, Kiwoom, or account-read calls.
- [ ] Run the focused tests and confirm they pass.

### Task 5: CLI And System Smoke

**Files:**
- Modify: `src/stock_risk_mcp/cli.py`
- Modify: `src/stock_risk_mcp/system_smoke.py`
- Create: `tests/test_strategy_cli.py`
- Modify: `tests/test_system_smoke.py`

- [ ] Write failing tests for all seven JSON-safe commands, strict fixture
  errors, secret-free output, disabled LLM health, and fixture-only smoke.
- [ ] Run the focused tests and confirm commands and smoke checks fail.
- [ ] Add CLI parsers and dispatch and add a temporary local fixture strategy
  smoke step while preserving `external_network_calls=false`.
- [ ] Run the focused tests and confirm they pass.

### Task 6: Documentation, Full Validation, And Commit

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document v3.0 purpose, architecture, fixture-only input, advisory-only
  LLM, draft flow, safety boundaries, commands, and future releases.
- [ ] Run `pytest -q`.
- [ ] Run `python -m compileall -q src`.
- [ ] Run `git diff --check`.
- [ ] Run `python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`.
- [ ] Confirm `COMPLETED`, `external_network_calls=false`, and no secret files
  are staged.
- [ ] Commit implementation with
  `Add strategy core and local LLM safety boundary`.
- [ ] Do not create a v3.0 tag.
