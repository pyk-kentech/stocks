# v7.10 Position Sizing / Risk Budget Engine

## Goal

Implement a local/offline/report-only position sizing layer that converts a reviewed candidate plus price, stop, ATR, FX, cost, market-regime, and provider-readiness evidence into a bounded sizing decision. The layer must remain non-executable and must not create live broker, account, or autonomous execution paths.

## Core design

- `PositionSizingInput` is the single local fixture-driven boundary object.
- The engine computes:
  - stop distance evidence
  - effective risk budget
  - quantity / notional / cost estimates
  - market-regime size adjustments
  - inverse / hedge eligibility and cap checks
  - boundary violations and data-readiness gaps
- Output remains report-only and may include a non-executable sizing preview, never a real order.

## Data dependencies

- Price, ATR, FX, and cost assumptions must carry provider/source/`available_at` evidence.
- v7.9 market regime is consumed as a report-only sizing constraint, not a trading instruction.
- v7.9.1 provider readiness and canonical contract refs determine whether sizing can become `SIZE_READY`, must stay `WATCH_ONLY`, or must degrade to `DATA_GAP` / `GAP`.

## Decision policy

- `SIZE_READY`: sufficient local evidence and all hard caps satisfied.
- `REDUCE_SIZE`: valid candidate but reduced by exposure/risk/cash/regime constraints.
- `CASH_LIMITED` / `RISK_BUDGET_LIMITED`: bounded by cash or daily risk.
- `WATCH_ONLY`: policy or regime allows monitoring but not sizing promotion.
- `DATA_GAP` / `GAP`: required evidence missing or below allowed readiness.
- `BLOCKED`: invalid stop, hard-cap breach, inverse/hedge breach, leakage, or unsafe boundary.
- `REJECTED`: structurally invalid input.

## Hard boundaries

- local/offline/report-only only
- no live trading, no real order, no account mutation
- no broker/Kiwoom/provider/network/WebSocket path
- no raw credential/token/account output
- no executable order output
- parquet remains unsupported

## CLI / smoke

- CLI exposes summary, stop, budget, readiness, quantity/notional, cost, regime, inverse/hedge, boundary, and gap reports.
- `system_smoke` confirms the v7.10 layer runs from local fixtures, emits report-only outputs, and keeps broker/network/order/provider paths blocked.
