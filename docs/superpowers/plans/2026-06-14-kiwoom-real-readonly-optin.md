# Kiwoom Real-Network Read-only Opt-in Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a separate explicit opt-in Kiwoom MOCK-host read-only network boundary with controlled credentials, token flow, and redacted audits.

**Architecture:** Strict config and credential models guard a manifest-backed real transport. A separate service and CLI persist redacted audits while existing fake and mock runtime paths remain unchanged.

**Tech Stack:** Python, Pydantic, urllib, SQLite, argparse, pytest

---

### Task 1: Config And Credential Loading

**Files:**
- Create: `src/stock_risk_mcp/kiwoom_real_readonly_models.py`
- Create: `src/stock_risk_mcp/kiwoom_credentials.py`
- Test: `tests/test_kiwoom_real_readonly_models.py`
- Test: `tests/test_kiwoom_credentials.py`

- [ ] Write failing tests for disabled defaults, exact MOCK host, masked credentials, explicit ENV/file loading, and missing-file JSON-safe errors.
- [ ] Verify RED.
- [ ] Implement strict config/models and explicit loaders without discovery.
- [ ] Verify GREEN.

### Task 2: Token Provider And Real Transport

**Files:**
- Create: `src/stock_risk_mcp/kiwoom_token_provider.py`
- Create: `src/stock_risk_mcp/kiwoom_real_readonly_transport.py`
- Test: `tests/test_kiwoom_token_provider.py`
- Test: `tests/test_kiwoom_real_readonly_transport.py`

- [ ] Write failing tests for fake token, controlled AUTH, disabled network, endpoint classification, exact host, websocket block, request limit, timeout, and redaction.
- [ ] Verify RED.
- [ ] Implement fake/real token providers and injectable stdlib transport.
- [ ] Verify GREEN.

### Task 3: Redacted Audit And Service

**Files:**
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Create: `src/stock_risk_mcp/kiwoom_real_readonly_service.py`
- Test: `tests/test_kiwoom_real_readonly_repository.py`
- Test: `tests/test_kiwoom_real_readonly_service.py`

- [ ] Write failing tests for append-only redacted audits and offline/opt-in service behavior with fake client.
- [ ] Verify RED.
- [ ] Add tables, repository helpers, and service.
- [ ] Verify no secret/token/header value is persisted.
- [ ] Verify GREEN.

### Task 4: Separate CLI And Safety

**Files:**
- Modify: `src/stock_risk_mcp/cli.py`
- Create: `tests/test_kiwoom_real_readonly_cli.py`
- Create: `tests/test_kiwoom_real_readonly_safety.py`

- [ ] Write failing tests for default-disabled health and six separate read-only commands using injected/offline behavior.
- [ ] Verify RED.
- [ ] Add real-readonly parsers and routing without changing v2.11 fake commands.
- [ ] Verify safety prohibitions and GREEN.

### Task 5: Documentation, Regression, Verification

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document opt-in, credential/redaction policy, exact MOCK host, and runtime separation.
- [ ] Run v2.11-v2.14, broker/order/realtime/provider-pack regressions.
- [ ] Run `pytest -q`.
- [ ] Run `python -m compileall -q src`.
- [ ] Run `git diff --check`.
- [ ] Run system-smoke and confirm `COMPLETED` plus `external_network_calls=false`.
- [ ] Commit with `git commit -m "Add Kiwoom real-network read-only opt-in adapter"`.
- [ ] Report without creating a v2.14 tag.
