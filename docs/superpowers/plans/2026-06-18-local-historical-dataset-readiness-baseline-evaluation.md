# Local Historical Dataset Readiness And Baseline Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local fixture-only v5.6 readiness and deterministic non-learning baseline evaluation layer that consumes v5.5 validation/split artifacts and produces report-only readiness reports, split quality reports, imbalance reports, drift checks, and baseline evaluation summaries, without performing any ML training or learned-model fitting.

**Architecture:** Add a dedicated historical dataset readiness module family that reads only local fixture-derived v5.5 validation outputs, enforces fail-closed safety gates, evaluates dataset readiness and split quality, measures imbalance and drift descriptively, and emits deterministic non-learning baseline reports from existing labels only. Keep every output report-only, non-executable, local-file-only, and explicitly unsuitable for runtime trading, order creation, or learned-model evaluation.

**Tech Stack:** Python 3.11, Pydantic v2, existing strict model patterns, local fixture loaders, deterministic pure-Python counting/statistics helpers, existing CLI patterns, pytest, system smoke

---

## File Structure

### New files

- `src/stock_risk_mcp/historical_dataset_readiness_models.py`
  Readiness config/input/report schemas, split quality report, imbalance report, baseline config, baseline evaluation report, readiness gap and safety report models.
- `src/stock_risk_mcp/historical_dataset_readiness_fixture.py`
  Local JSON fixture loader for v5.6 readiness inputs with local-path-only and parquet rejection.
- `src/stock_risk_mcp/historical_dataset_readiness_guard.py`
  Fail-closed safety guard for readiness metadata, baseline config, unsupported fields, and non-learning boundary enforcement.
- `src/stock_risk_mcp/historical_dataset_readiness_engine.py`
  Pure deterministic readiness checks, split quality checks, imbalance checks, drift checks, and non-learning baseline evaluation report builders.
- `tests/test_historical_dataset_readiness_models.py`
  Model construction, safety flags, fixture loader, and unsupported metadata tests.
- `tests/test_historical_dataset_readiness_engine.py`
  Readiness gate, split quality, imbalance, drift, baseline, and gap tests.
- `tests/test_historical_dataset_readiness_cli.py`
  CLI success/failure tests for local fixture-only readiness and baseline commands.

### Modified files

- `src/stock_risk_mcp/cli.py`
  Register v5.6 readiness, split quality, imbalance, baseline evaluation, and readiness safety report commands.
- `src/stock_risk_mcp/system_smoke.py`
  Add v5.6 local readiness and deterministic baseline smoke coverage.
- `tests/test_system_smoke.py`
  Assert v5.6 smoke checks.
- `WORK_SUMMARY.md`
  Append v5.6 summary only if repository convention still requires it at milestone close.

### Existing files to inspect for compatibility only

- `src/stock_risk_mcp/historical_dataset_validation_models.py`
- `src/stock_risk_mcp/historical_dataset_validation_fixture.py`
- `src/stock_risk_mcp/historical_dataset_validation_guard.py`
- `src/stock_risk_mcp/historical_dataset_validation_engine.py`
- `tests/test_historical_dataset_validation_engine.py`
- `tests/test_historical_dataset_validation_models.py`

## Inputs

v5.6 may consume only local fixture-derived v5.5 artifacts:

- `HistoricalDatasetValidationReport`
- `HistoricalDatasetLeakageAuditReport`
- `HistoricalDatasetSplitManifest`
- `HistoricalDatasetCoverageReport`
- `HistoricalDatasetLabelDistributionReport`
- `HistoricalDatasetValidationGapReport`
- `HistoricalDatasetValidationSafetyReport`
- safe v5.4 dataset records only if needed for report-only counting

The aggregate v5.6 input should remain:

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

v5.6 should introduce these first-class units:

- `HistoricalDatasetReadinessConfig`
- `HistoricalDatasetReadinessInput`
- `HistoricalDatasetReadinessReport`
- `HistoricalDatasetBaselineConfig`
- `HistoricalDatasetBaselineEvaluationReport`
- `HistoricalDatasetSplitQualityReport`
- `HistoricalDatasetImbalanceReport`
- `HistoricalDatasetReadinessGapReport`
- `HistoricalDatasetReadinessSafetyReport`

Expected responsibilities:

- `HistoricalDatasetReadinessConfig`
  Carries minimum count thresholds, required split policy expectations, label coverage requirements, imbalance warning thresholds, and hard safety flags.
- `HistoricalDatasetReadinessInput`
  Wraps v5.5 validation artifacts and optional safe v5.4 records for descriptive counting only.
- `HistoricalDatasetReadinessReport`
  Summarizes pass/block/warn readiness gates and explicitly indicates report-only degraded mode instead of training approval.
- `HistoricalDatasetBaselineConfig`
  Enumerates which deterministic non-learning baselines are enabled and explicitly forbids learned-model fitting or training modes.
- `HistoricalDatasetBaselineEvaluationReport`
  Summarizes deterministic baseline predictions and classification metrics by split without any training behavior.
- `HistoricalDatasetSplitQualityReport`
  Summarizes chronological integrity, split sizes, overlap/duplication checks, coverage drift, and missing split risks.
- `HistoricalDatasetImbalanceReport`
  Summarizes label imbalance, coverage concentration, rare-label warnings, and optionally split-to-split distribution shifts.
- `HistoricalDatasetReadinessGapReport`
  Captures blocked readiness gates, missingness, leakage findings, unsupported metadata, and non-learning boundary violations.
- `HistoricalDatasetReadinessSafetyReport`
  Restates the hard safety boundary and confirms no executable/runtime path or learned-model path was introduced.

## Dataset Readiness Gates

Readiness gating must remain fail-closed and descriptive only. It must check:

- validation report passed or explicit report-only degraded mode is recorded
- leakage audit is clean or explicitly blocked
- chronological split manifest exists
- split policy remains chronological
- no random shuffle is used
- no split partition overlap exists
- no duplicated dataset record ids across split partitions exist
- minimum total record count is satisfied
- minimum train, validation, and test record counts are satisfied
- minimum label coverage is satisfied
- imbalance warnings are surfaced explicitly
- missingness warnings are surfaced explicitly
- lineage completeness meets threshold or is degraded report-only
- safety flags remain intact across all upstream artifacts

Readiness output must never:

- approve model training
- approve deployment
- approve trading
- produce order candidates
- create runtime trading signals

## Split Quality Checks

Split quality reporting should evaluate:

- chronological order across train, validation, and test
- deterministic policy adherence
- no random shuffle
- no duplicate record ids across partitions
- no partition overlap
- sufficient count per partition
- earliest/latest anchor per split
- symbol coverage per split
- market coverage per split
- strategy track coverage per split
- label coverage per split
- large split drift warnings if distributions diverge materially

The split quality report must remain descriptive only and must not rebalance, reshuffle, or mutate the split.

## Label Imbalance Checks

Imbalance reporting should evaluate:

- global label count distribution
- per-split label count distribution
- per-label percentage
- rare-label warnings
- dominant-label concentration warnings
- missing-label-in-split warnings
- imbalance severity summary

The report should distinguish:

- blocking conditions
- report-only warnings
- neutral observations

It must not:

- reweight training samples
- synthesize new labels
- fit any model

## Symbol / Market / Track Coverage Checks

Coverage readiness checks should summarize:

- total records
- total symbols
- total markets
- total strategy tracks
- records by symbol
- records by market
- records by strategy track
- split-specific symbol and market coverage
- missing or underrepresented symbol warnings
- missing or underrepresented market warnings
- single-track confirmation for the current domestic-only boundary

Coverage reporting must remain descriptive and must not rank opportunities or score tradability.

## Feature Missingness Checks

Feature missingness reporting should summarize:

- missing feature block count
- missing outcome block count
- missing lineage count
- missing replay anchor count if represented
- field-level missingness rates for safe descriptive fields only
- per-split missingness counts
- report-only degraded mode if missingness exceeds warning threshold

It must not:

- impute values
- synthesize replacement features
- generate tensors

## Simple Deterministic Non-Learning Baselines

Allowed baseline families in v5.6:

- majority-label baseline
- per-symbol majority-label baseline
- per-market majority-label baseline
- per-track majority-label baseline
- prior-distribution baseline
- no-skill baseline

Each baseline must be deterministic and non-learning:

- no fitting learned parameters
- no stochastic search
- no gradient optimization
- no embeddings
- no local model runtime
- no cloud model calls

Baseline evaluation outputs must be explicitly marked:

- report-only
- non-executable
- not a trading signal
- not a deployment recommendation

## Evaluation Metrics

Metrics may be produced only if the existing label taxonomy supports them and only as descriptive classification summaries:

- accuracy
- balanced accuracy if feasible
- macro precision if feasible
- macro recall if feasible
- macro F1 if feasible
- label coverage
- confusion matrix counts
- per-split metric summary
- baseline-to-baseline comparison table

Metrics must not include:

- P/L backtest
- portfolio simulation
- order simulation
- runtime signal quality score
- deployment approval score

## Safety Guard

The v5.6 safety guard must reject:

- remote URL fixture paths
- provider/API/network source metadata
- broker/account/order fields
- execution approval fields
- buy/sell/entry/exit wording
- LIVE/PROD markers
- Kiwoom/LS/provider path markers
- Gemini/cloud LLM/local runtime metadata
- ML training triggers
- learned-model fitting or evaluation triggers
- tensor export markers
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

- `historical-dataset-readiness-report --fixture-file ... [--output-file ...]`
- `historical-dataset-split-quality-report --fixture-file ... [--output-file ...]`
- `historical-dataset-imbalance-report --fixture-file ... [--output-file ...]`
- `historical-dataset-baseline-evaluation --fixture-file ... [--output-file ...]`
- `historical-dataset-readiness-safety-report --fixture-file ... [--output-file ...]`

CLI design rules:

- `--fixture-file` is required
- inputs are local JSON fixtures only
- `--output-file` writes local JSON output only
- commands produce report-only outputs only
- commands must not mutate upstream v5.5 artifacts
- commands must not export tensors, weights, or training-ready binaries
- commands must not fit learned models
- commands must not create trading signals, trade approvals, or order candidates
- parquet output remains unsupported

## Tests

Planned focused test areas:

- model construction and required safety flags
- local fixture loader success
- local fixture loader remote/parquet rejection
- readiness report success path
- readiness degraded mode for warning-only thresholds
- leakage-blocked readiness fail-closed behavior
- split quality report generation
- no-random-shuffle enforcement
- no-overlap / no-duplicate split checks
- minimum count threshold checks
- imbalance report generation
- dominant-label warning generation
- missing-label-in-split warning generation
- baseline evaluation generation for each allowed deterministic baseline
- metric summary generation when label support is sufficient
- CLI success/failure paths
- CLI missing fixture and invalid local fixture handling
- parquet unsupported tests

## system_smoke Design

At v5.6 milestone close, `system_smoke` should confirm:

- `historical_dataset_readiness_fixture_run=true`
- `historical_dataset_readiness_report_generated=true`
- `historical_dataset_split_quality_report_generated=true`
- `historical_dataset_imbalance_report_generated=true`
- `historical_dataset_baseline_evaluation_generated=true`
- `historical_dataset_baseline_non_learning=true`
- `historical_dataset_readiness_report_only=true`
- `historical_dataset_readiness_read_only=true`
- `historical_dataset_readiness_non_executable=true`
- `historical_dataset_readiness_local_files_only=true`
- `historical_dataset_readiness_ml_training_run=false`
- `historical_dataset_readiness_learned_model_evaluation_run=false`
- `historical_dataset_readiness_order_intent_created=false`
- `external_network_calls=false`
- `investing_crawler_called=false`
- `finviz_scraper_called=false`
- `news_ingestion_called=false`
- `gemini_called=false`
- `kiwoom_api_called=false`
- `ls_api_called=false`
- `broker_api_called=false`

Smoke construction should:

- derive a local v5.5 validation fixture
- run v5.6 readiness report generation
- run split quality reporting
- run imbalance reporting
- run deterministic non-learning baseline evaluation
- confirm no mutation of upstream validation artifacts
- confirm report-only safety flags across generated reports

## Non-Goals

v5.6 must not implement:

- ML training
- learned-model fitting
- learned-model evaluation
- hyperparameter search
- tensor export
- feature engineering pipelines for training
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

### Task 1: Readiness Model Surface

- define readiness config/input/report models
- define baseline config and baseline evaluation report models
- define split quality and imbalance report models
- add required safety flags and local-fixture-only constraints
- add local JSON fixture loader
- add focused model tests

### Task 2: Readiness Safety Guard And Gap Taxonomy

- implement readiness guard for unsafe metadata and unsupported source types
- finalize readiness gap categories
- add focused safety and taxonomy tests

### Task 3: Readiness And Split Quality Engine

- implement readiness gate evaluation
- implement split quality reporting
- preserve upstream artifact immutability
- add focused readiness/split tests

### Task 4: Imbalance And Drift Reporting

- implement imbalance report generation
- implement simple drift/distribution shift warnings
- add focused imbalance/drift tests

### Task 5: Deterministic Baseline Evaluation Engine

- implement majority-label, per-symbol, per-market, per-track, prior-distribution, and no-skill baselines
- implement safe classification metric summaries
- add focused baseline evaluation tests

### Task 6: CLI Wiring

- register local fixture-only CLI commands
- add focused CLI tests
- verify outputs remain report-only and non-executable

### Task 7: system_smoke, Validation, Commit, And Tag

- add v5.6 smoke coverage
- run focused tests
- run `tests/test_system_smoke.py`
- run full pytest if feasible
- commit only v5.6 files after review
- create v5.6 tag only after milestone completion

## Self-Review

Spec coverage check:

- inputs: covered in `Inputs`
- readiness gates: covered in `Dataset Readiness Gates`
- split quality checks: covered in `Split Quality Checks`
- imbalance checks: covered in `Label Imbalance Checks`
- coverage checks: covered in `Symbol / Market / Track Coverage Checks`
- feature missingness: covered in `Feature Missingness Checks`
- deterministic baselines: covered in `Simple Deterministic Non-Learning Baselines`
- evaluation metrics: covered in `Evaluation Metrics`
- safety guard: covered in `Safety Guard`
- CLI design: covered in `CLI Design`
- tests: covered in `Tests`
- system smoke: covered in `system_smoke Design`
- non-goals: covered in `Non-Goals`
- execution order: covered in `Task-By-Task Execution Order`

Placeholder scan:

- no `TODO`, `TBD`, or deferred implementation placeholders included in execution tasks
- excluded future work is expressed only as explicit non-goals and hard boundaries

Type consistency check:

- readiness, split quality, imbalance, and baseline report names remain consistent across model, engine, CLI, and smoke sections
- baseline concepts consistently stay within non-learning, deterministic boundaries
- safety report and gap report names consistently use `HistoricalDatasetReadiness*` prefixes for v5.6 outputs
