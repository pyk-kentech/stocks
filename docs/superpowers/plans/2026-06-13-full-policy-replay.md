# Full Policy Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Regenerate policy-specific TradePlans, BasketPlans, and paper outcomes from ReplayRun candidate snapshots with strict as-of and forward price boundaries.

**Architecture:** Add a local as-of price provider, typed replay/comparison results, an engine that reuses the existing policy-aware pipeline, and a comparison service. Persist final replay/comparison records while keeping intermediate TradePlans and official BasketPlans opt-in.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite, argparse, pytest

---

### Task 1: As-Of Price History Provider

**Files:**
- Create: `tests/test_asof_price_history.py`
- Create: `src/stock_risk_mcp/asof_price_history.py`

- [ ] Write failing DB and file provider tests proving `get_history_until` returns only `date <= as_of_date`, requires `min_bars`, and `get_forward_history` returns only `date > as_of_date` within the horizon.
- [ ] Run `pytest tests/test_asof_price_history.py -q` and verify the missing-module failure.
- [ ] Implement `AsOfPriceHistoryProvider` with sorted ticker-local bars and strict date filters.
- [ ] Run `pytest tests/test_asof_price_history.py -q` and verify pass.

### Task 2: Replay And Comparison Models With Persistence

**Files:**
- Create: `tests/test_policy_replay_result.py`
- Create: `src/stock_risk_mcp/policy_replay_result.py`
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`

- [ ] Write failing tests for enums, `PolicyReplayResult`, `PolicyComparisonResult`, single replay objective calculation, and repository round trips.
- [ ] Run `pytest tests/test_policy_replay_result.py -q` and verify failures for missing models/tables/methods.
- [ ] Implement models and objective helper, add both SQLite tables, explicit repository save/get/list methods, and row converters.
- [ ] Run replay result tests and existing repository tests.

### Task 3: Full Policy Replay Engine

**Files:**
- Create: `tests/test_policy_replay_engine.py`
- Create: `src/stock_risk_mcp/policy_replay_engine.py`
- Create: `src/stock_risk_mcp/policy_replay.py`

- [ ] Write failing tests proving candidate snapshots define the ticker universe, ReplayTradePlanSnapshot is ignored, historical cutoff is enforced, policy metadata propagates, and insufficient data saves `NO_DATA`.
- [ ] Add failing tests proving `save_intermediate=false` does not change `trade_plans`, while true saves regenerated policy-aware TradePlans and records the linkage limitation note.
- [ ] Add failing tests proving `save_basket=false` does not save an official basket and true does.
- [ ] Run targeted replay engine tests and verify failures.
- [ ] Implement `replay_policy_on_replay_run`, shared `MIN_POLICY_REPLAY_CANDIDATES = 3`, candidate metadata restoration, current-pipeline regeneration, forward-only paper outcome, objective, statuses, and persistence.
- [ ] Run replay engine, replay snapshot, setup, basket, and paper trading tests.

### Task 4: Policy Comparison

**Files:**
- Create: `tests/test_policy_comparison.py`
- Create: `src/stock_risk_mcp/policy_comparison.py`

- [ ] Write failing tests for replay result reuse, baseline/candidate deltas, ACCEPT at `>= +5`, REJECT at `<= -5`, and inconclusive NEED_MORE_DATA.
- [ ] Add the required failing test where either replay has `candidate_count=2`, forcing NEED_MORE_DATA and the minimum basket note regardless of positive delta.
- [ ] Run `pytest tests/test_policy_comparison.py -q` and verify failures.
- [ ] Implement comparison creation, replay lookup/execution, delta calculation, minimum candidate helper, recommendation order, notes, and persistence.
- [ ] Run comparison and strategy objective tests.

### Task 5: Policy Replay CLI

**Files:**
- Create: `tests/test_policy_replay.py`
- Modify: `src/stock_risk_mcp/cli.py`

- [ ] Write failing CLI tests for `policy-replay`, `policy-replay-active`, `policy-replay-results`, and `policy-compare`.
- [ ] Assert replay output contains `save_intermediate`, `saved_trade_plan_count`, and `saved_to_basket_plans`.
- [ ] Run `pytest tests/test_policy_replay.py -q` and verify parser/dispatch failures.
- [ ] Add parsers, shared replay arguments, active-policy resolution, command handlers, and comparison summary output.
- [ ] Run policy replay CLI tests and existing CLI-heavy tests.

### Task 6: Documentation And Full Verification

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document Replay Snapshot versus `FULL_POLICY_REPLAY`, strict historical cutoff, forward-only outcome, opt-in storage, CLI usage, and paper-performance warning.
- [ ] Run `pytest -q` and confirm all existing and new tests pass.
- [ ] Run `python -m compileall -q src` and `git diff --check`.
- [ ] Review every requirement against implementation and tests, update the test count, commit, rerun full verification, and confirm a clean worktree.
