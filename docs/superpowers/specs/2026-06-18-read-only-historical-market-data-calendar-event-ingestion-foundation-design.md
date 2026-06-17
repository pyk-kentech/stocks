# v5.0 Read-Only Historical Market Data and Calendar/Event Ingestion Foundation Design

## Scope

v5.0 defines the first design-only bridge from the completed v4 fixture-only
offline pipeline to future offline research over already-local historical files.

The milestone does not implement ingestion runtime code. It defines the
architecture, schema boundaries, validation expectations, safety constraints,
manifest structure, audit expectations, and downstream integration references
for:

- local historical OHLCV files
- local trading calendar files
- local market event files
- local corporate event files

The v5.0 design is intentionally:

- local-file-only
- read-only
- non-executable
- no-network
- no-provider-API
- design-only

## Release Position

v5.0 begins after these confirmed completed lines:

- `v3.12.0-offline-prompt-pack-advisory-task-suite` -> `656c7ea`
- `v4.13.0-domestic-offline-pipeline-final-acceptance-handoff` -> `ac8f1e4`

This matters because v5 must not start by expanding execution authority. The
v4 line closed as fixture-only, offline, shadow/report-only, and
non-executable. v5.0 therefore starts with read-only historical data and
calendar/event context, not live trading, not real orders, and not provider
connectivity.

v5.0 is the first bridge from:

- fixture-derived offline evidence

to:

- validated historical OHLCV snapshots
- validated trading-session calendars
- validated macro/market/corporate event context

The bridge remains offline research infrastructure only.

## Architecture Position

The recommended v5.0 architecture uses two first-class units.

Primary unit:

- `HistoricalMarketDataSnapshot`

Secondary first-class unit:

- `HistoricalCalendarEventSnapshot`

Both units are defined only for already-local `CSV` or `JSONL` inputs. Both are
read-only, non-executable, no-network, and no-provider-API. Neither unit is
allowed to activate replay, labeling, training, execution approval, broker
connectivity, or model invocation in v5.0.

The design purpose is to define how local historical files are:

- described
- normalized
- validated
- gap-reported
- quality-reported
- audited
- manifested

so that future milestones can consume them under the same fail-closed safety
philosophy already established in v3 and v4.

## Future Offline Integration References

v5.0 does not implement real integration, but it should define how future
milestones may consume the validated outputs.

Future consumption references:

- v4.2 normalized event builders may derive normalized historical event context
  from validated OHLCV snapshots and validated calendar/event snapshots
- v4.3 scanner candidate generation may consume historical price snapshots and
  session/event context for offline candidate reconstruction
- v4.5 replay harness may consume validated OHLCV histories instead of
  fixture-only price paths
- v4.8 outcome labeling may consume forward observation windows counted by
  trading sessions, not raw calendar days
- v4.10 dataset pack builders may consume replay and outcome artifacts that were
  derived from validated historical snapshots
- v4.11/v4.12 regime-aware layers may consume index/sector historical snapshots
  plus macro event context

These are design references only. v5.0 does not implement replay integration,
outcome generation, dataset generation, or regime inference.

## Core Principle

v5.0 is validation-first and manifest-first.

Historical ingestion readiness must be decided by:

- explicit source descriptors
- explicit track and market profile resolution
- explicit provenance
- explicit safety boundaries
- deterministic validation reports
- deterministic gap reports
- deterministic quality reports
- explicit audit metadata

No local historical file should be treated as implicitly usable simply because
it exists on disk.

## Hard Non-Goals

v5.0 does not:

- implement runtime ingestion code
- fetch real market data
- fetch real calendar data
- crawl Investing.com
- crawl FINVIZ
- ingest news
- call Google AI Studio / Gemini
- call Kiwoom APIs
- call LS APIs
- call broker APIs
- call provider APIs
- access accounts, credentials, tokens, or secrets
- connect WebSocket or realtime feeds
- fetch realtime FX
- create `OrderIntent`
- create order drafts
- enable execution approval
- use `LIVE`
- use `PROD`
- train ML models
- call cloud LLMs
- call local model runtimes
- execute prompt packs or prompt stubs

## Scope Boundary and Future Roadmap

### v5.0 In-Scope

v5.0 is design-only for:

- local-file historical OHLCV foundation
- local-file trading calendar foundation
- local-file market event foundation
- local-file corporate event foundation
- manifest, validation, quality, gap, audit, and safety boundary design

### Explicitly Deferred Milestones

- v5.1 local file ingestion implementation
- v5.2 historical replay dataset generation
- v5.3 historical outcome labeling and calendar-aware forward observation
  windows
- v5.4 Investing.com calendar crawler implementation, read-only snapshot only
- v5.5 calendar diff/reconciliation and calendar quality reporting
- v5.6 FINVIZ snapshot feature ingestion design
- v5.7 FINVIZ read-only scraper or local feature adapter
- v5.8 news title packet ingestion design
- v5.9 deterministic news tagging
- v5.10 optional Google AI Studio / Gemini report-only NLP summarization
- v6.x or later read-only provider adapters, potentially LS read-only
- v7 realtime read-only paper-shadow
- v8 account read-only
- v9 order dry-run/mock
- v10+ limited live execution only after separate explicit approval

Future-source roadmap items must remain clearly separated from v5.0. They are
documented only as provenance candidates or future acquisition paths. They do
not become executable scope in this milestone.

## Supported Initial Source Types

Initial v5.0 supported source types are:

- `local_csv`
- `local_jsonl`

Explicit deferred type:

- `local_parquet`

`local_parquet` is:

- future optional only
- not part of initial v5.0 support
- not part of v5.0 fixtures
- not part of v5.0 CLI proposals
- not part of v5.0 validation requirements

No network source is allowed in v5.0.

Disallowed source classes in v5.0:

- remote URL
- provider API
- Kiwoom read path
- LS read path
- broker read path
- account read path
- credential-backed source
- token-backed source

## Track and Market Boundary

`StrategyTrack` is mandatory for all historical market data and calendar/event
design units.

Rules:

- `DOMESTIC_KR` is the primary supported v5.0 track
- `OVERSEAS_US` may be described for future local-file-only use, but must remain
  unsupported or explicit report-only unless the track and market profile are
  safely resolved
- `MarketProfile` must be resolved for every ingestible source descriptor
- missing `MarketProfile` must fail closed
- currency must match market profile unless explicit report-only downgrade is
  configured
- `DOMESTIC_KR` records should resolve to `KRW`
- `OVERSEAS_US` design references, when present, should resolve to `USD`

Cross-track leakage must be treated as a validation defect, not as a warning to
be silently tolerated.

## Architecture And Dependency Boundary

The future implementation should follow the same pure-core plus thin-service
pattern used in earlier milestones.

Recommended logical units for later implementation:

- market-data models
- calendar/event models
- strict local fixture/file loaders
- pure validation engines
- pure quality/gap report engines
- thin orchestration services
- CLI wrappers

Core modules must remain free of:

- broker imports
- Kiwoom imports
- LS imports
- account imports
- order imports
- credential imports
- token imports
- provider API imports
- network imports
- cloud imports
- local model runtime imports
- training imports
- execution approval imports

## Primary Unit: HistoricalMarketDataSnapshot

`HistoricalMarketDataSnapshot` is the primary v5.0 unit.

Its job is to represent a validated or validation-ready batch of already-local
historical OHLCV records under one explicit ingestion boundary.

It should aggregate or reference:

- `HistoricalDataIngestionConfig`
- `HistoricalDataSourceDescriptor`
- `HistoricalOHLCVRecord`
- `HistoricalMarketDataManifest`
- `HistoricalDataValidationReport`
- `HistoricalDataGapReport`
- `HistoricalDataQualityReport`
- `HistoricalDataSafetyBoundary`
- `HistoricalDataAuditRecord`
- `HistoricalDataProviderProvenance`
- `HistoricalDataAdjustmentPolicy`

It is the primary unit because replay, outcome labeling, regime context, and
dataset export all depend first on trustworthy historical price history.

## Secondary First-Class Unit: HistoricalCalendarEventSnapshot

`HistoricalCalendarEventSnapshot` is a secondary first-class v5.0 unit.

It is not a side note or optional metadata bag. It is a peer design unit
because reliable offline replay, calendar-aware forward windows, early-close
handling, corporate action context, and macro event context all depend on
calendar/event normalization that is separate from OHLCV rows themselves.

`HistoricalCalendarEventSnapshot` should aggregate or reference:

- `TradingSessionRecord`
- `MarketEventRecord`
- `CorporateEventRecord`
- `HistoricalCalendarManifest`
- `CalendarValidationReport`
- `CalendarGapReport`
- `CalendarSafetyBoundary`

It represents a validated or validation-ready batch of already-local trading
session and event context records under one explicit calendar/event ingestion
boundary.

## Historical Market Data Schemas

### HistoricalDataIngestionConfig

Recommended fields:

- `config_id`
- `strategy_track`
- `market_profile_id`
- `source_type`
- `strict_validation_mode`
- `allow_report_only_downgrade`
- `currency_mismatch_policy`
- `duplicate_record_policy`
- `missing_session_policy`
- `stale_batch_policy`
- `unsupported_track_policy`
- `unsafe_source_policy`
- `non_executable`
- `read_only`
- `network_access_allowed=false`
- `provider_api_allowed=false`

### HistoricalDataSourceDescriptor

Recommended fields:

- `source_descriptor_id`
- `source_type`
- `local_file_path`
- `declared_format`
- `declared_content_type`
- `strategy_track`
- `market_profile_id`
- `source_id`
- `source_vendor_name`
- `source_reliability_tier`
- `path_safety_class`
- `timezone`
- `currency`
- `source_symbol_namespace`
- `contains_adjusted_prices`
- `contains_unadjusted_prices`
- `contains_turnover`
- `contains_trade_value`
- `report_only`
- `read_only`
- `non_executable`

### HistoricalOHLCVRecord

Canonical required fields:

- `symbol`
- `market`
- `timestamp`
- `timezone`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `currency`
- `source_id`
- `ingestion_batch_id`

Optional fields:

- `adjusted_close`
- `turnover`
- `trade_value`
- `listed_market_segment`
- `data_vendor_note`
- `corporate_action_adjustment_flag`
- `split_adjustment_flag`
- `dividend_adjustment_flag`
- `source_symbol`
- `canonical_symbol`

### HistoricalDataAdjustmentPolicy

Recommended fields:

- `policy_id`
- `price_adjustment_mode`
- `split_adjustment_expected`
- `dividend_adjustment_expected`
- `corporate_action_backfill_expected`
- `adjusted_close_required`
- `mixed_adjustment_state_allowed`
- `report_only_if_uncertain`

### HistoricalDataProviderProvenance

Recommended fields:

- `provenance_id`
- `source_family`
- `source_name`
- `source_tier`
- `acquisition_mode`
- `original_export_context`
- `local_export_timestamp`
- `manual_or_automated_origin`
- `requires_reconciliation`
- `official_source_reference`
- `notes`

### HistoricalDataSafetyBoundary

Required encoded boundaries:

- `read_only=true`
- `non_executable=true`
- `network_access_allowed=false`
- `provider_api_allowed=false`
- `account_access_allowed=false`
- `credential_access_allowed=false`
- `token_access_allowed=false`
- `order_intent_allowed=false`
- `order_draft_allowed=false`
- `execution_approval_allowed=false`
- `live_or_prod_allowed=false`
- `cloud_llm_allowed=false`
- `local_model_runtime_allowed=false`
- `ml_training_allowed=false`

### HistoricalDataAuditRecord

Recommended fields:

- `audit_record_id`
- `ingestion_batch_id`
- `source_descriptor_id`
- `created_at`
- `operator_context`
- `local_file_path`
- `local_file_hash`
- `parser_version`
- `validation_report_id`
- `quality_report_id`
- `gap_report_id`
- `read_only`
- `non_executable`
- `no_network`
- `no_provider_api`

### HistoricalDataValidationReport

Recommended fields:

- `validation_report_id`
- `ingestion_batch_id`
- `strategy_track`
- `market_profile_id`
- `validation_status`
- `error_count`
- `warning_count`
- `validation_issues`
- `report_only`
- `read_only`
- `non_executable`

### HistoricalDataGapReport

Recommended fields:

- `gap_report_id`
- `ingestion_batch_id`
- `gap_status`
- `gap_categories`
- `blocking_gap_count`
- `report_only_gap_count`
- `gaps`
- `read_only`
- `non_executable`

### HistoricalDataQualityReport

Recommended fields:

- `quality_report_id`
- `ingestion_batch_id`
- `record_count`
- `symbol_count`
- `market_count`
- `date_range_start`
- `date_range_end`
- `timezone_distribution`
- `currency_distribution`
- `missing_value_count`
- `duplicate_count`
- `invalid_ohlc_count`
- `invalid_volume_count`
- `out_of_order_count`
- `missing_session_count`
- `stale_batch_marker`
- `adjustment_policy_summary`
- `quality_bucket`
- `report_only`
- `read_only`
- `non_executable`

### HistoricalMarketDataManifest

`HistoricalMarketDataManifest` should include:

- `manifest_id`
- `ingestion_batch_id`
- `source_descriptor_id`
- `source_file_path`
- `source_file_hash`
- `source_provenance`
- `strategy_track`
- `market_profile_id`
- `symbol_count`
- `record_count`
- `date_range`
- `timezone`
- `currency`
- `adjustment_policy`
- `validation_report_id`
- `quality_report_id`
- `gap_report_id`
- `audit_record_ids`
- `non_executable`
- `read_only`
- `no_network`
- `no_provider_api`
- `no_order`

## Historical Calendar and Event Schemas

### TradingCalendarConfig

Recommended fields:

- `calendar_config_id`
- `strategy_track`
- `market_profile_id`
- `source_type`
- `session_validation_mode`
- `unexpected_closure_policy`
- `early_close_policy`
- `event_type_policy`
- `timezone_mismatch_policy`
- `read_only`
- `non_executable`
- `network_access_allowed=false`
- `provider_api_allowed=false`

### TradingSessionRecord

Required fields should include:

- `market`
- `date`
- `timezone`
- `is_trading_day`
- `is_holiday`
- `is_early_close`
- `regular_open_time`
- `regular_close_time`
- `actual_open_time`
- `actual_close_time`
- `session_type`
- `source_id`
- `calendar_batch_id`

### MarketEventRecord

Required fields should include:

- `event_id`
- `market`
- `event_date`
- `event_time` if known
- `timezone`
- `event_type`
- `event_scope`
- `affected_symbols` or `affected_market`
- `source_id`
- `event_batch_id`
- `report_only`
- `non_executable`

### CorporateEventRecord

Required fields should include:

- `symbol`
- `market`
- `event_date`
- `event_type`
- `earnings_before_open_flag`
- `earnings_after_close_flag`
- `dividend_ex_date_flag`
- `split_effective_date_flag`
- `corporate_action_adjustment_flag`
- `source_id`

### CalendarSafetyBoundary

Required encoded boundaries:

- `read_only=true`
- `non_executable=true`
- `network_access_allowed=false`
- `provider_api_allowed=false`
- `exchange_api_allowed=false`
- `broker_api_allowed=false`
- `kiwoom_api_allowed=false`
- `ls_api_allowed=false`
- `account_access_allowed=false`
- `credential_access_allowed=false`
- `token_access_allowed=false`
- `live_or_prod_allowed=false`

### CalendarValidationReport

Recommended fields:

- `calendar_validation_report_id`
- `calendar_batch_id`
- `strategy_track`
- `market_profile_id`
- `validation_status`
- `error_count`
- `warning_count`
- `validation_issues`
- `read_only`
- `non_executable`

### CalendarGapReport

Recommended fields:

- `calendar_gap_report_id`
- `calendar_batch_id`
- `gap_status`
- `gap_categories`
- `blocking_gap_count`
- `report_only_gap_count`
- `gaps`
- `read_only`
- `non_executable`

### HistoricalCalendarManifest

Recommended fields:

- `calendar_manifest_id`
- `calendar_batch_id`
- `source_descriptor_ids`
- `strategy_track`
- `market_profile_id`
- `session_record_count`
- `market_event_count`
- `corporate_event_count`
- `date_range`
- `timezone`
- `validation_report_id`
- `gap_report_id`
- `safety_boundary`
- `read_only`
- `non_executable`
- `no_network`
- `no_provider_api`

## Required Event Types

Supported design-level event types should include:

- `MARKET_HOLIDAY`
- `EARLY_CLOSE`
- `REGULAR_SESSION`
- `OPTIONS_EXPIRATION`
- `FUTURES_EXPIRATION`
- `QUADRUPLE_WITCHING`
- `FOMC_DECISION`
- `CPI_RELEASE`
- `PPI_RELEASE`
- `JOBS_REPORT`
- `ELECTION_DAY`
- `EARNINGS_BEFORE_OPEN`
- `EARNINGS_AFTER_CLOSE`
- `DIVIDEND_EX_DATE`
- `SPLIT_EFFECTIVE_DATE`
- `CORPORATE_ACTION`

## Historical OHLCV Validation Rules

The future implementation should perform deterministic validation for:

- required field presence
- timestamp parseability
- timezone consistency
- symbol format validation
- market code validation
- currency validation
- numeric OHLCV validation
- `high >= open`
- `high >= close`
- `high >= low`
- `low <= open`
- `low <= close`
- `low <= high`
- non-negative volume
- duplicate timestamp detection
- duplicate symbol/timestamp detection
- missing trading-day/session detection
- out-of-order timestamp detection
- stale batch detection
- currency mismatch detection
- market profile mismatch detection
- unsupported track detection
- unsafe path/source detection
- remote URL rejection
- API source rejection

## Calendar and Event Validation Rules

The future implementation should perform deterministic validation for:

- required trading-session field presence
- required market-event field presence
- required corporate-event field presence
- session date parseability
- event timestamp or event date parseability
- timezone consistency
- market code validation
- event type validation
- unsupported event type detection
- session ordering consistency
- duplicate session detection
- duplicate event detection where appropriate
- unexpected market closure detection
- early-close session detection
- event market profile mismatch detection
- event timezone mismatch detection
- remote calendar fetch rejection
- API calendar source rejection
- unsafe path/source detection

## Historical Data Quality Report

The historical data quality report should include:

- record count
- symbol count
- market count
- date range
- timezone distribution
- currency distribution
- missing value count
- duplicate count
- invalid OHLC count
- invalid volume count
- out-of-order count
- missing session count
- stale batch marker
- adjustment policy summary
- quality bucket
- report-only marker
- read-only marker
- non-executable marker

## Historical Data Gap Categories

Gap categories should include:

- `MISSING_HISTORICAL_DATA_FILE`
- `MISSING_REQUIRED_FIELD`
- `INVALID_TIMESTAMP`
- `INVALID_TIMEZONE`
- `INVALID_SYMBOL`
- `INVALID_MARKET`
- `INVALID_CURRENCY`
- `INVALID_OHLC`
- `INVALID_VOLUME`
- `DUPLICATE_RECORD`
- `OUT_OF_ORDER_RECORD`
- `MISSING_TRADING_SESSION`
- `STALE_HISTORICAL_BATCH`
- `CURRENCY_MISMATCH`
- `MARKET_PROFILE_MISMATCH`
- `UNSUPPORTED_TRACK`
- `UNSAFE_SOURCE_PATH`
- `REMOTE_FETCH_NOT_ALLOWED`
- `API_CALL_NOT_ALLOWED`
- `EXECUTABLE_WORDING_DETECTED`
- `UNSAFE_TRIGGER_DETECTED`

## Calendar and Event Gap Categories

Calendar/event gap categories should include:

- `MISSING_TRADING_CALENDAR`
- `MISSING_TRADING_SESSION`
- `UNEXPECTED_MARKET_CLOSURE`
- `EARLY_CLOSE_SESSION`
- `MISSING_EVENT_CALENDAR`
- `MISSING_CORPORATE_EVENT_CALENDAR`
- `EVENT_TIMEZONE_MISMATCH`
- `EVENT_MARKET_PROFILE_MISMATCH`
- `UNSUPPORTED_EVENT_TYPE`
- `REMOTE_CALENDAR_FETCH_NOT_ALLOWED`
- `API_CALENDAR_SOURCE_NOT_ALLOWED`

## Calendar/Event Effects on Future Offline Pipeline

The future offline pipeline should treat calendar/event context as functional
context, not decoration.

Required design effects:

- missing trading sessions should not be treated as market data gaps when the
  calendar explicitly marks them as holidays
- forward outcome windows should be counted in trading sessions, not raw
  calendar days
- early-close sessions should be explicitly flagged for volume normalization and
  cautionary replay interpretation
- options expiration, futures expiration, and quadruple witching should be
  available as derivatives-related event features
- FOMC, CPI, PPI, jobs, and election events should be available as macro event
  context
- earnings, dividend, split, and corporate action records should be available
  as symbol-level context
- future market regime and dataset layers should be able to reference calendar
  and event context without turning them into execution authority

## Data Source Provenance Design

v5.0 must record provenance of already-local files only.

Candidate provenance origins that may appear in manifests:

- KRX manual export or local file
- KRX historical index membership local export
- pykrx-generated local CSV
- FinanceDataReader-generated local CSV
- Stooq local CSV for US stocks or ETFs
- Yahoo Finance local CSV
- future paid vendor local exports
- FINVIZ local CSV export
- FnGuide local CSV export
- SejongData local CSV export
- Investing.com local CSV export
- future LS read-only adapter output, but not in v5.0

Important constraints:

- v5.0 does not fetch from these sources
- v5.0 records provenance metadata only
- provenance must be captured in the manifest
- provenance does not imply source approval for runtime execution

## Future Investing.com Calendar Acquisition Roadmap

Investing.com should be documented only as a future read-only calendar
acquisition source for v5.4.

v5.0 does not:

- fetch Investing.com pages
- parse Investing.com pages
- crawl Investing.com

Future source candidates:

- `https://kr.investing.com/economic-calendar`
- `https://kr.investing.com/holiday-calendar/`
- `https://kr.investing.com/earnings-calendar`
- `https://kr.investing.com/stock-split-calendar/`
- `https://kr.investing.com/futures-expiration-calendar/`

Future normalized mapping references:

- economic calendar -> macro event records
- holiday calendar -> trading session or market holiday records
- earnings calendar -> corporate event records
- stock split calendar -> corporate action event records
- futures expiration calendar -> derivatives event records

Future parser targets should be separate:

- `InvestingEconomicCalendarParser`
- `InvestingHolidayCalendarParser`
- `InvestingEarningsCalendarParser`
- `InvestingStockSplitCalendarParser`
- `InvestingFuturesExpirationCalendarParser`

Future schedule profiles should remain:

- timezone-aware
- DST-aware
- market-session-aware
- compatible with `KR_US_4X_DAILY`, `KR_PRE_OPEN`, `KR_POST_CLOSE`,
  `US_PRE_OPEN`, and `US_POST_CLOSE`

Future crawler outputs may include:

- raw snapshot
- normalized event JSONL
- source manifest
- crawl audit record
- diff/change report
- validation report
- gap report
- safety report

Future Investing.com-derived records should be marked:

- `source_tier=AGGREGATOR`
- `requires_reconciliation=true` when official sources exist
- `read_only=true`
- `non_executable=true`

## Future FINVIZ Snapshot Feature Roadmap

FINVIZ should be documented only as a future v5.6/v5.7 feature source.

It is not an OHLCV source in this design.

Potential future FINVIZ-derived feature fields:

- relative volume
- short float
- market cap
- sector
- industry
- P/E
- forward P/E
- EPS growth
- ROE
- margin
- beta
- 52-week high or low distance
- analyst recommendation

v5.0 does not scrape FINVIZ and does not implement FINVIZ ingestion.

## Future News Title Packet and Optional Gemini Roadmap

Future roadmap only:

- v5.8 news title packet ingestion design
- v5.9 deterministic news tagging
- v5.10 optional Google AI Studio / Gemini report-only NLP summary

Reference architecture:

`news title packet`
-> raw news packet snapshot
-> deterministic ticker/entity/source/time/category tagging
-> optional Gemini summary/classification
-> normalized news event record
-> replay/outcome/dataset/regime context feature

Safety rules for the future optional Gemini layer:

- Gemini is not a news source
- Gemini is only an optional summarization or classification assistant
- the pipeline must work without Gemini
- Gemini failure must not block ingestion
- Gemini must remain report-only and non-executable
- Gemini must not produce buy/sell/entry/exit/order/execution advice
- Gemini must not create outcome labels
- Gemini must not bypass deterministic validation or safety boundaries
- Gemini must not create `OrderIntent`, order drafts, execution approval,
  `LIVE`, or `PROD` behavior
- no account, credential, token, order, holding, or private strategy state may
  be sent

Deterministic tagging must come before any future optional NLP step.

## Additional Future Data Layers

Future layers that should remain documented but out of v5.0 implementation:

- historical universe membership
- corporate action adjustment context
- session-aware outcome labeling
- source reliability tiering
- raw snapshot retention
- parser versioning
- source reconciliation

Recommended source reliability tiers:

- `OFFICIAL`
- `EXCHANGE`
- `REGULATOR`
- `BROKER_READONLY`
- `DATA_VENDOR`
- `AGGREGATOR`
- `BLOG_OR_MANUAL`

## CLI Design Proposal

Future implementation commands should remain local-file and report-oriented.

Historical market data CLI proposals:

- `historical-data-config-validate --fixture-file ...`
- `historical-data-manifest-build --fixture-file ... [--output-file ...]`
- `historical-data-validate --fixture-file ... [--output-file ...]`
- `historical-data-quality-report --fixture-file ... [--output-file ...]`
- `historical-data-gap-report --fixture-file ... [--output-file ...]`
- `historical-data-safety-report --fixture-file ... [--output-file ...]`

Historical calendar/event CLI proposals:

- `historical-calendar-config-validate --fixture-file ...`
- `historical-calendar-validate --fixture-file ... [--output-file ...]`
- `historical-calendar-gap-report --fixture-file ... [--output-file ...]`

Explicit exclusions:

- no parquet CLI in v5.0
- no remote fetch CLI
- no provider API CLI
- no account/broker/order CLI

## Fixture Design

Future fixture examples should include:

- valid local CSV descriptor
- valid local JSONL descriptor
- valid OHLCV record
- valid KR historical snapshot
- optional valid US local-file descriptor as design reference only when safely
  report-only
- valid historical manifest
- valid historical quality report
- valid trading session calendar
- valid market event calendar
- valid corporate event calendar
- valid early-close session
- valid market holiday session
- missing file failure
- missing required field failure
- invalid timestamp failure
- invalid OHLC failure
- invalid volume failure
- duplicate record warning or failure
- out-of-order record failure
- currency mismatch failure
- unsupported track failure
- remote URL rejection
- API source rejection
- unsafe path rejection
- missing trading calendar failure
- missing event calendar warning or failure
- unsupported event type failure
- executable wording detection failure
- unsafe trigger attempt failure

Explicit exclusions:

- no parquet fixtures
- no runtime provider fixtures
- no crawler fixtures
- no news ingestion fixtures

## System Smoke Design

Future system smoke should use temporary local fixture files only.

Expected smoke confirmations:

- `historical_data_ingestion_fixture_run=true`
- `historical_data_local_files_only=true`
- `strategy_track_required=true`
- `domestic_kr_primary=true`
- `market_profile_resolved=true`
- `historical_manifest_generated=true`
- `historical_validation_report_generated=true`
- `historical_quality_report_generated=true`
- `historical_gap_report_generated=true`
- `historical_data_read_only=true`
- `historical_data_non_executable=true`
- `historical_calendar_fixture_run=true`
- `historical_calendar_local_files_only=true`
- `historical_calendar_manifest_generated=true`
- `historical_calendar_validation_report_generated=true`
- `historical_calendar_gap_report_generated=true`
- `historical_calendar_read_only=true`
- `historical_calendar_non_executable=true`
- `remote_fetch_allowed=false`
- `api_provider_called=false`
- `kiwoom_api_called=false`
- `ls_api_called=false`
- `broker_api_called=false`
- `credentials_accessed=false`
- `external_network_calls=false`
- `orders_created=false`
- `order_intent_created=false`
- `order_drafts_created=false`
- `execution_approval_enabled=false`
- `live_or_prod_used=false`
- `cloud_llm_called=false`
- `model_runtime_called=false`
- `ml_training_run=false`

## Safety Boundary Summary

v5.0 must preserve and extend the v3/v4 safety philosophy.

Required invariants:

- local CSV or JSONL only
- read-only only
- non-executable only
- no network
- no provider API
- no broker
- no Kiwoom
- no LS
- no account read
- no credential or token access
- no `OrderIntent`
- no order draft
- no execution approval
- no `LIVE`
- no `PROD`
- no cloud LLM
- no local model runtime
- no prompt pack execution
- no ML training

Historical ingestion design must remain a data-governance layer, not an
execution layer.

## Recommended v5 Sequence After This Design

Recommended next milestones remain:

1. `v5.1 Read-Only Historical Market Data and Calendar/Event Local File Ingestion`
2. `v5.2 Historical Replay Dataset Generation from Real OHLCV Snapshots`
3. `v5.3 Offline Outcome Label Generation on Historical Data`
4. `v5.4 Investing.com Calendar Read-Only Snapshot Crawler`
5. `v5.5 Calendar Diff/Reconciliation and Quality Report`
6. `v5.6 FINVIZ Snapshot Feature Ingestion Design`
7. `v5.7 FINVIZ Read-Only Snapshot Feature Adapter`
8. `v5.8 News Title Packet Ingestion Design`
9. `v5.9 Deterministic News Tagging`
10. `v5.10 Optional Google AI Studio / Gemini Report-Only NLP Summary`

All remain non-executable until explicitly redesigned and approved otherwise.

## Summary

v5.0 should define a dual-foundation offline ingestion architecture:

- `HistoricalMarketDataSnapshot` as the primary unit
- `HistoricalCalendarEventSnapshot` as a secondary first-class unit

Both units remain:

- local CSV/JSONL only
- read-only
- non-executable
- no-network
- no-provider-API
- design-only in v5.0

This gives the project a disciplined path from v4 fixture-only offline research
to future historical-data-based offline replay, outcome labeling, dataset
generation, and regime context without starting live trading, real orders,
provider integration, or model execution.
