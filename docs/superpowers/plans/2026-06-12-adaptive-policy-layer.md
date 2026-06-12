# Adaptive Policy Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the storage, validation, deterministic proposal, common-outcome objective evaluation, memory, report, and CLI skeleton for the Adaptive Policy Layer.

**Architecture:** Keep policy validation, objective calculation, experiment construction, optimization, memory conversion, and reporting in focused modules. Persist explicit JSON-backed models through `RiskRepository`; evaluate every requested policy against the same stored `basket_backtest_results` and mark each experiment as `COMMON_OUTCOME_EVALUATION`.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite, argparse, pytest

---

## File Map

- Create `src/stock_risk_mcp/strategy_policy.py`: policy models, defaults, normalization, validation.
- Create `src/stock_risk_mcp/strategy_objective.py`: objective model and deterministic scoring.
- Create `src/stock_risk_mcp/strategy_experiments.py`: evaluation mode and experiment construction.
- Create `src/stock_risk_mcp/strategy_optimizer.py`: deterministic candidate mutations and repository-backed evaluation.
- Create `src/stock_risk_mcp/strategy_memory.py`: basket/trade outcome memory models and conversion.
- Create `src/stock_risk_mcp/strategy_report.py`: JSON-ready limitations and summaries.
- Modify `src/stock_risk_mcp/database.py`: add three strategy tables.
- Modify `src/stock_risk_mcp/repository.py`: add strategy persistence methods and row converters.
- Modify `src/stock_risk_mcp/cli.py`: add six strategy commands.
- Create six matching test files and update `README.md` plus `WORK_SUMMARY.md`.

### Task 1: Policy Model And Validation

**Files:**
- Create: `tests/test_strategy_policy.py`
- Create: `src/stock_risk_mcp/strategy_policy.py`

- [ ] Write failing tests for default policy, weight normalization, invalid weight sum, forbidden hard-risk keys, threshold ordering, and risk override ranges.
- [ ] Run `pytest tests/test_strategy_policy.py -q` and verify import failure.
- [ ] Implement enums, defaults, `StrategyPolicy`, `normalize_weights`, `validate_strategy_policy`, and `create_default_strategy_policy`.
- [ ] Run `pytest tests/test_strategy_policy.py -q` and verify pass.

### Task 2: Objective Calculation

**Files:**
- Create: `tests/test_strategy_objective.py`
- Create: `src/stock_risk_mcp/strategy_objective.py`

- [ ] Write failing tests proving score clamp, sample count recommendation, positive metrics, and large-drawdown penalty.
- [ ] Run `pytest tests/test_strategy_objective.py -q` and verify import failure.
- [ ] Implement `StrategyRecommendation`, `ObjectiveResult`, and `calculate_objective_from_summary`.
- [ ] Run `pytest tests/test_strategy_objective.py -q` and verify pass.

### Task 3: Common Outcome Experiments And Optimizer

**Files:**
- Create: `tests/test_strategy_experiments.py`
- Create: `tests/test_strategy_optimizer.py`
- Create: `src/stock_risk_mcp/strategy_experiments.py`
- Create: `src/stock_risk_mcp/strategy_optimizer.py`

- [ ] Write failing tests for common result aggregation, evaluation mode notes, deterministic `DRAFT` candidates, normalized weights, and no automatic activation.
- [ ] Run both new test files and verify import failure.
- [ ] Implement `StrategyEvaluationMode`, `StrategyExperiment`, common outcome aggregation, deterministic mutations, candidate proposal, repository-backed evaluation, and accepted-candidate recommendation.
- [ ] Run both new test files and verify pass.

### Task 4: Strategy Memory And Report

**Files:**
- Create: `tests/test_strategy_memory.py`
- Create: `tests/test_strategy_report.py`
- Create: `src/stock_risk_mcp/strategy_memory.py`
- Create: `src/stock_risk_mcp/strategy_report.py`

- [ ] Write failing tests for basket result memory, paper trade memory features, and report limitation warnings.
- [ ] Run both new test files and verify import failure.
- [ ] Implement memory conversion and report helpers without inventing missing historical features.
- [ ] Run both new test files and verify pass.

### Task 5: SQLite And Repository

**Files:**
- Modify: `src/stock_risk_mcp/database.py`
- Modify: `src/stock_risk_mcp/repository.py`
- Extend: `tests/test_strategy_policy.py`
- Extend: `tests/test_strategy_experiments.py`
- Extend: `tests/test_strategy_memory.py`

- [ ] Add failing repository round-trip tests for policies, active lookup/status update, experiments, and memories.
- [ ] Run the three tests and verify missing-method failures.
- [ ] Add `strategy_policies`, `strategy_experiments` with `evaluation_mode`, and `strategy_memories`.
- [ ] Add explicit repository save/get/list/update methods and row converters; validate policies before save.
- [ ] Run the three tests and verify pass.

### Task 6: Strategy CLI

**Files:**
- Modify: `src/stock_risk_mcp/cli.py`
- Extend: `tests/test_strategy_optimizer.py`
- Extend: `tests/test_strategy_experiments.py`

- [ ] Add failing CLI tests for `strategy-init`, `strategy-active`, `strategy-propose`, `strategy-evaluate`, `strategy-experiments`, and `strategy-policies`.
- [ ] Run CLI tests and verify command parse failure.
- [ ] Add parsers and handlers. Ensure `strategy-evaluate` outputs `COMMON_OUTCOME_EVALUATION` and an explicit non-comparison warning.
- [ ] Run CLI tests and verify pass.

### Task 7: Documentation And Full Verification

**Files:**
- Modify: `README.md`
- Modify: `WORK_SUMMARY.md`

- [ ] Document adjustable and forbidden policy fields, all strategy commands, common-outcome limitations, sample-count promotion warning, and future `FULL_POLICY_REPLAY`.
- [ ] Run `pytest -q`.
- [ ] Run `git diff --check`.
- [ ] Review requirements line by line, commit implementation, rerun `pytest -q`, and confirm clean worktree.
