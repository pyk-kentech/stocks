# v3.1 Strategy Fixture Backtest Harness Design

## Scope

v3.1 adds an offline deterministic backtest harness for v3.0 strategy fixture
decisions. It reads one explicitly selected local JSON fixture, runs the
existing deterministic strategy engine, simulates cash-constrained long
positions against fixture-contained timestamp/price paths, calculates
portfolio metrics, and stores append-only SQLite audits.

v3.1 does not query existing signal, realtime, price-history, account, ledger,
or order SQLite tables. It does not create OrderIntent records, submit orders,
call brokers or Kiwoom, read account data, load credentials or tokens, use a
network, enable PROD, or enable LIVE.

## Architecture

The implementation is split into three boundaries:

- `strategy_backtest.py` defines strict backtest models and the pure
  deterministic simulation engine. It imports v3.0 strategy models and engine
  only. It has no repository, SQLite, broker, Kiwoom, account, credential,
  network, or order dependency.
- `strategy_backtest_fixture.py` reads exactly one explicit JSON file and
  validates the v3.1 fixture contract. It does not discover files, inspect
  directories, read environment variables, or query SQLite.
- `strategy_backtest_service.py` coordinates exact-file loading, checksum,
  pure simulation, and append-only SQLite audit persistence.

The existing v3.0 `StrategyFeatureSnapshot`, `StrategyCandidate`,
`StrategyDecision`, `StrategyConfig`, and deterministic strategy engine are
reused without changing the v3.0 models.

## Fixture Contract

The strict top-level fixture is:

```json
{
  "schema_version": "3.1",
  "strategy_config": {},
  "backtest_config": {
    "initial_cash": 10000,
    "fixed_quantity": 1
  },
  "snapshots": [
    {
      "snapshot": {
        "snapshot_id": "snapshot-1",
        "ticker": "ABC",
        "region": "US",
        "observed_at": "2026-01-01T09:00:00+00:00",
        "features": {
          "signal_score": 0.8,
          "risk_score": 0.2,
          "hard_block": false
        }
      },
      "features_available_at": "2026-01-01T09:00:00+00:00"
    }
  ],
  "candidate_events": [
    {
      "candidate": {
        "candidate_id": "candidate-1",
        "snapshot_id": "snapshot-1",
        "side": "BUY",
        "order_type": "LIMIT",
        "rationale": "fixture"
      },
      "decision_timestamp": "2026-01-01T09:05:00+00:00"
    }
  ],
  "price_paths": [
    {
      "ticker": "ABC",
      "points": [
        {
          "timestamp": "2026-01-01T09:06:00+00:00",
          "price": 100
        }
      ]
    }
  ]
}
```

`StrategyCandidate.snapshot_id` is the stable candidate-event-to-snapshot
reference. A second wrapper reference is not added. Validation requires each
candidate snapshot ID to resolve to exactly one snapshot and requires the
candidate ticker, obtained through that snapshot, to resolve to at most one
price path.

`initial_cash` and `fixed_quantity` are required positive numeric values.
`StrategyCandidate.quantity` and `StrategyCandidate.notional` are ignored by
the v3.1 simulator.

Unknown fields, invalid enums, broken references, duplicate IDs, duplicate
price paths, invalid JSON, missing required config, and invalid values produce
a JSON-safe validation error.

## Timestamp And Lookahead Rules

Every snapshot wrapper `features_available_at`, candidate event
`decision_timestamp`, and price point `timestamp` must include timezone
information.

Validation requires:

- `features_available_at <= decision_timestamp`
- each candidate event references the snapshot whose features it uses
- no more than one candidate event for the same ticker at the same decision
  timestamp
- price point timestamps are strictly increasing within each ticker path

`FEATURES_AVAILABLE_AFTER_DECISION` identifies feature lookahead violations.
`DUPLICATE_CANDIDATE_TIMESTAMP_FOR_TICKER` identifies ambiguous same-ticker
events.

The simulator sorts candidate events by `decision_timestamp`, then ticker.
Different tickers at the same timestamp are therefore deterministic. BUY and
SELL fills use the first price point strictly after the decision timestamp.
Same-timestamp fills are forbidden. Future prices never affect strategy
decisions.

## Simulation Rules

The simulator starts with `backtest_config.initial_cash`, no positions, and no
real account or ledger state. It supports one long simulated position per
ticker.

The existing strategy engine first produces a `StrategyDecision` for every
candidate event. Only `CANDIDATE_BUY` and `CANDIDATE_SELL` enter simulation
handling. Existing strategy blocks, avoids, watches, and missing-data outcomes
remain non-trading decisions.

BUY rules:

- fill at the first price point strictly after the decision timestamp
- quantity is always `backtest_config.fixed_quantity`
- cost is `fixed_quantity * fill_price`
- existing same-ticker position is blocked with
  `BLOCKED_ALREADY_POSITIONED`
- cost above available cash is blocked with `BLOCKED_INSUFFICIENT_CASH`
- no fractional resize, negative cash, margin, credit, leverage, averaging,
  pyramiding, or replacement

SELL rules:

- fill at the first price point strictly after the decision timestamp
- close the entire existing same-ticker simulated position
- no position is blocked with `BLOCKED_NO_POSITION`
- no partial exit and no use of `StrategyCandidate.quantity`

At the end of the fixture, every open position is closed at the last available
price point for its ticker with `FORCED_END_OF_FIXTURE`. If no usable price
exists, the position receives a missing-data outcome instead of an inferred
price.

MARKET, margin, short, credit, leverage, options, futures, and fractional
candidate decisions remain blocked by the v3.0 strategy engine. Fees and
slippage are zero and are not configurable in v3.1. Stop-loss and take-profit
simulation are not implemented.

## Missing Data

Missing data is auditable and fail-closed:

- no price path or no price point strictly after a candidate decision produces
  a `NEEDS_MORE_DATA` backtest event
- an open position without a usable final price cannot be force-closed and
  produces a missing-data outcome
- if any held ticker cannot be valued using a price at or before an equity
  timestamp, that entire equity point is skipped and the missing-data count is
  incremented

Structural fixture errors remain JSON-safe validation failures and do not
create a successful backtest report.

## Trades And Audit Outcomes

`StrategyBacktestTrade` records both filled and non-filled simulation outcomes
so blocked and missing decisions remain auditable. It contains run and report
references, strategy decision and candidate references, ticker, side, status,
reason, decision/fill/exit timestamps, quantity, prices, proceeds, realized
PnL, realized return, and safe metadata.

Filled BUY and matching SELL or forced exit are represented as one closed
trade record. Blocked and missing candidate events are represented as
non-filled trade audit records.

Normalized reasons include:

- `BLOCKED_ALREADY_POSITIONED`
- `BLOCKED_INSUFFICIENT_CASH`
- `BLOCKED_NO_POSITION`
- `NEEDS_MORE_DATA`
- `FORCED_END_OF_FIXTURE`
- strategy decision reason values inherited from v3.0

## Equity Curve And Metrics

The portfolio equity curve uses the sorted union of every fixture price-path
timestamp. At each timestamp:

- cash is the current simulated cash as of that timestamp
- each open position is valued using the latest available price at or before
  that timestamp
- total equity is cash plus all valued open positions
- no future price is used
- if any held ticker cannot be valued, the equity point is skipped and
  missing-data count increases

To make historical cash and positions auditable, the simulator derives equity
from timestamped fills and exits rather than only the final portfolio state.

`StrategyBacktestMetric` stores:

- `total_return_pct`, relative to `initial_cash`
- `max_drawdown_pct`, from the portfolio equity curve
- `win_rate`
- `average_win_pct`
- `average_loss_pct`
- `trade_count`
- `exposure_time_pct`, the ratio of time with at least one open position over
  the complete fixture price timestamp range
- `blocked_decision_count`
- `missing_data_count`
- `stop_loss_hit_count`, always zero in v3.1

Only closed filled trades contribute to trade count, win rate, average win,
and average loss. Total return uses final cash after forced exits relative to
initial cash.

## Models And SQLite Audit

Add strict models:

- `StrategyBacktestConfig`
- `StrategyBacktestRun`
- `StrategyBacktestTrade`
- `StrategyBacktestMetric`
- `StrategyBacktestReport`

Add append-only tables:

- `strategy_backtest_runs`
- `strategy_backtest_trades`
- `strategy_backtest_reports`
- `strategy_backtest_metrics`

Metrics are stored both inside `StrategyBacktestReport` JSON and as separate
`strategy_backtest_metrics` rows. The service stores only fixture-derived
normalized audit data and never persists raw credentials, account data, or
external responses.

## CLI

Add JSON-safe commands:

- `strategy-backtest-run --db <path> --fixture-file <explicit-json>`
- `strategy-backtest-reports --db <path> [--limit <n>]`
- `strategy-backtest-show --db <path> --report-id <id>`

`strategy-backtest-run` reads only the explicit fixture and writes only the
new backtest audit tables. It does not call `strategy-run`, create OrderIntent,
evaluate gates, or use existing market-data tables.

## System Smoke And Testing

System smoke creates one temporary local v3.1 JSON fixture, runs the backtest
service, and verifies a completed report. It performs no real-data lookup and
keeps `external_network_calls=false`.

Focused tests cover strict validation, deterministic results, timezone and
ordering rules, feature availability lookahead, strict-after fills, missing
paths, MARKET and forbidden exposure blocks, repeated BUY, insufficient cash,
SELL without position, full SELL exits, forced exits, equity curve metrics,
SQLite round trips, CLI JSON safety, and source-level forbidden dependencies.
All existing v2 and v3 tests must continue to pass.

## Future Boundaries

v3.1 intentionally excludes OHLC paths, limit-fill simulation, slippage,
fees, partial exits, pyramiding, averaging, stop-loss, take-profit,
risk-based sizing, and portfolio or basket risk engines.

Future versions may add these only with explicit deterministic policies,
including fill-price rules such as open, close, VWAP, limit, or stop
simulation. PROD, LIVE, broker access, account-read, credentials, network
access, and real order submission remain separate blocked boundaries.
