# Local Historical Dataset Assembly And Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local fixture-only v5.4 dataset assembly/export layer that combines v5.1 historical snapshots, v5.2 replay/scanner context, and v5.3 outcome observations into offline dataset records for future evaluation or future ML training preparation, without performing any training in v5.4.

**Architecture:** Add a dedicated historical dataset module family that reads only local fixture-derived artifacts, assembles a strict feature block from replay-time known context, assembles a separate outcome block from post-anchor observations, validates no-lookahead and safety boundaries fail-closed, and exports report-only dataset files in safe local formats. Keep scanner replay input immutable and pre-outcome, and keep all outcome labels/forward returns isolated from the feature block.

**Tech Stack:** Python 3.11, Pydantic v2, existing strict model patterns, existing local fixture loaders, existing CLI patterns, pytest, system smoke

---

## File Structure

### New files

- `src/stock_risk_mcp/historical_dataset_models.py`
  Dataset assembly config, dataset record schema, feature block, outcome block, export manifest, gap report, safety report, audit record models.
- `src/stock_risk_mcp/historical_dataset_fixture.py`
  Loader for v5.4 local dataset assembly fixture inputs.
- `src/stock_risk_mcp/historical_dataset_guard.py`
  Fail-closed no-lookahead, report-only, local-file-only, and unsupported-path safety validation.
- `src/stock_risk_mcp/historical_dataset_engine.py`
  Pure deterministic dataset assembly, export payload shaping, gap detection, and report building.
- `tests/test_historical_dataset_models.py`
  Model/schema and safety-boundary tests.
- `tests/test_historical_dataset_engine.py`
  Assembly, leakage, export-shape, and gap tests.
- `tests/test_historical_dataset_cli.py`
  CLI success/failure tests for local fixture-only dataset commands.

### Modified files

- `src/stock_risk_mcp/cli.py`
  Register v5.4 dataset assembly/export commands.
- `src/stock_risk_mcp/system_smoke.py`
  Add v5.4 local dataset assembly/export smoke coverage.
- `tests/test_system_smoke.py`
  Assert v5.4 smoke checks.
- `WORK_SUMMARY.md`
  Append v5.4 milestone summary only if repository convention still requires it.

### Existing files to inspect for compatibility only

- `src/stock_risk_mcp/historical_data_models.py`
- `src/stock_risk_mcp/historical_calendar_models.py`
- `src/stock_risk_mcp/historical_replay_bridge_models.py`
- `src/stock_risk_mcp/historical_scanner_replay_models.py`
- `src/stock_risk_mcp/historical_outcome_models.py`
- `src/stock_risk_mcp/historical_outcome_engine.py`
- `tests/test_historical_outcome_engine.py`

## Inputs

v5.4 may consume only local fixture-derived artifacts:

- `HistoricalMarketDataSnapshot` from v5.1
- `HistoricalCalendarEventSnapshot` from v5.1
- `HistoricalReplayEventStream` from v5.2
- `HistoricalReplayWindowBundle` from v5.2
- `HistoricalScannerReplayInput` from v5.2
- `HistoricalOutcomeObservationInput` from v5.3
- `HistoricalOutcomeMetricSet` from v5.3
- `HistoricalOutcomeLabelReport` from v5.3
- `HistoricalOutcomeGapReport` from v5.3
- `HistoricalOutcomeSafetyReport` from v5.3

Each input must be local, read-only, fixture-backed, and already report-only where applicable.

## Dataset Record Schema

The primary v5.4 unit should be `HistoricalDatasetRecord`.

Expected first-class objects:

- `HistoricalDatasetAssemblyConfig`
- `HistoricalDatasetAssemblyInput`
- `HistoricalDatasetRecord`
- `HistoricalDatasetFeatureBlock`
- `HistoricalDatasetOutcomeBlock`
- `HistoricalDatasetExportManifest`
- `HistoricalDatasetGapReport`
- `HistoricalDatasetSafetyReport`
- `HistoricalDatasetAuditRecord`

`HistoricalDatasetRecord` should include:

- stable record id
- strategy track
- market profile id
- symbol
- market
- replay session date
- replay event id(s)
- replay window id
- scanner seed id
- source snapshot ids
- lineage ids
- feature block
- outcome block
- report-only marker
- no-lookahead marker
- safety flags

## Feature Block Vs Outcome Block Separation

The feature block must contain only replay-time known information, such as:

- replay event metadata
- market profile / track context
- replay window boundaries
- attached event context known at replay time
- scanner candidate seed metadata
- replay-time market snapshot references
- replay-time calendar references

The feature block must never contain:

- forward close
- forward return
- max favorable excursion
- max adverse excursion
- outcome label
- final outcome metrics
- post-anchor realized values

The outcome block must contain only post-anchor observations, such as:

- observation window ids
- sessions observed
- missing-session counts
- early-close counts
- forward close
- forward return percentage
- MFE / MAE
- high-water / low-water marks
- observed volume summaries
- report-only outcome label(s)
- outcome gap status

## No-Lookahead / Leakage Boundary

v5.4 must enforce:

- feature block contains only replay-time known information
- outcome block contains only post-anchor observations
- outcome labels and forward returns never appear in feature block
- scanner replay input remains pre-outcome and report-only
- assembled dataset records must not mutate `HistoricalScannerReplayInput`
- no dataset export path may merge outcome labels back into replay-time scanner payloads
- incomplete known-time event metadata must produce explicit report-only warnings or gaps
- fail closed on any attempt to treat outcome labels as runtime trading signals

Required explicit blocked cases:

- outcome label inserted into feature block
- forward return inserted into feature block
- runtime signal field from outcome label
- order candidate field generated from dataset record
- buy/sell/entry/exit wording in dataset decision fields
- executable or approval-like fields

## Dataset Gap Taxonomy

Initial gap taxonomy should include:

- `DATASET_MISSING_MARKET_SNAPSHOT`
- `DATASET_MISSING_CALENDAR_SNAPSHOT`
- `DATASET_MISSING_REPLAY_EVENT_STREAM`
- `DATASET_MISSING_REPLAY_WINDOW`
- `DATASET_MISSING_SCANNER_INPUT`
- `DATASET_MISSING_OUTCOME_INPUT`
- `DATASET_MISSING_OUTCOME_METRICS`
- `DATASET_MISSING_OUTCOME_LABEL_REPORT`
- `DATASET_FEATURE_OUTCOME_LEAKAGE_DETECTED`
- `DATASET_SCANNER_INPUT_MUTATION_DETECTED`
- `DATASET_UNSUPPORTED_TRACK`
- `DATASET_UNSUPPORTED_MARKET`
- `DATASET_REMOTE_SOURCE_NOT_ALLOWED`
- `DATASET_API_SOURCE_NOT_ALLOWED`
- `DATASET_NETWORK_SOURCE_NOT_ALLOWED`
- `DATASET_PROVIDER_SOURCE_NOT_ALLOWED`
- `DATASET_ORDER_FIELD_DETECTED`
- `DATASET_BUY_SELL_WORDING_DETECTED`
- `DATASET_LIVE_PROD_NOT_ALLOWED`
- `DATASET_LLM_METADATA_NOT_ALLOWED`
- `DATASET_ML_TRAINING_TRIGGER_NOT_ALLOWED`
- `DATASET_CRAWLER_TRIGGER_NOT_ALLOWED`
- `DATASET_PARQUET_NOT_ALLOWED`
- `DATASET_REPORT_ONLY_WARNING`
- `DATASET_EXPORT_GENERATED`

## Dataset Safety Guard

The v5.4 safety guard must remain fail-closed and must enforce:

- local fixture only
- read-only
- report-only
- non-executable
- no-network
- no-provider-api
- no-order
- no-LLM-runtime
- no-ML-training

It must reject:

- remote URL paths
- provider/API/network source metadata
- broker/account/order fields
- runtime trading signal fields
- LIVE/PROD markers
- Kiwoom/LS/provider paths
- Gemini/cloud/local model runtime metadata
- ML training triggers
- crawler triggers
- parquet paths or parquet export modes

## Local Export Formats

Allowed export formats in v5.4:

- JSON
- JSONL
- CSV only for a flat, explicitly safe record projection

CSV is allowed only if:

- feature block and outcome block fields remain clearly separated by column naming
- nested complex fields are flattened deterministically
- no runtime signal or executable semantics are introduced

Deferred / unsupported:

- parquet
- feather
- sqlite dataset export
- online dataset sinks

## CLI Design

Initial CLI shape:

- `historical-dataset-assemble --fixture-file ... [--output-file ...]`
- `historical-dataset-export-manifest --fixture-file ... [--output-file ...]`
- `historical-dataset-gap-report --fixture-file ... [--output-file ...]`
- `historical-dataset-safety-report --fixture-file ... [--output-file ...]`

CLI requirements:

- `--fixture-file` required
- local files only
- optional `--output-file` writes local JSON / JSONL / CSV output only
- report-only outputs
- no scanner replay input mutation
- no runtime trading signal generation
- no order candidate creation
- no order / execution / approval path

## Tests

Required test coverage:

- dataset model construction from local fixtures
- strict feature block / outcome block separation
- no-lookahead rejection when outcome data appears in feature block
- scanner replay input immutability
- unsupported remote/API/network/provider source rejection
- unsupported order / buy / sell / execution wording rejection
- unsupported LIVE/PROD rejection
- unsupported Gemini / LLM / model runtime rejection
- unsupported ML training trigger rejection
- unsupported crawler rejection
- unsupported parquet rejection
- JSON export generation
- JSONL export generation
- CSV export generation only for safe flat projection
- CLI success paths
- CLI missing-fixture fail-closed paths
- system smoke coverage

## System Smoke Design

`system_smoke` should confirm:

- `historical_dataset_fixture_run=true`
- `historical_dataset_records_generated=true`
- `historical_dataset_feature_block_generated=true`
- `historical_dataset_outcome_block_generated=true`
- `historical_dataset_labels_report_only=true`
- `historical_dataset_no_lookahead_guard_enabled=true`
- `historical_dataset_scanner_input_not_mutated=true`
- `historical_dataset_read_only=true`
- `historical_dataset_non_executable=true`
- `historical_dataset_local_files_only=true`
- `historical_dataset_remote_fetch_allowed=false`
- `historical_dataset_api_provider_called=false`
- `historical_dataset_order_candidate_created=false`
- `historical_dataset_runtime_signal_generated=false`
- `historical_dataset_live_or_prod_used=false`
- `historical_dataset_cloud_llm_called=false`
- `historical_dataset_model_runtime_called=false`
- `historical_dataset_ml_training_run=false`
- `investing_crawler_called=false`
- `finviz_scraper_called=false`
- `news_ingestion_called=false`
- `gemini_called=false`
- `kiwoom_api_called=false`
- `ls_api_called=false`
- `broker_api_called=false`
- `credentials_accessed=false`
- `external_network_calls=false`
- `parquet_supported=false`

## Non-Goals

- real market data fetch
- real calendar data fetch
- Investing.com crawler
- FINVIZ scraper
- news ingestion
- Gemini / Google AI Studio
- Kiwoom / LS / broker / account integrations
- order candidates
- runtime trading signals
- LIVE / PROD
- ML training
- cloud LLM
- local model runtime
- final model-fitting pipeline
- parquet support

---

### Task 1: Dataset Boundary And Schema Plan

**Files:**
- Create: `docs/superpowers/plans/2026-06-18-local-historical-dataset-assembly-export.md`
- Inspect: `src/stock_risk_mcp/historical_outcome_models.py`
- Inspect: `src/stock_risk_mcp/historical_scanner_replay_models.py`
- Inspect: `src/stock_risk_mcp/historical_replay_bridge_models.py`

- [ ] **Step 1: Confirm the v5.4 dataset boundary**

Write the plan so it explicitly states:

```text
Inputs:
- v5.1 market/calendar snapshots
- v5.2 replay/scanner context
- v5.3 outcome metrics and report-only labels

Outputs:
- dataset records
- export manifest
- gap report
- safety report

Safety:
- feature block replay-time only
- outcome block post-anchor only
- no order/runtime/LLM/ML/network/provider paths
```

- [ ] **Step 2: Re-read the v5.4 requirement list against the plan**

Run: `sed -n '1,260p' docs/superpowers/plans/2026-06-18-local-historical-dataset-assembly-export.md`
Expected: the plan names inputs, schema, feature/outcome separation, leakage boundary, gap taxonomy, safety guard, export formats, CLI, tests, smoke checks, non-goals, and task order.

### Task 2: Dataset Models And Fixture Loader

**Files:**
- Create: `src/stock_risk_mcp/historical_dataset_models.py`
- Create: `src/stock_risk_mcp/historical_dataset_fixture.py`
- Test: `tests/test_historical_dataset_models.py`

- [ ] **Step 1: Write the failing model test**

```python
def test_historical_dataset_models_accept_local_fixture_only_inputs():
    dataset_input = load_historical_dataset_fixture(fixture_file)
    assert dataset_input.assembly_config.read_only is True
    assert dataset_input.records == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_dataset_models.py -q`
Expected: FAIL because dataset fixture loader/models do not exist yet.

- [ ] **Step 3: Write minimal models and fixture loader**

Implement:

```python
class HistoricalDatasetFeatureBlock(StrictModel): ...
class HistoricalDatasetOutcomeBlock(StrictModel): ...
class HistoricalDatasetRecord(StrictModel): ...
def load_historical_dataset_fixture(path) -> HistoricalDatasetAssemblyInput: ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_historical_dataset_models.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stock_risk_mcp/historical_dataset_models.py src/stock_risk_mcp/historical_dataset_fixture.py tests/test_historical_dataset_models.py
git commit -m "Add historical dataset assembly models and fixture loader"
```

### Task 3: Feature / Outcome Separation Guard

**Files:**
- Create: `src/stock_risk_mcp/historical_dataset_guard.py`
- Modify: `src/stock_risk_mcp/historical_dataset_models.py`
- Test: `tests/test_historical_dataset_models.py`

- [ ] **Step 1: Write failing leakage-boundary tests**

```python
def test_historical_dataset_guard_rejects_outcome_label_in_feature_block(): ...
def test_historical_dataset_guard_rejects_forward_return_in_feature_block(): ...
def test_historical_dataset_guard_rejects_runtime_signal_fields(): ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_dataset_models.py -q`
Expected: FAIL with missing guard or missing validation behavior.

- [ ] **Step 3: Implement minimal fail-closed guard**

Implement:

```python
def validate_historical_dataset_feature_outcome_boundary(...): ...
def validate_historical_dataset_metadata_safety(...): ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_historical_dataset_models.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stock_risk_mcp/historical_dataset_guard.py src/stock_risk_mcp/historical_dataset_models.py tests/test_historical_dataset_models.py
git commit -m "Add historical dataset safety and leakage guard"
```

### Task 4: Dataset Assembly Engine

**Files:**
- Create: `src/stock_risk_mcp/historical_dataset_engine.py`
- Test: `tests/test_historical_dataset_engine.py`

- [ ] **Step 1: Write failing assembly tests**

```python
def test_build_historical_dataset_records_uses_replay_time_feature_block_only(): ...
def test_build_historical_dataset_records_places_forward_metrics_in_outcome_block_only(): ...
def test_build_historical_dataset_records_preserves_scanner_input_immutability(): ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_dataset_engine.py -q`
Expected: FAIL because engine does not exist yet.

- [ ] **Step 3: Implement minimal deterministic assembly**

Implement:

```python
def build_historical_dataset_records(dataset_input): ...
def build_historical_dataset_gap_report(dataset_input): ...
def build_historical_dataset_safety_report(dataset_input): ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_historical_dataset_engine.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stock_risk_mcp/historical_dataset_engine.py tests/test_historical_dataset_engine.py
git commit -m "Add historical dataset assembly engine"
```

### Task 5: Safe Local Export Formats

**Files:**
- Modify: `src/stock_risk_mcp/historical_dataset_engine.py`
- Test: `tests/test_historical_dataset_engine.py`

- [ ] **Step 1: Write failing export tests**

```python
def test_historical_dataset_export_supports_json_and_jsonl(): ...
def test_historical_dataset_export_supports_safe_flat_csv_projection_only(): ...
def test_historical_dataset_export_rejects_parquet(): ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_dataset_engine.py -q`
Expected: FAIL because export helpers do not exist yet.

- [ ] **Step 3: Implement minimal local export helpers**

Implement:

```python
def export_historical_dataset_json(...): ...
def export_historical_dataset_jsonl(...): ...
def export_historical_dataset_csv(...): ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_historical_dataset_engine.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stock_risk_mcp/historical_dataset_engine.py tests/test_historical_dataset_engine.py
git commit -m "Add historical dataset local export helpers"
```

### Task 6: CLI Wiring

**Files:**
- Modify: `src/stock_risk_mcp/cli.py`
- Test: `tests/test_historical_dataset_cli.py`

- [ ] **Step 1: Write failing CLI tests**

```python
def test_historical_dataset_cli_commands_return_report_only_outputs(): ...
def test_historical_dataset_cli_missing_fixture_is_json_safe(): ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_dataset_cli.py -q`
Expected: FAIL because v5.4 commands are not registered yet.

- [ ] **Step 3: Add fixture-only CLI commands**

Implement commands:

```text
historical-dataset-assemble
historical-dataset-export-manifest
historical-dataset-gap-report
historical-dataset-safety-report
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_historical_dataset_cli.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stock_risk_mcp/cli.py tests/test_historical_dataset_cli.py
git commit -m "Add historical dataset assembly CLI"
```

### Task 7: System Smoke Coverage

**Files:**
- Modify: `src/stock_risk_mcp/system_smoke.py`
- Modify: `tests/test_system_smoke.py`

- [ ] **Step 1: Write failing smoke assertions**

Add assertions for:

```text
historical_dataset_fixture_run
historical_dataset_records_generated
historical_dataset_feature_block_generated
historical_dataset_outcome_block_generated
historical_dataset_labels_report_only
historical_dataset_no_lookahead_guard_enabled
historical_dataset_scanner_input_not_mutated
historical_dataset_runtime_signal_generated=false
parquet_supported=false
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_system_smoke.py -q`
Expected: FAIL because v5.4 smoke checks do not exist yet.

- [ ] **Step 3: Implement minimal v5.4 smoke flow**

Add a local fixture-only smoke helper that assembles dataset records and verifies disabled unsafe paths.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_system_smoke.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stock_risk_mcp/system_smoke.py tests/test_system_smoke.py
git commit -m "Add historical dataset system smoke coverage"
```

### Task 8: Milestone Validation And Close

**Files:**
- Inspect: `src/stock_risk_mcp/historical_dataset_models.py`
- Inspect: `src/stock_risk_mcp/historical_dataset_engine.py`
- Inspect: `src/stock_risk_mcp/cli.py`
- Inspect: `src/stock_risk_mcp/system_smoke.py`
- Modify: `WORK_SUMMARY.md` only if required by repo convention

- [ ] **Step 1: Run focused v5.4 tests**

Run: `python3.11 -m pytest tests/test_historical_dataset_models.py tests/test_historical_dataset_engine.py tests/test_historical_dataset_cli.py -q`
Expected: PASS

- [ ] **Step 2: Run system smoke**

Run: `python3.11 -m pytest tests/test_system_smoke.py -q`
Expected: PASS

- [ ] **Step 3: Run full pytest if feasible**

Run: `python3.11 -m pytest -q`
Expected: PASS, or record exact failure if unrelated.

- [ ] **Step 4: Confirm scope and safety boundary**

Run:

```bash
git status --short
```

Expected:

```text
Only v5.4 dataset assembly/export files changed.
No live/provider/order/network/runtime additions.
```

- [ ] **Step 5: Commit and tag**

```bash
git add src/stock_risk_mcp/historical_dataset_models.py src/stock_risk_mcp/historical_dataset_fixture.py src/stock_risk_mcp/historical_dataset_guard.py src/stock_risk_mcp/historical_dataset_engine.py src/stock_risk_mcp/cli.py src/stock_risk_mcp/system_smoke.py tests/test_historical_dataset_models.py tests/test_historical_dataset_engine.py tests/test_historical_dataset_cli.py tests/test_system_smoke.py WORK_SUMMARY.md
git commit -m "Implement local historical dataset assembly and export"
git tag v5.4.0-local-historical-dataset-assembly-export
```

## Task-By-Task Execution Order

1. Task 1: lock the boundary and schema plan
2. Task 2: add models and fixture loader
3. Task 3: add safety and leakage guard
4. Task 4: add deterministic dataset assembly engine
5. Task 5: add safe local export helpers
6. Task 6: wire CLI
7. Task 7: update system smoke
8. Task 8: validate, commit, and tag

## Plan Self-Review

- Spec coverage: all requested sections are present, including inputs, schema, separation, leakage boundary, gap taxonomy, safety guard, export formats, CLI, tests, smoke, non-goals, and task order.
- Placeholder scan: no `TODO` / `TBD` placeholders remain.
- Scope check: the plan stops at offline local dataset assembly/export and does not include model training, real data fetch, network/provider execution, or parquet support.
