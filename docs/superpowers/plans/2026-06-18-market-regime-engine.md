# v7.9 Market Regime Engine

## Goal
Build a local, offline, report-only market regime engine that classifies broad market conditions from point-in-time-safe cross-asset snapshots and emits downstream risk constraints, not trading instructions.

## Scope
- Market regime input snapshot for NQ, ES, VIX, DXY, U.S. 10Y, USD/KRW, optional CNN Fear & Greed ref
- Deterministic feature normalization
- Risk appetite / direction / volatility / stress classifications
- Readiness decision and report surfaces
- Local JSON fixture loader
- CLI report commands
- `system_smoke` coverage

## Core Rules
- Local fixture only
- Offline only
- Report-only
- Non-executable
- No broker, Kiwoom, LS, account, order, WebSocket, network, or LIVE/PROD paths
- No raw credential, token, or account output
- No profitable-action encoding such as buy, sell, inverse, or execution approval
- Parquet remains unsupported

## Input Model
- `MarketRegimeInputSnapshot`
  - `snapshot_id`
  - `anchor_at`
  - `observed_at`
  - `available_at`
  - source refs for NQ, ES, VIX, DXY, 10Y, USD/KRW
  - optional `cnn_fear_greed_feature_ref`
  - per-asset snapshot values and one-day change proxies
  - freshness policy metadata

## Derived Features
- `nq_trend`
- `es_trend`
- `nq_es_divergence`
- `vix_level_bucket`
- `vix_change_bucket`
- `dxy_trend`
- `us10y_trend`
- `usdkrw_stress_bucket`
- `cross_asset_confirmation_score`
- `cross_asset_conflict_score`
- `data_staleness_score`

## Classification Surface
- Risk appetite: `RISK_ON`, `RISK_OFF`, `MIXED`, `UNKNOWN`
- Market direction: `BULL`, `BEAR`, `SIDEWAYS`, `TRANSITION`, `UNKNOWN`
- Volatility state: `HIGH_VOL`, `NORMAL_VOL`, `LOW_VOL`, `VOL_EXPANSION`, `UNKNOWN`
- Stress state: `NORMAL`, `FX_STRESS`, `RATE_STRESS`, `DOLLAR_STRESS`, `CROSS_ASSET_STRESS`, `UNKNOWN`

## Decision Surface
- `BLOCKED`
- `RESEARCH_ONLY`
- `REGIME_READY`
- `TRAINING_FEATURE_READY`
- `GAP`
- `REJECTED`

`BLOCKED` is for leakage or impossible/unsafe dependencies. `GAP` is for stale or missing required evidence. `TRAINING_FEATURE_READY` means the feature surface is usable downstream, not executable.

## Classification Policy
- Deterministic scoring only
- NQ/ES positive with calm vol and weak dollar stress can support `RISK_ON`
- NQ/ES negative with elevated VIX and stress markers can support `RISK_OFF`
- Divergence or conflicting cross-asset signals lower confidence and increase conflict score
- Missing optional CNN Fear & Greed only produces a note
- Regime output may recommend constraints such as `WATCH_ONLY`, `REDUCE_NEW_ENTRIES`, `REQUIRE_SMALLER_POSITION_SIZING`, `PREFER_CASH_CONTROL`, `REQUIRE_EVENT_RISK_CHECK`, `REQUIRE_BREADTH_CONFIRMATION`, `BLOCK_PROMOTION_IF_EVIDENCE_IS_INSUFFICIENT`
- No downstream constraint may imply an execution instruction

## Guard Policy
- Missing `available_at` => `GAP` or `BLOCKED`
- `available_at > anchor_at` => future leakage => `BLOCKED`
- stale critical data => `GAP`
- explicit source refs required for all core assets
- remote URLs and parquet rejected at fixture boundary
- secret/token/account/auth/order/live/prod/network/provider markers rejected

## Outputs
- summary report
- cross-asset input snapshot report
- risk appetite report
- direction regime report
- volatility regime report
- FX/rate/dollar stress report
- cross-asset conflict report
- downstream constraint report
- training feature integration report
- gap report
- redacted audit record

## CLI
- `market-regime-check`
- `market-regime-summary-report`
- `market-regime-input-snapshot-report`
- `risk-appetite-report`
- `market-direction-regime-report`
- `volatility-regime-report`
- `fx-rate-dollar-stress-report`
- `cross-asset-conflict-report`
- `market-regime-downstream-constraint-report`
- `market-regime-training-feature-report`
- `market-regime-gap-report`

## system_smoke
Add one local fixture-driven run that confirms:
- report generation succeeds
- decision is non-executable and local/offline
- no broker/network/Kiwoom/order/account/live path exists
- parquet remains unsupported

## Verification
- Focused: regime model/engine/CLI tests
- `tests/test_system_smoke.py`
- full `pytest -q`
