# Broker Adapter Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a broker-neutral adapter contract, deterministic local mock broker, and append-only broker audit flow after v2.9 ExecutionGate approval.

**Architecture:** Broker models and protocol remain independent of persistence. `MockBrokerAdapter` performs deterministic local behavior only, while `BrokerAdapterService` enforces approval, routing, duplicate auditing, and persistence. Strategies never receive adapters.

**Tech Stack:** Python, Pydantic, Protocol, SQLite, argparse, pytest

---

### Task 1: Add Broker Models And Protocol

**Files:**
- Create: `src/stock_risk_mcp/broker_models.py`
- Create: `src/stock_risk_mcp/broker_adapter.py`
- Create: `tests/test_broker_models.py`

- [ ] Write failing tests for every enum, request/receipt/health ID defaults, JSON serialization, metadata preservation, and runtime protocol conformance.
- [ ] Run `pytest -q tests/test_broker_models.py` and verify RED because modules are absent.
- [ ] Implement broker enums and `StrictModel` classes with normalized ticker and JSON-safe fields.
- [ ] Implement the broker-neutral `BrokerAdapter` `Protocol`.
- [ ] Re-run the focused test and verify GREEN.

### Task 2: Add Deterministic MockBrokerAdapter

**Files:**
- Create: `src/stock_risk_mcp/mock_broker_adapter.py`
- Create: `tests/test_mock_broker_adapter.py`

- [ ] Write failing tests for LOCAL_MOCK health, submit/cancel capabilities, absence of market/account capabilities, deterministic LIMIT and STOP_LIMIT fills, MARKET rejection without `mock_fill_price`, MARKET fill with positive `mock_fill_price`, and clear invalid-request rejections.
- [ ] Run `pytest -q tests/test_mock_broker_adapter.py` and verify RED.
- [ ] Implement local-only `MockBrokerAdapter` with no repository, credential, network, or live dependency.
- [ ] Re-run the focused test and verify GREEN.

### Task 3: Add Append-Only Broker Audit Persistence

**Files:**
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Create: `tests/test_broker_repository.py`

- [ ] Write failing tests for request save/get/list filters, receipt save/get/list filters, latest request receipt, intent receipt history, successful-receipt detection, and health save/list.
- [ ] Verify RED.
- [ ] Add `broker_order_requests`, `broker_order_receipts`, and `broker_adapter_health_checks` tables through idempotent schema creation. Do not add a unique constraint on intent requests.
- [ ] Add repository imports, save/get/list/filter helpers, latest receipt lookup, intent receipt list, and successful-receipt detection.
- [ ] Re-run repository tests and verify GREEN.

### Task 4: Add BrokerAdapterService

**Files:**
- Create: `src/stock_risk_mcp/broker_adapter_service.py`
- Create: `tests/test_broker_adapter_service.py`

- [ ] Write failing tests that require an execution-approved intent and matching approved PAPER ExecutionGateDecision.
- [ ] Add failing tests that reject non-MOCK brokers and non-LOCAL_MOCK environments as normal results.
- [ ] Add failing duplicate tests proving first submission fills, second submission saves a new request, second saves REJECTED receipt, no second successful fill exists, and message contains `duplicate broker submission`.
- [ ] Verify RED.
- [ ] Implement request building from OrderIntent and `mock_fill_price` metadata override.
- [ ] Implement service health checks, approved submission, routing blocks, and request-first duplicate handling.
- [ ] Ensure duplicate handling does not call adapter submit and rejected outcomes remain JSON-safe.
- [ ] Re-run service tests and verify GREEN.

### Task 5: Add Four Broker CLI Commands

**Files:**
- Modify: `src/stock_risk_mcp/cli.py`
- Create: `tests/test_broker_cli.py`

- [ ] Write failing CLI tests for health, submit, request list, and receipt list.
- [ ] Add a CLI duplicate test proving the second result is REJECTED and contains the duplicate reason without traceback.
- [ ] Add tests for non-MOCK and non-LOCAL_MOCK JSON-safe rejection.
- [ ] Verify RED.
- [ ] Add parsers and routing for the four commands, filters, and optional `--mock-fill-price`.
- [ ] Re-run CLI tests and verify GREEN.

### Task 6: Add Safety And Regression Tests

**Files:**
- Create: `tests/test_broker_adapter_safety.py`

- [ ] Write tests proving no Kiwoom/pykiwoom/OCX/Alpaca/KIS/IBKR/Polygon import appears in new broker modules, no network library is imported, no secret path is read, strategies do not import broker adapters, and v2.9 PaperExecutor behavior remains unchanged.
- [ ] Run the new safety test plus v2.9, realtime, and provider-pack focused regressions.
- [ ] Make only minimal changes required for GREEN.

### Task 7: Document v2.10

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document the adapter boundary, strategy isolation, MockBroker capabilities, append-only duplicate audit behavior, and difference from v2.9 PaperExecutor.
- [ ] State that Kiwoom, account/balance/position reads, live orders, network, and secrets remain absent.
- [ ] Document the v2.11-v2.13 future path.
- [ ] Run `git diff --check`.

### Task 8: Full Verification And Commit

**Files:**
- Verify all changed files

- [ ] Run `pytest -q`.
- [ ] Run `python -m compileall -q src`.
- [ ] Run `git diff --check`.
- [ ] Run `python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`.
- [ ] Verify smoke is `COMPLETED` and `external_network_calls=false`.
- [ ] Confirm `api_key_kiwoom/` remains ignored and no secret file is staged.
- [ ] Commit implementation with:

```powershell
git add .
git commit -m "Add broker adapter interface"
```

- [ ] Run `git status --short` and record the final commit hash. Do not create a v2.10 tag.
