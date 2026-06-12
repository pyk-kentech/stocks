# Policy-Aware Scoring Integration Design

## Goal

Apply `StrategyPolicy` to the current Setup, TradePlan, Basket, Paper Trading,
and StrategyMemory pipeline while preserving all existing fixed behavior when no
policy is supplied.

This is current-pipeline policy application, not `FULL_POLICY_REPLAY`.

## Compatibility Boundary

- `policy=None` keeps existing setup grading and basket candidate scoring.
- Existing CLI commands without policy flags keep `FIXED_RULES` behavior.
- StrategyPolicy can affect only soft scoring, setup thresholds, basket
  construction parameters, and allocation risk units.
- Existing hard blocks and safety rules remain outside StrategyPolicy control.
- New model and database fields are optional so existing rows remain readable.

## Policy Resolution

Policy-aware CLI commands support:

- `--use-active-policy`
- `--policy-id`
- `--policy-version`

Rules:

- No policy option: use `FIXED_RULES`.
- `--use-active-policy`: requires `--db` and loads the current active policy.
- Explicit policy selection requires both `--policy-id` and
  `--policy-version`, plus `--db`.
- Active and explicit selection options are mutually exclusive.
- A missing active or explicit policy raises a clear `LookupError`.

## Setup Scoring

`SetupGrader.grade(indicator_set, policy=None)` remains the public entry point.
Add `grade_setup(indicator_set, policy=None)` as a functional wrapper.

When no policy is supplied, the current fixed point-based implementation is
unchanged and returns:

- `policy_id=None`
- `policy_version=None`
- `scoring_mode="FIXED_RULES"`

When policy is supplied, each supported indicator becomes a normalized
component score using the requested value bands. Policy setup weights are
selected from:

- `return_5d_score`
- `return_20d_score`
- `sma_alignment_score`
- `rsi_score`
- `volume_spike_score`
- `dollar_volume_score`
- `volatility_penalty`
- `max_drawdown_penalty`
- `bollinger_position_score`

Only these setup weights are normalized together. The final score is their
weighted sum, clamped to `0..100`. Policy thresholds determine A/B/C/NO_TRADE.

The volatility and drawdown “penalty” keys weight safety-oriented component
scores where lower-risk values receive higher scores. This avoids subtracting a
positive policy weight twice.

The weighted result returns:

- policy ID and version
- `scoring_mode="POLICY_WEIGHTED"`
- component indicator codes in `indicator_codes_used`
- concise reasons and warnings derived from the final grade and missing inputs

## TradePlan Propagation

Add optional fields to `SetupSignal` and `TradePlan`:

- `policy_id`
- `policy_version`
- setup scoring mode (`scoring_mode` on SetupSignal,
  `setup_scoring_mode` on TradePlan)

`create_trade_plan` copies the policy metadata from SetupSignal. SQLite
`trade_plans` adds nullable columns using startup migration for existing DBs.

The analyze/create trade-plan CLI pipeline resolves a policy and passes it to
SetupGrader. Policy flags are supported by:

- `analyze-setup`
- `create-trade-plan`
- `create-trade-plan-and-save`

## Basket Policy Mapping

Add a focused mapper:

```text
apply_strategy_policy_to_basket_policy(base BasketPolicy, StrategyPolicy)
```

It copies only allowed fields:

- basket rules: max/min candidates, sector/theme limits, review/C setup flags
- risk overrides: A/B/C risk units, basket loss/notional limits, single
  candidate loss limit

Account equity, available cash, currency, single-position safety limit, and
other hard-risk values remain owned by the existing BasketPolicy/CLI inputs.

## Basket Candidate Scoring

`score_candidate(candidate, policy=None)` preserves existing scoring when policy
is absent.

Policy-weighted scoring uses only eligible `PROPOSE` and `REVIEW` candidates.
`BLOCK` and `NO_TRADE` are filtered before scoring.

Components:

- setup grade: A=100, B=70, C=30, NO_TRADE=0
- risk/reward: >=4=100, >=3=80, >=2.5=60, <2.5=20, missing=0
- decision: PROPOSE=90, REVIEW=65

Weights:

```text
basket_policy_weight_total = setup_grade_score + risk_reward_score

if basket_policy_weight_total > 0:
    setup_weight = 0.60 * setup_grade_score / basket_policy_weight_total
    rr_weight = 0.60 * risk_reward_score / basket_policy_weight_total
else:
    setup_weight = 0.35
    rr_weight = 0.25

decision_weight = 0.40
```

The final candidate score is the weighted component sum, rounded to an integer
for compatibility with the existing `BasketCandidate.score` field.

## Basket Construction And Propagation

`build_basket(candidates, basket_policy, strategy_policy=None)`:

1. Filters hard-ineligible `BLOCK` and `NO_TRADE` candidates.
2. Scores remaining candidates with fixed or policy-weighted scoring.
3. Applies existing review/C setup and concentration filters.
4. Allocates using the mapped BasketPolicy risk units and limits.
5. Records optional policy metadata and `basket_scoring_mode`.

Add optional fields to `BasketPlan`:

- `policy_id`
- `policy_version`
- `basket_scoring_mode`

The basket CLI resolves StrategyPolicy, maps it onto the CLI-created
BasketPolicy, and passes both to `build_basket`.

## Paper Trading And Memory Propagation

Add optional policy ID/version to:

- `PaperTrade`
- `BasketBacktestResult`

`run_basket_backtest` copies policy metadata from BasketPlan into every trade
and the result. SQLite tables add nullable migration columns.

StrategyMemory copies available policy ID/version and includes:

- `policy_id`
- `policy_version`
- `setup_scoring_mode`
- `basket_scoring_mode`

Unknown scoring modes remain `None`; they are never inferred.

## Database Migration

`create_schema` continues creating current tables and then checks existing table
columns with `PRAGMA table_info`. Missing nullable policy columns are added with
`ALTER TABLE`.

Affected tables:

- `trade_plans`
- `basket_plans`
- `paper_trades`
- `basket_backtest_results`

Repository row conversion and save methods preserve optional metadata.

## CLI Output

Policy-aware output naturally includes model policy metadata through
`model_dump`. Commands covered:

- `analyze-setup`
- `create-trade-plan`
- `create-trade-plan-and-save`
- `build-basket-from-trade-plans`
- `build-basket-and-save`
- `paper-trade-basket`
- `paper-trade-basket-from-file`

## Testing

Tests will prove:

- fixed setup and basket behavior remains unchanged without policy
- weighted setup score responds to weights and thresholds
- hard-risk override validation remains enforced
- policy metadata persists through TradePlan and BasketPlan
- basket policy mapping affects allowed soft fields only
- basket scoring uses the 0.40 decision and normalized 0.60 setup/RR contract
- policy metadata reaches PaperTrade, BasketBacktestResult, and StrategyMemory
- active/explicit policy CLI flows work
- old SQLite schemas receive nullable migration columns
- all existing 111 tests continue passing

## Future Work

`FULL_POLICY_REPLAY` remains future work. This integration applies a policy only
to newly executed current-pipeline analysis and basket construction; it does not
reconstruct historical feature snapshots or historical policy decisions.
