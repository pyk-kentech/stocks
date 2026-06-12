# Replay Snapshot Layer Design

## Goal

Store reproducible run-level snapshots of the current candidate, trade plan,
basket, and paper outcome pipeline so a future `FULL_POLICY_REPLAY` engine has
stable source records.

This layer does not recalculate historical indicators, enforce an as-of cutoff,
call external APIs, execute orders, or compare policies.

## As-Of Date And Leakage Boundary

Every ReplayRun and candidate snapshot stores an explicit `as_of_date`.

In this MVP, `as_of_date` is metadata only. Existing recent trade plans and
latest price history may contain information after that date. Every run created
from recent trade plans records:

- `as_of cutoff replay is not yet implemented`
- `This is not FULL_POLICY_REPLAY.`
- a future-data leakage warning

Future `FULL_POLICY_REPLAY` must regenerate indicators, setup scores, trade
plans, basket construction, and outcomes using data cut off at `as_of_date`.

## Models

### Replay Run

Define:

- `ReplayRunStatus`: `CREATED`, `COMPLETED`, `FAILED`
- `ReplaySnapshotMode`: `FIXED_RULES`, `POLICY_WEIGHTED`
- `ReplayRun`

ReplayRun records the selected policy metadata, run counts, optional basket ID,
status, notes, and creation time.

### Snapshot Models

Define:

- `ReplayCandidateSnapshot`
- `ReplayTradePlanSnapshot`
- `ReplayBasketSnapshot`
- `ReplayOutcomeSnapshot`

Each snapshot keeps searchable typed columns plus an exact `snapshot_json`
payload for future replay engine evolution.

Candidate metadata is intentionally open-ended. Trade, basket, and outcome
snapshots use full model dumps for `snapshot_json`.

## Snapshot Conversion

`replay_snapshot.py` provides pure conversion helpers:

- allocations or BasketCandidates to candidate snapshots
- TradePlans or BasketAllocations to trade plan snapshots
- BasketPlan to basket snapshot
- BasketBacktestResult to outcome snapshot

Existing-basket conversion uses allocations because persisted BasketPlan
reconstruction does not retain every original eligible candidate field.

## Replay Dataset

`replay_dataset.py` groups all snapshots for one run:

```text
ReplayDataset:
  run
  candidates
  trade_plans
  basket
  outcome
```

It provides one repository-backed loader used by `replay-show`.

## Replay Run Service

`replay_run.py` provides a repository-backed `ReplayRunService`.

### Existing Basket

`create_replay_run_from_existing_basket`:

1. Loads the stored BasketPlan and allocations.
2. Resolves policy metadata from explicit arguments or BasketPlan.
3. Converts allocations to candidate/trade snapshots.
4. Converts BasketPlan to a basket snapshot.
5. Includes the latest basket backtest result when available.
6. Saves snapshots and a `COMPLETED` ReplayRun.

Notes include:

- `Snapshot created from existing basket.`
- `This is not FULL_POLICY_REPLAY.`
- `as_of_date is metadata; historical cutoff regeneration was not performed.`

### Recent Trade Plans

`create_replay_run_from_recent_trade_plans`:

1. Resolves active, explicit, or fixed-rules policy mode.
2. Loads recent eligible TradePlans.
3. Builds a BasketPlan through the existing current pipeline.
4. Saves candidate, trade plan, and basket snapshots.
5. Runs paper trading only when each allocation has usable DB price history.
6. Saves an outcome snapshot when paper trading runs.
7. Saves a `COMPLETED` ReplayRun.

This flow is snapshot-only by default:

- The generated basket ID is always stored in ReplayBasketSnapshot.
- The basket ID may not exist in the official `basket_plans` table.
- Official `basket_plans`, allocations, and blocked candidates are saved only
  when `--save-basket` is provided.

ReplayRun notes contain exactly one storage note:

- `Basket was stored only as replay snapshot.`
- `Basket was also saved to basket_plans.`

CLI output includes:

```text
saved_to_basket_plans: true | false
```

## Persistence

Add SQLite tables:

- `replay_runs`
- `replay_candidate_snapshots`
- `replay_trade_plan_snapshots`
- `replay_basket_snapshots`
- `replay_outcome_snapshots`

No foreign key is added from replay basket IDs to `basket_plans`; snapshot-only
runs intentionally allow replay-only basket IDs.

Repository methods explicitly serialize and restore all models. Snapshot list
methods order by insertion ID.

## CLI

Add:

- `replay-snapshot-from-basket`
- `replay-snapshot-from-recent-trade-plans`
- `replay-runs`
- `replay-show`

Recent-trade-plan command supports:

- account equity and cash
- optional active or explicit StrategyPolicy
- max candidates
- horizon days
- `--save-basket`

`replay-show` outputs the complete ReplayDataset.

## Error Handling

- Missing basket or replay run raises `LookupError`.
- Invalid policy option combinations reuse the existing CLI policy resolver.
- Existing basket snapshot creation succeeds without an outcome.
- Recent-trade-plan snapshot creation succeeds without an outcome when DB price
  data is insufficient.
- Unexpected service failures save a `FAILED` ReplayRun with an error note
  before re-raising when a run ID has already been created.

## Testing

Tests prove:

- every replay model round-trips through SQLite
- existing basket snapshot creation preserves policy metadata
- replay-show returns the complete dataset
- replay-runs and snapshot-from-basket CLI work
- recent trade plans default to snapshot-only
- `--save-basket` saves the official BasketPlan
- notes and CLI report `saved_to_basket_plans`
- as-of leakage limitations are documented
- all existing 124 tests continue passing

## Future Work

Implement `FULL_POLICY_REPLAY` with as-of-date price cutoff, historical
indicator regeneration, policy-specific setup/trade/basket reconstruction, and
outcome comparison. Replay Snapshot Layer records are the stable input contract
for that engine.
