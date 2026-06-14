# Kiwoom Sandbox/Mock Execution Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Kiwoom-shaped, deterministic local mock execution adapter behind the existing execution gates with complete SQLite audit trails.

**Architecture:** A dedicated service validates approved intents, persists generic and Kiwoom-specific audits, and calls a local-only adapter backed by an allowlisted fake transport. Existing v2.9-v2.11 behavior remains unchanged.

**Tech Stack:** Python, Pydantic, Protocol, SQLite, argparse, pytest

---

### Task 1: Models And Internal Endpoint Allowlist

**Files:**
- Create: `src/stock_risk_mcp/kiwoom_mock_execution_models.py`
- Create: `src/stock_risk_mcp/kiwoom_mock_execution_transport.py`
- Test: `tests/test_kiwoom_mock_execution_models.py`
- Test: `tests/test_kiwoom_mock_execution_transport.py`

- [ ] Write failing tests for model validation, JSON serialization, exact three endpoint pairs, deterministic submit/cancel/status, and normalized error fixtures.
- [ ] Run focused tests and verify RED.
- [ ] Implement minimal models, exact allowlist, and fake transport with no network or credential behavior.
- [ ] Run focused tests and verify GREEN.

### Task 2: Adapter

**Files:**
- Create: `src/stock_risk_mcp/kiwoom_mock_execution_adapter.py`
- Test: `tests/test_kiwoom_mock_execution_adapter.py`

- [ ] Write failing tests for health/capabilities, KR-only routing, LIMIT/STOP_LIMIT/MARKET fills, invalid input rejection, cancel, and status.
- [ ] Verify RED.
- [ ] Implement the adapter using only fake transport.
- [ ] Verify GREEN.

### Task 3: SQLite Audits And Service

**Files:**
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Create: `src/stock_risk_mcp/kiwoom_mock_execution_service.py`
- Test: `tests/test_kiwoom_mock_execution_repository.py`
- Test: `tests/test_kiwoom_mock_execution_service.py`

- [ ] Write failing tests for append-only Kiwoom audit persistence and approved/blocked/expired/duplicate submission behavior.
- [ ] Verify RED.
- [ ] Add tables, repository helpers, and service orchestration.
- [ ] Verify duplicate attempts persist requests/rejections without adapter refill.
- [ ] Verify GREEN.

### Task 4: CLI And Safety

**Files:**
- Modify: `src/stock_risk_mcp/cli.py`
- Create: `tests/test_kiwoom_mock_execution_cli.py`
- Create: `tests/test_kiwoom_mock_execution_safety.py`

- [ ] Write failing tests for six JSON CLI commands and safety prohibitions.
- [ ] Verify RED.
- [ ] Add parsers and routing without network, token, account, or live flags.
- [ ] Verify GREEN.

### Task 5: Documentation And Regression

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document deterministic behavior, duplicate audit contract, restrictions, and v2.13-v2.15 path.
- [ ] Run Kiwoom read-only, broker, order-intent, realtime, and provider-pack regressions.

### Task 6: Full Verification And Commit

- [ ] Run `pytest -q`.
- [ ] Run `python -m compileall -q src`.
- [ ] Run `git diff --check`.
- [ ] Run `python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`.
- [ ] Confirm smoke `COMPLETED` and `external_network_calls=false`.
- [ ] Confirm clean secret/network safety audit.
- [ ] Commit with `git commit -m "Add Kiwoom mock execution adapter"`.
- [ ] Report result without creating a v2.12 tag.
