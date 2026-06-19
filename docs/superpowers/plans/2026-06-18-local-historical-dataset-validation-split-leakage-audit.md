# Local Historical Dataset Validation, Split, And Leakage Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local fixture-only v5.5 validation and split layer that consumes v5.4 historical dataset artifacts and produces report-only validation reports, leakage audit reports, and deterministic chronological split manifests for future offline evaluation or future ML training preparation, without performing any training or learned-model evaluation in v5.5.

**Architecture:** Add a dedicated historical dataset validation module family that reads only local fixture-derived v5.4 dataset artifacts, validates safety and lineage invariants fail-closed, audits feature/outcome leakage boundaries, and emits deterministic chronological train/validation/test split manifests keyed by replay anchor time. Keep all outputs report-only, non-executable, and unsuitable for runtime trading or order generation.

**Tech Stack:** Python 3.11, Pydantic v2, existing strict model patterns, local fixture loaders, deterministic pure-Python report builders, existing CLI patterns, pytest, system smoke

---

## File Structure

### New files

- `src/stock_risk_mcp/historical_dataset_validation_models.py`
  Validation config/input/report schemas, leakage audit report, split config/manifest, coverage and label distribution reports, validation gap and safety report models.
- `src/stock_risk_mcp/historical_dataset_validation_fixture.py`
  Local JSON fixture loader for v5.5 validation inputs, with local-path-only and parquet rejection.
- `src/stock_risk_mcp/historical_dataset_validation_guard.py`
  Fail-closed safety and leakage guard for validation metadata, split config, and report outputs.
- `src/stock_risk_mcp/historical_dataset_validation_engine.py`
  Pure deterministic validation, leakage audit, chronological split generation, coverage summary, label distribution summary, and report assembly.
- `tests/test_historical_dataset_validation_models.py`
  Model construction, required safety flags, local fixture loader, and unsupported metadata tests.
- `tests/test_historical_dataset_validation_engine.py`
  Validation rule, leakage audit, chronological split, coverage, distribution, and gap tests.
- `tests/test_historical_dataset_validation_cli.py`
  CLI success/failure tests for local fixture-only validation and split commands.

### Modified files

- `src/stock_risk_mcp/cli.py`
  Register v5.5 validation, leakage audit, split manifest, coverage report, and label distribution commands.
- `src/stock_risk_mcp/system_smoke.py`
  Add v5.5 local validation/split smoke coverage.
- `tests/test_system_smoke.py`
  Assert v5.5 smoke checks.
- `WORK_SUMMARY.md`
  Append v5.5 summary only if the repository convention still requires it at milestone close.

### Existing files to inspect for compatibility only

- `src/stock_risk_mcp/historical_dataset_models.py`
- `src/stock_risk_mcp/historical_dataset_fixture.py`
- `src/stock_risk_mcp/historical_dataset_guard.py`
- `src/stock_risk_mcp/historical_dataset_engine.py`
- `tests/test_historical_dataset_engine.py`
- `tests/test_historical_dataset_models.py`

## Inputs

v5.5 may consume only local fixture-derived v5.4 artifacts:

- `HistoricalDatasetRecord`
- `HistoricalDatasetFeatureBlock`
- `HistoricalDatasetOutcomeBlock`
- `HistoricalDatasetExportManifest`
- `HistoricalDatasetQualityReport`
- `HistoricalDatasetGapReport`
- `HistoricalDatasetSafetyReport`

The aggregate v5.5 input should wrap those v5.4 artifacts in a local JSON fixture and must remain:

- read-only
- report-only
- non-executable
- local-file-only
- no-network
- no-provider-api
- no-order
- no-LLM-runtime
- no-ML-training

## Core Model Concepts

v5.5 should introduce these first-class units:

- `HistoricalDatasetValidationConfig`
- `HistoricalDatasetValidationInput`
- `HistoricalDatasetValidationReport`
- `HistoricalDatasetLeakageAuditReport`
- `HistoricalDatasetSplitConfig`
- `HistoricalDatasetSplitManifest`
- `HistoricalDatasetSplitRecordRef`
- `HistoricalDatasetCoverageReport`
- `HistoricalDatasetLabelDistributionReport`
- `HistoricalDatasetValidationGapReport`
- `HistoricalDatasetValidationSafetyReport`

Expected responsibilities:

- `HistoricalDatasetValidationConfig`
  Carries deterministic validation and split policy options, accepted strategy track, split ratios or cut points, and required safety flags.
- `HistoricalDatasetValidationInput`
  Wraps v5.4 dataset records and related v5.4 reports/manifests plus audit metadata for v5.5 processing.
- `HistoricalDatasetValidationReport`
  Summarizes record validity, safety flag compliance, missing lineage/feature/outcome counts, blocked counts, warnings, and report-only status.
- `HistoricalDatasetLeakageAuditReport`
  Summarizes leakage findings and explicitly reports whether feature/outcome leakage is absent or detected.
- `HistoricalDatasetSplitManifest`
  Records deterministic chronological train/validation/test boundaries and per-split counts/distributions.
- `HistoricalDatasetSplitRecordRef`
  References a dataset record id and the split partition it belongs to without copying record payloads into a new executable surface.
- `HistoricalDatasetCoverageReport`
  Summarizes symbol, market, strategy track, replay-date, and partition coverage.
- `HistoricalDatasetLabelDistributionReport`
  Summarizes outcome label counts per whole dataset and per split.
- `HistoricalDatasetValidationGapReport`
  Captures validation failures, leakage findings, unsupported metadata, missingness, and policy-blocked cases.
- `HistoricalDatasetValidationSafetyReport`
  Restates the hard safety boundary and confirms no executable/runtime path was introduced.

## Dataset Validation Rules

Validation must remain fail-closed and verify, at minimum:

- every dataset record is `report_only=true`
- every dataset record is `read_only=true`
- every dataset record is `non_executable=true`
- every dataset record is `local_file_only=true`
- every dataset record is `no_network=true`
- every dataset record is `no_provider_api=true`
- every dataset record is `no_order=true`
- every dataset record is `no_llm_runtime=true`
- every dataset record is `no_ml_training=true`
- required source lineage exists
- feature block exists
- outcome block exists
- outcome block is explicitly marked as post-anchor observation
- scanner replay input metadata remains pre-outcome and report-only
- no order-like fields exist
- no execution-like fields exist
- no buy/sell/entry/exit wording exists
- no network/provider/crawler/LLM/ML-training markers exist
- parquet remains unsupported

Recommended record-level checks:

- `dataset_record_id` is present and unique within the input
- `strategy_track` remains supported and expected
- symbol and market identifiers are non-empty
- replay anchor date/timestamp is available for chronological ordering
- feature and outcome lineage references match the parent dataset manifest where applicable
- validation summaries never mutate original v5.4 dataset records

## Feature / Outcome Leakage Audit Rules

The leakage audit must explicitly verify the no-lookahead boundary:

- feature block does not contain outcome label
- feature block does not contain forward return
- feature block does not contain max favorable excursion
- feature block does not contain max adverse excursion
- feature block does not contain post-anchor actual values
- feature block does not contain realized future event values
- feature block does not contain any field or string suggesting runtime signal generation
- outcome block remains the only location for post-anchor observational values
- scanner replay input remains pre-outcome and report-only
- validation outputs do not merge labels or forward returns back into replay-time scanner context

Leakage audit output should include:

- total records audited
- clean record count
- blocked record count
- warning count
- leakage category counts
- affected record ids
- explicit `feature_outcome_leakage_absent` boolean

Explicit blocked leakage cases:

- `outcome_label` in feature block
- `forward_return_pct` in feature block
- `max_favorable_excursion_pct` in feature block
- `max_adverse_excursion_pct` in feature block
- any post-anchor actual price/value field in feature block
- mutated scanner replay input carrying outcome data
- outcome label treated as approval/signal/recommendation

## Chronological Split Policy

Splitting must be deterministic and chronological, never random:

- sort by replay anchor timestamp first
- use stable tie-breakers such as `dataset_record_id`
- default policy produces train, validation, and test partitions in that order
- train period must end before validation period begins
- validation period must end before test period begins
- no identical `dataset_record_id` may appear in multiple partitions
- no shuffle step is allowed
- split manifests must remain report-only and local-file-only

Recommended split policy defaults:

- deterministic chronological ordering by replay anchor timestamp ascending
- default partition ratios documented in config, but still local/report-only
- explicit fail-closed behavior when too few records exist for all partitions
- optional report-only degraded mode only if clearly named and intentionally enabled

Split manifest content should include:

- split manifest id
- split config id
- partition names
- record counts per split
- date range per split
- symbol counts per split
- market counts per split
- strategy track coverage per split
- label distribution per split
- safety flags

## Symbol / Market / Track Coverage Reports

Coverage reporting should summarize:

- unique symbol count
- unique market count
- strategy track count
- record counts per symbol
- record counts per market
- record counts per strategy track
- earliest and latest replay anchors
- per-split symbol coverage
- per-split market coverage
- per-split track coverage

Coverage reporting must remain descriptive only. It must not:

- rank symbols for trading
- score markets for actionability
- prioritize trades
- generate any order candidate

## Label Distribution Reports

Label distribution reporting should summarize the existing report-only outcome labels already present in v5.4 outcome blocks:

- total label counts
- per-label percentage
- per-split label counts
- per-symbol label counts if safe and simple
- inconclusive / insufficient-data counts
- blocked-safety label counts

The report must remain strictly descriptive and must not:

- re-label records using a learned model
- convert labels into trade decisions
- generate evaluation scores for live execution

## Missingness And Gap Reports

v5.5 should define explicit gap categories covering:

- missing validation input
- missing dataset records
- missing feature block
- missing outcome block
- missing lineage
- missing replay anchor timestamp
- duplicate dataset record id
- unsupported strategy track
- unsupported market
- feature/outcome leakage detected
- scanner input mutation detected
- order field detected
- buy/sell wording detected
- remote source not allowed
- API source not allowed
- network source not allowed
- provider source not allowed
- LLM metadata not allowed
- ML training trigger not allowed
- crawler trigger not allowed
- LIVE/PROD not allowed
- parquet not allowed
- split chronology violation
- split partition overlap
- insufficient records for split
- report-only validation complete

Missingness reporting should summarize:

- feature missing count
- outcome missing count
- lineage missing count
- anchor timestamp missing count
- blocked split count
- report-only warning count

## Safety Guard

The v5.5 safety guard must reject:

- remote URL fixture paths
- provider/API/network source metadata
- broker/account/order fields
- execution approval fields
- buy/sell/entry/exit wording
- LIVE/PROD markers
- Kiwoom/LS/provider path markers
- Gemini/cloud LLM/local runtime metadata
- ML training triggers
- learned-model evaluation triggers
- crawler triggers
- parquet sources or export modes

The safety guard must preserve:

- `read_only=true`
- `report_only=true`
- `non_executable=true`
- `local_file_only=true`
- `no_network=true`
- `no_provider_api=true`
- `no_order=true`
- `no_llm_runtime=true`
- `no_ml_training=true`

## CLI Design

Planned local fixture-only commands:

- `historical-dataset-validate --fixture-file ... [--output-file ...]`
- `historical-dataset-leakage-audit --fixture-file ... [--output-file ...]`
- `historical-dataset-split-manifest --fixture-file ... [--output-file ...]`
- `historical-dataset-coverage-report --fixture-file ... [--output-file ...]`
- `historical-dataset-label-distribution --fixture-file ... [--output-file ...]`

CLI design rules:

- `--fixture-file` is required
- inputs are local JSON fixtures only
- `--output-file` writes local JSON output only
- commands produce report-only outputs only
- commands must not mutate the input dataset
- commands must not export tensors, model weights, or training-ready binary artifacts
- commands must not train models
- commands must not run learned-model evaluation
- commands must not create trading signals, trade approvals, or order candidates
- parquet output remains unsupported

## Tests

Planned focused test areas:

- model construction and required safety flags
- local fixture loader success
- local fixture loader remote/parquet rejection
- validation report generation from valid v5.4 fixture input
- lineage/feature/outcome missing gap detection
- leakage audit detection for forbidden feature fields
- scanner replay input immutability verification
- chronological split generation by replay anchor timestamp
- split overlap rejection
- duplicate dataset record id rejection
- insufficient-record split fail-closed behavior
- coverage report generation
- label distribution report generation
- CLI command success paths
- CLI error handling for missing fixture and invalid local fixture
- parquet unsupported tests

## system_smoke Design

At v5.5 milestone close, `system_smoke` should confirm:

- `historical_dataset_validation_fixture_run=true`
- `historical_dataset_validation_report_generated=true`
- `historical_dataset_leakage_audit_generated=true`
- `historical_dataset_chronological_split_manifest_generated=true`
- `historical_dataset_feature_outcome_leakage_absent=true`
- `historical_dataset_split_is_chronological=true`
- `historical_dataset_validation_report_only=true`
- `historical_dataset_validation_read_only=true`
- `historical_dataset_validation_non_executable=true`
- `historical_dataset_validation_local_files_only=true`
- `historical_dataset_validation_ml_training_run=false`
- `historical_dataset_validation_order_intent_created=false`
- `historical_dataset_validation_external_network_calls=false`
- `investing_crawler_called=false`
- `finviz_scraper_called=false`
- `news_ingestion_called=false`
- `gemini_called=false`
- `kiwoom_api_called=false`
- `ls_api_called=false`
- `broker_api_called=false`

Smoke construction should:

- derive a local v5.4 dataset fixture
- run v5.5 validation
- run v5.5 leakage audit
- run v5.5 chronological split manifest generation
- confirm no mutation of source dataset input
- confirm report-only safety flags across generated reports

## Non-Goals

v5.5 must not implement:

- ML training
- learned-model evaluation
- hyperparameter search
- tensor export
- feature scaling pipelines for training runtime
- prediction serving
- runtime trading signals
- trade approval
- order candidate creation
- broker/account integration
- network/provider adapters
- real market or calendar data fetching
- Investing.com crawling
- FINVIZ scraping
- news ingestion
- Gemini / Google AI Studio integration
- Kiwoom / LS integration
- LIVE / PROD execution paths
- parquet support

## Task-By-Task Execution Order

### Task 1: Validation Model Surface

- define `HistoricalDatasetValidationConfig`
- define `HistoricalDatasetValidationInput`
- define validation/leakage/split/coverage/distribution/safety report models
- add required safety flags and local-fixture-only constraints
- add local JSON fixture loader
- add focused model tests

### Task 2: Validation Safety Guard And Gap Taxonomy

- implement validation guard for unsafe metadata and unsupported source types
- finalize validation gap categories
- add focused safety and taxonomy tests

### Task 3: Validation Engine

- implement record-level validation report generation
- count missing lineage/feature/outcome/anchor fields
- preserve source dataset immutability
- add focused validation engine tests

### Task 4: Leakage Audit Engine

- implement feature/outcome leakage scan
- detect forbidden future/outcome fields in feature block
- detect mutated scanner replay metadata
- add focused leakage audit tests

### Task 5: Chronological Split Engine

- implement deterministic chronological train/validation/test split policy
- add split manifest and record refs
- enforce no partition overlap and no shuffle
- add focused split tests

### Task 6: Coverage And Label Distribution Reports

- implement symbol/market/track coverage summaries
- implement whole-dataset and per-split label distribution reports
- add focused report tests

### Task 7: CLI Wiring

- register local fixture-only CLI commands
- add focused CLI tests
- verify outputs remain report-only and non-executable

### Task 8: system_smoke, Validation, Commit, And Tag

- add v5.5 smoke coverage
- run focused tests
- run `tests/test_system_smoke.py`
- run full pytest if feasible
- commit only v5.5 files after review
- create v5.5 tag only after milestone completion

## Self-Review

Spec coverage check:

- inputs: covered in `Inputs`
- validation rules: covered in `Dataset Validation Rules`
- feature/outcome leakage audit: covered in `Feature / Outcome Leakage Audit Rules`
- chronological split policy: covered in `Chronological Split Policy`
- symbol/market/track coverage: covered in `Symbol / Market / Track Coverage Reports`
- label distribution: covered in `Label Distribution Reports`
- missingness/gaps: covered in `Missingness And Gap Reports`
- safety guard: covered in `Safety Guard`
- CLI design: covered in `CLI Design`
- tests: covered in `Tests`
- system smoke: covered in `system_smoke Design`
- non-goals: covered in `Non-Goals`
- execution order: covered in `Task-By-Task Execution Order`

Placeholder scan:

- no `TODO`, `TBD`, or deferred implementation placeholders included in execution tasks
- future functionality excluded only through explicit non-goals and hard boundaries

Type consistency check:

- config/input/report names remain consistent across model, engine, CLI, and smoke sections
- split concepts consistently use `HistoricalDatasetSplitManifest` and `HistoricalDatasetSplitRecordRef`
- report names consistently use `HistoricalDatasetValidation*` prefixes for v5.5 outputs
