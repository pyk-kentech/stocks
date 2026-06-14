# Kiwoom Sandbox SELL Schema Verification And Dry-Run Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an offline SELL schema verifier and fail-closed SELL dry-run audit gate while keeping actual sandbox SELL submission blocked.

**Architecture:** Model verification evidence and dry-run decisions separately from the existing sandbox order service. The verifier reads only the curated local manifest and explicit injected official evidence; the dry-run service reads persisted gate decisions and local ledger state without credentials, tokens, transport, or order submission.

**Tech Stack:** Python, Pydantic, SQLite, argparse, pytest

---

### Task 1: Verification Models And Offline Verifier

**Files:**
- Create: `src/stock_risk_mcp/kiwoom_sandbox_sell_schema.py`
- Create: `src/stock_risk_mcp/kiwoom_sandbox_sell_schema_verifier.py`
- Test: `tests/test_kiwoom_sandbox_sell_schema_verifier.py`

- [ ] Write failing tests for current `UNVERIFIED` result, missing mappings,
  unofficial assumptions, non-ORDER classes, WebSocket, PROD, and offline
  metadata.
- [ ] Run the verifier tests and confirm missing modules fail.
- [ ] Implement minimal models and pure verifier using only committed manifest
  evidence and optional explicit official evidence.
- [ ] Run verifier tests and confirm they pass.

### Task 2: SQLite Audit And Repository

**Files:**
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Test: `tests/test_kiwoom_sandbox_sell_schema_repository.py`

- [ ] Write failing tests for report, field evidence, and dry-run append-only
  safe persistence.
- [ ] Add the three v2.22 tables and repository save/get/list helpers.
- [ ] Run repository tests and confirm redacted audit records pass.

### Task 3: SELL Dry-Run Gate

**Files:**
- Create: `src/stock_risk_mcp/kiwoom_sandbox_sell_dry_run.py`
- Test: `tests/test_kiwoom_sandbox_sell_dry_run.py`

- [ ] Write failing tests for schema, SellSafety, RiskGate, SANDBOX
  ExecutionGate, LIMIT, MOCK, and current-ledger gates.
- [ ] Implement a transport-free dry-run service that always audits the
  sanitized decision and never submits an order.
- [ ] Prove actual sandbox SELL remains blocked and BUY remains unchanged.

### Task 4: CLI And Safety Tests

**Files:**
- Modify: `src/stock_risk_mcp/cli.py`
- Create: `tests/test_kiwoom_sandbox_sell_schema_cli.py`
- Create: `tests/test_kiwoom_sandbox_sell_schema_safety.py`

- [ ] Write failing tests for the four JSON CLI commands and forbidden
  credential/token/network/account/strategy dependencies.
- [ ] Add parsers and offline command dispatch.
- [ ] Run CLI and safety tests and confirm sanitized output.

### Task 5: Documentation And Release Validation

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document current `UNVERIFIED` result, no-field-guessing policy, blocked
  dry-run/actual SELL behavior, and v2.23 boundary.
- [ ] Run `pytest -q`, `python -m compileall -q src`, `git diff --check`, and
  system smoke.
- [ ] Commit with `Add sandbox SELL schema verification and dry-run gate`.
- [ ] Do not create a v2.22 tag.
