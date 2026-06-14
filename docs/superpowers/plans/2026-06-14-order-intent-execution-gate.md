# Order Intent / Execution Gate Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a broker-neutral, SQLite-audited OrderIntent -> RiskGate -> ExecutionGate -> PaperExecution flow with no broker or network integration.

**Architecture:** Typed order models remain structurally permissive enough to preserve blocked requests for audit. Pure gate functions return decisions, while `OrderIntentService` owns persistence and lifecycle transitions. Only deterministic PAPER execution is supported.

**Tech Stack:** Python, Pydantic, SQLite, argparse, pytest

---

### Task 1: Add Order Intent And Decision Models

**Files:**
- Create: `src/stock_risk_mcp/order_intent.py`
- Create: `tests/test_order_intent.py`

- [ ] Write failing tests that construct and serialize every enum/model, normalize ticker, default IDs/status, preserve metadata, and allow structurally invalid safety values such as missing stop loss for later audit evaluation.
- [ ] Run `pytest -q tests/test_order_intent.py` and verify collection fails because the module is absent.
- [ ] Implement `OrderSide`, `OrderType`, `ExecutionMode`, `OrderIntentStatus`, `OrderIntent`, `RiskGateDecision`, `ExecutionGateDecision`, and `PaperExecution` using `StrictModel`.
- [ ] Re-run `pytest -q tests/test_order_intent.py` and verify GREEN.

### Task 2: Add Pure RiskGate

**Files:**
- Create: `src/stock_risk_mcp/order_risk_gate.py`
- Create: `tests/test_order_risk_gate.py`

- [ ] Write failing tests for missing ticker, UNKNOWN region, invalid side input through model construction helpers, quantity/notional requirements, non-positive amounts, MARKET default block and opt-in, invalid LIMIT price, BUY stop-loss requirements, risk amount, position amount, daily loss, blocked products, blocked ticker, HOT neutrality, and BLOCKED watchlist behavior.
- [ ] Run `pytest -q tests/test_order_risk_gate.py` and verify RED.
- [ ] Implement `RiskGateConfig`, deterministic derived-value helpers, and `evaluate_risk_gate(intent, config, watchlist_entry=None)`.
- [ ] Ensure every applicable rule is accumulated in `reasons_json` and `rule_hits_json`; approval occurs only with no hits.
- [ ] Re-run `pytest -q tests/test_order_risk_gate.py` and verify GREEN.

### Task 3: Add Pure ExecutionGate And Paper Executor

**Files:**
- Create: `src/stock_risk_mcp/execution_gate.py`
- Create: `src/stock_risk_mcp/paper_execution.py`
- Create: `tests/test_execution_gate.py`
- Create: `tests/test_order_paper_execution.py`

- [ ] Write failing ExecutionGate tests for required approved risk decision, expiry, duplicate execution, PAPER approval, and unconditional SANDBOX_DISABLED/LIVE_DISABLED blocks.
- [ ] Write failing paper executor tests for deterministic explicit fill, limit-price fallback, required execution approval, non-positive fill rejection, and duplicate prevention.
- [ ] Run both test files and verify RED.
- [ ] Implement `evaluate_execution_gate(...)` with no persistence or broker dependency.
- [ ] Implement `create_paper_execution(...)` with explicit fill then limit-price fallback and no slippage.
- [ ] Re-run both test files and verify GREEN.

### Task 4: Add SQLite Audit Persistence

**Files:**
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Create: `tests/test_order_intent_repository.py`

- [ ] Write failing repository tests covering save/get/list/filter OrderIntent, status update, append-only risk and execution decisions, latest decision lookup, save/get/list PaperExecution, and duplicate detection.
- [ ] Run `pytest -q tests/test_order_intent_repository.py` and verify RED.
- [ ] Add `order_intents`, `risk_gate_decisions`, `execution_gate_decisions`, and `paper_executions` tables through idempotent schema creation. Make `paper_executions.order_intent_id` unique.
- [ ] Add repository model imports, row converters, filters, saves, gets, lists, latest-decision helpers, status update, and `has_paper_execution`.
- [ ] Re-run repository tests and verify GREEN.

### Task 5: Add OrderIntentService Lifecycle

**Files:**
- Create: `src/stock_risk_mcp/order_intent_service.py`
- Create: `tests/test_order_intent_service.py`

- [ ] Write failing service tests proving create persists CREATED, evaluation saves both decisions and transitions statuses, blocked risk skips ExecutionGate, expired/disabled modes are audited, paper execution persists and transitions, and duplicate execution remains blocked.
- [ ] Run `pytest -q tests/test_order_intent_service.py` and verify RED.
- [ ] Implement `OrderIntentService.create`, `evaluate`, `evaluate_many`, `paper_execute`, and `paper_execute_many`.
- [ ] Fetch linked watchlist entries conservatively: missing entry means no watchlist block; BLOCKED means hard block; HOT provides no approval.
- [ ] Return structured result models/dicts for CLI serialization without expected blocked outcomes raising tracebacks.
- [ ] Re-run service tests and verify GREEN.

### Task 6: Add Five CLI Commands

**Files:**
- Modify: `src/stock_risk_mcp/cli.py`
- Create: `tests/test_order_intent_cli.py`

- [ ] Write failing CLI tests for `create-order-intent`, `order-intents-list`, `evaluate-order-intents`, `paper-execute-approved-intents`, and `paper-executions-list`.
- [ ] Include tests that normal validation/blocking outcomes return JSON with reasons and no traceback.
- [ ] Run `pytest -q tests/test_order_intent_cli.py` and verify RED.
- [ ] Add parsers and command routing. Use `--allow-market-orders` as an opt-in flag, `--current-daily-loss` default `0`, repeatable `--blocked-ticker`, and requested filters.
- [ ] Ensure create catches model validation errors and returns `{"status": "FAILED", "errors": [...]}` rather than a traceback.
- [ ] Re-run CLI tests and verify GREEN.

### Task 7: Safety Regression Tests

**Files:**
- Create: `tests/test_order_intent_safety.py`

- [ ] Write tests proving no live-enable CLI option exists, no broker/network module is added, ordinary SELL is not treated as short, short metadata is blocked, HOT does not auto-approve, and no code reads `api_key_kiwoom`.
- [ ] Run `pytest -q tests/test_order_intent_safety.py tests/test_realtime_monitor.py tests/test_provider_pack_pipeline.py` and verify RED for any missing safety behavior.
- [ ] Make only the minimal production changes needed for GREEN.
- [ ] Re-run focused safety and regression tests.

### Task 8: Document v2.9

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document OrderIntent, RiskGate, ExecutionGate, PaperExecution, strategy/broker separation, PAPER-only limitation, safety defaults, five CLI commands, and the v2.10-v2.13 future path.
- [ ] State that v2.9 introduces no broker, network, account, balance, position, or secret-reading integration.
- [ ] Run `git diff --check`.

### Task 9: Full Verification And Commit

**Files:**
- Verify all changed files

- [ ] Run `pytest -q`.
- [ ] Run `python -m compileall -q src`.
- [ ] Run `git diff --check`.
- [ ] Run `python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`.
- [ ] Verify smoke status is `COMPLETED` and `external_network_calls=false`.
- [ ] Run `git status --short` and confirm only intended files are present; confirm `api_key_kiwoom/` is absent and ignored.
- [ ] Commit all implementation files with:

```powershell
git add README.md WORK_SUMMARY.md src tests
git commit -m "Add order intent and execution gate foundation"
```

- [ ] Run `git status --short` and record the final commit hash.
