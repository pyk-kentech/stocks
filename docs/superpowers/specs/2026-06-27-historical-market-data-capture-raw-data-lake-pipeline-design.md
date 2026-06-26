## v14.0 Historical Market Data Capture / Raw Data Lake / OHLCV Normalization Pipeline Design

### Milestone

- Version: `v14.0`
- Final tag: `v14.0.0-historical-market-data-capture-raw-data-lake-pipeline`
- Version discipline: do not create `v14.1`, `v14.2`, or any additional `v14.x` milestone

### Corrected Roadmap

The previously considered v14 offline model training scope is postponed.

Corrected roadmap:

- `v14.0`: Historical Market Data Capture / Raw Data Lake / OHLCV Normalization
- `v15.0`: Offline Model Training / Promotion Gate
- `v16.0`: Forward Paper Trading / Shadow Mode
- `v17.0`: Operational Hardening / Observability

### Goal

Implement the missing historical market data capture layer between Kiwoom chart APIs and the v10 feature-store/training-dataset pipeline.

v14 must provide:

- historical chart capture planning
- local/manual chart response import
- redacted raw chart response lake
- normalized OHLCV storage
- coverage/gap reports
- continuation/page handling model
- dataset profile and capacity guard
- v10 input manifest generation
- v8/v10/v11 integration reports
- strategy research readiness report

v14 is not model training, not paper trading, not live trading, not order execution, not account read, and not account mutation. It must not submit orders, must not call account/order APIs, must not run real network calls in tests, must not read env/credentials/API keys/tokens in tests, and must not output executable orders.

### Missing Gap To Close

v10 assumes that local/manual price-history or locally stored Kiwoom chart history can exist, but the dedicated layer that captures/imports, stores, normalizes, and coverage-checks historical OHLCV is missing.

v14 closes this gap:

Kiwoom chart API or captured chart response
-> local raw data lake
-> normalized OHLCV rows
-> coverage manifest
-> v10-compatible local price-history manifest
-> v10 feature/label/training dataset builder

### Upstream Context

Use existing context from:

- v8.1 Kiwoom chart/OHLCV adapter for `ka10080` and `ka10081`
- v8.7 manual response import harness
- v8.8 final read-only transport / capture / snapshot validation
- v10 feature-store / local price-history / deterministic label derivation design
- v11 paper evaluation pipeline
- v13 controlled execution layer, but v14 must not use execution
- existing local/offline fixture patterns
- existing CLI and `system_smoke` style

### Architecture

v14 uses a new `historical_market_data_*` public layer. Existing v8 chart adapter, v8.7 manual import, and v8.8 readonly transport evidence are reused as input evidence only. Downstream code depends on canonical v14 capture, normalization, coverage, and manifest contracts rather than raw provider semantics.

The pipeline is split into six layers:

1. API catalog and capability layer
   - represent chart API catalog and exact local evidence status
   - `ka10080` and `ka10081` are schema-ready
   - `ka10079`, `ka10082`, `ka10083`, `ka10094` stay capability-only or schema-gap unless exact local evidence exists
2. Capture planning layer
   - build bounded capture plans and per-task request previews
   - real opt-in boundary is represented only through request preview and blocked execution decision
3. Import and raw lake layer
   - import local manual or mocked chart responses
   - redact, classify, and persist raw lake records under safe local roots
   - raw lake is preservation-oriented and not the source of truth
4. Normalization layer
   - transform raw chart responses into canonical OHLCV rows
   - detect duplicates, out-of-order bars, missing fields, and adjustment-policy ambiguity
5. Manifest and coverage layer
   - generate coverage manifest plus normalized OHLCV manifest
   - this coverage + normalized manifest pair is the source of truth
   - derive a v10-compatible local price-history manifest from those manifests
6. Integration and readiness layer
   - produce v8, v10, and v11 integration reports
   - produce storage, freshness, completeness, safety, gap, audit, and strategy research readiness reports

Strict default policy:

- default mode is `MANUAL_IMPORT_ONLY` or `CAPTURE_PLAN_ONLY`
- tests may use manual import, mocked capture, normalize-only, coverage-only, and v10 manifest generation
- tests must never use real network, real provider, real env, real credentials, or account/order APIs
- full all-symbol intraday capture remains disabled by default
- no background polling, no indefinite continuation, and no unbounded merges

### API Evidence and Scope

Kiwoom domestic stock chart API candidates:

- `ka10079`: stock tick chart request
- `ka10080`: stock minute chart request
- `ka10081`: stock daily chart request
- `ka10082`: stock weekly chart request
- `ka10083`: stock monthly chart request
- `ka10094`: stock yearly chart request

Schema-ready initial implementation:

- use exact existing repo evidence for `ka10080` and `ka10081` from the v8 chart adapter
- implement full request/response import and normalization for `ka10080` and `ka10081`

Capability handling:

- `ka10079`, `ka10082`, `ka10083`, and `ka10094` must appear in the API catalog and capability matrix
- if exact schema evidence already exists locally, parser support may be implemented
- if exact schema evidence is missing, mark as `SCHEMA_GAP` or `CAPABILITY_ONLY`
- do not invent request or response fields

Known common Kiwoom REST envelope from existing project evidence:

- provider: Kiwoom REST
- method: POST
- domain enum, not raw URL
- JSON body
- headers:
  - `api-id`
  - `authorization: Bearer <TOKEN_REF_ONLY>`
  - `cont-yn`
  - `next-key`
- continuation:
  - request/response `cont-yn`
  - request/response `next-key`

Known v8 chart evidence:

- `ka10081` daily chart
  - path: `/api/dostk/chart`
  - body fields from existing evidence: `stk_cd`, `base_dt`, `upd_stkpc_tp`
- `ka10080` minute chart
  - path: `/api/dostk/chart`
  - body fields from existing evidence: `stk_cd`, `tic_scope`, `upd_stkpc_tp`, `base_dt`

If exact field names differ in repo-local evidence, defer to existing v8 adapter code and tests.

### Provider and Network Policy

v14 supports three capture paths:

1. Manual local import
   - local raw Kiwoom chart response JSON files
   - safe fixture path only
   - no network
   - default path for tests and smoke
2. Mocked transport capture
   - fake adapter response
   - used in tests
   - no network
   - no env read
   - no credentials
3. Future real opt-in chart capture boundary
   - default blocked
   - not used in tests
   - no real network in pytest
   - requires explicit opt-in flags
   - only schema-ready chart API IDs allowed
   - token provider ref only
   - no raw token/API key output
   - redacted capture only
   - bounded request plan only

Real opt-in chart capture requires all of:

- `allow_real_chart_capture = true`
- `acknowledge_readonly_only = true`
- `acknowledge_no_orders = true`
- `acknowledge_user_initiated = true`
- `acknowledge_rate_limit_and_capacity = true`
- API ID allowlisted and schema-ready
- symbol list bounded
- date range bounded
- interval/profile bounded
- token provider explicitly configured
- runtime is not pytest
- response capture redaction policy passes
- no order/account API markers
- no raw credential output

If any condition is missing:

- block real capture
- no network call
- produce safety/gap report

### Core Models

Create:

- `HistoricalMarketDataProvider`
- `HistoricalMarketDataApiId`
- `HistoricalMarketDataInterval`
- `HistoricalMarketDataMode`
- `HistoricalMarketDataSourceKind`
- `HistoricalMarketDataCaptureProfile`
- `HistoricalMarketDataStorageFormat`
- `HistoricalMarketDataApiCapability`
- `HistoricalMarketDataSchemaStatus`
- `HistoricalMarketDataCredentialPolicy`
- `HistoricalMarketDataOptIn`
- `HistoricalChartRequestSpec`
- `HistoricalChartRequestPreview`
- `HistoricalChartCapturePlan`
- `HistoricalChartCaptureTask`
- `HistoricalChartCaptureDecision`
- `HistoricalChartRawResponse`
- `HistoricalChartRawLakeRecord`
- `HistoricalOhlcvRow`
- `HistoricalOhlcvPartitionSpec`
- `HistoricalOhlcvDatasetManifest`
- `HistoricalMarketDataCoverageReport`
- `HistoricalMarketDataGapReport`
- `HistoricalMarketDataFreshnessReport`
- `HistoricalMarketDataCompletenessReport`
- `HistoricalMarketDataStorageCapabilityReport`
- `HistoricalMarketDataV8IntegrationReport`
- `HistoricalMarketDataV10IntegrationReport`
- `HistoricalMarketDataV11IntegrationReport`
- `HistoricalMarketDataStrategyResearchReadinessReport`
- `HistoricalMarketDataSafetyReport`
- `HistoricalMarketDataAuditRecord`
- `HistoricalMarketDataPipelineResult`

Model boundaries:

- `HistoricalChartRawResponse`
  - imported or captured provider envelope plus payload summary
  - always redacted
- `HistoricalChartRawLakeRecord`
  - persisted raw capture metadata under safe local roots
  - not the source of truth
- `HistoricalOhlcvRow`
  - canonical normalized OHLCV row with interval, bar timestamps, OHLCV, adjustment policy, lineage, and quality/gap flags
- `HistoricalMarketDataCoverageReport`
  - symbol/date/interval/API coverage, continuation completeness, and missing-page status
- `HistoricalOhlcvDatasetManifest`
  - normalized partitions, row counts, readiness, and storage references
  - one half of the source-of-truth pair
- `HistoricalMarketDataV10IntegrationReport`
  - explicit bridge status into v10 `price_history_rows`
- `HistoricalMarketDataStrategyResearchReadinessReport`
  - strategy-family support classification based on available normalized data

Source-of-truth rule:

- source of truth is the `coverage manifest + normalized OHLCV manifest` pair
- raw lake records are preservation artifacts only
- Parquet, DuckDB, or Polars artifacts are optional materializations and never the source of truth

### Capture Modes

Represent:

- `MANUAL_IMPORT_ONLY`
- `MOCKED_CAPTURE_ONLY`
- `CAPTURE_PLAN_ONLY`
- `REAL_READONLY_CHART_CAPTURE_OPT_IN`
- `NORMALIZE_ONLY`
- `COVERAGE_REPORT_ONLY`
- `V10_MANIFEST_ONLY`
- `REJECTED`

Default:

- `MANUAL_IMPORT_ONLY` or `CAPTURE_PLAN_ONLY`

Tests may use:

- manual import
- mocked capture
- normalize-only
- coverage-only
- v10 manifest generation

Tests must never use:

- real network
- real provider
- real env
- real credentials
- order/account APIs

### Dataset and Capture Profiles

Create:

- `SMOKE_PROFILE`
- `DAILY_RESEARCH_PROFILE`
- `INTRADAY_CANDIDATE_PROFILE`
- `FULL_INTRADAY_DISABLED`

Profile rules:

`SMOKE_PROFILE`

- tiny local fixtures
- <= 3 symbols
- <= 30 days
- in-memory or JSON only
- tests only

`DAILY_RESEARCH_PROFILE`

- daily bars
- bounded symbols
- bounded date range
- intended for v10 labels and training dataset
- safe for 64GB RAM with partitioned storage
- default realistic profile

`INTRADAY_CANDIDATE_PROFILE`

- candidate symbols only
- 5m, 15m, or minute bars depending on evidence
- bounded date range
- partitioned only
- no full in-memory all-symbol merge
- requires capacity warning acknowledgment for large runs

`FULL_INTRADAY_DISABLED`

- all-symbol all-minute/tick multi-year capture
- disabled by default
- never allowed in tests
- requires explicit capacity acknowledgment and future planning
- must not be implemented as default materialization

Hard rules:

- do not build full all-symbol all-minute datasets by default
- do not perform unbounded in-memory merges
- do not retry indefinitely
- do not schedule background polling

### Raw Data Lake

Implement local raw data lake under safe ignored roots:

- `local_data/historical_market_data/raw/kiwoom/chart/`
- `local_data/historical_market_data/normalized/ohlcv/`
- `local_data/historical_market_data/manifests/`
- `local_data/historical_market_data/audit/`

Ensure `.gitignore` covers:

- `local_data/historical_market_data/`
- raw captured chart responses
- normalized OHLCV output
- runtime manifests that are not intended for commit
- audit captures with local paths

Raw response storage rules:

- raw response may be stored only after redaction scan
- authorization headers must never be stored
- tokens, API keys, and app secrets must never be stored
- account/order fields must block capture
- raw response source path must be sanitized
- no path traversal
- no writes outside safe root
- response metadata may store only:
  - provider
  - api_id
  - symbol
  - interval
  - request date or base date
  - captured_at
  - observed_at when available
  - available_at
  - cont_yn
  - redacted or omitted `next_key`
  - status code if mocked/real boundary metadata exists
  - source_ref
  - redaction status

### Normalized OHLCV

Canonical normalized row fields:

- `instrument_id`
- `provider_symbol`
- `market`
- `currency`
- `interval`
- `bar_start`
- `bar_end`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `trading_value` when available
- `adjustment_policy`
- `price_adjustment_flag`
- `source_api_id`
- `source_ref`
- `raw_record_ref`
- `observed_at`
- `available_at`
- `capture_time`
- `quality_flags`
- `gap_flags`
- `non_executable`
- `report_only`

Normalization rules:

- signed numeric strings must be parsed safely
- comma formatting must be handled when present
- negative sign from Kiwoom signed fields must be normalized carefully
- timestamps must be timezone-aware or use an explicit timezone policy
- daily bars use Korea market calendar semantics when available, otherwise mark calendar gap
- minute bars require bar timestamp precision
- duplicate bars must be detected
- out-of-order bars must be sorted and reported
- missing OHLCV fields produce schema/data gap
- zero or negative invalid prices produce quality warnings or rejection
- missing volume produces a data gap depending on interval
- split/adjustment policy must be explicit:
  - `RAW_PRICE`
  - `ADJUSTED_PRICE`
  - `UNKNOWN_ADJUSTMENT_POLICY`
- unknown adjustment policy must not block smoke but must downgrade research readiness

### Storage Formats

Support:

- `IN_MEMORY`
- `JSON`
- `JSONL`
- `PARQUET`
- `DUCKDB`
- `POLARS`
- `UNSUPPORTED`

Storage rules:

- in-memory and JSON manifest modes must always work
- JSONL may be implemented if simple
- Parquet, DuckDB, and Polars are optional
- missing optional dependencies return `DEPENDENCY_GAP`
- no import-time crash if dependency is missing
- no remote scan
- no network
- no unsafe path writes

Optional Parquet, DuckDB, and Polars rules:

- local-only
- optional
- partitioned by safe keys:
  - provider
  - api_id
  - interval
  - market
  - symbol or symbol bucket
  - date
- never the source of truth
- manifests remain the source of truth

### Capture Planning

Capture plan engine inputs:

- provider
- api_id
- symbols
- interval
- date range
- profile
- max requests
- max symbols
- max days
- rate-limit hint
- continuation policy

Capture plan outputs:

- task list
- estimated request count
- capacity estimate
- storage estimate
- profile compliance result
- blocked/gap reasons
- non-executable report

Planning rules:

- bounded symbol list required
- bounded date range required
- bounded request count required
- continuation max page count required
- no infinite continuation loop
- rate-limit hint recorded
- if the plan exceeds profile limits, reject or require explicit capacity acknowledgment
- no real call during planning

### Import Engine

Manual import engine:

- reads local raw Kiwoom chart response fixture files
- validates source path
- detects API ID
- detects symbol, interval, and base date where available
- routes to parser and normalizer
- writes or returns raw lake record and normalized rows
- produces import report

Supported import inputs:

- local JSON chart response files
- mocked chart response payloads in tests

Import rules:

- no remote path
- no parquet source
- no path traversal
- redaction scan before persistence
- no invented schema fields
- capability-only APIs may be classified and reported without normalization

### Coverage and Continuation

Coverage engine responsibilities:

- compute symbol/date/interval/API coverage
- report missing response pages
- report continuation completeness
- report stale or partial imports
- produce a coverage manifest consumable by downstream integration

Continuation model rules:

- request and response continuation use `cont-yn` and `next-key`
- request preview must surface continuation metadata only in redacted/non-sensitive form
- continuation planning must carry maximum page bounds
- missing continuation evidence produces `DATA_GAP` or `CAPABILITY_ONLY`
- no infinite continuation retries

### V10, V8, and V11 Integration

`HistoricalMarketDataV8IntegrationReport`

- verifies that v14 uses exact local v8 chart evidence for `ka10080` and `ka10081`
- reports which APIs are schema-ready, capability-only, or schema-gap

`HistoricalMarketDataV10IntegrationReport`

- verifies that normalized OHLCV can be translated into a v10-compatible local price-history manifest
- reports readiness for v10 `price_history_rows`
- reports interval, coverage, and adjustment-policy gaps that would affect label derivation or feature assembly

`HistoricalMarketDataV11IntegrationReport`

- verifies whether normalized OHLCV is sufficient to support v11 paper evaluation bar usage
- reports daily/minute chart readiness for offline replay and fill/portfolio evaluation contexts

### Strategy Research Readiness

Add `HistoricalMarketDataStrategyResearchReadinessReport`.

This report is data-readiness only. v14 must not train strategies.

Supported or supportable strategy families when captured normalized data is sufficient:

- MACD/RSI crossover and pullback strategies
- RSI divergence strategies
- HMA trend-filter strategies
- volume-confirmed momentum strategies
- reward/risk and stop/target label simulation

Explicit unsupported or partial strategy families:

- CVD/order-flow strategies require tick/trade/order-flow data
- POC/volume-profile strategies require intraday volume-at-price or sufficient intraday reconstruction
- true liquidity absorption detection is not supported by daily OHLCV alone

Readiness report outputs must classify strategy families as:

- `SUPPORTED`
- `PARTIAL`
- `UNSUPPORTED`

with explicit reasons tied to interval coverage, intraday availability, tick/order-flow absence, or adjustment-policy ambiguity.

v15, not v14, will implement:

- strategy templates
- parameter search
- walk-forward validation
- model training
- promotion gates

### Safety and Audit

Safety guarantees:

- no real provider/network calls in tests
- no env/credential/API key/token reads in tests
- no account/order APIs
- no account mutation
- no executable order output
- no live trading or execution path

Audit records must capture:

- action id
- timestamp
- source refs
- api id
- symbol
- interval
- mode
- decision
- redaction status
- non-executable/report-only flags
- reason codes

Audit records must not capture:

- raw authorization header
- token
- API key
- app secret
- account/order data
- unsafe local paths

### CLI Surface

v14 should expose report-oriented CLI commands for:

- API capability catalog
- chart request preview
- capture plan report
- import report
- raw lake report
- normalization report
- coverage report
- v10 manifest report
- v8 integration report
- v10 integration report
- v11 integration report
- strategy research readiness report
- storage capability report
- safety report
- gap report

CLI behavior:

- default to report-only or plan-only flows
- manual import and mocked capture only in tests
- no real network/provider/env/credential/account/order usage in tests
- redacted JSON output
- any real opt-in capture representation remains blocked by default and excluded from tests

### System Smoke

System smoke uses tiny local fixtures to verify:

- API catalog generation
- bounded capture plan generation
- manual import routing
- raw lake redacted storage path
- OHLCV normalization
- coverage manifest generation
- v10-compatible manifest generation
- v8/v10/v11 integration reports
- strategy research readiness report
- no network
- no env read
- no account/order path
- no executable output

At least one blocked path should be included:

- unsupported API schema gap
- continuation overflow or missing page
- unsafe raw response metadata

### Files To Create Or Modify

- `docs/superpowers/plans/2026-06-18-v14-historical-market-data-capture-raw-data-lake-pipeline.md`
- `src/stock_risk_mcp/historical_market_data_models.py`
- `src/stock_risk_mcp/historical_market_data_guard.py`
- `src/stock_risk_mcp/historical_market_data_fixture.py`
- `src/stock_risk_mcp/historical_market_data_api_catalog.py`
- `src/stock_risk_mcp/historical_market_data_capture_plan_engine.py`
- `src/stock_risk_mcp/historical_market_data_import_engine.py`
- `src/stock_risk_mcp/historical_market_data_raw_lake.py`
- `src/stock_risk_mcp/historical_market_data_normalizer.py`
- `src/stock_risk_mcp/historical_market_data_coverage_engine.py`
- `src/stock_risk_mcp/historical_market_data_manifest_engine.py`
- `src/stock_risk_mcp/historical_market_data_integration_engine.py`
- `src/stock_risk_mcp/cli.py`
- `src/stock_risk_mcp/system_smoke.py`
- `tests/test_historical_market_data_models.py`
- `tests/test_historical_market_data_guard.py`
- `tests/test_historical_market_data_api_catalog.py`
- `tests/test_historical_market_data_capture_plan_engine.py`
- `tests/test_historical_market_data_import_engine.py`
- `tests/test_historical_market_data_raw_lake.py`
- `tests/test_historical_market_data_normalizer.py`
- `tests/test_historical_market_data_coverage_engine.py`
- `tests/test_historical_market_data_integration_cli.py`
- `tests/test_system_smoke.py`

### Test Rules

Tests must cover:

- schema-ready `ka10080` and `ka10081` request preview and import behavior
- capability-only or schema-gap handling for `ka10079`, `ka10082`, `ka10083`, `ka10094`
- safe local path enforcement
- raw lake redaction enforcement
- OHLCV normalization edge cases
- duplicate/out-of-order bar handling
- coverage and continuation gap reporting
- v10 manifest bridge generation
- strategy research readiness classification
- CLI wiring
- system smoke integration

Hard test constraints:

- no real network/provider call in tests
- no real env/credential/API key/token read in tests
- no account/order API use in tests
- no executable order output in tests

### Milestone Close Criteria

v14.0 closes when all of the following are true:

- new `historical_market_data_*` public surface is complete
- bounded capture planning works
- redacted raw lake storage works under safe local roots
- normalized OHLCV rows are generated for schema-ready APIs
- coverage manifest plus normalized manifest pair is generated and acts as source of truth
- v10-compatible local price-history manifest generation works
- v8, v10, and v11 integration reports are generated
- strategy research readiness report is generated
- focused pytest passes
- full pytest passes
- final tag is created once and only once:
  - `v14.0.0-historical-market-data-capture-raw-data-lake-pipeline`

### Explicit Non-Goals

v14 is not:

- model training
- paper trading
- live trading
- order execution
- account read
- account mutation
- strategy template implementation
- parameter search
- walk-forward validation
- promotion gating

### Implementation Notes

Implementation should follow repository patterns established by:

- `kiwoom_rest_readonly_chart_*`
- `kiwoom_manual_response_import_*`
- `kiwoom_readonly_final_transport_*`
- `feature_store_*`
- `paper_evaluation_*`
- existing local/offline fixture, CLI, and `system_smoke` conventions

The v14 contract stays data-capture, normalization, manifest, and readiness oriented. Strategy training or validation remains outside v14 and starts in v15.
