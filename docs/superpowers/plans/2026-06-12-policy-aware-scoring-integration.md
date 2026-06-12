# Policy-Aware Scoring Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply optional StrategyPolicy soft scoring and basket construction settings to the current pipeline while preserving fixed behavior and hard-risk safety boundaries.

**Architecture:** Add policy-aware alternate paths behind optional parameters, propagate nullable policy metadata through existing models and persistence, and centralize CLI policy resolution. Existing fixed setup and basket scoring remain untouched when `policy=None`; this is current-pipeline integration, not historical replay.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite, argparse, pytest

---

### Task 1: Policy-Aware Setup Scoring

**Files:**
- Create: `tests/test_policy_aware_setup_grading.py`
- Modify: `src/stock_risk_mcp/setup.py`
- Modify: `src/stock_risk_mcp/setup_grading.py`

- [ ] Add failing tests for fixed compatibility, weighted mode metadata, threshold changes, and weight-sensitive score changes.
- [ ] Run `pytest tests/test_policy_aware_setup_grading.py -q` and verify failures.
- [ ] Add optional SetupSignal policy fields, `grade_setup`, component scoring, setup-weight normalization, and policy thresholds.
- [ ] Run setup grading tests plus existing `tests/test_setup_grading.py`.

### Task 2: TradePlan Propagation And Migration

**Files:**
- Modify: `src/stock_risk_mcp/setup.py`
- Modify: `src/stock_risk_mcp/trade_plan.py`
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Extend: `tests/test_policy_aware_setup_grading.py`

- [ ] Add failing tests proving TradePlan metadata propagation, repository round-trip, and old-schema nullable-column migration.
- [ ] Run the targeted tests and verify failures.
- [ ] Add optional TradePlan fields, propagation, schema columns, migration helper, save and row conversion support.
- [ ] Run targeted and existing trade plan/repository tests.

### Task 3: Policy-Aware Basket Scoring And Mapping

**Files:**
- Create: `tests/test_policy_aware_basket_scoring.py`
- Modify: `src/stock_risk_mcp/basket_scoring.py`
- Modify: `src/stock_risk_mcp/strategy_policy.py`

- [ ] Add failing tests for fixed compatibility, 0.40 decision contract, setup/RR 0.60 redistribution, and allowed BasketPolicy mapping.
- [ ] Run the new tests and verify failures.
- [ ] Implement policy-weighted candidate scoring and focused StrategyPolicy-to-BasketPolicy mapper.
- [ ] Run new and existing basket scoring/allocator tests.

### Task 4: BasketPlan And Paper Trading Propagation

**Files:**
- Create: `tests/test_policy_aware_basket_builder.py`
- Modify: `src/stock_risk_mcp/basket.py`
- Modify: `src/stock_risk_mcp/basket_builder.py`
- Modify: `src/stock_risk_mcp/paper_trading.py`
- Modify: `src/stock_risk_mcp/basket_backtest.py`
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Modify: `src/stock_risk_mcp/strategy_memory.py`

- [ ] Add failing tests for pre-score BLOCK/NO_TRADE filtering, BasketPlan metadata, paper result propagation, memory features, repository round-trips, and old-schema migration.
- [ ] Run targeted tests and verify failures.
- [ ] Implement optional metadata propagation and persistence while retaining fixed behavior.
- [ ] Run targeted and existing basket/paper/memory tests.

### Task 5: Policy-Aware CLI

**Files:**
- Create: `tests/test_policy_aware_cli.py`
- Modify: `src/stock_risk_mcp/cli.py`

- [ ] Add failing CLI tests for no-option FIXED_RULES, active policy setup/trade plan, active policy basket build/save, explicit policy selection, and policy-aware paper output.
- [ ] Run the new CLI tests and verify failures.
- [ ] Add shared policy arguments and resolver; pass resolved policies into setup and basket pipelines.
- [ ] Run new CLI tests and existing CLI-related tests.

### Task 6: Documentation And Verification

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document FIXED_RULES versus POLICY_WEIGHTED, policy CLI flags, applied scope, immutable hard-risk scope, and current-pipeline versus `FULL_POLICY_REPLAY`.
- [ ] Run `pytest -q`.
- [ ] Run `python -m compileall -q src` and `git diff --check`.
- [ ] Review requirements line by line, commit implementation, rerun full tests, and confirm clean worktree.
