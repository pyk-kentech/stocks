# Adaptive Policy Layer Design

## Goal

Add an Adaptive Policy Layer that stores, validates, proposes, evaluates, and
reports strategy policy experiments using existing Basket Paper Trading results.

This layer is for paper-trading strategy experiments only. It does not call
external APIs, make realtime web requests, execute orders, or modify hard risk
blocks.

## MVP Evaluation Contract

The MVP implements only:

```text
COMMON_OUTCOME_EVALUATION
```

Every evaluated policy uses the same complete set of stored
`basket_backtest_results`. The resulting objective measures the common observed
basket performance and is stored separately for each candidate policy.

This does not prove that one candidate policy is better than another because the
candidate policy is not reapplied to historical feature snapshots.

Reserved future evaluation modes:

- `FEATURE_RESCORING`: not implemented because it risks producing retrospective
  scores without reconstructing actual basket decisions.
- `FULL_POLICY_REPLAY`: future Policy Replay Engine work that will reconstruct
  candidates, allocations, and basket outcomes from historical feature snapshots.

`StrategyExperiment` stores an `evaluation_mode` field. Its notes also contain
`evaluation_mode=COMMON_OUTCOME_EVALUATION` so older or external consumers can
identify the limitation.

## Policy Safety Boundary

`StrategyPolicy` may adjust only:

- soft scoring weights
- setup thresholds
- basket candidate and concentration rules
- allowed basket allocation and loss limits

The optimizer must reject forbidden hard-risk override keys:

- `block_nasdaq_noncompliant`
- `block_dilution_high`
- `block_unknown_dilution`
- `allow_market_order`
- `allow_margin`
- `allow_options`
- `allow_disable_stop_loss`
- `max_daily_loss_pct`
- `max_single_position_pct`
- `min_cash_pct`

Validation also enforces normalized non-negative weights, ordered setup
thresholds, and bounded basket loss overrides.

## Components

### `strategy_policy.py`

Defines:

- `StrategyPolicyStatus`
- `StrategyPolicy`
- policy creator/source enum
- forbidden hard-risk keys
- `create_default_strategy_policy`
- `validate_strategy_policy`
- `normalize_weights`

The default policy is `default` version `v1` with `ACTIVE` status.

### `strategy_objective.py`

Defines:

- experiment recommendation enum
- `ObjectiveResult`
- `calculate_objective_from_summary`

The deterministic objective combines return, win rate, profit factor, loss
rate, drawdown, and realized PnL. It clamps scores to `0..100`.

Recommendations:

- sample count below 30: `NEED_MORE_DATA`
- score at least 70: `ACCEPT`
- score at least 50: `NEED_MORE_DATA`
- otherwise: `REJECT`

Large negative drawdown receives a strong penalty even when average return is
positive.

### `strategy_experiments.py`

Defines:

- `StrategyEvaluationMode`
- `StrategyExperiment`
- common-outcome experiment construction from stored basket results

The only executable mode is `COMMON_OUTCOME_EVALUATION`.

### `strategy_optimizer.py`

Defines `StrategyOptimizer` with deterministic perturbations and an injected
`RiskRepository`.

It:

- proposes `n` `DRAFT` candidate policies from an active baseline
- applies one bounded mutation per candidate
- normalizes changed weights
- validates every candidate
- evaluates a policy from the repository's common basket results
- resolves and returns the highest-scoring persisted candidate only when its
  experiment recommendation is `ACCEPT`

The MVP does not activate or approve policies automatically.

For evaluation, the active policy is recorded as the baseline and the requested
policy is recorded as the candidate. Evaluating the active policy itself records
the same policy in both roles.

### `strategy_memory.py`

Defines:

- `StrategyMemory`
- basket-result memory creation
- paper-trade memory creation

Memory records retain outcome context and future replay fields, including
optional policy ID and version. Paper trade memory features include setup grade,
exit reason, risk/reward ratio when available, allocated loss, notional value,
decision, policy ID, and policy version.

Because current `PaperTrade` does not contain risk/reward ratio or policy
identity, those feature values are stored as `None` unless supplied by a future
replay flow.

Basket-result memory uses `decision="BASKET_BACKTEST"`. Paper-trade memory uses
the trade status as its decision value. This preserves current facts without
inventing a historical policy decision.

### `strategy_report.py`

Builds JSON-ready summaries of policies, experiments, common evaluation
limitations, and the warning that insufficient samples must not promote a
policy.

### Persistence

Add SQLite tables:

- `strategy_policies`
- `strategy_experiments`, including `evaluation_mode`
- `strategy_memories`

Repository methods follow existing explicit SQLite serialization patterns.
Status updates do not alter policy contents.

## CLI

Add:

- `strategy-init`: create `default/v1` once, otherwise show it
- `strategy-active`: show the active policy or `null`
- `strategy-propose --n N`: create and save deterministic `DRAFT` candidates
- `strategy-evaluate --policy-id ... --version ... --horizon-days ...`: evaluate
  all stored basket results in common-outcome mode and save the experiment
- `strategy-experiments`: list stored experiments
- `strategy-policies`: list stored policies

`strategy-evaluate` output includes `evaluation_mode`, objective score,
recommendation, and notes.

## Error Handling

- Invalid policies raise `ValueError` before persistence.
- Duplicate `strategy-init` returns the existing default policy.
- Proposing without an active policy raises a clear `LookupError`.
- Evaluating a missing policy raises a clear `LookupError`.
- Empty basket result history produces sample count zero and
  `NEED_MORE_DATA`.
- Unsupported evaluation modes raise `ValueError`.

## Testing

Add focused tests for:

- default policy and validation boundaries
- normalization
- deterministic candidate generation
- objective scoring and drawdown penalty
- common-outcome experiment calculation and evaluation-mode notes
- memory creation
- repository round trips and active status lookup
- all six CLI commands
- README/work summary documentation

Success means all new tests and the existing 92 tests pass.

## Future Work

Implement a Policy Replay Engine for `FULL_POLICY_REPLAY`. It must persist
historical feature snapshots and reconstruct candidate scoring, setup grading,
basket selection, allocation, and outcomes under each policy. Only that mode can
support a defensible comparison between candidate policies.
