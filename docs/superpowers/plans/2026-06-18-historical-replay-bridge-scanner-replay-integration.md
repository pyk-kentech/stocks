# Historical Replay Bridge And Scanner Replay Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a safe offline v5.2 bridge that converts v5.1 historical market and calendar snapshots into replay-compatible, scanner-compatible, report-only inputs for the existing v4 offline pipeline.

**Architecture:** Add a dedicated historical replay bridge layer that loads only local v5.1 snapshot fixtures, validates fail-closed safety boundaries, produces deterministic replay event streams and calendar-aware replay windows, and then derives scanner replay input bundles without creating any order-like or executable artifacts. Reuse v4 replay/scanner concepts only as compatibility targets and metadata references; do not activate realtime, provider, trading, model, or crawler paths.

**Tech Stack:** Python 3.11, Pydantic v2, existing strict model patterns, existing CLI/service/system-smoke patterns, pytest

---

## File Structure

### New files

- `src/stock_risk_mcp/historical_replay_bridge_models.py`
  Bridge config, fixture input, replay event stream, replay window, bridge report, gap report, safety report, and audit record models.
- `src/stock_risk_mcp/historical_scanner_replay_models.py`
  Scanner replay input, candidate seed, replay context, scanner replay report, and scanner replay gap models.
- `src/stock_risk_mcp/historical_replay_bridge_fixture.py`
  Loader for a v5.2 bridge fixture that embeds or references v5.1 `HistoricalMarketDataSnapshot` and `HistoricalCalendarEventSnapshot`.
- `src/stock_risk_mcp/historical_replay_bridge_guard.py`
  Dedicated bridge safety checks for local-file-only, no-provider, no-order, no-network, no-LLM, no-ML boundaries.
- `src/stock_risk_mcp/historical_replay_bridge_engine.py`
  Pure conversion logic from historical snapshots to replay event stream, replay windows, scanner replay bundle, and reports.
- `src/stock_risk_mcp/historical_replay_bridge_service.py`
  Thin orchestration service for fixture load, build, validate, and JSON output persistence.
- `tests/test_historical_replay_bridge_models.py`
  Bridge model construction and fail-closed safety tests.
- `tests/test_historical_replay_bridge_engine.py`
  Replay event conversion, window generation, context attachment, scanner replay bundle, and report tests.
- `tests/test_historical_replay_bridge_service.py`
  Service success and failure path tests.
- `tests/test_historical_replay_bridge_cli.py`
  CLI success and JSON-safe failure tests.
- `tests/test_historical_replay_bridge_safety.py`
  Explicit offline-only safety assertions for remote/API/order/LLM/ML/crawler rejection.

### Modified files

- `src/stock_risk_mcp/cli.py`
  Register new v5.2 replay bridge and scanner replay commands.
- `src/stock_risk_mcp/system_smoke.py`
  Add v5.2 historical replay bridge fixture-only smoke generation and assertions.
- `tests/test_system_smoke.py`
  Assert v5.2 smoke checks.
- `WORK_SUMMARY.md`
  Append a short v5.2 summary only if the repo’s summary convention still appends milestone status.

### Existing files to inspect for compatibility only

- `src/stock_risk_mcp/historical_data_models.py`
- `src/stock_risk_mcp/historical_calendar_models.py`
- `src/stock_risk_mcp/domestic_replay_models.py`
- `src/stock_risk_mcp/domestic_replay_engine.py`
- `src/stock_risk_mcp/domestic_scanner_models.py`
- `src/stock_risk_mcp/domestic_scanner_engine.py`
- `src/stock_risk_mcp/domestic_shadow_outcome_models.py`
- `src/stock_risk_mcp/domestic_market_regime_models.py`

## Bridge Fixture Shape

The v5.2 bridge input should be a dedicated fixture file so the bridge can be exercised without external state. The fixture should carry:

- `schema_version = "5.2-historical-replay-bridge-fixture"`
- `fixture_id`
- `created_at`
- `bridge_config`
- `historical_market_data_snapshot`
- `historical_calendar_event_snapshot`
- optional `scanner_replay_hints`

The embedded snapshot objects must be valid v5.1 `HistoricalMarketDataSnapshot` and `HistoricalCalendarEventSnapshot` payloads. This keeps v5.2 local-file-only while avoiding any raw provider ingestion or implicit external dependency.

## Compatibility Assumptions

- v5.2 replay output is **report-only compatibility** with v4 replay/scanner layers.
- v5.2 does **not** create `ReplayRun`, `ScannerCandidate`, `OrderIntent`, or trade plans directly.
- v5.2 can mirror selected v4 fields such as strategy track, market profile, timestamps, compatibility markers, and summary counters.
- v5.2 windows are counted by trading sessions, not raw calendar days.
- v5.2 holiday recognition is not a data-gap error when supported by the calendar snapshot.

## Non-Goals

- realtime ingestion
- real market/calendar fetch
- provider APIs
- Investing.com crawler
- FINVIZ scraper
- news packet ingestion
- Gemini / Google AI Studio
- Kiwoom / LS / broker / account integrations
- order creation, order drafts, execution approval
- LIVE / PROD paths
- cloud LLMs or local model runtimes
- ML training
- parquet support

## Task 1: Plan And Fixture Boundary

**Files:**
- Create: `docs/superpowers/plans/2026-06-18-historical-replay-bridge-scanner-replay-integration.md`
- Inspect: `src/stock_risk_mcp/historical_data_models.py`
- Inspect: `src/stock_risk_mcp/historical_calendar_models.py`
- Inspect: `src/stock_risk_mcp/domestic_replay_models.py`
- Inspect: `src/stock_risk_mcp/domestic_scanner_models.py`

- [ ] **Step 1: Confirm input/output boundary in the plan**

Write the plan so it explicitly states:

```text
Inputs:
- HistoricalMarketDataSnapshot
- HistoricalCalendarEventSnapshot

Outputs:
- HistoricalReplayEventStream
- HistoricalReplayWindow
- HistoricalScannerReplayInput
- HistoricalReplayBridgeReport
- HistoricalReplayBridgeGapReport
- HistoricalReplayBridgeSafetyReport

Safety:
- read-only
- non-executable
- local-file-only
- no-network
- no-provider-api
- no-order
- no-llm-runtime
- no-ml-training
```

- [ ] **Step 2: Re-read the v5.2 requirement list against the plan**

Run: `sed -n '1,260p' docs/superpowers/plans/2026-06-18-historical-replay-bridge-scanner-replay-integration.md`
Expected: the plan names replay event stream conversion, calendar-aware windowing, scanner replay integration, safety guard, CLI, tests, and smoke updates.

## Task 2: Bridge Models And Fixture Loader

**Files:**
- Create: `src/stock_risk_mcp/historical_replay_bridge_models.py`
- Create: `src/stock_risk_mcp/historical_scanner_replay_models.py`
- Create: `src/stock_risk_mcp/historical_replay_bridge_fixture.py`
- Test: `tests/test_historical_replay_bridge_models.py`

- [ ] **Step 1: Write the failing model test**

```python
import pytest

from stock_risk_mcp.historical_replay_bridge_fixture import load_historical_replay_bridge_fixture
from stock_risk_mcp.historical_replay_bridge_models import (
    HistoricalReplayBridgeGapCategory,
    HistoricalReplayBridgeInput,
    HistoricalReplayBridgeSafetyReport,
)


def test_historical_replay_bridge_models_accept_local_snapshot_inputs(tmp_path):
    fixture_file = tmp_path / "bridge_fixture.json"
    fixture_file.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError):
        load_historical_replay_bridge_fixture(fixture_file)

    assert HistoricalReplayBridgeGapCategory.REPLAY_REMOTE_SOURCE_NOT_ALLOWED.value == "REPLAY_REMOTE_SOURCE_NOT_ALLOWED"
    assert HistoricalReplayBridgeSafetyReport.model_fields["read_only"].default is True
    assert HistoricalReplayBridgeInput.model_fields["historical_market_data_snapshot"].annotation is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_replay_bridge_models.py::test_historical_replay_bridge_models_accept_local_snapshot_inputs -v`
Expected: FAIL with import error for `stock_risk_mcp.historical_replay_bridge_models`

- [ ] **Step 3: Write minimal bridge model implementation**

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.historical_calendar_models import HistoricalCalendarEventSnapshot
from stock_risk_mcp.historical_data_models import HistoricalMarketDataSnapshot
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import StrategyTrack


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


class HistoricalReplayBridgeGapCategory(StrEnum):
    MISSING_HISTORICAL_MARKET_SNAPSHOT = "MISSING_HISTORICAL_MARKET_SNAPSHOT"
    MISSING_HISTORICAL_CALENDAR_EVENT_SNAPSHOT = "MISSING_HISTORICAL_CALENDAR_EVENT_SNAPSHOT"
    MISSING_SOURCE_MANIFEST = "MISSING_SOURCE_MANIFEST"
    MISSING_STRATEGY_TRACK = "MISSING_STRATEGY_TRACK"
    MISSING_MARKET_PROFILE = "MISSING_MARKET_PROFILE"
    UNSUPPORTED_REPLAY_TRACK = "UNSUPPORTED_REPLAY_TRACK"
    UNSUPPORTED_REPLAY_MARKET = "UNSUPPORTED_REPLAY_MARKET"
    REPLAY_CURRENCY_MISMATCH = "REPLAY_CURRENCY_MISMATCH"
    REPLAY_TIMEZONE_MISMATCH = "REPLAY_TIMEZONE_MISMATCH"
    REPLAY_EVENT_OUT_OF_ORDER = "REPLAY_EVENT_OUT_OF_ORDER"
    REPLAY_EVENT_DUPLICATE = "REPLAY_EVENT_DUPLICATE"
    REPLAY_MISSING_TRADING_SESSION = "REPLAY_MISSING_TRADING_SESSION"
    REPLAY_HOLIDAY_SESSION_RECOGNIZED = "REPLAY_HOLIDAY_SESSION_RECOGNIZED"
    REPLAY_EARLY_CLOSE_SESSION_FLAGGED = "REPLAY_EARLY_CLOSE_SESSION_FLAGGED"
    REPLAY_UNSUPPORTED_EVENT_CONTEXT = "REPLAY_UNSUPPORTED_EVENT_CONTEXT"
    REPLAY_SOURCE_PROVENANCE_MISSING = "REPLAY_SOURCE_PROVENANCE_MISSING"
    REPLAY_EXECUTABLE_WORDING_DETECTED = "REPLAY_EXECUTABLE_WORDING_DETECTED"
    REPLAY_ORDER_FIELD_DETECTED = "REPLAY_ORDER_FIELD_DETECTED"
    REPLAY_REMOTE_SOURCE_NOT_ALLOWED = "REPLAY_REMOTE_SOURCE_NOT_ALLOWED"
    REPLAY_API_SOURCE_NOT_ALLOWED = "REPLAY_API_SOURCE_NOT_ALLOWED"
    REPLAY_NETWORK_SOURCE_NOT_ALLOWED = "REPLAY_NETWORK_SOURCE_NOT_ALLOWED"


class HistoricalReplayBridgeConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    calendar_required: bool = True
    allow_report_only_degraded_calendar: bool = False
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True


class HistoricalReplayBridgeInput(StrictModel):
    bridge_input_id: str = Field(..., min_length=1)
    historical_market_data_snapshot: HistoricalMarketDataSnapshot
    historical_calendar_event_snapshot: HistoricalCalendarEventSnapshot | None = None
    source_manifest_ids: list[str] = Field(default_factory=list)
    source_audit_record_ids: list[str] = Field(default_factory=list)


class HistoricalReplayBridgeSafetyReport(StrictModel):
    safety_report_id: str = Field(..., min_length=1)
    read_only: bool = True
    non_executable: bool = True
    local_file_only: bool = True
    no_network: bool = True
    no_provider_api: bool = True
    no_order: bool = True
    no_llm_runtime: bool = True
    no_ml_training: bool = True


class HistoricalReplayBridgeFixture(StrictModel):
    schema_version: str
    fixture_id: str = Field(..., min_length=1)
    created_at: datetime
    bridge_config: HistoricalReplayBridgeConfig
    historical_market_data_snapshot: HistoricalMarketDataSnapshot
    historical_calendar_event_snapshot: HistoricalCalendarEventSnapshot | None = None

    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "5.2-historical-replay-bridge-fixture":
            raise ValueError("schema_version must be exactly 5.2-historical-replay-bridge-fixture")
        return value
```

- [ ] **Step 4: Write the fixture loader**

```python
from pathlib import Path

from stock_risk_mcp.historical_replay_bridge_models import HistoricalReplayBridgeFixture


def load_historical_replay_bridge_fixture(path) -> HistoricalReplayBridgeFixture:
    try:
        return HistoricalReplayBridgeFixture.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid historical replay bridge fixture: {exc}") from exc
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_historical_replay_bridge_models.py::test_historical_replay_bridge_models_accept_local_snapshot_inputs -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/stock_risk_mcp/historical_replay_bridge_models.py src/stock_risk_mcp/historical_scanner_replay_models.py src/stock_risk_mcp/historical_replay_bridge_fixture.py tests/test_historical_replay_bridge_models.py
git commit -m "feat: add historical replay bridge model foundation"
```

## Task 3: Replay Event Stream Conversion

**Files:**
- Create: `src/stock_risk_mcp/historical_replay_bridge_guard.py`
- Create: `src/stock_risk_mcp/historical_replay_bridge_engine.py`
- Test: `tests/test_historical_replay_bridge_engine.py`

- [ ] **Step 1: Write the failing event stream test**

```python
from stock_risk_mcp.historical_replay_bridge_engine import build_historical_replay_event_stream


def test_historical_replay_event_stream_converts_ohlcv_rows_without_synthesizing_prices(bridge_fixture):
    stream = build_historical_replay_event_stream(bridge_fixture)

    assert stream.strategy_track.value == "DOMESTIC_KR"
    assert len(stream.events) == 2
    assert stream.events[0].open == 70000
    assert stream.events[0].no_order is True
    assert stream.events[0].source_manifest_id == bridge_fixture.historical_market_data_snapshot.manifest.manifest_id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_replay_bridge_engine.py::test_historical_replay_event_stream_converts_ohlcv_rows_without_synthesizing_prices -v`
Expected: FAIL with missing `build_historical_replay_event_stream`

- [ ] **Step 3: Implement minimal event stream conversion**

```python
def build_historical_replay_event_stream(fixture):
    snapshot = fixture.historical_market_data_snapshot
    manifest_id = snapshot.manifest.manifest_id
    events = []
    for index, record in enumerate(snapshot.records, start=1):
        events.append(HistoricalReplayEvent(
            replay_event_id=f"{snapshot.snapshot_id}-event-{index}",
            symbol=record.symbol,
            market=record.market,
            strategy_track=snapshot.ingestion_config.strategy_track,
            timestamp=record.timestamp,
            timezone=record.timezone,
            open=record.open,
            high=record.high,
            low=record.low,
            close=record.close,
            volume=record.volume,
            currency=record.currency,
            source_manifest_id=manifest_id,
            source_record_id=f"{record.symbol}-{record.timestamp.isoformat()}",
            source_audit_record_ids=[item.audit_record_id for item in snapshot.audit_records],
            read_only=True,
            non_executable=True,
            no_order=True,
        ))
    return HistoricalReplayEventStream(
        event_stream_id=f"{snapshot.snapshot_id}-stream",
        strategy_track=snapshot.ingestion_config.strategy_track,
        market_profile_id=snapshot.manifest.market_profile_id,
        source_snapshot_id=snapshot.snapshot_id,
        source_manifest_id=manifest_id,
        event_count=len(events),
        events=events,
        read_only=True,
        non_executable=True,
        no_order=True,
    )
```

- [ ] **Step 4: Implement the safety guard**

```python
FORBIDDEN_TEXT = (
    "ORDER",
    "EXECUTE",
    "BROKER",
    "KIWOOM",
    "LS",
    "GEMINI",
    "TRAIN",
    "PARQUET",
)


def ensure_safe_bridge_input(fixture):
    descriptor = fixture.historical_market_data_snapshot.source_descriptor
    if descriptor.source_type.value != "local_csv" and descriptor.source_type.value != "local_jsonl":
        raise ValueError("historical replay bridge requires local_csv or local_jsonl only")
    for candidate in (
        descriptor.local_file_path,
        fixture.historical_market_data_snapshot.manifest.source_file_path,
    ):
        upper = candidate.upper()
        if upper.startswith("HTTP://") or upper.startswith("HTTPS://") or "://" in upper:
            raise ValueError("historical replay bridge rejects remote source paths")
        if upper.endswith(".PARQUET"):
            raise ValueError("historical replay bridge rejects parquet sources")
    text = fixture.model_dump_json().upper()
    if any(token in text for token in FORBIDDEN_TEXT):
        raise ValueError("historical replay bridge rejects executable or integration wording")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_historical_replay_bridge_engine.py::test_historical_replay_event_stream_converts_ohlcv_rows_without_synthesizing_prices -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/stock_risk_mcp/historical_replay_bridge_guard.py src/stock_risk_mcp/historical_replay_bridge_engine.py tests/test_historical_replay_bridge_engine.py
git commit -m "feat: add historical replay event stream conversion"
```

## Task 4: Calendar-Aware Replay Windows And Event Context

**Files:**
- Modify: `src/stock_risk_mcp/historical_replay_bridge_engine.py`
- Test: `tests/test_historical_replay_bridge_engine.py`

- [ ] **Step 1: Write the failing replay window test**

```python
def test_historical_replay_windows_use_trading_sessions_and_attach_event_context(bridge_fixture):
    bundle = build_historical_replay_windows(bridge_fixture)

    assert bundle.windows[0].trading_session_date.isoformat() == "2026-06-18"
    assert bundle.windows[0].session_type.value == "REGULAR_SESSION"
    assert bundle.windows[0].market_holiday is False
    assert bundle.windows[0].early_close is False
    assert "CPI_RELEASE" in bundle.windows[0].attached_event_types
    assert bundle.windows[0].report_only_event_context is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_replay_bridge_engine.py::test_historical_replay_windows_use_trading_sessions_and_attach_event_context -v`
Expected: FAIL with missing `build_historical_replay_windows`

- [ ] **Step 3: Implement minimal calendar-aware window generation**

```python
def build_historical_replay_windows(fixture):
    calendar = fixture.historical_calendar_event_snapshot
    if calendar is None and fixture.bridge_config.calendar_required:
        raise ValueError("historical replay bridge requires historical calendar snapshot")
    if calendar is None:
        return HistoricalReplayWindowBundle(
            window_bundle_id=f"{fixture.fixture_id}-window-bundle",
            windows=[],
            read_only=True,
            non_executable=True,
            report_only=True,
        )

    event_types_by_date = {}
    for market_event in calendar.market_events:
        event_types_by_date.setdefault(market_event.event_date.isoformat(), set()).add(market_event.event_type.value)
    for corporate_event in calendar.corporate_events:
        event_types_by_date.setdefault(corporate_event.event_date.isoformat(), set()).add(corporate_event.event_type.value)

    windows = []
    for session in calendar.session_records:
        windows.append(HistoricalReplayWindow(
            replay_window_id=f"{fixture.fixture_id}-{session.date.isoformat()}",
            trading_session_date=session.date,
            session_type=session.session_type,
            market_holiday=session.is_holiday,
            early_close=session.is_early_close,
            attached_event_types=sorted(event_types_by_date.get(session.date.isoformat(), set())),
            report_only_event_context=True,
            read_only=True,
            non_executable=True,
            no_order=True,
        ))
    return HistoricalReplayWindowBundle(
        window_bundle_id=f"{fixture.fixture_id}-window-bundle",
        windows=windows,
        read_only=True,
        non_executable=True,
        report_only=True,
    )
```

- [ ] **Step 4: Add gap handling tests**

```python
def test_historical_replay_bridge_treats_holidays_as_session_context_not_missing_data(holiday_bridge_fixture):
    bundle = build_historical_replay_windows(holiday_bridge_fixture)
    assert bundle.windows[0].market_holiday is True


def test_historical_replay_bridge_flags_early_close_sessions(early_close_bridge_fixture):
    bundle = build_historical_replay_windows(early_close_bridge_fixture)
    assert bundle.windows[0].early_close is True
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3.11 -m pytest tests/test_historical_replay_bridge_engine.py -k "window or holiday or early_close" -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/stock_risk_mcp/historical_replay_bridge_engine.py tests/test_historical_replay_bridge_engine.py
git commit -m "feat: add calendar aware replay windows"
```

## Task 5: Scanner Replay Input And Reports

**Files:**
- Modify: `src/stock_risk_mcp/historical_scanner_replay_models.py`
- Modify: `src/stock_risk_mcp/historical_replay_bridge_engine.py`
- Test: `tests/test_historical_replay_bridge_engine.py`

- [ ] **Step 1: Write the failing scanner replay test**

```python
def test_historical_scanner_replay_input_is_report_only_and_not_an_order_candidate(bridge_fixture):
    scanner_input = build_historical_scanner_replay_input(bridge_fixture)

    assert scanner_input.report_only is True
    assert scanner_input.non_executable is True
    assert scanner_input.no_order is True
    assert scanner_input.candidate_seeds[0].symbol == "005930"
    assert scanner_input.candidate_seeds[0].is_order_candidate is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_replay_bridge_engine.py::test_historical_scanner_replay_input_is_report_only_and_not_an_order_candidate -v`
Expected: FAIL with missing `build_historical_scanner_replay_input`

- [ ] **Step 3: Implement minimal scanner replay bundle**

```python
def build_historical_scanner_replay_input(fixture):
    stream = build_historical_replay_event_stream(fixture)
    windows = build_historical_replay_windows(fixture)
    latest_by_symbol = {}
    for event in stream.events:
        latest_by_symbol[event.symbol] = event
    seeds = [
        HistoricalScannerReplayCandidateSeed(
            seed_id=f"{fixture.fixture_id}-{symbol}-seed",
            symbol=symbol,
            market=event.market,
            source_replay_event_id=event.replay_event_id,
            source_manifest_id=event.source_manifest_id,
            is_order_candidate=False,
            report_only=True,
            non_executable=True,
            no_order=True,
        )
        for symbol, event in sorted(latest_by_symbol.items())
    ]
    return HistoricalScannerReplayInput(
        scanner_replay_input_id=f"{fixture.fixture_id}-scanner-replay",
        strategy_track=fixture.bridge_config.strategy_track,
        source_event_stream_id=stream.event_stream_id,
        source_window_bundle_id=windows.window_bundle_id,
        candidate_seeds=seeds,
        report_only=True,
        read_only=True,
        non_executable=True,
        no_order=True,
    )
```

- [ ] **Step 4: Build bridge, gap, and safety reports**

```python
def build_historical_replay_bridge_report(fixture, stream, windows, scanner_input):
    return HistoricalReplayBridgeReport(
        report_id=f"{fixture.fixture_id}-bridge-report",
        strategy_track=fixture.bridge_config.strategy_track,
        source_market_snapshot_id=fixture.historical_market_data_snapshot.snapshot_id,
        source_calendar_snapshot_id=(
            fixture.historical_calendar_event_snapshot.snapshot_id
            if fixture.historical_calendar_event_snapshot is not None
            else None
        ),
        event_stream_id=stream.event_stream_id,
        window_bundle_id=windows.window_bundle_id,
        scanner_replay_input_id=scanner_input.scanner_replay_input_id,
        event_count=stream.event_count,
        window_count=len(windows.windows),
        seed_count=len(scanner_input.candidate_seeds),
        report_only=True,
        read_only=True,
        non_executable=True,
    )
```

- [ ] **Step 5: Run the focused scanner tests**

Run: `python3.11 -m pytest tests/test_historical_replay_bridge_engine.py -k "scanner_replay or bridge_report" -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/stock_risk_mcp/historical_scanner_replay_models.py src/stock_risk_mcp/historical_replay_bridge_engine.py tests/test_historical_replay_bridge_engine.py
git commit -m "feat: add scanner replay input bridge"
```

## Task 6: Service And CLI

**Files:**
- Create: `src/stock_risk_mcp/historical_replay_bridge_service.py`
- Modify: `src/stock_risk_mcp/cli.py`
- Test: `tests/test_historical_replay_bridge_service.py`
- Test: `tests/test_historical_replay_bridge_cli.py`

- [ ] **Step 1: Write the failing service test**

```python
from stock_risk_mcp.historical_replay_bridge_service import (
    run_historical_replay_bridge_build,
    run_historical_replay_event_stream,
    run_historical_replay_gap_report,
    run_historical_replay_safety_report,
    run_historical_replay_window_report,
    run_historical_scanner_replay_input,
)


def test_historical_replay_bridge_service_builds_all_outputs(bridge_fixture_file, tmp_path):
    report = run_historical_replay_bridge_build(bridge_fixture_file, tmp_path / "bridge.json")
    stream = run_historical_replay_event_stream(bridge_fixture_file, tmp_path / "stream.json")
    windows = run_historical_replay_window_report(bridge_fixture_file, tmp_path / "windows.json")
    scanner = run_historical_scanner_replay_input(bridge_fixture_file, tmp_path / "scanner.json")
    gap = run_historical_replay_gap_report(bridge_fixture_file, tmp_path / "gap.json")
    safety = run_historical_replay_safety_report(bridge_fixture_file, tmp_path / "safety.json")

    assert report.event_count == stream.event_count
    assert len(windows.windows) >= 1
    assert len(scanner.candidate_seeds) >= 1
    assert safety.no_network is True
    assert gap.gap_count >= 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_replay_bridge_service.py::test_historical_replay_bridge_service_builds_all_outputs -v`
Expected: FAIL with missing service module

- [ ] **Step 3: Implement service wrappers**

```python
from pathlib import Path

from stock_risk_mcp.historical_replay_bridge_engine import (
    build_historical_replay_bridge_bundle,
    build_historical_replay_event_stream,
    build_historical_replay_gap_report,
    build_historical_replay_safety_report,
    build_historical_replay_windows,
    build_historical_scanner_replay_input,
)
from stock_risk_mcp.historical_replay_bridge_fixture import load_historical_replay_bridge_fixture


def run_historical_replay_event_stream(fixture_file, output_file=None):
    fixture = load_historical_replay_bridge_fixture(fixture_file)
    stream = build_historical_replay_event_stream(fixture)
    if output_file:
        Path(output_file).write_text(stream.model_dump_json(indent=2), encoding="utf-8")
    return stream
```

Add analogous wrappers for:

- `run_historical_replay_bridge_build`
- `run_historical_replay_window_report`
- `run_historical_scanner_replay_input`
- `run_historical_replay_gap_report`
- `run_historical_replay_safety_report`

- [ ] **Step 4: Write the failing CLI test**

```python
import json

from stock_risk_mcp.cli import main


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_historical_replay_bridge_cli_commands_return_json_safe_outputs(bridge_fixture_file, tmp_path, capsys):
    report = run(capsys, ["historical-replay-bridge-build", "--fixture-file", str(bridge_fixture_file), "--output-file", str(tmp_path / "bridge.json")])
    stream = run(capsys, ["historical-replay-event-stream", "--fixture-file", str(bridge_fixture_file), "--output-file", str(tmp_path / "stream.json")])
    windows = run(capsys, ["historical-replay-window-report", "--fixture-file", str(bridge_fixture_file), "--output-file", str(tmp_path / "windows.json")])
    scanner = run(capsys, ["historical-scanner-replay-input", "--fixture-file", str(bridge_fixture_file), "--output-file", str(tmp_path / "scanner.json")])
    gap = run(capsys, ["historical-replay-gap-report", "--fixture-file", str(bridge_fixture_file), "--output-file", str(tmp_path / "gap.json")])
    safety = run(capsys, ["historical-replay-safety-report", "--fixture-file", str(bridge_fixture_file), "--output-file", str(tmp_path / "safety.json")])

    assert report["status"] == "COMPLETED"
    assert stream["status"] == "COMPLETED"
    assert windows["status"] == "COMPLETED"
    assert scanner["status"] == "COMPLETED"
    assert gap["status"] == "COMPLETED"
    assert safety["status"] == "COMPLETED"
```

- [ ] **Step 5: Implement CLI registration**

Add parser entries and command handlers for:

```text
historical-replay-bridge-build
historical-replay-event-stream
historical-replay-window-report
historical-scanner-replay-input
historical-replay-gap-report
historical-replay-safety-report
```

Use the same JSON-safe pattern already used by:

- `historical-data-manifest-build`
- `historical-calendar-gap-report`
- `prompt-pack-gap-report`

- [ ] **Step 6: Run service and CLI tests**

Run: `python3.11 -m pytest tests/test_historical_replay_bridge_service.py tests/test_historical_replay_bridge_cli.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/stock_risk_mcp/historical_replay_bridge_service.py src/stock_risk_mcp/cli.py tests/test_historical_replay_bridge_service.py tests/test_historical_replay_bridge_cli.py
git commit -m "feat: add historical replay bridge cli"
```

## Task 7: Safety Coverage, Fixtures, And Smoke

**Files:**
- Create: `tests/test_historical_replay_bridge_safety.py`
- Modify: `src/stock_risk_mcp/system_smoke.py`
- Modify: `tests/test_system_smoke.py`

- [ ] **Step 1: Add fixture builders for valid and invalid bridge inputs**

Create fixture helpers in the bridge test modules that cover:

- valid KR historical replay bridge input
- holiday session bridge input
- early-close bridge input
- macro event bridge input
- corporate event bridge input
- missing calendar bridge input
- missing market snapshot bridge input
- market profile mismatch bridge input
- timezone mismatch bridge input
- duplicate replay event bridge input
- out-of-order replay event bridge input
- remote source rejection bridge input
- API source rejection bridge input
- order-like field rejection bridge input
- executable wording rejection bridge input
- parquet rejection bridge input

- [ ] **Step 2: Write the failing safety test**

```python
import pytest

from stock_risk_mcp.historical_replay_bridge_engine import build_historical_replay_safety_report


@pytest.mark.parametrize(
    "mutator, expected_message",
    [
        (lambda fixture: fixture.historical_market_data_snapshot.source_descriptor.__setattr__("local_file_path", "https://example.com/data.csv"), "remote"),
        (lambda fixture: fixture.historical_market_data_snapshot.source_descriptor.__setattr__("local_file_path", "fixture.parquet"), "parquet"),
    ],
)
def test_historical_replay_bridge_rejects_unsafe_sources(bridge_fixture, mutator, expected_message):
    mutator(bridge_fixture)
    with pytest.raises(ValueError, match=expected_message):
        build_historical_replay_safety_report(bridge_fixture)
```

- [ ] **Step 3: Implement smoke coverage**

Extend `run_system_smoke()` with a local v5.2 bridge fixture and assert:

```python
"historical_replay_bridge_fixture_run": True,
"historical_replay_event_stream_generated": True,
"historical_replay_windows_generated": True,
"historical_scanner_replay_input_generated": True,
"calendar_aware_windowing_enabled": True,
"holiday_sessions_not_counted_as_data_gaps": True,
"early_close_sessions_flagged": True,
"event_context_attached_report_only": True,
"historical_replay_read_only": True,
"historical_replay_non_executable": True,
"historical_replay_local_files_only": True,
"historical_replay_remote_fetch_allowed": False,
"historical_replay_api_provider_called": False,
"historical_replay_order_intent_created": False,
"historical_replay_live_or_prod_used": False,
"historical_replay_cloud_llm_called": False,
"historical_replay_model_runtime_called": False,
"historical_replay_ml_training_run": False,
"investing_crawler_called": False,
"finviz_scraper_called": False,
"news_ingestion_called": False,
"gemini_called": False,
"kiwoom_api_called": False,
"ls_api_called": False,
"broker_api_called": False,
"credentials_accessed": False,
"external_network_calls": False,
```

- [ ] **Step 4: Run the focused safety and smoke tests**

Run: `python3.11 -m pytest tests/test_historical_replay_bridge_safety.py tests/test_system_smoke.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_historical_replay_bridge_safety.py src/stock_risk_mcp/system_smoke.py tests/test_system_smoke.py
git commit -m "test: add historical replay bridge safety and smoke coverage"
```

## Task 8: Milestone Verification And Release

**Files:**
- Modify: `WORK_SUMMARY.md` only if summary convention still requires it

- [ ] **Step 1: Run targeted v5.2 tests**

Run:

```bash
python3.11 -m pytest \
  tests/test_historical_replay_bridge_models.py \
  tests/test_historical_replay_bridge_engine.py \
  tests/test_historical_replay_bridge_service.py \
  tests/test_historical_replay_bridge_cli.py \
  tests/test_historical_replay_bridge_safety.py \
  tests/test_system_smoke.py -q
```

Expected: PASS

- [ ] **Step 2: Run `system_smoke` coverage explicitly**

Run: `python3.11 -m pytest tests/test_system_smoke.py -q`
Expected: PASS

- [ ] **Step 3: Run full pytest if feasible**

Run: `python3.11 -m pytest -q`
Expected: PASS with complete count and runtime captured

- [ ] **Step 4: Review working tree scope**

Run: `git status --short`
Expected: only v5.2 bridge/scanner replay implementation files, tests, CLI, smoke, and optional summary update

- [ ] **Step 5: Commit milestone**

```bash
git add src/stock_risk_mcp/historical_replay_bridge_models.py \
        src/stock_risk_mcp/historical_scanner_replay_models.py \
        src/stock_risk_mcp/historical_replay_bridge_fixture.py \
        src/stock_risk_mcp/historical_replay_bridge_guard.py \
        src/stock_risk_mcp/historical_replay_bridge_engine.py \
        src/stock_risk_mcp/historical_replay_bridge_service.py \
        src/stock_risk_mcp/cli.py \
        src/stock_risk_mcp/system_smoke.py \
        tests/test_historical_replay_bridge_models.py \
        tests/test_historical_replay_bridge_engine.py \
        tests/test_historical_replay_bridge_service.py \
        tests/test_historical_replay_bridge_cli.py \
        tests/test_historical_replay_bridge_safety.py \
        tests/test_system_smoke.py \
        docs/superpowers/plans/2026-06-18-historical-replay-bridge-scanner-replay-integration.md
git commit -m "Implement historical replay bridge and scanner replay integration"
```

- [ ] **Step 6: Create the v5.2 tag**

Run:

```bash
git tag v5.2.0-historical-replay-bridge-scanner-replay-integration
git rev-list -n 1 v5.2.0-historical-replay-bridge-scanner-replay-integration
```

Expected: tag exists and points to the new v5.2 commit

## Plan Self-Review

- Spec coverage: this plan covers bridge models, scanner replay models, deterministic event conversion, calendar-aware windows, event context attachment, gap/safety/report generation, service wrappers, CLI, smoke, and release verification.
- Placeholder scan: no `TBD`, `TODO`, or “implement later” placeholders remain.
- Type consistency: the plan uses `HistoricalReplayBridgeFixture`, `HistoricalReplayEventStream`, `HistoricalReplayWindowBundle`, and `HistoricalScannerReplayInput` consistently across model, engine, service, CLI, and smoke tasks.

## Execution Notes

- v5.2 must remain local fixture-only and must not introduce realtime, provider, order, execution, account, crawler, or model runtime behavior.
- Prefer reusing v5.1 snapshot payload helpers in tests rather than inventing parallel historical payload formats.
- When adding bridge outputs, preserve source manifest ids, snapshot ids, and audit record ids in every downstream report-oriented artifact.
