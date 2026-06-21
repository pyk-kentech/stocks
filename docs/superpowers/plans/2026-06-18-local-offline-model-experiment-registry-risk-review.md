# Local Offline Model Experiment Registry Risk Review Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Design a local, offline, fixture-only v5.8 experiment registry and model risk review layer that consumes v5.7 sandbox training outputs and emits report-only experiment registry reports, comparison reports, risk review reports, promotion-block reports, lineage reports, safety reports, and audit manifests without creating deployment, live inference, runtime trading signal, order candidate, paper-trading, or production registry paths.

**Architecture:** Add a dedicated historical model experiment governance module family that reads only local fixture-derived v5.7 artifacts, validates lineage and safety markers, registers sandbox experiments into a local report-only registry surface, compares sandbox experiments strictly by offline metrics, evaluates model risk and promotion-block conditions, and emits blocked-by-default governance artifacts. Keep every output explicitly non-executable from a trading perspective and isolated from broker, account, order, live, provider, network, cloud LLM, local LLM runtime, and deployment surfaces.

**Tech Stack:** Python 3.11, Pydantic v2, existing strict model patterns, existing local fixture loaders, pure-Python comparison/risk checks, pytest, system smoke

---

## File Structure

### Planned new files

- `src/stock_risk_mcp/historical_model_experiment_models.py`
  Registry config/input/report schemas, experiment record, comparison report, risk review report, promotion-block report, lineage report, safety report, gap report, and audit record models.
- `src/stock_risk_mcp/historical_model_experiment_fixture.py`
  Local JSON fixture loader for v5.8 experiment registry inputs with local-path-only and parquet rejection.
- `src/stock_risk_mcp/historical_model_experiment_guard.py`
  Fail-closed governance guard for deployment/live/runtime/order/LLM/provider/network/crawler/parquet/unsafe-artifact markers and missing safety flags.
- `src/stock_risk_mcp/historical_model_experiment_engine.py`
  Registry assembly, lineage validation, experiment comparison, risk review evaluation, promotion-block generation, and report builders.
- `tests/test_historical_model_experiment_models.py`
  Model construction, fixture loading, registry defaults, blocked markers, and safety-boundary tests.
- `tests/test_historical_model_experiment_engine.py`
  Registry, comparison, risk review, promotion-block, lineage, and blocked-path tests.
- `tests/test_historical_model_experiment_cli.py`
  CLI success/failure tests for local fixture-only experiment governance commands.

### Planned modified files

- `src/stock_risk_mcp/cli.py`
  Register v5.8 experiment registry and risk review commands.
- `src/stock_risk_mcp/system_smoke.py`
  Add v5.8 local offline experiment registry and risk review smoke coverage.
- `tests/test_system_smoke.py`
  Assert v5.8 smoke checks.
- `WORK_SUMMARY.md`
  Append v5.8 milestone summary only if repository convention still requires it at milestone close.

### Existing files to inspect for compatibility only

- `src/stock_risk_mcp/historical_model_training_models.py`
- `src/stock_risk_mcp/historical_model_training_engine.py`
- `src/stock_risk_mcp/historical_dataset_readiness_models.py`
- `src/stock_risk_mcp/historical_dataset_validation_models.py`
- `tests/test_historical_model_training_engine.py`
- `tests/test_historical_model_training_models.py`

## 1. Inputs

v5.8 may consume only local fixture-derived artifacts from v5.7 and earlier lineage references:

- `HistoricalModelTrainingRunReport`
- `HistoricalModelEvaluationReport`
- `HistoricalModelMetricsReport`
- `HistoricalModelArtifactManifest`
- `HistoricalModelTrainingSafetyReport`
- `HistoricalModelTrainingGapReport`
- v5.6 `HistoricalDatasetBaselineEvaluationReport` when explicit baseline comparison is needed
- v5.5 `HistoricalDatasetSplitManifest` when split lineage restatement is needed
- v5.5 `HistoricalDatasetLeakageAuditReport` when leakage dependency lineage is needed

Each input must remain:

- local fixture only
- offline only
- read-only on input
- report-only on output
- non-executable from a trading perspective
- no-network
- no-provider-api
- no-order
- no-cloud-LLM
- no-local-LLM-runtime
- no-runtime-trading-signal
- no-order-candidate

The aggregate v5.8 input should bundle the above into a single strict `HistoricalModelExperimentRegistryInput`.

## 2. Experiment Registry Schema

Core planned concepts:

- `HistoricalModelExperimentRegistryConfig`
- `HistoricalModelExperimentRegistryInput`
- `HistoricalModelExperimentRecord`
- `HistoricalModelExperimentRegistryReport`
- `HistoricalModelComparisonReport`
- `HistoricalModelRiskReviewReport`
- `HistoricalModelPromotionBlockReport`
- `HistoricalModelExperimentLineageReport`
- `HistoricalModelExperimentSafetyReport`
- `HistoricalModelExperimentGapReport`
- `HistoricalModelExperimentAuditRecord`

Each `HistoricalModelExperimentRecord` should track:

- local sandbox experiment id
- model id
- model type
- dataset manifest id
- split manifest id
- feature schema version
- label schema version
- metrics report id
- artifact manifest id
- safety report id
- gap report id
- training timestamp
- source manifest ids
- source audit record ids
- provider provenance ids if already present in lineage
- report-only marker
- non-executable marker
- local-file-only marker
- offline-only marker
- no-runtime-signal marker
- no-order-candidate marker

Registry records must not contain:

- production registry ids
- deployment endpoints
- runtime scoring endpoints
- broker metadata
- account metadata
- order metadata
- provider API credentials
- live/prod enablement markers

## 3. Experiment Comparison Rules

Comparison stays sandbox-only and report-only.

Compare experiments only on:

- validation accuracy
- test accuracy
- balanced accuracy if available
- macro precision / recall / F1 if available
- confusion matrix summary
- per-label support summary
- baseline improvement
- train/test gap
- overfit warnings
- low-support warnings
- safety blocked status

Comparison outputs must not:

- rank for live deployment
- recommend trading use
- select a production champion
- imply buy/sell quality
- imply runtime approval

If comparison inputs are incomplete, emit explicit report-only gaps rather than silent fallback.

## 4. Model Risk Review Rules

Risk review should inspect the registry record plus supporting lineage.

Required checks:

- overfit risk present or absent
- low label support present or absent
- severe label imbalance present or absent
- large train/validation gap
- large train/test gap
- weak or absent baseline improvement
- missing leakage audit dependency
- missing validation/split lineage
- missing or unsafe artifact metadata
- optional sklearn dependency risk
- unsupported model type
- missing safety flags
- any runtime/deployment/trading marker

Risk review output should be blocked-by-default and explicitly report:

- risk severity counts
- blocking risk count
- warning count
- blocked reasons
- report-only warnings

## 5. Promotion-Block Rules

Every experiment remains blocked from production/runtime use by default.

Required blocked fields:

- `production_use_allowed=false`
- `live_inference_allowed=false`
- `runtime_trading_signal_allowed=false`
- `order_candidate_allowed=false`
- `paper_trading_allowed=false`
- `broker_path_allowed=false`
- `live_prod_allowed=false`
- `deployment_allowed=false`

Promotion-block report should additionally restate:

- report-only governance only
- sandbox-only origin
- non-executable from trading perspective
- no broker/order/account/provider path

No v5.8 output may flip any of these to `true`.

## 6. Artifact Lineage Validation

Lineage validation should confirm:

- run report id, evaluation report id, metrics report id, artifact manifest id, safety report id, and gap report id are internally consistent
- dataset manifest id exists
- split manifest id exists
- feature schema version exists
- label schema version exists
- source manifest ids are present when expected
- leakage audit reference is present when expected
- split lineage is chronological when present
- training timestamp exists and is timezone-aware

If lineage is partial or inconsistent:

- emit explicit lineage gaps
- keep report-only semantics
- keep promotion blocked

## 7. Baseline Comparison Rules

If v5.6 deterministic baseline data is available:

- compare sandbox validation/test metrics against baseline accuracy
- compute delta vs baseline
- flag weak improvement
- flag baseline underperformance

If baseline data is missing:

- do not synthesize baseline numbers
- emit explicit report-only missing-baseline gap/warning

Baseline comparison must remain:

- deterministic
- local-only
- non-learning
- non-deployment

## 8. Overfit / Instability Checks

v5.8 should plan explicit governance checks for:

- train/test accuracy gap over threshold
- train/validation accuracy gap over threshold
- unstable metric profile across partitions
- low support for minority labels
- severe imbalance warning inherited from v5.6
- sklearn optional dependency risk

These checks should only:

- flag risk
- affect blocked status
- produce report-only warnings

These checks must not:

- trigger retraining
- mutate training outputs
- generate new trading logic

## 9. Safety Guard

The guard should reject:

- production deployment markers
- live inference markers
- runtime trading signal fields
- order candidate fields
- buy/sell/entry/exit wording
- broker/account/order metadata
- credentials/tokens/secrets
- network/API/provider markers
- cloud LLM markers
- local LLM runtime markers
- crawler markers
- LIVE/PROD markers
- parquet source/export
- unsafe artifact manifest metadata
- experiment entry claiming production readiness

Guard output should map each failure to explicit blocked categories rather than silently discarding fields.

## 10. CLI Design

Planned local fixture-only commands:

- `historical-model-experiment-register --fixture-file ... [--output-file ...]`
- `historical-model-experiment-compare --fixture-file ... [--output-file ...]`
- `historical-model-risk-review --fixture-file ... [--output-file ...]`
- `historical-model-promotion-block-report --fixture-file ... [--output-file ...]`
- `historical-model-experiment-safety-report --fixture-file ... [--output-file ...]`

CLI contract:

- `--fixture-file` required
- local JSON fixture only
- optional `--output-file` writes local JSON/report output only
- no deployment
- no live inference
- no data fetch
- no network
- no LLM
- no broker/order/account/provider API
- no runtime trading signal
- no order candidate
- no buy/sell recommendation
- no paper/live trading

## 11. Tests

Planned focused tests:

- valid experiment registry config/input construction
- required safety flags
- experiment record lineage construction
- production/deployment/live markers rejected
- runtime trading signal/order candidate markers rejected
- buy/sell wording rejected
- broker/account/order/provider metadata rejected
- credential/token/secret markers rejected
- network/API/provider markers rejected
- cloud/local LLM markers rejected
- crawler markers rejected
- LIVE/PROD rejected
- parquet rejected
- comparison report generated from safe sandbox inputs
- risk review flags overfit/imbalance/low-support/weak-baseline cases
- promotion-block report always blocked by default
- lineage gaps emitted for missing dependencies
- optional sklearn dependency risk flagged without requiring sklearn installation
- CLI returns report-only JSON and file outputs

## 12. system_smoke Design

The future v5.8 smoke should confirm:

- `historical_model_experiment_registry_fixture_run=true`
- `historical_model_experiment_registry_report_generated=true`
- `historical_model_comparison_report_generated=true`
- `historical_model_risk_review_generated=true`
- `historical_model_promotion_block_report_generated=true`
- `historical_model_experiment_report_only=true`
- `historical_model_experiment_non_executable=true`
- `historical_model_experiment_no_runtime_signal=true`
- `historical_model_experiment_no_order_candidate=true`
- `historical_model_experiment_no_live_inference=true`
- `historical_model_experiment_no_deployment=true`
- `historical_model_experiment_no_broker_path=true`
- `historical_model_experiment_no_live_prod=true`
- `historical_model_experiment_no_network=true`
- `historical_model_experiment_no_cloud_llm=true`
- `historical_model_experiment_no_local_llm_runtime=true`
- `investing_crawler_called=false`
- `finviz_scraper_called=false`
- `news_ingestion_called=false`
- `gemini_called=false`
- `kiwoom_api_called=false`
- `ls_api_called=false`
- `broker_api_called=false`
- `credentials_accessed=false`
- `external_network_calls=false`

## 13. Non-Goals

v5.8 explicitly does not include:

- production model registry
- model deployment
- live inference
- advisory recommendation engine
- buy/sell signal generation
- order intent
- paper trading
- live trading
- portfolio simulator
- backtest P/L engine
- real provider ingestion
- LLM interpretation layer

## 14. Task-By-Task Execution Order

- [ ] Task 1: Define v5.8 experiment registry plan and invariants
- [ ] Task 2: Implement registry models and local fixture loader
- [ ] Task 3: Implement experiment safety guard and gap taxonomy
- [ ] Task 4: Implement registry/comparison/risk-review/promotion-block engine
- [ ] Task 5: Implement CLI wiring for registry and risk-review reports
- [ ] Task 6: Update system smoke, run targeted tests, run smoke, run full pytest if feasible, then commit/tag

## Acceptance Notes

Implementation should remain disciplined under the v5 offline governance philosophy:

- local fixture only
- offline only
- read-only input
- report-only output
- non-executable from trading perspective
- blocked-by-default governance
- no deployment path
- no live inference path
- no runtime trading signal
- no order candidate
- no paper/live trading connection
- parquet unsupported
