# v7.9.1 Global Market Data Provider Registry / Canonical Data Contract

## Goal
Create a local, offline, report-only provider registry and canonical data contract layer that all future data-consuming modules can reference without making any provider call.

## Scope
- Provider candidate registry
- Module data requirement registry
- Readiness matrix
- Canonical provider-independent data contract
- Symbol mapping surface
- Report-only provider selection logic
- Local JSON fixture loader
- CLI reports
- `system_smoke` coverage

## Hard Boundaries
- No real data fetch
- No network or provider call
- No broker, Kiwoom, IBKR, Databento, CME, Yahoo, Investing.com, FRED, BLS, BEA, Fed, ECOS/BOK execution
- No API key, credential, token, or account read
- No live/order/account/prod/autonomous path
- Report-only and non-executable only
- Parquet remains unsupported

## Core Concepts

### Provider Candidate
- provider name and type
- free/paid/manual/local classification
- official/unofficial/internal/delayed flags
- historical/live/delayed/read-only support
- API key and subscription requirement flags
- latency class and expected freshness
- allowed/disallowed use cases
- implementation status and risk note

### Module Data Requirement
For each downstream module:
- required and optional data classes
- minimum readiness level
- freshness and `available_at` requirement
- `source_ref` requirement
- historical depth requirement
- training-grade and live-read-only flags
- fallback policy

### Canonical Data Contract
Normalized provider-independent record fields:
- canonical instrument key
- provider symbol
- data class
- observed_at / available_at
- value and OHLCV fields where relevant
- percent change
- currency, market, timezone
- data delay seconds
- source provider and source ref
- quality flags
- stale flag
- gap reason
- corporate-action adjusted flag
- survivorship-safe flag

### Provider Selection Policy
- Pick preferred provider per data class and required readiness
- Keep fallback provider separately
- Emit gaps for missing subscription evidence, license gap, latency gap, coverage gap, symbol mapping gap
- Never mark unresolved providers as fake-ready

## Initial Policy
- Futures (`NQ_FUTURES`, `ES_FUTURES`): `DATABENTO` preferred for backtest/training, `IBKR` candidate for live read-only, delayed web sources only sanity-check
- Volatility / FX / rates: split-source candidates allowed, unresolved coverage stays `GAP`
- Economic calendar: official sources preferred; `INVESTING_CALENDAR` only fallback candidate
- `CNN_FEAR_GREED`: sentiment feature only, not oracle
- `MANUAL_CSV` and `LOCAL_FIXTURE`: valid for development; not live-read-only substitutes

## Reports
- global provider registry report
- module data requirement report
- provider readiness matrix report
- canonical data contract report
- symbol mapping report
- provider selection report
- provider gap report
- redacted audit report

## CLI
- `market-data-provider-registry-check`
- `global-provider-registry-report`
- `module-data-requirement-report`
- `provider-readiness-matrix-report`
- `canonical-data-contract-report`
- `symbol-mapping-report`
- `provider-selection-report`
- `market-data-provider-gap-report`

## system_smoke
One local fixture-driven run that verifies:
- registry and reports generate
- layer is local/offline/report-only
- no provider/network/broker path exists
- no credential or API key read occurs
- parquet remains unsupported

## Verification
- Focused provider-registry tests
- `tests/test_system_smoke.py`
- full `pytest -q`
