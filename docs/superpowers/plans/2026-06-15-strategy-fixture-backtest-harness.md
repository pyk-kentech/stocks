# Strategy Fixture Backtest Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit-local-JSON-only deterministic strategy backtest harness with lookahead-safe simulation, portfolio metrics, SQLite audits, and JSON CLI commands.

**Architecture:** Keep strict fixture parsing and the simulation engine independent from repository, SQLite, broker, account, order, credential, and network modules. Use a small service layer to load the exact fixture, call the pure simulator, and persist normalized append-only audit models.

**Tech Stack:** Python, Pydantic, SQLite, argparse, pytest

---

### Task 1: Strict Backtest Fixture Models And Validation

**Files:**
- Create: `src/stock_risk_mcp/strategy_backtest_fixture.py`
- Create: `tests/test_strategy_backtest_fixture.py`

- [ ] Write failing tests for schema version, required positive initial cash
  and fixed quantity, timezone-aware timestamps, snapshot references,
  feature-availability lookahead, duplicate candidate timestamps, duplicate
  price paths, and strictly increasing positive price points.
- [ ] Run `python3.11 -m pytest -q tests/test_strategy_backtest_fixture.py` and
  confirm the missing module fails.
- [ ] Implement strict exact-path JSON fixture models and cross-reference
  validation using `StrategyCandidate.snapshot_id`.
- [ ] Run the focused fixture tests and confirm they pass.

### Task 2: Pure Deterministic Backtest Engine

**Files:**
- Create: `src/stock_risk_mcp/strategy_backtest.py`
- Create: `tests/test_strategy_backtest.py`
- Create: `tests/test_strategy_backtest_safety.py`

- [ ] Write failing tests for strict-after fills, deterministic results,
  strategy decision reuse, missing future prices, MARKET/forbidden exposure
  blocks, repeated BUY, insufficient cash, SELL without position, full SELL,
  forced fixture-end exit, fixed config quantity, equity curve, total return,
  drawdown, exposure time, and forbidden source dependencies.
- [ ] Run the focused tests and confirm the missing module fails.
- [ ] Implement strict audit models and a pure cash-constrained single-long-
  position-per-ticker simulator with timestamped events and metrics.
- [ ] Run the focused engine and safety tests and confirm they pass.

### Task 3: SQLite Audit And Backtest Service

**Files:**
- Create: `src/stock_risk_mcp/strategy_backtest_service.py`
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Create: `tests/test_strategy_backtest_service.py`

- [ ] Write failing tests for exact fixture execution, fixture checksum,
  append-only run/trade/report/metric round trips, metrics duplicated in
  report JSON and metric rows, and no reads from existing market-data tables.
- [ ] Run the focused service test and confirm missing schema and service fail.
- [ ] Add four SQLite audit tables and repository methods, then implement the
  exact-file orchestration and persistence service.
- [ ] Run the focused service tests and confirm they pass.

### Task 4: CLI And System Smoke

**Files:**
- Modify: `src/stock_risk_mcp/cli.py`
- Modify: `src/stock_risk_mcp/system_smoke.py`
- Create: `tests/test_strategy_backtest_cli.py`
- Modify: `tests/test_system_smoke.py`

- [ ] Write failing tests for run/list/show commands, JSON-safe invalid
  fixture errors, secret-free output, temporary-fixture-only system smoke,
  completed report, and `external_network_calls=false`.
- [ ] Run the focused tests and confirm the commands and smoke check fail.
- [ ] Add the three CLI commands and a temporary local v3.1 fixture smoke
  check without creating OrderIntent or using external data.
- [ ] Run the focused CLI and smoke tests and confirm they pass.

### Task 5: Documentation, Full Validation, And Commit

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document v3.1 fixture schema, strict-after fills, lookahead boundary,
  trade rules, metrics, commands, safety boundaries, and future exclusions.
- [ ] Run `python3.11 -m pytest -q`.
- [ ] Run `python3.11 -m compileall -q src`.
- [ ] Run `git diff --check`.
- [ ] Run `python3.11 -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`.
- [ ] Confirm `COMPLETED`, strategy backtest smoke success,
  `external_network_calls=false`, and a clean staged scope.
- [ ] Commit implementation with `Add strategy fixture backtest harness`.
- [ ] Do not create a v3.1 tag.
