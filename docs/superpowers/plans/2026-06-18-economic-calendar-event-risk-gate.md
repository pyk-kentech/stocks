# v7.11 Economic Calendar / Event Risk Gate

## Goal

Implement a local/offline/report-only event risk gate that decides whether a candidate, size promotion, or hedge/inverse adjustment may proceed near scheduled high-impact events.

## Core design

- `EventRiskInput` is the single local fixture-driven boundary object.
- The engine evaluates:
  - economic and earnings event evidence
  - event timing windows
  - provider/calendar readiness
  - leakage and freshness boundaries
  - integration with v7.10 position sizing decisions
- Output remains report-only and non-executable. It can downgrade or block promotion, but it cannot create real orders.

## Decision policy

- `ALLOW`: no relevant restriction applies.
- `REDUCE_SIZE`: candidate may proceed only with reduced sizing.
- `BLOCK_NEW_ENTRY`: no new entry promotion inside the event window.
- `REDUCE_ONLY`: only exposure-reducing actions allowed.
- `WATCH_ONLY`: monitor only, no promotion.
- `EVENT_ACTIVE`: event is inside the active block window.
- `COOLDOWN`: post-event cooldown still applies.
- `DATA_GAP`: required event/provider evidence is missing or stale.
- `BLOCKED`: leakage, invalid timing, unsafe dependency, or fail-closed critical calendar gap.
- `REJECTED`: invalid structural input.

## Dependencies

- v7.9 market regime remains report-only context.
- v7.9.1 provider readiness and canonical refs gate calendar validity.
- v7.10 position sizing is consumed as a non-executable upstream review and may be reduced or downgraded by event policy.

## Hard boundaries

- local/offline/report-only only
- no live trading, no real order, no account mutation
- no broker/Kiwoom/provider/network/WebSocket path
- no real Investing.com/Fed/BLS/BEA/BOK/company API use
- no raw credential/token/account output
- parquet remains unsupported

## CLI / smoke

- CLI exposes summary, calendar snapshot, window, restriction, sizing adjustment, provider readiness, leakage, and gap reports.
- `system_smoke` confirms the layer runs from local fixtures and keeps broker/network/provider/order paths blocked.
