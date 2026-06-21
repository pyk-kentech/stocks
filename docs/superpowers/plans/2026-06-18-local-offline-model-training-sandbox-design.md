# Local Offline Model Training Sandbox Design Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Design a local, offline, fixture-only v5.7 supervised model training sandbox that consumes validated historical dataset artifacts from v5.4-v5.6 and produces report-only research training/evaluation outputs without creating production models, runtime trading signals, order candidates, or any live/provider-connected path.

**Architecture:** Add a dedicated historical model sandbox module family that reads only local validated dataset artifacts, enforces fail-closed eligibility and leakage gates before any training attempt, extracts features only from replay-time feature blocks, copies labels only from outcome-side targets after leakage validation, trains only local experimental non-production models inside an offline sandbox, and emits report-only manifests, metrics, safety reports, and optional local artifact manifests. Keep all outputs explicitly non-executable from a trading perspective and isolated from runtime scanner, broker, account, order, live, and provider paths.

**Tech Stack:** Python 3.11, Pydantic v2, existing strict model patterns, existing local fixture loaders, optional local `scikit-learn` only behind availability checks, pure-Python fallback baselines/helpers, pytest, system smoke

---

## File Structure

### Planned new files

- `src/stock_risk_mcp/historical_model_training_models.py`
  Training sandbox config/input/report schemas, experiment manifest, artifact manifest, metrics report, safety report, and audit record models.
- `src/stock_risk_mcp/historical_model_training_fixture.py`
  Local JSON fixture loader for v5.7 sandbox inputs with local-path-only and parquet rejection.
- `src/stock_risk_mcp/historical_model_training_guard.py`
  Fail-closed training eligibility, leakage, forbidden-runtime-path, unsupported-metadata, and artifact-safety guard.
- `src/stock_risk_mcp/historical_model_training_engine.py`
  Offline training eligibility checks, safe feature/label extraction, optional local model fitting, deterministic evaluation, baseline comparison, and report builders.
- `tests/test_historical_model_training_models.py`
  Model construction, fixture loading, and safety-boundary tests.
- `tests/test_historical_model_training_engine.py`
  Eligibility gating, split usage, feature/label isolation, optional trainer availability, metrics, artifact, and blocked-path tests.
- `tests/test_historical_model_training_cli.py`
  CLI success/failure tests for local fixture-only sandbox commands.

### Planned modified files

- `src/stock_risk_mcp/cli.py`
  Register v5.7 local offline sandbox commands.
- `src/stock_risk_mcp/system_smoke.py`
  Add v5.7 local offline model training sandbox smoke coverage.
- `tests/test_system_smoke.py`
  Assert v5.7 smoke checks.
- `WORK_SUMMARY.md`
  Append v5.7 milestone summary only if repository convention still requires it at milestone close.

### Existing files to inspect for compatibility only

- `src/stock_risk_mcp/historical_dataset_models.py`
- `src/stock_risk_mcp/historical_dataset_validation_models.py`
- `src/stock_risk_mcp/historical_dataset_readiness_models.py`
- `src/stock_risk_mcp/historical_dataset_validation_engine.py`
- `src/stock_risk_mcp/historical_dataset_readiness_engine.py`
- `tests/test_historical_dataset_engine.py`
- `tests/test_historical_dataset_validation_engine.py`
- `tests/test_historical_dataset_readiness_engine.py`

## 1. Inputs

v5.7 may consume only local fixture-derived artifacts from prior stages:

- v5.4 `HistoricalDatasetRecord`
- v5.4 `HistoricalDatasetExportManifest`
- v5.5 `HistoricalDatasetValidationReport`
- v5.5 `HistoricalDatasetLeakageAuditReport`
- v5.5 `HistoricalDatasetSplitManifest`
- v5.5 `HistoricalDatasetCoverageReport`
- v5.5 `HistoricalDatasetLabelDistributionReport`
- v5.6 `HistoricalDatasetReadinessReport`
- v5.6 `HistoricalDatasetSplitQualityReport`
- v5.6 `HistoricalDatasetImbalanceReport`
- v5.6 `HistoricalDatasetBaselineEvaluationReport`

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

The aggregate v5.7 sandbox input should bundle the above into a single strict `HistoricalModelTrainingSandboxInput`.

## 2. Training Eligibility Gates

No training attempt should start until all eligibility gates pass. The gate report should check:

- required v5.4-v5.6 artifacts are present
- validation report is clean or explicitly blocked
- leakage audit confirms no feature/outcome leakage
- chronological split manifest exists
- split remains chronological
- random shuffle is absent
- no partition overlap exists
- no duplicated record ids exist across partitions
- readiness report is report-only and non-approval
- readiness blocking gates are zero or fail closed
- baseline evaluation report is deterministic and non-learning
- feature schema and label schema versions are present
- dataset lineage is complete enough for offline audit
- label support is above configured minimum for planned model type
- any missing dependency produces explicit report-only blocked status rather than implicit fallback

Eligibility output must never:

- approve trading
- approve production deployment
- create runtime inference hooks
- create order candidates
- create live scoring artifacts

## 3. Allowed Local Model Types

v5.7 may plan only lightweight experimental classifiers:

- pure-Python dummy classifier / majority-label baseline
- optional `scikit-learn` logistic regression
- optional `scikit-learn` decision tree
- optional `scikit-learn` random forest only if lightweight and already acceptable locally

Model-type policy:

- `dummy` path must always exist as the dependency-safe fallback
- `sklearn` path must be optional behind availability detection
- tests must pass without network or package download
- no deep learning
- no neural networks
- no local LLM
- no cloud LLM

If local dependency risk exists, the implementation plan should prioritize:

1. pure-Python dummy baseline path
2. optional sklearn-backed experimental path
3. blocked/report-only status when an unavailable optional trainer is requested

## 4. Forbidden Model / Runtime Paths

v5.7 must explicitly reject:

- production model promotion
- runtime trading signal generation
- order candidate generation
- live inference path registration
- broker/account/order integration
- Kiwoom/LS/provider metadata
- network/provider/API fetch
- LIVE/PROD markers
- cloud LLM
- local LLM runtime
- paper/live trading
- backtest P/L engine
- portfolio simulator
- advisory recommendation engine
- parquet input/output unless explicitly deferred as unsupported

The safety guard should map forbidden paths to explicit blocked categories rather than silently ignoring them.

## 5. Feature Extraction Boundary

Only replay-time known feature-block information may enter model features. The extractor must use:

- v5.4 feature block only
- safe top-level descriptive metadata already known at replay time
- allowed split/coverage lineage references if they are non-predictive audit metadata

The feature extractor must reject:

- outcome label
- forward return
- max favorable excursion
- max adverse excursion
- any post-anchor actual value
- readiness-side blocked/safety metadata as predictive feature input
- baseline evaluation outputs as training features

Feature extraction should preserve:

- report-only semantics
- replay-time known boundary
- scanner replay pre-outcome immutability

## 6. Label Handling Boundary

Training targets may come only from the outcome block after validation confirms no leakage.

Label handling rules:

- labels originate from v5.4 outcome block only
- selected supervised target label must be copied into a dedicated target vector only after eligibility checks pass
- labels must never be written back into the feature block
- labels must never mutate scanner replay input
- labels must remain research-only and report-only
- insufficient/unsupported labels must produce blocked or inconclusive training reports

The label pipeline must explicitly prevent:

- label leakage into features
- use of future returns inside features
- use of evaluation predictions as labels
- treating labels as runtime trading decisions

## 7. Train / Validation / Test Split Usage

v5.7 must use only the v5.5 chronological split manifest.

Rules:

- train only on train partition
- evaluate on validation/test partitions only
- never random shuffle across time
- never mix future partitions into train
- never rebuild alternate shuffled splits inside the sandbox
- optional hyperparameter search, if ever planned later, must remain validation-only and deterministic

The split usage report should restate:

- chronological split used
- no random shuffle
- no overlap
- no duplicated record ids
- partition counts used by the sandbox

## 8. Metrics And Reports

v5.7 outputs must be report-only research artifacts. Planned reports:

- `HistoricalModelTrainingEligibilityReport`
- `HistoricalModelEvaluationReport`
- `HistoricalModelComparisonReport`
- `HistoricalModelTrainingGapReport`
- `HistoricalModelTrainingSafetyReport`

Planned report-only metrics:

- train accuracy
- validation accuracy
- test accuracy
- balanced accuracy if feasible
- macro precision / recall / F1 if feasible
- confusion matrix
- per-label metrics
- low-support label warning
- overfit warning when train/test gap exceeds threshold
- comparison versus v5.6 deterministic baselines
- blocked/unsafe training summary

Metrics must not be interpreted as:

- trade approval
- model deployment approval
- live alpha signal
- order recommendation

## 9. Model Artifact Safety Rules

Any saved artifact must remain local-only and research-only.

Planned artifact rules:

- saved locally only
- never uploaded
- never consumed by runtime trading path
- never contain credentials
- never contain broker/account/provider metadata
- never contain order execution metadata
- explicit report-only marker
- explicit non-executable marker
- explicit no-live marker
- explicit no-order marker

Planned artifact manifest fields:

- model id
- model type
- training dataset manifest id
- split manifest id
- feature schema version
- label schema version
- training timestamp
- metrics report id
- report-only marker
- non-executable marker
- no-live marker
- no-order marker

Artifacts should be optional. If artifact persistence is disabled, the sandbox should still emit a manifest/report-only record explaining that no artifact was saved.

## 10. Local Experiment Manifest

Introduce a first-class experiment manifest to track offline research runs, for example:

- sandbox run id
- experiment id
- requested model type
- actual trainer backend used
- dependency availability status
- dataset manifest id
- validation report id
- leakage audit id
- split manifest id
- readiness report id
- baseline evaluation report id
- feature schema version
- label schema version
- metrics report id
- artifact manifest id if any
- blocked status / warning summary
- report-only marker

This manifest should become the audit root for v5.7 outputs.

## 11. CLI Design

Plan local fixture-only commands:

- `historical-model-training-plan-check --fixture-file ... [--output-file ...]`
- `historical-model-train-sandbox --fixture-file ... [--output-file ...]`
- `historical-model-evaluation-report --fixture-file ... [--output-file ...]`
- `historical-model-artifact-manifest --fixture-file ... [--output-file ...]`
- `historical-model-training-safety-report --fixture-file ... [--output-file ...]`

CLI rules:

- `--fixture-file` required
- local JSON fixture only
- optional `--output-file` writes local JSON/report output only
- no data fetch
- no network
- no provider API
- no LLM calls
- no broker/account/order integration
- no runtime trading signal generation
- no order candidate generation
- no live inference

CLI should return JSON-safe `FAILED` payloads on blocked or invalid fixtures.

## 12. Tests

Planned focused tests:

- valid sandbox config/model construction
- required safety flags
- local fixture loader success
- local fixture loader source-path-aware failure
- parquet unsupported/rejected
- training eligibility pass path
- blocked path when validation report is not clean
- blocked path when leakage audit is not clean
- blocked path when split is non-chronological
- blocked path when random shuffle is represented
- blocked path when feature leakage is detected
- blocked path when unsupported model type is requested
- dummy baseline fallback path
- optional sklearn availability check path
- train/validation/test partition usage correctness
- no validation/test contamination into training
- no feature mutation from outcome values
- metrics report generation
- baseline comparison report generation
- artifact manifest report-only safety markers
- unsafe metadata rejection for order/buy/sell/network/provider/LLM/LIVE/PROD/parquet

Tests must not:

- require network
- require model downloads
- require optional sklearn if not present

## 13. system_smoke Design

Planned `system_smoke` additions should eventually confirm:

- `historical_model_training_sandbox_fixture_run=true`
- `historical_model_training_local_only=true`
- `historical_model_training_offline_only=true`
- `historical_model_training_chronological_split_used=true`
- `historical_model_training_no_random_shuffle=true`
- `historical_model_training_report_only=true`
- `historical_model_training_non_executable=true`
- `historical_model_training_no_runtime_signal=true`
- `historical_model_training_no_order_candidate=true`
- `historical_model_training_no_broker_path=true`
- `historical_model_training_no_live_prod=true`
- `historical_model_training_no_network=true`
- `historical_model_training_no_cloud_llm=true`
- `historical_model_training_no_local_llm_runtime=true`
- `investing_crawler_called=false`
- `finviz_scraper_called=false`
- `news_ingestion_called=false`
- `gemini_called=false`
- `kiwoom_api_called=false`
- `ls_api_called=false`
- `broker_api_called=false`
- `credentials_accessed=false`
- `external_network_calls=false`

Smoke should use only a local fixture-built sandbox run and should not require optional sklearn. The dummy baseline path should be sufficient for smoke coverage if optional trainers are unavailable.

## 14. Non-Goals

Explicit non-goals for v5.7:

- no production model
- no live inference
- no advisory recommendation engine
- no buy/sell signal generation
- no order intent
- no portfolio simulator
- no backtest P/L engine
- no real provider ingestion
- no LLM interpretation layer
- no cloud training service
- no model serving endpoint
- no parquet support unless later revisited explicitly

## 15. Task-By-Task Execution Order

- [ ] Task 1: review v5.4-v5.6 input contracts and confirm the exact sandbox fixture shape
- [ ] Task 2: add v5.7 model surface and local fixture loader with strict safety flags
- [ ] Task 3: add v5.7 training safety guard and gap taxonomy
- [ ] Task 4: implement eligibility gating, safe feature extraction, target extraction, and deterministic dummy baseline path
- [ ] Task 5: implement optional sklearn-backed sandbox trainers behind availability checks and report-only experiment outputs
- [ ] Task 6: implement metrics, baseline comparison, artifact manifest, and safety reports
- [ ] Task 7: wire local fixture-only CLI commands
- [ ] Task 8: extend `system_smoke`, run targeted tests, run smoke, run full pytest if feasible, then commit/tag

## Implementation Notes

- Prefer pure-Python deterministic helpers first.
- Treat optional sklearn as a secondary backend, never a hard requirement for tests.
- Keep all training outputs isolated from any runtime trading path.
- Preserve v3-v6 safety boundaries without weakening read-only/report-only guarantees.
