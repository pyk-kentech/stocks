# Full Policy Replay Design

## Goal

Implement `FULL_POLICY_REPLAY` using a saved ReplayRun candidate universe,
as-of-date historical price cutoffs, policy-specific pipeline regeneration, and
forward-only paper outcomes.

The engine remains local and paper-trading-only. It does not call external APIs,
request realtime data, place orders, or promise real investment performance.

## Architecture

Use the existing indicator, setup grading, TradePlan, BasketPlan, and paper
trading pipeline rather than duplicating policy logic.

Add focused modules:

- `asof_price_history.py`: safe historical and forward price windows
- `policy_replay_result.py`: replay models, enums, and single-result objective
- `policy_replay_engine.py`: policy-specific pipeline regeneration
- `policy_comparison.py`: baseline/candidate comparison
- `policy_replay.py`: service entry points and shared constants

## As-Of Price Contract

`AsOfPriceHistoryProvider` loads local DB or price-history-file data and exposes:

- `get_history_until(ticker, as_of_date, min_bars=120)`: only bars whose
  `date <= as_of_date`; insufficient history returns an empty list
- `get_forward_history(ticker, after_date, horizon_days)`: only bars whose
  `date > after_date`, limited to the requested horizon window

Indicator, SetupSignal, TradePlan, and BasketPlan generation may only use
`get_history_until`. Paper outcomes may only use `get_forward_history`.

## Models

### Policy Replay

Define:

- `PolicyReplayMode`: `FULL_POLICY_REPLAY`
- `PolicyReplayStatus`: `CREATED`, `COMPLETED`, `FAILED`, `NO_DATA`
- `PolicyReplayResult`

`PolicyReplayResult` stores source run, policy, as-of date, horizon, regenerated
counts, optional basket/outcome metrics, objective score, status, notes, and
creation time.

### Policy Comparison

Define `PolicyComparisonResult` with baseline/candidate policy and replay IDs,
return/objective values and deltas, recommendation, notes, and creation time.

## Replay Data Flow

`replay_policy_on_replay_run`:

1. Loads the source ReplayRun and requires a non-null `as_of_date`.
2. Loads and validates the selected StrategyPolicy.
3. Reads the candidate universe only from ReplayCandidateSnapshot records.
4. Deduplicates tickers while preserving snapshot sector/theme metadata when
   available.
5. Loads at least 120 historical bars ending at `as_of_date` for each ticker.
6. Regenerates IndicatorSet, policy-weighted SetupSignal, and TradePlan using
   only historical bars.
7. Never reuses ReplayTradePlanSnapshot as the regenerated TradePlan.
8. Builds a policy-weighted BasketPlan from regenerated TradePlans.
9. Saves the official BasketPlan only when `save_basket=true`.
10. Runs paper outcomes only with bars after `as_of_date`.
11. Saves and returns PolicyReplayResult.

`candidate_count` is the regenerated BasketPlan allocation count. The source
candidate universe count is recorded in notes. `trade_plan_count` is the number
of regenerated TradePlans.

## Intermediate Storage

With `save_intermediate=false`, regenerated IndicatorSet, SetupSignal, and
TradePlan objects remain in memory.

With `save_intermediate=true`, only regenerated TradePlans are saved to the
existing `trade_plans` table. They retain `policy_id`, `policy_version`, and
`setup_scoring_mode`.

IndicatorSet and SetupSignal are not persisted. No `policy_replay_id` column is
added to `trade_plans`. Notes include:

`save_intermediate=true: regenerated TradePlans were saved to trade_plans without policy_replay_id linkage`

CLI output includes:

- `save_intermediate`
- `saved_trade_plan_count`
- `saved_to_basket_plans`

## Result Status

- Missing source run, policy, or source `as_of_date`: input error
- Empty candidate snapshots or no candidates with sufficient historical data:
  saved `NO_DATA`
- Basket with no usable allocation/outcome data: saved `NO_DATA`
- Successful regenerated basket and forward outcome: saved `COMPLETED`
- Unexpected execution failure after replay creation: saved `FAILED`, then the
  original error is raised

## Objective

Add a helper for one replay result that reuses
`calculate_objective_from_summary`.

The objective rewards realized return and winning outcomes, and penalizes
losses, no-data outcomes, negative realized PnL, and an undersized candidate
basket.

## Policy Comparison

`compare_policy_replays` finds the latest matching completed/no-data replay for
each policy and source run/horizon or creates a new replay.

Define `MIN_POLICY_REPLAY_CANDIDATES = 3` in a shared helper boundary so a
future StrategyPolicy/BasketPolicy-derived minimum can replace it.

Recommendation order:

1. If baseline or candidate `candidate_count < 3`, return `NEED_MORE_DATA`
   regardless of return or objective delta. Notes include
   `candidate_count below minimum basket size`.
2. Otherwise, objective delta `>= +5` returns `ACCEPT`.
3. Otherwise, objective delta `<= -5` returns `REJECT`.
4. Otherwise, return `NEED_MORE_DATA`.

## Persistence

Add SQLite tables:

- `policy_replay_results`
- `policy_comparison_results`

Add repository save/get/list methods specified by the request. Existing SQLite
databases remain compatible through `CREATE TABLE IF NOT EXISTS`.

## CLI

Add:

- `policy-replay`
- `policy-replay-active`
- `policy-replay-results`
- `policy-compare`

Replay commands accept DB, source replay run, horizon, account equity, cash,
optional local price-history file, `--save-intermediate`, and `--save-basket`.

`policy-replay-active` resolves the active StrategyPolicy. `policy-compare`
executes or reuses baseline and candidate replays and prints their values,
deltas, recommendation, and notes.

## Documentation

README explains:

- Replay Snapshot versus Full Policy Replay
- strict as-of historical cutoff
- forward-only paper outcome data
- CLI usage
- snapshot-only and intermediate storage contracts
- paper replay comparisons do not guarantee real investment performance

## Testing

Tests prove:

- historical windows exclude future bars
- forward windows exclude as-of and earlier bars
- insufficient history yields `NO_DATA`
- candidate universe comes from candidate snapshots
- ReplayTradePlanSnapshot is not reused
- regenerated objects carry policy metadata
- replay results and comparisons round-trip through SQLite
- `save_intermediate` and `save_basket` are opt-in
- no IndicatorSet or SetupSignal persistence is added
- baseline or candidate count of 2 forces `NEED_MORE_DATA`
- objective delta produces ACCEPT/REJECT/NEED_MORE_DATA
- all four CLI commands work
- all existing tests continue passing
