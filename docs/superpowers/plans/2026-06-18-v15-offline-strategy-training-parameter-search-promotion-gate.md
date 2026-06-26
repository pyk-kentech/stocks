# v15.0 Real Chart Capture And Offline Strategy Training Gate Implementation Plan

## Scope

This single v15 milestone includes both:

1. corrective real read-only Kiwoom historical chart capture in `historical_market_data_*`
2. new offline strategy training, bounded parameter search, walk-forward validation, and promotion gate in `offline_strategy_*`

Do not create `v14.1`, `v14.2`, `v15.1`, or `v15.2`.

Final tag only:

- `v15.0.0-real-chart-capture-and-offline-strategy-training-gate`

## Architecture Order

1. Extend `historical_market_data_*` models and guards for real capture config, credential refs, transport boundary, run result, and audit models
2. Implement real capture transport, credential-ref loading, runner orchestration, and redacted raw lake updates
3. Extend CLI and `system_smoke` for real capture preflight, plan, run, and audit
4. Add `offline_strategy_*` models, guards, fixtures, and template catalog
5. Implement indicators, signals, bounded grid search, dataset compatibility, walk-forward, conservative backtest, metrics, promotion gate, training plan, and artifact manifest
6. Wire offline strategy CLI and `system_smoke`
7. Add focused tests for both halves
8. Run focused pytest, `system_smoke`, and full pytest
9. Commit and tag once

## Part A: Historical Real Capture

### A1. Model and safety extension

- add credential-ref, transport, real-capture config, run result, and run audit models
- add explicit `acknowledge_credential_redaction`
- add capture profile state for `FULL_INTRADAY_DISABLED`
- keep all non-chart APIs blocked

### A2. Guard and credential policy

- block all credential/env reads in pytest
- require explicit local credential ref only outside pytest
- validate safe local output roots
- validate bounded symbols/date ranges/request count/page count
- scan user-facing output for token/header/account/order markers

### A3. Transport and runner

- implement mock and real chart transport boundary
- use real transport only after full opt-in validation
- run task-by-task with bounded timeout and retry count
- cap continuation loops
- redact raw responses before persistence
- update raw lake, normalization, coverage, and manifest

### A4. CLI and smoke

- add:
  - `historical-market-data-real-capture-preflight-report`
  - `historical-market-data-real-capture-plan-report`
  - `historical-market-data-real-capture-run`
  - `historical-market-data-real-capture-audit-report`
- keep `system_smoke` on mock transport only

## Part B: Offline Strategy Layer

### B1. Public model surface

- add all `offline_strategy_*` enums, templates, candidate, signal, trade intent, simulated trade, walk-forward, metrics, gate, artifact, safety, and gap models
- ensure `OfflineStrategyTradeIntent` is non-executable, offline-only, simulated-only, and report-only

### B2. Template and indicator layer

- implement:
  - `VOLUME_PULLBACK_LONG`
  - `UPPER_WICK_REVERSAL`
  - `RSI_OVERSOLD_REBOUND`
  - `MACD_RSI_MOMENTUM`
- reuse existing repo-local MACD, RSI, HMA, and divergence calculations where safe
- keep promotion direction default `LONG_ONLY`

### B3. Search and compatibility

- implement manifest-first input loading
- allow direct OHLCV row fixtures for tests and smoke
- add dataset compatibility checks for required OHLCV/high-low/volume/interval coverage
- implement bounded grid search only with strict combination caps

### B4. Walk-forward and backtest

- implement default anchored chronological walk-forward with purge/embargo
- allow rolling chronological walk-forward as explicit opt-in secondary evidence only
- implement conservative next-bar fill for all assets
- support configurable fee/slippage and asset/liquidity profiles

### B5. Metrics and gate

- compute trade count, OOS sample count, cumulative return, expectancy, profit factor, win rate, max drawdown, stop-hit rate, turnover, and exposure when configured
- implement stability-first promotion gate
- anchored mode determines main promotion result
- rolling-only success may produce only `WATCHLIST_ONLY_ROLLING_ONLY` or `RESEARCH_ONLY`

### B6. CLI and smoke

- add:
  - `offline-strategy-template-catalog-report`
  - `offline-strategy-dataset-compatibility-report`
  - `offline-strategy-training-plan-report`
  - `offline-strategy-walk-forward-report`
  - `offline-strategy-backtest-report`
  - `offline-strategy-metric-report`
  - `offline-strategy-promotion-gate-report`
  - `offline-strategy-artifact-manifest-report`
  - `offline-strategy-safety-report`
  - `offline-strategy-gap-report`
- add small deterministic offline smoke path

## Verification

### Focused tests

- historical real capture:
  - models
  - guard
  - credential ref
  - transport
  - runner
- offline strategy:
  - models
  - guard
  - template catalog
  - indicators
  - signals
  - parameter space
  - dataset compatibility
  - walk-forward
  - backtest
  - metrics
  - promotion gate
  - training plan
  - CLI

### Integration verification

- mock real-capture runner end-to-end
- offline strategy pipeline from local manifest or direct OHLCV fixture
- `system_smoke`
- full `pytest`

## Acceptance

v15 is complete when:

- real Kiwoom read-only historical chart capture is available only under explicit local opt-in and never in pytest
- raw responses remain redacted
- normalized OHLCV manifest generation remains intact
- offline strategy pipeline runs from manifest input without network access
- promoted candidates remain offline-only, non-executable, and long-only by default
- all focused tests, `system_smoke`, and full `pytest` pass
