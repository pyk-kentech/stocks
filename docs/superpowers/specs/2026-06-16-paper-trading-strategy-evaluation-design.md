# v3.6 Paper Trading Strategy Evaluation Design

## Scope

v3.6 adds an offline deterministic paper trading strategy evaluation layer. It
consumes one explicit local JSON fixture containing advisory decision inputs,
trade plans, optional evidence summaries, local OHLC price paths, and paper
evaluation configuration. It simulates a paper-only trade lifecycle, measures
paper performance, and emits evaluation reports only.

This release does not perform live trading, does not enable PROD, does not
integrate with brokers, does not use real accounts, and does not submit orders
or create real broker requests. v3.6 evaluates advisory outputs in simulation
only.

## Release Baseline

The design assumes the current release state is:

- `v3.0.0-strategy-core-local-llm-safety-boundary`
- `v3.1.0-strategy-fixture-backtest-harness`
- `v3.2.0-technical-setup-evidence-pack`
- `v3.3.0-market-universe-volume-spike-discovery`
- `v3.4.0-llm-feature-store-signal-evaluation`
- `v3.5.0-trade-plan-basket-risk-engine` -> `aa51005`

v3.6 is design-only in this step. The v3.5 tag remains unchanged.

## Goals

v3.6 introduces deterministic paper-only evaluation for advisory strategy or
trade-plan outputs. The engine must:

- consume explicit local fixture inputs only
- simulate planned entry, fill, stop, target, and exit in paper only
- calculate paper P/L, equity curve, and drawdown
- expose missing-data and blocked-plan outcomes explicitly
- remain fully offline, reproducible, and auditable

The output is an evaluation report. It is not a trading instruction.

## Non-Goals

v3.6 does not:

- submit orders
- create real broker requests
- create `OrderIntent`
- create order drafts
- approve execution
- bypass `RiskGate` or `ExecutionGate`
- read real accounts, holdings, balances, or broker state
- read credentials or tokens
- access external network
- call local or cloud LLMs
- use LIVE or PROD paths
- import broker, Kiwoom, account-read, realtime, provider, repository, or
  network dependencies into core paper-evaluation modules

## Architecture And Dependency Boundaries

The implementation should use a pure-core plus thin-service design:

- `paper_eval_models.py`
  - strict Pydantic models for fixture, config, decision inputs, price bars,
    paper trades, positions, portfolio state, metrics, and report output
- `paper_eval_fixture.py`
  - exact-file JSON loading and strict validation
- `paper_fill_engine.py`
  - pure OHLC rule-based fill, stop, and target logic
- `paper_eval_engine.py`
  - pure paper lifecycle simulation, cash/equity updates, and metric
    aggregation
- `paper_eval_service.py`
  - orchestration only: load exact fixture, compute checksums, run pure core,
    write JSON output, and optionally append audit records later only if
    justified

Core modules must not import database, repository, provider, realtime, broker,
Kiwoom, account, order, strategy, credential, token, network, cloud, RiskGate,
or ExecutionGate modules. Default execution is JSON output only. If SQLite
audit is ever added later, it must remain optional, append-only, and
service-layer only.

## Fixture Strategy

v3.6 should use one strict local JSON fixture rather than multiple referenced
files. This keeps every simulation input inside one deterministic artifact.

The fixture may contain:

- advisory strategy decisions or candidate decisions
- advisory trade plans
- optional technical evidence summaries
- optional market discovery summaries
- optional LLM signal summaries
- local OHLC price paths
- paper evaluation configuration

The engine must never fetch missing inputs from external files, databases,
providers, or network paths.

## Fixture Contract

The v3.6 fixture should be one exact local JSON file:

```json
{
  "schema_version": "3.6-paper-eval-fixture",
  "run_id": "paper-eval-run-1",
  "created_at": "2026-01-12T16:00:00+00:00",
  "config": {
    "initial_cash": 100000.0,
    "allow_limit_entry_only": true,
    "fee_per_trade": 0.0,
    "slippage_per_share": 0.0,
    "same_bar_exit_policy": "STOP_FIRST",
    "max_open_positions": 10
  },
  "inputs": [
    {
      "ticker": "ABC",
      "source_type": "TRADE_PLAN",
      "decision_time": "2026-01-10T09:30:00+00:00",
      "side": "BUY",
      "setup_grade": "A",
      "entry_reference": 100.0,
      "stop_reference": 96.0,
      "target_reference": 108.0,
      "suggested_quantity": 250,
      "plan_status": "TRADE_PLAN_READY",
      "technical_evidence_summary": "Tight pullback",
      "market_discovery_summary": "Volume spike candidate",
      "llm_signal_summary": "Positive catalyst"
    }
  ],
  "price_paths": [
    {
      "ticker": "ABC",
      "bars": [
        {
          "timestamp": "2026-01-10T09:31:00+00:00",
          "open": 99.5,
          "high": 101.0,
          "low": 99.0,
          "close": 100.5
        }
      ]
    }
  ]
}
```

Validation requires:

- schema version exactly `3.6-paper-eval-fixture`
- non-empty `run_id`
- timezone-aware `created_at`
- exactly one `config`
- at least one `inputs` item
- at least one `price_paths` item
- no unknown fields
- uppercase normalized non-empty tickers
- ordered non-duplicate price bars per ticker
- finite positive `open`, `high`, `low`, and `close`
- `low <= min(open, close, high)`
- `high >= max(open, close, low)`
- timezone-aware `decision_time` and bar timestamps
- `suggested_quantity` non-negative integer
- finite positive `entry_reference`
- finite positive `stop_reference` when provided
- finite positive `target_reference` when provided
- finite non-negative fee and slippage values
- `same_bar_exit_policy` exactly `STOP_FIRST` for v3.6

The fixture may include advisory inputs from different source families, but
every input must normalize into one paper-evaluation candidate contract. The
engine must not infer missing timestamps, prices, or quantities.

## Core Models

Recommended models:

- `PaperEvalFixture`
  - top-level fixture with `schema_version`, `run_id`, `created_at`, `config`,
    `inputs`, and `price_paths`
- `PaperEvalConfig`
  - simulation parameters such as cash, fees, slippage, exit policy, and max
    open positions
- `PaperEvalInput`
  - normalized advisory candidate input
- `PaperPriceBar`
  - one OHLC bar used for rule-based fill and exit evaluation
- `PaperPricePath`
  - ordered bars for one ticker
- `PaperTrade`
  - one completed or incomplete paper trade lifecycle
- `PaperPosition`
  - active simulated position state between entry and exit
- `PaperPortfolioState`
  - current cash, open exposure, realized P/L, unrealized P/L, and equity
- `PaperEvalMetrics`
  - aggregate evaluation metrics
- `PaperEvalReport`
  - top-level JSON output with trades, curve, metrics, and safety metadata

Suggested `PaperTrade` fields:

- `ticker`
- `source_type`
- `decision_time`
- `entry_reference`
- `planned_quantity`
- `simulated_entry_time`
- `simulated_entry_price`
- `simulated_exit_time`
- `simulated_exit_price`
- `exit_reason`
- `gross_pnl`
- `net_pnl`
- `holding_bars`
- `holding_seconds`
- `stop_hit`
- `target_hit`
- `blocked`
- `missing_data`
- `warnings`

## Input Normalization

The engine may accept source rows that originated from:

- strategy decision fixtures
- candidate decision fixtures
- trade plan fixtures
- technical evidence fixtures
- market discovery fixtures
- LLM summary fixtures

However, v3.6 should not require the original native model types. Each source
row must normalize into one advisory paper-evaluation input with:

- `ticker`
- `decision_time`
- `side`
- `entry_reference`
- `stop_reference`
- `target_reference`
- `suggested_quantity`
- `source_type`
- `plan_status` or decision-status summary

If an input cannot provide enough deterministic planning context, it should be
counted under `blocked_plan_count` or `missing_data_count` rather than guessed.

## Fill Policy

v3.6 should use deterministic OHLC rule-based fill logic.

Entry policy:

- default and only supported entry style is advisory `LIMIT`
- evaluation starts from the first eligible bar at or after `decision_time`
- a BUY entry fills when:
  `bar.low <= entry_reference <= bar.high`
- if no bar satisfies the entry condition, the candidate ends with no paper
  position and an auditable reason such as `ENTRY_NOT_FILLED`

Exit policy after entry:

- stop hit when:
  `bar.low <= stop_reference`
- target hit when:
  `bar.high >= target_reference`
- if neither is hit and fixture bars end, close at the last available bar close
  with an auditable `END_OF_DATA_EXIT`

Same-bar collision policy:

- when a bar hits both stop and target for a BUY position, v3.6 uses
  `STOP_FIRST`
- this is intentionally conservative and must be explicit in the spec and
  output metadata

v3.6 does not support intrabar path inference beyond these OHLC rules.

## Stop And Target Policy

For BUY paper positions:

- stop must be below entry
- target must be above entry
- missing or invalid stop blocks the candidate before entry simulation
- missing target may be allowed only if the fixture explicitly chooses a
  stop-only evaluation mode later; for the first v3.6 implementation, missing
  target should count as insufficient data or blocked input

Stop and target are advisory references from the fixture. The engine must not
recalculate them from ATR, indicators, or external evidence during simulation.

## Cash And Buying Power Policy

The engine uses a pure local paper cash ledger only.

Definitions:

- `initial_cash` comes from fixture config
- `cash_available` decreases when a simulated entry fills
- `cash_available` increases when a simulated exit closes the position
- `position_notional = simulated_entry_price * quantity`

Restrictions:

- no negative cash
- no margin
- no leverage
- no short selling
- no averaging down
- no pyramiding

If cash is insufficient for the planned quantity at the simulated entry price,
the candidate is blocked or reduced only if the fixture explicitly allows size
reduction in a future version. For the first v3.6 implementation, it should be
blocked to preserve deterministic behavior.

## Fee And Slippage Policy

Fees and slippage should default to zero.

The fixture may explicitly set:

- `fee_per_trade`
- `slippage_per_share`

If provided, they must be finite and non-negative. There is no dynamic fee or
market-impact model in v3.6. The engine must not estimate fees from brokers,
venues, or live spreads.

Net P/L is:

```text
gross_pnl - entry_fee - exit_fee - total_slippage
```

where `total_slippage` is derived only from explicit fixture config.

## Portfolio And Equity Curve

The simulator should maintain deterministic paper portfolio state after each
bar and after each fill/exit event.

Suggested portfolio state fields:

- `timestamp`
- `cash_available`
- `open_position_count`
- `market_value_open_positions`
- `realized_pnl`
- `unrealized_pnl`
- `equity`
- `peak_equity`
- `drawdown_amount`
- `drawdown_pct`

The equity curve should be a time-ordered list of points generated from the
simulation timeline. Drawdown is measured from running peak equity, not from
initial cash alone.

## Metrics

The report should calculate:

- `total_return_pct`
- `max_drawdown_pct`
- `win_rate`
- `average_win_amount`
- `average_loss_amount`
- `profit_factor`
- `expectancy_amount`
- `exposure_time_pct`
- `trade_count`
- `stop_hit_count`
- `target_hit_count`
- `blocked_plan_count`
- `missing_data_count`

Definitions:

- `profit_factor = gross_profit / abs(gross_loss)` when losses exist
- `expectancy_amount = total_net_pnl / trade_count` when at least one trade
  exists
- `exposure_time_pct` uses total time with at least one open paper position
  divided by total simulated timeline duration

If the denominator is missing or zero, the metric should be reported as `null`
or an explicit deterministic empty-state value rather than inferred.

## Report JSON Schema

The JSON report should contain:

- schema version `3.6-paper-eval-report`
- fixture checksum
- `run_id`
- `created_at`
- normalized `config`
- normalized `inputs`
- `paper_trades`
- `equity_curve`
- `metrics`
- `blocked_reasons`
- safety metadata

Required safety metadata:

- `paper_only=true`
- `advisory_only=true`
- `orders_created=false`
- `order_intents_created=false`
- `strategy_decisions_created=false`
- `gates_bypassed=false`
- `external_network_calls=false`

The report must make the conservative same-bar exit policy visible so later
consumers do not assume optimistic paper fills.

## Optional Audit Persistence

JSON output is the preferred and default persistence format in v3.6.

If SQLite audit is later justified, it must satisfy all of:

- service-layer only
- optional and default-off
- append-only
- never used as fixture input
- not imported by core paper-evaluation modules

SQLite is not required for the first v3.6 implementation.

## CLI

Suggested commands:

```bash
python3.11 -m stock_risk_mcp.cli paper-eval-run --fixture-file data/paper_eval_fixture.json --output-file outputs/paper_eval_report.json
python3.11 -m stock_risk_mcp.cli paper-eval-show --output-file outputs/paper_eval_report.json
```

`paper-eval-run`:

- requires one exact local fixture file
- runs the offline deterministic paper simulation
- writes JSON output only by default
- must not access broker, Kiwoom, account, network, cloud, or credential paths

`paper-eval-show`:

- reads one exact output JSON file
- prints or returns a deterministic report summary
- performs no recalculation and no external access

## Safety Boundary

v3.6 must keep the existing v3 advisory safety boundary intact:

- no LIVE
- no PROD
- no broker integration
- no Kiwoom integration
- no account-read
- no credential or token access
- no external network
- no cloud LLM call
- no real `OrderIntent` submission
- no order draft creation
- no execution approval
- no RiskGate or ExecutionGate bypass
- no real account or holdings dependency

Even though v3.6 simulates fills and exits, every event remains paper-only.

## Testing Requirements

The implementation plan should include tests for:

- strict fixture validation
- deterministic OHLC fill logic
- same-bar `STOP_FIRST` resolution
- invalid stop and invalid target handling
- cash insufficiency blocking
- no margin, leverage, short, pyramiding, or averaging-down behavior
- fixed zero-fee and explicit-fee/slippage calculations
- equity curve and drawdown calculation
- metric determinism
- missing-data handling
- no `OrderIntent` creation
- no order draft creation
- no broker, Kiwoom, account, order, or network imports in core modules
- offline deterministic system-smoke
- preservation of existing v2 through v3.5 tests

Representative deterministic cases should include:

- one trade that fills and exits at target
- one trade that fills and exits at stop
- one trade where stop and target collide in the same bar and stop wins
- one candidate that never fills
- one candidate blocked for insufficient cash
- one candidate blocked for invalid stop
- one candidate blocked for missing target
- one fixture with missing price path data

## System Smoke

The v3.6 system-smoke should use a temporary local JSON fixture only. It should
verify:

- `paper_eval_fixture_run=true`
- deterministic JSON output written
- `paper_only=true`
- `orders_created=false`
- `order_intents_created=false`
- `external_network_calls=false`

The smoke path must not depend on broker, Kiwoom, account, network, cloud,
credential, token, or real execution infrastructure.

## Implementation Notes

The first implementation should stay intentionally boring:

- single fixture
- explicit OHLC rules
- explicit cash ledger
- explicit stop-first collision handling
- no ranking or optimization layer
- no stochastic fill model
- no partial fills
- no dynamic resizing after start

Later releases may add richer portfolio simulation, multi-order staging,
partial fills, or intent-handoff analysis, but only through separately scoped
designs with the same safety review discipline.
