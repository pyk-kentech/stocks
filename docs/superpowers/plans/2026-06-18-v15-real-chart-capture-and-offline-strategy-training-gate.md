# v15.0 Real Chart Capture And Offline Strategy Training Gate Corrected Implementation Plan

## Scope

This single v15 milestone includes both:

1. corrective real read-only Kiwoom historical chart capture in `historical_market_data_*`
2. new offline strategy training, bounded parameter search, walk-forward validation, and promotion gate in `offline_strategy_*`

Final tag only:

- `v15.0.0-real-chart-capture-and-offline-strategy-training-gate`

Do not create `v14.1`, `v14.2`, `v15.1`, or `v15.2`.

## Real Capture Boundary

- real capture applies only to read-only Kiwoom chart collection
- real capture supports only `KA10080` and `KA10081`
- real capture is explicit local opt-in only
- API key handling remains credential-ref-only
- raw API keys, secrets, tokens, and auth headers must never be printed or persisted
- real capture is never allowed in pytest
- pytest must perform no real provider/network call
- pytest must perform no env read and no credential file read
- no account API, order API, or executable output is allowed anywhere in this scope

## Offline Strategy Boundary

- `offline_strategy_*` remains manifest-first and offline-only
- `offline_strategy_*` consumes only local canonical inputs and local fixtures
- `offline_strategy_*` performs no provider connectivity check
- `offline_strategy_*` performs no Kiwoom, LS, FRED, Yahoo, Databento, CME, or other network fetch
- `offline_strategy_*` performs no env read, token load, or credential read
- `offline_strategy_*` performs no account/order path
- `offline_strategy_*` performs no executable order output
- local LLM remains advisory or fixture-only and is not a strategy training runtime dependency

## Delivery Items

### Historical real capture

- add real-capture config, transport kind, credential-ref, run result, and audit models
- add guardrails for safe local roots, bounded request counts, bounded continuation pages, and sensitive marker checks
- add a real transport boundary for Kiwoom chart capture and a mock transport for tests and smoke
- keep normalization and manifest generation downstream of the redacted raw capture boundary
- add CLI surfaces:
  - `historical-market-data-real-capture-preflight-report`
  - `historical-market-data-real-capture-plan-report`
  - `historical-market-data-real-capture-run`
  - `historical-market-data-real-capture-audit-report`

### Offline strategy

- add independent `offline_strategy_*` public models and engines
- keep default promotion direction `LONG_ONLY`
- keep conservative next-bar fill assumptions
- keep anchored chronological walk-forward as the default promotion path
- keep bounded parameter search only
- add CLI/report surfaces for template catalog, dataset compatibility, parameter search plan, walk-forward plan, backtest smoke, promotion gate, training launch plan, research readiness, safety, and gaps

## Verification

- focused pytest for historical real capture guard, credential-ref loading, transport, runner, and offline strategy engines
- `tests/test_system_smoke.py`
- full `pytest`

## Acceptance

v15 is complete when:

- real chart capture remains read-only, opt-in, bounded, and `KA10080`/`KA10081`-only
- no real provider/network call runs in pytest
- no credential/env read runs in pytest
- offline strategy remains manifest-only and offline-only
- no account/order API or executable order output is introduced
- command-line reports for both real capture and offline strategy are registered and reachable from the command parser
