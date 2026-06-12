# Replay Snapshot Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist stable replay run, candidate, trade plan, basket, and outcome snapshots for future as-of-date `FULL_POLICY_REPLAY`.

**Architecture:** Add focused replay models/converters, explicit SQLite repository methods, and a repository-backed run service. Existing-basket snapshots read persisted records; recent-trade-plan snapshots build through the current pipeline and remain snapshot-only unless `--save-basket` is explicitly requested.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite, argparse, pytest

---

### Task 1: Replay Models And Pure Snapshot Conversion

**Files:**
- Create: `tests/test_replay_snapshot.py`
- Create: `src/stock_risk_mcp/replay_snapshot.py`

- [ ] Add failing tests for replay enums/models and conversion from allocation, TradePlan, BasketPlan, and BasketBacktestResult.
- [ ] Run `pytest tests/test_replay_snapshot.py -q` and verify import failure.
- [ ] Implement replay models and pure conversion helpers with full model dumps in `snapshot_json`.
- [ ] Run the new tests and verify pass.

### Task 2: SQLite And Repository

**Files:**
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Extend: `tests/test_replay_snapshot.py`

- [ ] Add failing repository round-trip tests for all five replay tables and row counters.
- [ ] Run the targeted tests and verify missing-method failures.
- [ ] Add replay tables, save/get/list methods, and explicit row converters.
- [ ] Run targeted tests plus existing repository tests.

### Task 3: Replay Dataset And Existing Basket Run

**Files:**
- Create: `tests/test_replay_dataset.py`
- Create: `tests/test_replay_run.py`
- Create: `src/stock_risk_mcp/replay_dataset.py`
- Create: `src/stock_risk_mcp/replay_run.py`

- [ ] Add failing tests for loading a complete dataset and creating a replay run from an existing basket with optional outcome and preserved policy metadata.
- [ ] Run the new tests and verify failures.
- [ ] Implement dataset loader and existing-basket run creation with completed status and no-cutoff notes.
- [ ] Run new tests and existing basket/paper tests.

### Task 4: Recent Trade Plan Snapshot-Only Run

**Files:**
- Extend: `tests/test_replay_run.py`
- Modify: `src/stock_risk_mcp/replay_run.py`

- [ ] Add failing tests proving default snapshot-only behavior, replay-only basket ID, optional `--save-basket` persistence, storage notes, and optional outcome.
- [ ] Run targeted tests and verify failures.
- [ ] Implement recent trade-plan current-pipeline build, snapshot persistence, optional paper outcome, and explicit official-basket opt-in.
- [ ] Run replay run tests and existing basket tests.

### Task 5: Replay CLI

**Files:**
- Extend: `tests/test_replay_run.py`
- Modify: `src/stock_risk_mcp/cli.py`

- [ ] Add failing CLI tests for snapshot-from-basket, snapshot-from-recent-trade-plans default/`--save-basket`, replay-runs, and replay-show.
- [ ] Run CLI tests and verify parser failures.
- [ ] Add four commands and ensure recent-plan output contains `saved_to_basket_plans`.
- [ ] Run replay CLI tests and existing CLI-related tests.

### Task 6: Documentation And Verification

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document snapshot purpose, snapshot-only default, replay-only basket IDs, commands, as-of metadata limitation, leakage warning, and future `FULL_POLICY_REPLAY`.
- [ ] Run `pytest -q`.
- [ ] Run `python -m compileall -q src` and `git diff --check`.
- [ ] Review requirements line by line, commit implementation, rerun full tests, and confirm clean worktree.
