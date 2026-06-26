# v10.0 Feature Store / Cache / Training Dataset Pipeline Design

## Scope

v10.0 introduces a new manifest-first `feature_store_*` pipeline for local/offline feature caching, deterministic/manual label generation, leakage-checked training-row assembly, walk-forward split planning, and report-only training dataset readiness.

The milestone must remain:

- local-only
- offline-only
- report-only
- non-executable
- non-trading
- non-training
- non-paper-trading
- non-provider-calling

v10.0 must not:

- call Kiwoom, LS, FRED, Yahoo, Databento, CME, BLS, BEA, BOK, or any other provider
- read env vars, credentials, API keys, tokens, or account data
- run model training
- run paper trading
- evaluate strategy performance
- generate buy/sell recommendations
- output executable order objects

## Public Output Surface

The primary public outputs are:

- `FeatureStoreFeatureRow`
- `FeatureStoreLabelRow`
- `FeatureStoreTrainingRow`
- `FeatureStoreWalkForwardPlan`
- `FeatureStoreLeakageReport`
- `FeatureStoreTrainingDatasetManifest`
- `FeatureStoreBackendCapabilityReport`
- `FeatureStoreMaterializationResult`

Secondary report/control outputs include:

- `FeatureStoreCacheManifest`
- `FeatureStoreDatasetManifest`
- `FeatureStoreCompletenessReport`
- `FeatureStoreFreshnessReport`
- `FeatureStoreTrainingReadinessReport`
- `FeatureStoreSafetyReport`
- `FeatureStoreGapReport`
- `FeatureStorePipelineResult`

The training dataset manifest is the v10 source of truth. Physical Parquet/DuckDB/Polars artifacts are optional secondary outputs and never the canonical state.

## Architecture

v10.0 uses a manifest-first five-layer architecture plus dataset scale profiles.

### 1. Canonical Input Ingestion

v10 consumes only already-canonical local inputs:

- v8 domestic stock snapshots
- v8 captured/local-manual-imported Kiwoom chart history
- v9 macro snapshot, classification, and event windows
- v7 risk-context reports
- manual label fixtures
- local/manual price-history fixtures

Raw provider payloads are not allowed as direct v10 inputs. No network/provider/account/credential path is permitted.

### 2. Row Assembly

Assembly order is fixed:

1. Build `FeatureStoreFeatureRow` objects in memory.
2. Build `FeatureStoreLabelRow` objects from:
   - manual label fixtures
   - deterministic derivation from local/manual price history
   - deterministic derivation from locally stored v8 Kiwoom chart history
3. Build `FeatureStoreTrainingRow` by joining:
   - feature row
   - optional multiple label rows
   - walk-forward split assignment

Training rows must support both labeled and unlabeled states and degrade explicitly through:

- `LABELED_DATASET_READY`
- `UNLABELED_DATASET_READY`
- `LABEL_GAP`

### 3. Validation and Control Plane

Validation runs before any backend write and covers:

- lineage checks
- namespace separation
- label timing checks
- leakage checks
- `available_at <= feature_asof`
- `label_available_at > feature_asof`
- survivorship/readiness downgrades
- completeness/freshness checks
- unsafe field checks
- account/order/credential marker checks

If validation fails, promoted dataset materialization is blocked.

### 4. Manifest and Split Planning

Primary planning/report outputs are:

- `FeatureStoreWalkForwardPlan`
- `FeatureStoreLeakageReport`
- `FeatureStoreBackendCapabilityReport`
- `FeatureStoreTrainingDatasetManifest`

The manifest is the v10 source of truth.

Existing `historical_dataset_*` modules may be referenced for compatibility thinking or reporting conventions, but v10 does not use them as its primary architecture.

### 5. Optional Materialization

Materialization is strictly secondary.

If dependencies exist and the path is safe, local materialization is allowed only under:

- `local_data/feature_store/`
- test-controlled temporary roots

If dependencies are missing, the pipeline must degrade with:

- `DEPENDENCY_GAP`
- `BACKEND_GAP`

Missing optional dependencies must never fail the milestone’s manifest-first pipeline.

### 6. Dataset Scale Profiles

v10 must explicitly model safe scale profiles:

- `SMOKE_PROFILE`
  - tiny fixture
  - 3 symbols or fewer
  - short date range
  - in-memory only
- `DAILY_RESEARCH_PROFILE`
  - default realistic profile
  - daily rows
  - capped instruments
  - safe for a 64GB RAM machine
  - manifest-first, optional Parquet/DuckDB/Polars materialization
- `INTRADAY_CANDIDATE_PROFILE`
  - candidate symbols only
  - 5m/15m rows
  - partitioned only
  - no full unbounded in-memory merge
- `FULL_INTRADAY_PROFILE`
  - disabled by default
  - explicit capacity acknowledgment required
  - must be partitioned
  - must not run in tests

Memory rule:

- no all-symbol all-minute dataset by default
- no unbounded Pandas-style in-memory merge
- large materialization must be partitioned by safe keys such as dataset id, market, date, split, and optional instrument group

## Data Model

### Enums and Identifiers

Create:

- `FeatureStoreBackend`
- `FeatureStoreBackendStatus`
- `FeatureStoreFormat`
- `FeatureStoreRootPolicy`
- `FeatureStoreDatasetId`
- `FeatureStorePartitionSpec`
- `FeatureStoreSourceKind`
- `FeatureStoreFeatureNamespace`
- `FeatureStoreDatasetProfile`
- `FeatureStoreReadinessStatus`

`FeatureStoreBackendStatus` must include:

- `AVAILABLE`
- `MISSING_DEPENDENCY`
- `DISABLED_BY_POLICY`
- `SCHEMA_GAP`
- `DEPENDENCY_GAP`
- `BACKEND_GAP`
- `REJECTED`

`FeatureStoreReadinessStatus` must include at least:

- `FEATURE_ROWS_READY`
- `MANUAL_LABELS_READY`
- `DETERMINISTIC_LABELS_READY`
- `LABEL_GAP`
- `UNLABELED_DATASET_READY`
- `LABELED_DATASET_READY`
- `TRAINING_DATASET_MANIFEST_READY`
- `MATERIALIZATION_READY`
- `DEPENDENCY_GAP`
- `BACKEND_GAP`
- `BLOCKED_LEAKAGE`
- `RESEARCH_ONLY`

### Source Kinds

`FeatureStoreSourceKind` must include:

- `V8_DOMESTIC_STOCK_SNAPSHOT`
- `V8_CAPTURED_KIWOOM_CHART_HISTORY`
- `V8_MANUAL_IMPORTED_KIWOOM_CHART_HISTORY`
- `V9_MACRO_REGIME_SNAPSHOT`
- `V9_REGIME_CLASSIFICATION`
- `V9_MACRO_EVENT_WINDOW`
- `V7_POSITION_SIZING_CONTEXT`
- `V7_EVENT_RISK_CONTEXT`
- `V7_OUTLIER_ROUTING_CONTEXT`
- `MANUAL_LABEL_FIXTURE`
- `MANUAL_PRICE_HISTORY_FIXTURE`
- `LOCAL_PRICE_HISTORY_FIXTURE`
- `UNKNOWN`

### Feature Rows

`FeatureStoreFeatureRow` includes:

- `dataset_id`
- `row_id`
- `instrument_id`
- `market`
- `currency`
- `feature_asof`
- `available_at`
- `snapshot_at`
- `feature_namespace`
- `feature_values`
- `feature_availability_map`
- `source_refs`
- `lineage_records`
- `source_kind`
- `non_executable`
- `report_only`

Availability rules:

- row `available_at` is the row-level maximum available timestamp across all required feature sources
- every included feature source must satisfy `source_available_at <= feature_asof`
- row `available_at <= feature_asof`
- per-feature/per-namespace availability must be preserved in lineage or `feature_availability_map`
- missing critical `available_at` becomes `DATA_GAP` or `BLOCKED_LEAKAGE`

Feature value policy:

- `feature_values` is a flat scalar-only map
- allowed values:
  - `int`
  - `float`
  - `str`
  - `bool`
  - `null`
- nested dicts/lists/raw payloads are forbidden
- credentials/account/order/executable objects are forbidden
- labels are forbidden in feature namespaces

### Label Rows

`FeatureStoreLabelRow` includes:

- `dataset_id`
- `label_row_id`
- `row_id`
- `instrument_id`
- `label_name`
- `label_horizon`
- `label_value`
- `label_unit`
- `label_direction`
- `label_window_start`
- `label_window_end`
- `label_observed_at`
- `label_available_at`
- `label_input_source_kind`
- `label_input_source_ref`
- `derivation_method`
- anchor metadata:
  - `anchor_price`
  - `anchor_observed_at`
  - `anchor_available_at`
  - `anchor_source_ref`
  - `anchor_price_policy`
- quality flags

Supported derivation methods:

- `MANUAL_FIXTURE`
- `LOCAL_PRICE_HISTORY_FORWARD_RETURN`
- `LOCAL_PRICE_HISTORY_FORWARD_LOG_RETURN`
- `LOCAL_PRICE_HISTORY_MFE`
- `LOCAL_PRICE_HISTORY_MAE`
- `LOCAL_PRICE_HISTORY_VOL_ADJUSTED_RETURN`
- `LOCAL_PRICE_HISTORY_OUTLIER_CONTINUATION`

Supported anchor policies:

- `LAST_AVAILABLE_CLOSE`
- `LAST_AVAILABLE_BAR_CLOSE`
- `NEXT_OPEN_AFTER_ASOF`
- `EXPLICIT_MANUAL_ANCHOR`
- `UNKNOWN_ANCHOR_POLICY`

Anchor rules:

- `anchor_available_at <= feature_asof`
- if only a post-`feature_asof` anchor exists, emit `LABEL_GAP` or `BLOCKED_LEAKAGE`
- same-day close cannot anchor an intraday feature row unless already available
- daily close is allowed only when the close was already available at `feature_asof`
- `NEXT_OPEN_AFTER_ASOF` is allowed only as an explicit forward execution-style label anchor and never as a feature

Window rules:

- `label_window_start` is strictly after the anchor timestamp unless the method uses the anchor only as denominator/reference
- `label_window_end` must match the requested horizon
- `label_available_at` must be after the last price point required for the label
- `label_available_at > feature_asof` is mandatory
- insufficient future bars produces `LABEL_GAP`

### Training Rows

`FeatureStoreTrainingRow` includes:

- `dataset_id`
- `training_row_id`
- `row_id`
- `instrument_id`
- `split_id`
- `split_role`
- `label_row_ids`
- `label_values`
- `labeled`
- `blocked_from_training`
- `blocking_reasons`
- `label_gap_reasons`

A single feature row may have multiple labels. Training rows therefore support multiple label references rather than a single label pointer.

### Schema and Lineage

Create:

- `FeatureStoreFeatureColumn`
- `FeatureStoreFeatureSchema`
- `FeatureStoreSourceRef`
- `FeatureStoreLineageRecord`

`FeatureStoreSourceRef` must expose:

- safe logical source id
- source kind
- sanitized basename
- allowed-root-relative path when needed

It must not expose unsafe raw absolute paths as the primary identity. Path traversal and unsafe path material must be blocked or redacted.

### Manifests and Reports

Create:

- `FeatureStoreCacheManifest`
- `FeatureStoreDatasetManifest`
- `FeatureStoreTrainingDatasetManifest`
- `FeatureStoreWalkForwardSplit`
- `FeatureStoreWalkForwardPlan`
- `FeatureStoreLeakageReport`
- `FeatureStoreCompletenessReport`
- `FeatureStoreFreshnessReport`
- `FeatureStoreBackendCapabilityReport`
- `FeatureStoreMaterializationPlan`
- `FeatureStoreMaterializationResult`
- `FeatureStoreTrainingReadinessReport`
- `FeatureStoreSafetyReport`
- `FeatureStoreGapReport`
- `FeatureStoreAuditRecord`
- `FeatureStorePipelineResult`

`FeatureStoreTrainingDatasetManifest` must include:

- `dataset_id`
- `schema_version`
- `created_at`
- `generator_version` or safe code version ref
- `dataset_profile`
- `feature_schema_ref`
- `row_count`
- `training_row_count`
- `labeled_row_count`
- `unlabeled_row_count`
- `row_count_by_split`
- `label_count_by_horizon`
- `label_coverage_summary`
- `split_coverage_summary`
- `source_refs`
- `lineage_summary`
- `freshness_summary`
- `completeness_summary`
- `leakage_summary`
- `survivorship_readiness_summary`
- `backend_capability_summary`
- `materialization_summary`
- `non_executable`
- `report_only`

## Label Derivation Rules

v10 supports:

1. manual label fixtures
2. deterministic local derivation from local OHLCV history

Supported deterministic labels:

- `FORWARD_RETURN`
- `FORWARD_LOG_RETURN`
- `MAX_FAVORABLE_EXCURSION`
- `MAX_ADVERSE_EXCURSION`
- `VOLATILITY_ADJUSTED_RETURN`
- `OUTLIER_CONTINUATION`

Supported horizons:

- `1D`
- `3D`
- `5D`
- `10D`
- `20D`

Deterministic computation rules:

- all label computation uses only local/manual price-history or locally stored Kiwoom chart history
- no fetching is allowed
- no feature namespace may contain a label field

Method semantics:

- `FORWARD_RETURN`: end-price vs anchor-price return over the horizon
- `FORWARD_LOG_RETURN`: log return over the horizon
- `MFE`/`MAE`: excursion within the forward window relative to anchor
- `VOLATILITY_ADJUSTED_RETURN`: forward return divided by a backward-looking volatility denominator available at `feature_asof`
- `OUTLIER_CONTINUATION`: deterministic only, and only when outlier/rank context plus sufficient forward path exists

Direction policy:

- supported directions:
  - `LONG`
  - `SHORT`
  - `DIRECTIONLESS`
  - `UNKNOWN`
- default direction is `LONG` for current domestic equity/outlier research

Excursion policy:

- long MFE = max favorable high/close move relative to anchor
- long MAE = max adverse low/close move relative to anchor
- if high/low is unavailable, either:
  - compute close-only excursion with a quality flag, or
  - emit `LABEL_GAP`

Volatility denominator policy:

- denominator must be backward-looking
- denominator must be available at `feature_asof`
- denominator must be preserved in lineage
- no future-return input is allowed
- missing safe volatility input produces `LABEL_GAP`

Outlier continuation policy:

- only allowed if the feature row contains outlier/rank context
- requires enough local forward path
- continuation criteria must be deterministic and recorded
- otherwise emit `LABEL_GAP`

## Leakage Validation

Leakage validation runs after feature and label assembly, before promoted manifest/materialization.

Hard rules:

- every included feature source must satisfy `source_available_at <= feature_asof`
- row `available_at <= feature_asof`
- `anchor_available_at <= feature_asof`
- `label_available_at > feature_asof`
- labels never appear in `feature_values`
- feature values remain scalar-only
- no future outcome metric appears in feature namespaces

Additional blocking checks:

- anchor price availability violation
- label window incorrectly uses price points before or equal to `feature_asof`
- normalization/scaling fit on validation/test data
- feature schema contains label-like names:
  - `forward_return`
  - `future_return`
  - `mfe`
  - `mae`
  - `target`
  - `label`
  - `outcome`
- split overlap by instrument and timestamp
- split boundary lacks purge/embargo for max label horizon

Blocking output:

- `BLOCKED_LEAKAGE`

Downgrade output:

- `RESEARCH_ONLY`
- `LABEL_GAP`
- `UNLABELED_DATASET_READY`

Leakage report must summarize:

- blocked rows
- warning rows
- leakage categories
- label-horizon coverage/rejection counts
- survivorship/readiness downgrade reasons

## Walk-Forward Split Policy

Split assignment operates on `feature_asof`, not label timestamps.

Default split mode:

- anchored chronological split

Optional split mode:

- rolling chronological split
- allowed only when explicitly configured by fixture/profile

Core rules:

- no random shuffle
- no overlapping train/validation/test windows
- purge and embargo windows are based on the maximum requested label horizon
- training rows with unsafe labels are excluded from promoted labeled manifests
- unlabeled safe rows may remain in feature-only research manifests
- repeated test tuning is reported as a v7.2 data-snooping risk where applicable
- `FULL_INTRADAY_PROFILE` remains blocked in tests and disabled by default

Profile behaviors:

- `SMOKE_PROFILE`
  - tiny deterministic split
  - in-memory only
- `DAILY_RESEARCH_PROFILE`
  - bounded chronological train/validation/test windows
  - optional forward holdout
- `INTRADAY_CANDIDATE_PROFILE`
  - partitioned split planning only
  - bounded dates and candidate symbols
- `FULL_INTRADAY_PROFILE`
  - explicit capacity acknowledgment required
  - never allowed in tests

## Backend and Materialization Policy

Materialization is secondary and never the source of truth.

Backends:

- `IN_MEMORY`
- `JSON`
- `PARQUET`
- `DUCKDB`
- `POLARS`

`IN_MEMORY` and JSON/manifest modes must always work.

Optional backends must degrade safely through `FeatureStoreBackendCapabilityReport`.

Capability reporting per backend includes:

- backend name
- status
- missing modules
- allowed formats
- safe-root policy result
- dataset-profile compatibility
- partitioning notes

Safe-root policy:

- default root: `local_data/feature_store/`
- tests use temp roots
- path traversal blocked
- writes outside approved roots blocked
- arbitrary absolute paths blocked unless explicitly validated in tests

Profile materialization policy:

- `SMOKE_PROFILE`
  - in-memory and JSON only by default
- `DAILY_RESEARCH_PROFILE`
  - manifest-first default
  - optional Parquet/DuckDB/Polars materialization
- `INTRADAY_CANDIDATE_PROFILE`
  - partitioned-only materialization
  - no unbounded all-symbol merge
- `FULL_INTRADAY_PROFILE`
  - disabled by default
  - explicit capacity acknowledgment required
  - never allowed in tests

Write policy:

- no backend write if leakage status is `BLOCKED_LEAKAGE`
- no promoted labeled dataset materialization if label timing/survivorship checks fail
- unlabeled feature-only research manifests may still materialize when policy allows
- dependency absence downgrades materialization only and never fails manifest generation

`FeatureStoreMaterializationResult` includes:

- dataset id
- requested backend(s)
- selected backend
- materialized path/table ids
- partition summary
- row counts written
- status summary
- degradation reasons
- safe-root validation result

## CLI and Report Surfaces

CLI remains report-first and fixture-driven.

Add commands:

- `feature-store-backend-capability-report`
- `feature-store-cache-manifest-build`
- `feature-store-dataset-manifest-build`
- `feature-store-training-dataset-manifest-build`
- `feature-store-walk-forward-plan`
- `feature-store-leakage-report`
- `feature-store-training-readiness-report`
- `feature-store-materialization-plan`
- `feature-store-materialize`
- `feature-store-safety-report`
- `feature-store-gap-report`

Command rules:

- all inputs must be local fixtures/config
- report-only by default
- `feature-store-materialize` must remain safe-local only
- no command may trigger provider fetches, env reads, credential loads, training, paper trading, or order generation

## Verification Plan

Create/modify:

- `docs/superpowers/plans/2026-06-18-v10-feature-store-cache-training-dataset-pipeline.md`
- `src/stock_risk_mcp/feature_store_models.py`
- `src/stock_risk_mcp/feature_store_guard.py`
- `src/stock_risk_mcp/feature_store_backend.py`
- `src/stock_risk_mcp/feature_store_fixture.py`
- `src/stock_risk_mcp/feature_store_cache_engine.py`
- `src/stock_risk_mcp/feature_store_dataset_engine.py`
- `src/stock_risk_mcp/feature_store_walk_forward_engine.py`
- `src/stock_risk_mcp/feature_store_integration_engine.py`
- `src/stock_risk_mcp/cli.py`
- `src/stock_risk_mcp/system_smoke.py`
- `tests/test_feature_store_models.py`
- `tests/test_feature_store_backend.py`
- `tests/test_feature_store_cache_engine.py`
- `tests/test_feature_store_dataset_engine.py`
- `tests/test_feature_store_walk_forward_engine.py`
- `tests/test_feature_store_integration_cli.py`
- `tests/test_system_smoke.py`

Targeted tests:

- `test_feature_store_models.py`
  - enum/status normalization
  - scalar-only feature values
  - separate labels
  - safe source refs
  - profile rules
- `test_feature_store_backend.py`
  - optional import handling
  - capability reporting
  - safe-root policy
  - blocked path traversal
- `test_feature_store_cache_engine.py`
  - canonical feature-row assembly
  - lineage preservation
  - availability aggregation
  - cache-manifest output
- `test_feature_store_dataset_engine.py`
  - manual labels
  - deterministic labels
  - anchor policy handling
  - multi-label rows
  - labeled/unlabeled manifests
- `test_feature_store_walk_forward_engine.py`
  - anchored default split
  - optional rolling split
  - purge/embargo behavior
  - overlap rejection
  - profile gating
- `test_feature_store_integration_cli.py`
  - CLI manifest/report generation
  - dependency-gap degradation
  - safe materialization behavior
- `test_system_smoke.py`
  - offline end-to-end v10 smoke coverage

Verification commands:

- `python3.11 -m pytest tests/test_feature_store_models.py tests/test_feature_store_backend.py tests/test_feature_store_cache_engine.py tests/test_feature_store_dataset_engine.py tests/test_feature_store_walk_forward_engine.py tests/test_feature_store_integration_cli.py tests/test_system_smoke.py -q`
- `python3.11 -m pytest -q`

Success criteria:

- manifest-first pipeline works fully in memory with local fixtures only
- labeled dataset manifests work when safe local future-path labels are available
- unlabeled manifests degrade cleanly with `LABEL_GAP`
- backend dependency absence downgrades materialization only
- no provider/network/env/credential/account/order/training/paper-trading path exists
- full pytest remains green

## Milestone Discipline

- Do not create v10.1 or v10.2
- Finish under v10.0 only
- Final tag:
  - `v10.0.0-feature-store-cache-training-dataset-pipeline`
