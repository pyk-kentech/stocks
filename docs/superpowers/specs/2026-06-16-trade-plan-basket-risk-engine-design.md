# v3.5 Trade Plan And Basket Risk Engine Design

## Scope

v3.5 adds an offline deterministic advisory trade plan and basket risk engine.
It consumes one explicit local JSON fixture containing trade-plan candidates and
portfolio risk configuration, validates the fixture strictly, produces per-name
advisory trade plans, evaluates aggregate basket risk, and emits a JSON report.

This release does not perform live trading, broker integration, execution,
account reads, credential access, network access, cloud LLM calls, or order
creation of any kind. v3.5 may eventually provide advisory inputs to later
`OrderIntent` drafts, but v3.5 itself must not create `StrategyDecision`,
`OrderIntent`, order drafts, execution approvals, or submitted orders.

## Release Baseline

The design assumes the current release state is:

- `v3.0.0-strategy-core-local-llm-safety-boundary`
- `v3.1.0-strategy-fixture-backtest-harness`
- `v3.2.0-technical-setup-evidence-pack`
- `v3.3.0-market-universe-volume-spike-discovery`
- `v3.4.0-llm-feature-store-signal-evaluation` -> `107228f`

v3.5 is design-only in this step. The v3.4 tag remains unchanged.

## Goals

v3.5 introduces deterministic planning and basket-risk review for explicit
candidate inputs. The engine must:

- size positions from max-loss-first risk math
- derive advisory stop, target, and quantity outputs from fixture evidence
- block unsafe or unsupported plans with explicit reasons
- enforce a fixture-defined aggregate basket risk cap
- remain fully offline, reproducible, and testable from local fixtures only

The engine is advisory only. Its output is a trade plan report, not a trading
instruction.

## Non-Goals

v3.5 does not:

- read broker, Kiwoom, realtime, provider, account, credential, token, or
  network data
- create `StrategyDecision`
- create `OrderIntent`
- create order drafts
- submit or approve execution
- support LIVE or PROD modes
- support margin, leverage, short selling, pyramiding, or averaging down
- enable market orders by default
- infer missing evidence from external sources

## Architecture And Dependency Boundaries

The implementation should use a two-stage deterministic design:

1. per-trade plan generation
2. basket-risk review across generated plans

Recommended module boundaries:

- `trade_plan_models.py`
  - strict Pydantic models for fixture, input, config, plan, basket state,
    basket decision, and report objects
- `trade_plan_fixture.py`
  - exact-file JSON loading and strict schema validation
- `trade_plan_engine.py`
  - pure per-name planning logic: stop distance, reward distance, risk/reward,
    maximum-loss sizing, status selection, block reasons, warnings
- `basket_risk_engine.py`
  - pure aggregate basket-risk evaluation over generated plans
- `trade_plan_service.py`
  - orchestration only: load exact fixture, compute checksums, invoke pure core,
    write JSON report, optionally append audit records through a service-layer
    storage boundary if approved later

Core modules must not import database, repository, provider, realtime, broker,
Kiwoom, account, order, strategy, credential, token, network, cloud, RiskGate,
or ExecutionGate modules. SQLite, if ever added, must remain optional,
append-only, and service-layer only. Default execution is JSON output only.

## Fixture Contract

The v3.5 fixture should be one exact local JSON file:

```json
{
  "schema_version": "3.5-trade-plan-fixture",
  "run_id": "trade-plan-run-1",
  "created_at": "2026-01-10T15:30:00+00:00",
  "config": {
    "portfolio_equity": 100000.0,
    "risk_pct_per_trade": 0.01,
    "max_basket_risk_pct": 0.03,
    "fixed_min_risk_reward": 2.0
  },
  "candidates": [
    {
      "ticker": "ABC",
      "side": "BUY",
      "setup_type": "BREAKOUT_PULLBACK",
      "setup_grade": "A",
      "entry_reference": 100.0,
      "stop_reference": 96.0,
      "target_reference": 108.0,
      "atr_value": 2.0,
      "stop_distance_evidence": 4.0,
      "support_level": 95.5,
      "resistance_level": 108.0,
      "technical_evidence_summary": "Tight pullback above breakout level",
      "llm_signal_summary": "Positive catalyst and manageable risk",
      "warnings": []
    }
  ]
}
```

Validation requires:

- schema version exactly `3.5-trade-plan-fixture`
- non-empty `run_id`
- timezone-aware `created_at`
- exactly one `config`
- at least one candidate
- no unknown fields
- uppercase normalized non-empty tickers
- `side` exactly `BUY` for v3.5
- non-empty `setup_type`
- `setup_grade` exactly one of `A`, `B`, `C`, `D`, `F`
- finite positive `entry_reference`
- finite positive `stop_reference` when provided
- finite positive `target_reference` when provided
- finite positive `portfolio_equity`
- `risk_pct_per_trade` greater than `0` and less than or equal to `1`
- `max_basket_risk_pct` greater than `0` and less than or equal to `1`
- finite positive `fixed_min_risk_reward`

Optional evidence fields may be omitted, but the engine must never invent them
from outside the fixture. A duplicate candidate key of `ticker + side +
setup_type` is a validation error. Array order is preserved only for report
readability and must not change rule outcomes.

## Core Models

Recommended models:

- `TradePlanFixture`
  - top-level fixture with `schema_version`, `run_id`, `created_at`, `config`,
    and `candidates`
- `TradePlanInput`
  - normalized advisory candidate input
- `TradePlanConfig`
  - `portfolio_equity`, `risk_pct_per_trade`, `max_basket_risk_pct`,
    `fixed_min_risk_reward`
- `TradePlan`
  - normalized advisory output per candidate
- `BasketRiskState`
  - running basket risk totals from plan candidates already evaluated
- `BasketRiskDecision`
  - cap review result and optional block reason per candidate
- `TradePlanReport`
  - top-level JSON output containing checksum, config, plans, basket summary,
    and safety flags

Suggested `TradePlan` fields:

- `ticker`
- `side`
- `setup_type`
- `setup_grade`
- `entry_reference`
- `stop_reference`
- `target_reference`
- `stop_distance`
- `reward_distance`
- `risk_reward_ratio`
- `max_loss_amount`
- `suggested_quantity`
- `basket_risk_amount`
- `plan_status`
- `block_reasons`
- `warnings`
- `technical_evidence_summary`
- `llm_signal_summary`

## Deterministic Planning Rules

The per-trade engine is pure and deterministic. It must use fixture values only.

For each candidate:

1. normalize and validate the advisory input
2. reject unsupported sides before any sizing math
3. derive stop distance:
   `abs(entry_reference - stop_reference)`
4. compute risk amount:
   `portfolio_equity * risk_pct_per_trade`
5. compute suggested quantity:
   `floor(risk_amount / stop_distance)`
6. compute max loss amount:
   `suggested_quantity * stop_distance`
7. compute reward distance:
   `target_reference - entry_reference`
8. compute risk/reward ratio:
   `reward_distance / stop_distance`

BUY plans require:

- `stop_reference < entry_reference`
- `target_reference > entry_reference`

If stop distance is missing, zero, negative after validation semantics, or not
finite, the plan is blocked with `BLOCKED_INVALID_STOP`.

If target evidence is missing, invalid, or non-positive relative to the entry,
the plan becomes `WATCH_ONLY` or `BLOCKED_INSUFFICIENT_EVIDENCE` depending on
whether the remaining evidence still describes a coherent setup. v3.5 should
prefer blocking when deterministic sizing or deterministic reward review cannot
be justified.

If computed quantity is `0`, the plan becomes `NO_TRADE` with a warning that
the account-level risk budget is too small for the stop distance.

## Risk And Basket Rules

The risk engine must enforce these permanent v3.5 restrictions:

- no averaging down
- no pyramiding
- no margin
- no leverage
- no short selling
- no market orders by default

These restrictions are status-level blockers, not warnings.

`risk_reward_ratio` is compared to `fixed_min_risk_reward`.

- if ratio is below the threshold and the setup remains otherwise coherent, the
  plan should default to `BLOCKED_RISK_REWARD_TOO_LOW`
- `WATCH_ONLY` is allowed only when the candidate is informationally useful but
  not actionable because evidence quality is incomplete rather than unsafe

Basket risk review should consider only plans that survived per-trade blocking
and produced positive `suggested_quantity`.

Definitions:

- `per_plan_basket_risk = max_loss_amount`
- `max_basket_risk_amount = portfolio_equity * max_basket_risk_pct`
- `running_basket_risk_amount = sum(max_loss_amount for accepted ready plans)`

For each eligible plan in deterministic fixture order:

- if adding the plan would exceed `max_basket_risk_amount`, set
  `BLOCKED_BASKET_RISK_CAP`
- otherwise keep the plan eligible for `TRADE_PLAN_READY`

This keeps basket review deterministic and auditable while avoiding any ranking
heuristic that depends on non-fixture data.

## Plan Status Semantics

Suggested statuses and meanings:

- `TRADE_PLAN_READY`
  - valid advisory plan with positive quantity, valid stop, valid target,
    acceptable risk/reward, supported side, and basket capacity available
- `WATCH_ONLY`
  - setup is interesting, but evidence is not strong enough for a ready plan
- `BLOCKED_INVALID_STOP`
  - missing, invalid, zero-width, or semantically wrong stop reference
- `BLOCKED_RISK_REWARD_TOO_LOW`
  - reward relative to stop is below `fixed_min_risk_reward`
- `BLOCKED_BASKET_RISK_CAP`
  - valid plan would exceed configured basket cap
- `BLOCKED_INSUFFICIENT_EVIDENCE`
  - required references are missing or too incomplete for deterministic planning
- `BLOCKED_UNSUPPORTED_SIDE`
  - side other than `BUY`
- `NO_TRADE`
  - valid arithmetic but no actionable quantity or no advisory action should be
    taken

`block_reasons` should use explicit machine-readable strings. `warnings` should
capture lower-severity advisory notes without changing the hard status.

## Output Report

The JSON report should contain:

- schema version `3.5-trade-plan-report`
- fixture checksum
- `run_id`
- `created_at`
- normalized `config`
- `plans`
- basket summary totals
- safety flags

Suggested summary fields:

- `candidate_count`
- `ready_count`
- `watch_only_count`
- `blocked_count`
- `no_trade_count`
- `total_ready_basket_risk_amount`
- `max_basket_risk_amount`
- `external_network_calls`
- `strategy_decision_created`
- `order_intent_created`
- `order_draft_created`

The three creation flags above must always be `false` in v3.5.

## CLI

Suggested commands:

```bash
python3.11 -m stock_risk_mcp.cli trade-plan-run --fixture-file data/trade_plan_fixture.json --output-file outputs/trade_plan_report.json
python3.11 -m stock_risk_mcp.cli trade-plan-show --output-file outputs/trade_plan_report.json
```

`trade-plan-run`:

- requires one exact local fixture file
- writes JSON output only by default
- must not auto-discover files
- must not call network, broker, Kiwoom, or account paths

`trade-plan-show`:

- reads one exact output JSON file
- prints a deterministic human-readable summary
- performs no recalculation and no external access

## Optional Audit Persistence

JSON output is the preferred and default persistence format in v3.5.

If SQLite audit storage is proposed later, it must satisfy all of:

- service-layer only
- optional and default-off
- append-only
- never used as fixture input
- not imported by core planning or basket-risk modules

SQLite is not required for the first v3.5 implementation.

## Safety Boundary

v3.5 must keep the existing v3 advisory safety boundary intact:

- no LIVE
- no PROD
- no broker integration
- no Kiwoom integration
- no account-read
- no credential or token access
- no external network
- no cloud LLM call
- no `StrategyDecision` creation
- no `OrderIntent` creation
- no order draft creation
- no order submission
- no execution approval
- no RiskGate or ExecutionGate bypass

The system-smoke and tests must explicitly confirm that the advisory planning
path stays inside these boundaries.

## Testing Requirements

The v3.5 implementation plan should include tests for:

- strict fixture validation
- deterministic trade plan generation
- invalid stop handling
- risk/reward threshold enforcement
- max-loss quantity sizing
- basket risk cap blocking
- unsupported side blocking
- no margin, leverage, or short support
- no `StrategyDecision` creation
- no `OrderIntent` creation
- no broker, Kiwoom, account, order, or network imports in core modules
- offline deterministic system-smoke
- preservation of existing v2 and v3 tests

Representative deterministic cases should include:

- valid BUY setup with positive quantity and acceptable basket capacity
- BUY setup with stop above entry
- BUY setup with missing stop
- BUY setup with reward below minimum threshold
- BUY setup whose quantity floors to zero
- two individually valid setups where the second exceeds basket cap
- unsupported `SELL` input blocked before planning

## System Smoke

The v3.5 system-smoke should use a temporary local JSON fixture only. It should
verify:

- `trade_plan_fixture_run=true`
- deterministic JSON output written
- no strategy decision created
- no order intent created
- `external_network_calls=false`

The smoke path must not depend on SQLite, cloud, network, broker, Kiwoom,
account, or order infrastructure.

## Implementation Notes

The first implementation should stay intentionally boring:

- explicit formulas
- explicit status transitions
- explicit block reasons
- fixture-order basket evaluation
- no optimization, ranking, or recommendation heuristics beyond approved rules

Future versions may add richer ranking, long/short symmetry, draft order
translation, or execution-intent handoff, but only in later scoped releases
with separate safety review.
