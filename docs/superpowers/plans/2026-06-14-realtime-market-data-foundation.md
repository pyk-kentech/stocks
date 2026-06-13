# Realtime Market Data Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build deterministic read-only realtime monitoring, rolling intraday metrics, and a persisted dynamic Hot Watchlist.

**Architecture:** Providers emit typed market events into an in-memory symbol/region rolling calculator. A deterministic watchlist engine ranks the latest metrics, while the monitor orchestrator persists only monitor runs and current watchlist entries. Mock and local replay providers share the exact same calculation path and perform no network calls.

**Tech Stack:** Python, Pydantic, SQLite, argparse, pytest

---

### Task 1: Add Models And Universe Registry

**Files:**
- Create: `src/stock_risk_mcp/realtime_market_data.py`
- Create: `src/stock_risk_mcp/market_universe.py`
- Create: `tests/test_realtime_market_data.py`
- Create: `tests/test_market_universe.py`

- [ ] Write failing tests for enums, event normalization/validation, monitor models, watchlist models, universe dedupe, UNKNOWN rejection, and max-symbol enforcement.
- [ ] Run `pytest -q tests/test_realtime_market_data.py tests/test_market_universe.py` and verify RED.
- [ ] Implement the minimal models and registry.
- [ ] Re-run the focused tests and verify GREEN.

### Task 2: Add Deterministic Providers

**Files:**
- Create: `src/stock_risk_mcp/realtime_provider_mock.py`
- Create: `src/stock_risk_mcp/realtime_provider_replay.py`
- Create: `tests/test_realtime_provider_mock.py`
- Create: `tests/test_realtime_provider_replay.py`

- [ ] Write failing tests for deterministic mock events, replay CSV/JSON parsing, sorting, symbol/region/time filtering, and invalid-row isolation.
- [ ] Verify RED.
- [ ] Implement the provider interface, mock provider, and local replay provider without network code.
- [ ] Verify GREEN.

### Task 3: Add Rolling Metrics

**Files:**
- Create: `src/stock_risk_mcp/rolling_market_metrics.py`
- Create: `tests/test_rolling_market_metrics.py`

- [ ] Write failing tests for 1m/5m/15m returns and volumes, breakout, bad ticks, and all relative-volume contract cases.
- [ ] Include a test proving mock and replay identical events produce identical metrics.
- [ ] Verify RED.
- [ ] Implement one-minute bucket aggregation and pure rolling calculations.
- [ ] Verify GREEN.

### Task 4: Add Dynamic Watchlist

**Files:**
- Create: `src/stock_risk_mcp/dynamic_watchlist.py`
- Create: `tests/test_dynamic_watchlist.py`

- [ ] Write failing tests for each HOT rule, `relative_volume=None`, blocked bad ticks, score ordering, max HOT size, candidate, and cooling behavior.
- [ ] Verify RED.
- [ ] Implement deterministic promotion, scoring, and status transition logic.
- [ ] Verify GREEN.

### Task 5: Add Persistence

**Files:**
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Create: `tests/test_realtime_repository.py`

- [ ] Write failing repository round-trip and watchlist-upsert tests.
- [ ] Verify RED.
- [ ] Add `realtime_monitor_runs` and `watchlist_entries` tables and repository helpers.
- [ ] Verify GREEN.

### Task 6: Add Monitor Orchestration And CLI

**Files:**
- Create: `src/stock_risk_mcp/realtime_monitor.py`
- Modify: `src/stock_risk_mcp/cli.py`
- Create: `tests/test_realtime_monitor.py`

- [ ] Write failing tests for completed, partial, and failed monitor runs; max events/symbols/HOT; summary output; and four CLI commands.
- [ ] Verify RED.
- [ ] Implement monitor orchestration and CLI routing with expected-failure JSON output.
- [ ] Verify GREEN.

### Task 7: Document And Verify

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document the realtime foundation, relative-volume calculation, provider usage, CLI, no raw-tick default storage, and v2.8 no-order boundary.
- [ ] Run:

```powershell
pytest -q
python -m compileall -q src
git diff --check
python -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs
```

- [ ] Confirm system smoke is `COMPLETED` and `external_network_calls=false`.
- [ ] Commit with `Add realtime market data foundation`.
