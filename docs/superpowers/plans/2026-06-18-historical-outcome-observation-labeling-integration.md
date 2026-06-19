# Historical Outcome Observation And Labeling Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a safe offline v5.3 outcome-observation layer that consumes local v5.1/v5.2 fixture-derived replay artifacts, observes forward trading-session outcomes, and emits report-only labels without mutating replay-time inputs or enabling any runtime trading path.

**Architecture:** Add a dedicated historical outcome module family that loads only local fixture-derived replay/scanner inputs, validates fail-closed safety and leakage boundaries, generates deterministic forward observation windows using trading-session calendars, computes observational metrics, and assigns conservative report-only labels. Keep replay-time artifacts pre-outcome and immutable; outcome records live in a separate offline observation layer and must never feed back into scanner/runtime execution paths.

**Tech Stack:** Python 3.11, Pydantic v2, existing strict model patterns, existing CLI/service/system-smoke patterns, pytest

---

## File Structure

### New files

- `src/stock_risk_mcp/historical_outcome_models.py`
  Outcome config, input, observation window, metric set, label, label report, gap report, safety report, and audit record models.
- `src/stock_risk_mcp/historical_outcome_fixture.py`
  Loader for a v5.3 outcome observation fixture that references only local v5.1/v5.2 snapshot/replay/scanner artifacts.
- `src/stock_risk_mcp/historical_outcome_guard.py`
  Fail-closed safety and leakage validation for outcome-side inputs and metadata.
- `src/stock_risk_mcp/historical_outcome_engine.py`
  Pure deterministic logic for forward window generation, metric calculation, label assignment, and report building.
- `src/stock_risk_mcp/historical_outcome_service.py`
  Thin orchestration layer for local fixture loading, engine execution, and report serialization.
- `tests/test_historical_outcome_models.py`
  Model construction and safety-boundary tests.
- `tests/test_historical_outcome_engine.py`
  Forward observation, metric generation, labeling, leakage, and fail-closed gap tests.
- `tests/test_historical_outcome_cli.py`
  CLI success/failure tests for local fixture-only commands.

### Modified files

- `src/stock_risk_mcp/cli.py`
  Register four v5.3 local-fixture-only outcome commands.
- `src/stock_risk_mcp/system_smoke.py`
  Add v5.3 fixture-only outcome observation smoke coverage.
- `tests/test_system_smoke.py`
  Assert v5.3 smoke checks.
- `WORK_SUMMARY.md`
  Append v5.3 milestone status only if repo convention still requires summary updates.

### Existing files to inspect for compatibility only

- `src/stock_risk_mcp/historical_replay_bridge_models.py`
- `src/stock_risk_mcp/historical_replay_bridge_engine.py`
- `src/stock_risk_mcp/historical_scanner_replay_models.py`
- `src/stock_risk_mcp/historical_data_models.py`
- `src/stock_risk_mcp/historical_calendar_models.py`
- `tests/test_historical_replay_bridge_engine.py`

## Inputs

v5.3 may consume only local fixture-derived outputs:

- `HistoricalReplayEventStream`
- calendar-aware replay windows from v5.2
- event-context-attached replay windows from v5.2
- `HistoricalScannerReplayInput`
- `HistoricalScannerReplayCandidateSeed`
- `HistoricalScannerReplayContext`
- local historical OHLCV snapshots from v5.1
- local trading calendar/event snapshots from v5.1

## Outcome Observation Objects

The outcome layer should add these first-class units:

- `HistoricalOutcomeObservationConfig`
- `HistoricalOutcomeObservationInput`
- `HistoricalOutcomeObservationWindow`
- `HistoricalOutcomeObservationRecord`
- `HistoricalOutcomeMetricSet`
- `HistoricalOutcomeLabel`
- `HistoricalOutcomeLabelReport`
- `HistoricalOutcomeGapReport`
- `HistoricalOutcomeSafetyReport`
- `HistoricalOutcomeAuditRecord`

## Label Taxonomy

The initial report-only label set should include:

- `OUTCOME_FAVORABLE`
- `OUTCOME_ADVERSE`
- `OUTCOME_NEUTRAL`
- `OUTCOME_VOLATILE_MIXED`
- `OUTCOME_INCONCLUSIVE`
- `OUTCOME_INSUFFICIENT_FORWARD_DATA`
- `OUTCOME_BLOCKED_SAFETY`
- `OUTCOME_REPORT_ONLY`

Labels must be threshold-driven, observational only, and must never be runtime signals or approval decisions.

## Leakage Boundary

The outcome layer must explicitly enforce:

- `outcome_observed_after_anchor=true` on outcome records
- no mutation of `HistoricalScannerReplayInput`
- no attachment of outcome labels back into replay-time scanner input context
- scheduled event context may remain replay-side, but actual future values remain outcome-side only
- incomplete known-time metadata must create report-only leakage warnings or gaps

## Safety Boundary

The outcome layer must remain:

- local fixture only
- read-only
- non-executable
- no-network
- no-provider-api
- no-order
- no-LLM-runtime
- no-ML-training

It must reject:

- remote URL source
- provider/API/network source
- order/execution fields
- buy/sell/entry/exit wording
- LIVE/PROD markers
- broker/account/Kiwoom/LS/provider paths
- Gemini/LLM/cloud model metadata
- ML training triggers
- crawler triggers
- parquet source
- outcome labels used as runtime signals
- outcome labels attached to pre-outcome scanner input

## Non-Goals

- real market or calendar fetch
- Investing.com crawler
- FINVIZ scraper
- news ingestion
- Gemini / Google AI Studio
- Kiwoom / LS / broker / account integrations
- order creation or approval
- LIVE / PROD
- cloud LLM or local model runtime
- ML training
- final dataset export
- parquet support

## Expected Tests

- outcome model construction
- forward observation window generation
- trading-session counting
- weekend/holiday skipping
- early-close flagging
- favorable/adverse/neutral/volatile-mixed/inconclusive label assignment
- missing threshold fail-closed behavior
- missing anchor/forward price gaps
- leakage guard enforcement
- replay-time scanner input immutability
- remote/API/network/provider rejection
- order/buy/sell wording rejection
- Gemini/LLM rejection
- ML training/crawler/LIVE-PROD/parquet rejection
- CLI success/failure paths
- system smoke coverage

## Smoke Updates

`system_smoke` must confirm:

- `historical_outcome_observation_fixture_run=true`
- `historical_outcome_windows_generated=true`
- `historical_outcome_metrics_generated=true`
- `historical_outcome_labels_report_only=true`
- `historical_outcome_no_lookahead_guard_enabled=true`
- `historical_outcome_scanner_input_not_mutated=true`
- `historical_outcome_read_only=true`
- `historical_outcome_non_executable=true`
- `historical_outcome_local_files_only=true`
- `historical_outcome_remote_fetch_allowed=false`
- `historical_outcome_api_provider_called=false`
- `historical_outcome_order_intent_created=false`
- `historical_outcome_live_or_prod_used=false`
- `historical_outcome_cloud_llm_called=false`
- `historical_outcome_model_runtime_called=false`
- `historical_outcome_ml_training_run=false`
- `investing_crawler_called=false`
- `finviz_scraper_called=false`
- `news_ingestion_called=false`
- `gemini_called=false`
- `kiwoom_api_called=false`
- `ls_api_called=false`
- `broker_api_called=false`
- `credentials_accessed=false`
- `external_network_calls=false`

---

### Task 1: Outcome Plan And File Boundary

**Files:**
- Create: `docs/superpowers/plans/2026-06-18-historical-outcome-observation-labeling-integration.md`
- Inspect: `src/stock_risk_mcp/historical_replay_bridge_models.py`
- Inspect: `src/stock_risk_mcp/historical_scanner_replay_models.py`
- Inspect: `src/stock_risk_mcp/historical_data_models.py`
- Inspect: `src/stock_risk_mcp/historical_calendar_models.py`

- [ ] **Step 1: Confirm the v5.3 boundary in the plan**

Write the plan so it explicitly states:

```text
Inputs:
- HistoricalReplayEventStream
- HistoricalReplayWindowBundle
- HistoricalScannerReplayInput
- HistoricalMarketDataSnapshot
- HistoricalCalendarEventSnapshot

Outputs:
- HistoricalOutcomeObservationRecord
- HistoricalOutcomeMetricSet
- HistoricalOutcomeLabelReport
- HistoricalOutcomeGapReport
- HistoricalOutcomeSafetyReport

Safety:
- report-only
- outcome observed after anchor
- scanner replay input remains pre-outcome
- no order/runtime/LLM/ML/network/provider paths
```

- [ ] **Step 2: Re-read the requirement list against the plan**

Run: `sed -n '1,260p' docs/superpowers/plans/2026-06-18-historical-outcome-observation-labeling-integration.md`
Expected: the plan names inputs, observation objects, forward trading-session windowing, metrics, labels, leakage boundaries, safety boundaries, tests, smoke updates, and non-goals.

### Task 2: Outcome Models And Fixture Loader

**Files:**
- Create: `src/stock_risk_mcp/historical_outcome_models.py`
- Create: `src/stock_risk_mcp/historical_outcome_fixture.py`
- Test: `tests/test_historical_outcome_models.py`

- [ ] **Step 1: Write the failing model test**

```python
import pytest

from stock_risk_mcp.historical_outcome_fixture import load_historical_outcome_fixture
from stock_risk_mcp.historical_outcome_models import (
    HistoricalOutcomeLabel,
    HistoricalOutcomeObservationConfig,
    HistoricalOutcomeSafetyReport,
)


def test_historical_outcome_models_accept_fixture_only_inputs(tmp_path):
    fixture_file = tmp_path / "historical_outcome_fixture.json"
    fixture_file.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError):
        load_historical_outcome_fixture(fixture_file)

    assert HistoricalOutcomeLabel.model_fields["label_type"].annotation is not None
    assert HistoricalOutcomeObservationConfig.model_fields["read_only"].default is True
    assert HistoricalOutcomeSafetyReport.model_fields["no_order"].default is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_outcome_models.py::test_historical_outcome_models_accept_fixture_only_inputs -v`
Expected: FAIL with import error for `stock_risk_mcp.historical_outcome_models`

- [ ] **Step 3: Write minimal model implementation**

Define:

```python
class HistoricalOutcomeObservationConfig(StrictModel):
    config_id: str
    strategy_track: StrategyTrack
    forward_window_sizes: list[int]
    favorable_return_threshold_pct: float | None = None
    adverse_return_threshold_pct: float | None = None
    volatile_mfe_threshold_pct: float | None = None
    volatile_mae_threshold_pct: float | None = None
    allow_report_only_degraded_calendar: bool = False
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True


class HistoricalOutcomeObservationInput(StrictModel):
    observation_input_id: str
    replay_event_stream: HistoricalReplayEventStream
    replay_window_bundle: HistoricalReplayWindowBundle
    scanner_replay_input: HistoricalScannerReplayInput
    historical_market_data_snapshot: HistoricalMarketDataSnapshot
    historical_calendar_event_snapshot: HistoricalCalendarEventSnapshot | None = None


class HistoricalOutcomeSafetyReport(StrictModel):
    safety_report_id: str
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True
```

Also define:

- `HistoricalOutcomeObservationWindow`
- `HistoricalOutcomeObservationRecord`
- `HistoricalOutcomeMetricSet`
- `HistoricalOutcomeLabel`
- `HistoricalOutcomeLabelReport`
- `HistoricalOutcomeGapReport`
- `HistoricalOutcomeAuditRecord`

with uppercase ID normalization, timezone-aware timestamps, and fail-closed safe-flag validators.

- [ ] **Step 4: Implement the local fixture loader**

Load:

```python
def load_historical_outcome_fixture(path) -> HistoricalOutcomeObservationInput:
    source_path = str(path)
    try:
        return HistoricalOutcomeObservationInput.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid historical outcome fixture at {source_path}: {exc}") from exc
```

- [ ] **Step 5: Run model tests**

Run: `python3.11 -m pytest tests/test_historical_outcome_models.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/stock_risk_mcp/historical_outcome_models.py src/stock_risk_mcp/historical_outcome_fixture.py tests/test_historical_outcome_models.py
git commit -m "Add historical outcome observation models"
```

### Task 3: Outcome Guard And Gap Taxonomy

**Files:**
- Create: `src/stock_risk_mcp/historical_outcome_guard.py`
- Modify: `src/stock_risk_mcp/historical_outcome_models.py`
- Test: `tests/test_historical_outcome_models.py`

- [ ] **Step 1: Write the failing safety test**

```python
import pytest

from stock_risk_mcp.historical_outcome_guard import validate_historical_outcome_metadata_safety


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"remote_url": "https://example.com/file.csv"}, "remote"),
        ({"provider_api": "broker"}, "provider"),
        ({"network_socket": "tcp://feed"}, "network"),
        ({"order_intent": "BUY"}, "order"),
        ({"label_summary": "buy now"}, "buy"),
        ({"runtime_signal": "OUTCOME_FAVORABLE"}, "runtime"),
        ({"gemini_prompt": "analyze"}, "gemini"),
        ({"ml_training_job": "fit"}, "training"),
        ({"crawler_trigger": "run"}, "crawler"),
        ({"parquet_path": "fixture.parquet"}, "parquet"),
    ],
)
def test_historical_outcome_guard_rejects_unsafe_metadata(payload, message):
    with pytest.raises(ValueError, match=message):
        validate_historical_outcome_metadata_safety(payload, context="historical outcome")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_outcome_models.py::test_historical_outcome_guard_rejects_unsafe_metadata -v`
Expected: FAIL with import error for `stock_risk_mcp.historical_outcome_guard`

- [ ] **Step 3: Implement guard patterns and gap categories**

Add gap categories for:

- `OUTCOME_OBSERVATION_GENERATED`
- `OUTCOME_REPORT_ONLY`
- `OUTCOME_MISSING_REPLAY_INPUT`
- `OUTCOME_MISSING_CANDIDATE_SEED`
- `OUTCOME_MISSING_REPLAY_WINDOW`
- `OUTCOME_MISSING_HISTORICAL_MARKET_DATA`
- `OUTCOME_MISSING_TRADING_CALENDAR`
- `OUTCOME_MISSING_FORWARD_SESSION`
- `OUTCOME_INSUFFICIENT_FORWARD_DATA`
- `OUTCOME_MISSING_ANCHOR_PRICE`
- `OUTCOME_MISSING_FORWARD_PRICE`
- `OUTCOME_INVALID_PRICE_SERIES`
- `OUTCOME_UNSUPPORTED_TRACK`
- `OUTCOME_UNSUPPORTED_MARKET`
- `OUTCOME_MARKET_PROFILE_MISMATCH`
- `OUTCOME_CURRENCY_MISMATCH`
- `OUTCOME_TIMEZONE_MISMATCH`
- `OUTCOME_THRESHOLD_CONFIG_MISSING`
- `OUTCOME_LABEL_INCONCLUSIVE`
- `OUTCOME_LEAKAGE_RISK_DETECTED`
- `OUTCOME_ORDER_FIELD_DETECTED`
- `OUTCOME_BUY_SELL_WORDING_DETECTED`
- `OUTCOME_REMOTE_SOURCE_NOT_ALLOWED`
- `OUTCOME_API_SOURCE_NOT_ALLOWED`
- `OUTCOME_NETWORK_SOURCE_NOT_ALLOWED`
- `OUTCOME_PROVIDER_SOURCE_NOT_ALLOWED`
- `OUTCOME_LLM_METADATA_NOT_ALLOWED`
- `OUTCOME_ML_TRAINING_TRIGGER_NOT_ALLOWED`
- `OUTCOME_CRAWLER_TRIGGER_NOT_ALLOWED`
- `OUTCOME_LIVE_PROD_NOT_ALLOWED`
- `OUTCOME_PARQUET_NOT_ALLOWED`

Implement metadata/key scanning aligned with the existing v5.2 guard style.

- [ ] **Step 4: Run safety tests**

Run: `python3.11 -m pytest tests/test_historical_outcome_models.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stock_risk_mcp/historical_outcome_guard.py src/stock_risk_mcp/historical_outcome_models.py tests/test_historical_outcome_models.py
git commit -m "Add historical outcome safety guard"
```

### Task 4: Forward Observation Window Engine

**Files:**
- Create: `src/stock_risk_mcp/historical_outcome_engine.py`
- Test: `tests/test_historical_outcome_engine.py`

- [ ] **Step 1: Write the failing forward-window test**

```python
from stock_risk_mcp.historical_outcome_engine import build_historical_outcome_windows


def test_build_historical_outcome_windows_uses_trading_sessions_and_skips_holidays(outcome_fixture):
    bundle = build_historical_outcome_windows(outcome_fixture, forward_window_sizes=(1, 3))

    assert bundle.observation_records
    assert bundle.observation_records[0].sessions_observed >= 1
    assert bundle.gap_report.blocking_gap_count == 0
    assert "OUTCOME_OBSERVATION_GENERATED" in bundle.gap_report.gap_categories
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_outcome_engine.py::test_build_historical_outcome_windows_uses_trading_sessions_and_skips_holidays -v`
Expected: FAIL with import error for `stock_risk_mcp.historical_outcome_engine`

- [ ] **Step 3: Implement deterministic forward observation window generation**

The engine must:

- use trading-session calendar, not calendar-day offsets
- skip weekends and holidays
- flag early-close sessions
- fail closed when calendar is missing unless explicit report-only degraded mode is enabled
- refuse to synthesize OHLCV data
- create explicit gaps for missing expected forward sessions
- compute observations only from local `HistoricalMarketDataSnapshot.records`

Implement functions:

```python
def build_historical_outcome_windows(observation_input, *, forward_window_sizes=(1, 3, 5)):
    ...


def _forward_trading_sessions(calendar_snapshot, anchor_date, window_size):
    ...


def _lookup_forward_price_records(market_snapshot, symbol, market, session_dates):
    ...
```

- [ ] **Step 4: Run focused engine tests**

Run: `python3.11 -m pytest tests/test_historical_outcome_engine.py -q`
Expected: PASS for holiday skipping, early-close flagging, missing-calendar failure, and missing-session gaps.

- [ ] **Step 5: Commit**

```bash
git add src/stock_risk_mcp/historical_outcome_engine.py tests/test_historical_outcome_engine.py
git commit -m "Add historical outcome forward observation engine"
```

### Task 5: Metrics And Report-Only Labels

**Files:**
- Modify: `src/stock_risk_mcp/historical_outcome_engine.py`
- Modify: `src/stock_risk_mcp/historical_outcome_models.py`
- Test: `tests/test_historical_outcome_engine.py`

- [ ] **Step 1: Write the failing label-assignment tests**

```python
def test_assigns_favorable_outcome_label(outcome_fixture):
    report = build_historical_outcome_label_report(outcome_fixture)
    assert report.labels[0].label_type == "OUTCOME_FAVORABLE"


def test_assigns_inconclusive_label_when_thresholds_missing(outcome_fixture_missing_thresholds):
    report = build_historical_outcome_label_report(outcome_fixture_missing_thresholds)
    assert report.labels[0].label_type in {"OUTCOME_INCONCLUSIVE", "OUTCOME_REPORT_ONLY"}
    assert "OUTCOME_THRESHOLD_CONFIG_MISSING" in report.gap_report.gap_categories
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3.11 -m pytest tests/test_historical_outcome_engine.py -k "favorable or thresholds" -v`
Expected: FAIL because label builder is not implemented

- [ ] **Step 3: Implement observational metrics**

For each observation record compute:

- anchor close
- forward close
- forward return percentage
- max favorable excursion percentage
- max adverse excursion percentage
- high-water mark
- low-water mark
- observed volume summary
- number of trading sessions observed
- missing-session count
- early-close count
- event-context presence flags

- [ ] **Step 4: Implement report-only label assignment**

Assign conservative labels using explicit config thresholds only. If thresholds or forward data are incomplete, emit report-only inconclusive labels and gap entries instead of guessing.

- [ ] **Step 5: Run focused label tests**

Run: `python3.11 -m pytest tests/test_historical_outcome_engine.py -q`
Expected: PASS for favorable, adverse, neutral, volatile mixed, insufficient forward data, and threshold-missing cases.

- [ ] **Step 6: Commit**

```bash
git add src/stock_risk_mcp/historical_outcome_engine.py src/stock_risk_mcp/historical_outcome_models.py tests/test_historical_outcome_engine.py
git commit -m "Add historical outcome metrics and labels"
```

### Task 6: Leakage Guard And Scanner Input Separation

**Files:**
- Modify: `src/stock_risk_mcp/historical_outcome_engine.py`
- Modify: `src/stock_risk_mcp/historical_outcome_guard.py`
- Test: `tests/test_historical_outcome_engine.py`

- [ ] **Step 1: Write the failing leakage test**

```python
def test_outcome_labels_do_not_mutate_scanner_replay_input(outcome_fixture):
    scanner_input_before = outcome_fixture.scanner_replay_input.model_dump(mode="json")
    report = build_historical_outcome_label_report(outcome_fixture)
    scanner_input_after = outcome_fixture.scanner_replay_input.model_dump(mode="json")

    assert report.labels
    assert scanner_input_after == scanner_input_before
    assert all(label.outcome_observed_after_anchor is True for label in report.labels)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_outcome_engine.py::test_outcome_labels_do_not_mutate_scanner_replay_input -v`
Expected: FAIL because leakage/separation is not enforced yet

- [ ] **Step 3: Enforce no-lookahead separation**

Ensure:

- outcome records are generated in separate objects
- replay/scanner input remains unchanged
- actual future event results stay outcome-side only
- missing known-time metadata creates report-only leakage warnings or gaps
- runtime-signal wording is rejected

- [ ] **Step 4: Run focused leakage tests**

Run: `python3.11 -m pytest tests/test_historical_outcome_engine.py -k "leakage or mutate or runtime" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stock_risk_mcp/historical_outcome_engine.py src/stock_risk_mcp/historical_outcome_guard.py tests/test_historical_outcome_engine.py
git commit -m "Enforce historical outcome leakage boundaries"
```

### Task 7: Service Layer And CLI

**Files:**
- Create: `src/stock_risk_mcp/historical_outcome_service.py`
- Modify: `src/stock_risk_mcp/cli.py`
- Test: `tests/test_historical_outcome_cli.py`

- [ ] **Step 1: Write the failing CLI test**

```python
import json

from stock_risk_mcp.cli import main


def test_historical_outcome_cli_returns_json_safe_reports(tmp_path, capsys, outcome_fixture_file):
    main(["historical-outcome-label-report", "--fixture-file", str(outcome_fixture_file)])
    result = json.loads(capsys.readouterr().out)

    assert result["schema_version"] == "5.3-historical-outcome-label-report"
    assert result["read_only"] is True
    assert result["non_executable"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_outcome_cli.py::test_historical_outcome_cli_returns_json_safe_reports -v`
Expected: FAIL because the service/CLI command is missing

- [ ] **Step 3: Implement service functions**

Add:

```python
def run_historical_outcome_observe(fixture_file, output_file=None):
    ...


def run_historical_outcome_label_report(fixture_file, output_file=None):
    ...


def run_historical_outcome_gap_report(fixture_file, output_file=None):
    ...


def run_historical_outcome_safety_report(fixture_file, output_file=None):
    ...
```

These functions must load local fixtures only and serialize report-only outputs only.

- [ ] **Step 4: Wire CLI commands**

Register:

- `historical-outcome-observe --fixture-file ... [--output-file ...]`
- `historical-outcome-label-report --fixture-file ... [--output-file ...]`
- `historical-outcome-gap-report --fixture-file ... [--output-file ...]`
- `historical-outcome-safety-report --fixture-file ... [--output-file ...]`

- [ ] **Step 5: Run focused CLI tests**

Run: `python3.11 -m pytest tests/test_historical_outcome_cli.py -q`
Expected: PASS for success paths and fail-closed unsafe fixture rejection.

- [ ] **Step 6: Commit**

```bash
git add src/stock_risk_mcp/historical_outcome_service.py src/stock_risk_mcp/cli.py tests/test_historical_outcome_cli.py
git commit -m "Add historical outcome CLI integration"
```

### Task 8: System Smoke, Final Validation, And Milestone Close

**Files:**
- Modify: `src/stock_risk_mcp/system_smoke.py`
- Modify: `tests/test_system_smoke.py`
- Modify: `WORK_SUMMARY.md` if required by repo convention

- [ ] **Step 1: Write the failing smoke assertion**

```python
def test_system_smoke_validates_local_workflow(tmp_path):
    result = run_system_smoke(tmp_path / "smoke.sqlite3", tmp_path / "outputs")
    assert result["checks"]["historical_outcome_observation_fixture_run"] is True
    assert result["checks"]["historical_outcome_labels_report_only"] is True
    assert result["checks"]["historical_outcome_no_lookahead_guard_enabled"] is True
```

- [ ] **Step 2: Run the smoke test to verify it fails**

Run: `python3.11 -m pytest tests/test_system_smoke.py -q`
Expected: FAIL with missing v5.3 check keys

- [ ] **Step 3: Add fixture-only outcome smoke coverage**

Build temporary local fixtures only. Confirm:

- `historical_outcome_observation_fixture_run=true`
- `historical_outcome_windows_generated=true`
- `historical_outcome_metrics_generated=true`
- `historical_outcome_labels_report_only=true`
- `historical_outcome_no_lookahead_guard_enabled=true`
- `historical_outcome_scanner_input_not_mutated=true`
- `historical_outcome_read_only=true`
- `historical_outcome_non_executable=true`
- `historical_outcome_local_files_only=true`
- all forbidden network/provider/order/LLM/ML/crawler flags remain false

- [ ] **Step 4: Run focused v5.3 validation**

Run: `python3.11 -m pytest tests/test_historical_outcome_models.py tests/test_historical_outcome_engine.py tests/test_historical_outcome_cli.py tests/test_system_smoke.py -q`
Expected: PASS

- [ ] **Step 5: Run full system smoke**

Run: `python3.11 -m pytest tests/test_system_smoke.py -q`
Expected: PASS

- [ ] **Step 6: Run full pytest if feasible**

Run: `python3.11 -m pytest -q`
Expected: PASS

- [ ] **Step 7: Commit milestone**

```bash
git add src/stock_risk_mcp/historical_outcome_models.py src/stock_risk_mcp/historical_outcome_fixture.py src/stock_risk_mcp/historical_outcome_guard.py src/stock_risk_mcp/historical_outcome_engine.py src/stock_risk_mcp/historical_outcome_service.py src/stock_risk_mcp/cli.py src/stock_risk_mcp/system_smoke.py tests/test_historical_outcome_models.py tests/test_historical_outcome_engine.py tests/test_historical_outcome_cli.py tests/test_system_smoke.py WORK_SUMMARY.md
git commit -m "Implement historical outcome observation and labeling integration"
```

- [ ] **Step 8: Tag v5.3**

```bash
git tag v5.3.0-historical-outcome-observation-labeling-integration
```

---

## Self-Review

- Spec coverage: the plan includes models, guard, engine, service, CLI, smoke, and milestone-close validation for all listed v5.3 requirements.
- Placeholder scan: no `TODO`/`TBD` markers remain.
- Type consistency: the plan consistently uses `HistoricalOutcomeObservationInput`, `HistoricalOutcomeLabelReport`, `HistoricalOutcomeGapReport`, and local fixture-only service/CLI naming.
