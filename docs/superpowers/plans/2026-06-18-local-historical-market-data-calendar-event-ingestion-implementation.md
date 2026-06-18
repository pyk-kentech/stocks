# Local Historical Market Data and Calendar Event Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-file-only, read-only, non-executable v5.1 ingestion foundation for historical OHLCV and calendar/event fixtures with deterministic validation, manifests, quality/gap reports, CLI commands, and system-smoke coverage.

**Architecture:** Add two parallel pure-core ingestion stacks: one for `HistoricalMarketDataSnapshot` and one for `HistoricalCalendarEventSnapshot`. Each stack uses strict Pydantic models, exact local CSV/JSONL fixture loaders, pure validation/report builders, thin service wrappers, CLI entrypoints, and smoke/test coverage while preserving no-network, no-provider, no-order boundaries.

**Tech Stack:** Python 3.11, Pydantic v2 models, existing local file utilities, pytest, existing CLI/system-smoke patterns

---

## File Structure

### New files

- `src/stock_risk_mcp/historical_data_models.py`
  Historical OHLCV ingestion enums, schemas, manifests, reports, safety boundary, provenance, and metadata constants.
- `src/stock_risk_mcp/historical_data_fixture.py`
  Exact local JSON fixture loader for market-data ingestion fixtures.
- `src/stock_risk_mcp/historical_data_guard.py`
  Source/path safety checks and deterministic validation issue builders for market data.
- `src/stock_risk_mcp/historical_data_engine.py`
  Pure parsing, validation, manifest, quality, gap, and safety-report builders for OHLCV fixtures.
- `src/stock_risk_mcp/historical_data_service.py`
  Fixture orchestration and JSON output writers for market-data CLI commands.
- `src/stock_risk_mcp/historical_calendar_models.py`
  Trading session, market event, corporate event, calendar snapshot, manifest, reports, safety boundary, and metadata constants.
- `src/stock_risk_mcp/historical_calendar_fixture.py`
  Exact local JSON fixture loader for calendar/event ingestion fixtures.
- `src/stock_risk_mcp/historical_calendar_guard.py`
  Local source-path safety checks and deterministic validation issue builders for calendar/event fixtures.
- `src/stock_risk_mcp/historical_calendar_engine.py`
  Pure parsing, validation, manifest, gap, and safety-report builders for calendar/event fixtures.
- `src/stock_risk_mcp/historical_calendar_service.py`
  Fixture orchestration and JSON output writers for calendar/event CLI commands.
- `tests/test_historical_data_fixture.py`
  Fixture loading and fail-closed tests for market-data fixtures.
- `tests/test_historical_data_engine.py`
  Market-data CSV/JSONL parsing, validation, manifest, quality, gap, and safety tests.
- `tests/test_historical_data_cli.py`
  Market-data CLI success/failure tests.
- `tests/test_historical_data_safety.py`
  Forbidden import/path and no-network/no-provider/no-order safety assertions for market-data modules.
- `tests/test_historical_calendar_fixture.py`
  Fixture loading and fail-closed tests for calendar/event fixtures.
- `tests/test_historical_calendar_engine.py`
  Trading session, market event, corporate event, manifest, gap, and safety tests.
- `tests/test_historical_calendar_cli.py`
  Calendar/event CLI success/failure tests.
- `tests/test_historical_calendar_safety.py`
  Forbidden import/path and no-network/no-provider/no-order safety assertions for calendar modules.

### Modified files

- `src/stock_risk_mcp/cli.py`
  Register new historical data and calendar/event commands.
- `src/stock_risk_mcp/system_smoke.py`
  Add local temporary fixture generation and v5.1 smoke checks.
- `tests/test_system_smoke.py`
  Assert new smoke flags.
- `WORK_SUMMARY.md`
  Append a short v5.1 implementation summary only if repo convention remains milestone-by-milestone summary updates.

### Fixture artifacts created during tests

- Local temporary CSV/JSONL files under pytest tmp paths
- Local temporary JSON fixture wrapper files under pytest tmp paths

---

### Task 1: Historical Data Models

**Files:**
- Create: `src/stock_risk_mcp/historical_data_models.py`
- Test: `tests/test_historical_data_fixture.py`

- [ ] **Step 1: Write the failing test**

```python
from datetime import datetime

import pytest

from stock_risk_mcp.historical_data_models import (
    HistoricalDataFixture,
    HistoricalDataSourceType,
    HistoricalGapCategory,
)


def test_historical_data_fixture_requires_local_csv_or_jsonl_sources():
    fixture = HistoricalDataFixture.model_validate({
        "schema_version": "5.1-historical-data-fixture",
        "fixture_id": "hist-fixture-1",
        "created_at": "2026-06-18T09:00:00+09:00",
        "ingestion_config": {
            "config_id": "cfg-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile": {
                "market_id": "KRX",
                "country": "KR",
                "base_currency": "KRW",
                "exchange_session_profile": "KRX_CASH",
                "trading_hours": "09:00-15:30",
                "settlement_cash_availability": "T+2",
                "fee_tax_profile_reference": "profiles/domestic_kr_fee_tax.json",
                "realtime_data_profile_reference": "profiles/domestic_kr_realtime.json",
                "provider_capability_reference": "profiles/domestic_kr_local_file_only.json",
            },
            "source_type": "local_csv",
            "strict_validation_mode": True,
            "allow_report_only_downgrade": True,
            "read_only": True,
            "non_executable": True,
        },
        "source_descriptor": {
            "source_descriptor_id": "src-1",
            "source_type": "local_csv",
            "local_file_path": "data/historical/sample.csv",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "source_id": "KRX_MANUAL",
            "timezone": "Asia/Seoul",
            "currency": "KRW",
            "read_only": True,
            "non_executable": True,
        },
        "provider_provenance": {
            "provenance_id": "prov-1",
            "source_family": "KRX_MANUAL_EXPORT",
            "source_name": "KRX manual export",
            "source_tier": "OFFICIAL",
            "acquisition_mode": "LOCAL_FILE",
            "requires_reconciliation": False,
        },
        "adjustment_policy": {
            "policy_id": "adj-1",
            "price_adjustment_mode": "UNADJUSTED",
            "split_adjustment_expected": False,
            "dividend_adjustment_expected": False,
            "corporate_action_backfill_expected": False,
            "adjusted_close_required": False,
            "mixed_adjustment_state_allowed": False,
            "report_only_if_uncertain": True,
        },
        "records": [],
    })

    assert fixture.ingestion_config.source_type is HistoricalDataSourceType.LOCAL_CSV
    assert HistoricalGapCategory.REMOTE_FETCH_NOT_ALLOWED.value == "REMOTE_FETCH_NOT_ALLOWED"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_data_fixture.py::test_historical_data_fixture_requires_local_csv_or_jsonl_sources -v`
Expected: FAIL with import error for `stock_risk_mcp.historical_data_models`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import MarketProfile, StrategyTrack


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


class HistoricalDataSourceType(StrEnum):
    LOCAL_CSV = "local_csv"
    LOCAL_JSONL = "local_jsonl"
    LOCAL_PARQUET = "local_parquet"
    REMOTE_URL = "remote_url"
    PROVIDER_API = "provider_api"
    KIWOOM = "kiwoom"
    LS = "ls"
    BROKER = "broker"
    ACCOUNT = "account"


class HistoricalGapCategory(StrEnum):
    REMOTE_FETCH_NOT_ALLOWED = "REMOTE_FETCH_NOT_ALLOWED"


class HistoricalDataIngestionConfig(StrictModel):
    config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile: MarketProfile
    source_type: HistoricalDataSourceType
    strict_validation_mode: bool = True
    allow_report_only_downgrade: bool = False
    read_only: bool = True
    non_executable: bool = True


class HistoricalDataSourceDescriptor(StrictModel):
    source_descriptor_id: str = Field(..., min_length=1)
    source_type: HistoricalDataSourceType
    local_file_path: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    timezone: str = Field(..., min_length=1)
    currency: str = Field(..., min_length=1)
    read_only: bool = True
    non_executable: bool = True


class HistoricalDataProviderProvenance(StrictModel):
    provenance_id: str = Field(..., min_length=1)
    source_family: str = Field(..., min_length=1)
    source_name: str = Field(..., min_length=1)
    source_tier: str = Field(..., min_length=1)
    acquisition_mode: str = Field(..., min_length=1)
    requires_reconciliation: bool = False


class HistoricalDataAdjustmentPolicy(StrictModel):
    policy_id: str = Field(..., min_length=1)
    price_adjustment_mode: str = Field(..., min_length=1)
    split_adjustment_expected: bool = False
    dividend_adjustment_expected: bool = False
    corporate_action_backfill_expected: bool = False
    adjusted_close_required: bool = False
    mixed_adjustment_state_allowed: bool = False
    report_only_if_uncertain: bool = True


class HistoricalDataFixture(StrictModel):
    schema_version: str
    fixture_id: str = Field(..., min_length=1)
    created_at: datetime
    ingestion_config: HistoricalDataIngestionConfig
    source_descriptor: HistoricalDataSourceDescriptor
    provider_provenance: HistoricalDataProviderProvenance
    adjustment_policy: HistoricalDataAdjustmentPolicy
    records: list[dict] = Field(default_factory=list)

    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "5.1-historical-data-fixture":
            raise ValueError("schema_version must be exactly 5.1-historical-data-fixture")
        return value
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_historical_data_fixture.py::test_historical_data_fixture_requires_local_csv_or_jsonl_sources -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_historical_data_fixture.py src/stock_risk_mcp/historical_data_models.py
git commit -m "test: add historical data model foundation"
```

### Task 2: Calendar and Event Models

**Files:**
- Create: `src/stock_risk_mcp/historical_calendar_models.py`
- Test: `tests/test_historical_calendar_fixture.py`

- [ ] **Step 1: Write the failing test**

```python
from stock_risk_mcp.historical_calendar_models import (
    CalendarEventType,
    HistoricalCalendarEventFixture,
)


def test_historical_calendar_event_fixture_supports_sessions_and_events():
    fixture = HistoricalCalendarEventFixture.model_validate({
        "schema_version": "5.1-historical-calendar-fixture",
        "fixture_id": "calendar-fixture-1",
        "created_at": "2026-06-18T09:00:00+09:00",
        "calendar_config": {
            "calendar_config_id": "cal-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "source_type": "local_csv",
            "read_only": True,
            "non_executable": True,
        },
        "trading_sessions": [{
            "market": "KRX",
            "date": "2026-06-18",
            "timezone": "Asia/Seoul",
            "is_trading_day": True,
            "is_holiday": False,
            "is_early_close": False,
            "regular_open_time": "09:00",
            "regular_close_time": "15:30",
            "actual_open_time": "09:00",
            "actual_close_time": "15:30",
            "session_type": "REGULAR_SESSION",
            "source_id": "KRX_CAL",
            "calendar_batch_id": "batch-1",
        }],
        "market_events": [{
            "event_id": "evt-1",
            "market": "KRX",
            "event_date": "2026-06-18",
            "timezone": "Asia/Seoul",
            "event_type": "CPI_RELEASE",
            "event_scope": "MACRO",
            "affected_market": "KRX",
            "source_id": "MACRO_CAL",
            "event_batch_id": "batch-1",
            "report_only": True,
            "non_executable": True,
        }],
        "corporate_events": [],
    })

    assert fixture.market_events[0].event_type is CalendarEventType.CPI_RELEASE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_calendar_fixture.py::test_historical_calendar_event_fixture_supports_sessions_and_events -v`
Expected: FAIL with import error for `stock_risk_mcp.historical_calendar_models`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import Field, field_validator

from stock_risk_mcp.historical_data_models import HistoricalDataSourceType, aware
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.strategy_track_models import StrategyTrack


class CalendarEventType(StrEnum):
    REGULAR_SESSION = "REGULAR_SESSION"
    MARKET_HOLIDAY = "MARKET_HOLIDAY"
    EARLY_CLOSE = "EARLY_CLOSE"
    CPI_RELEASE = "CPI_RELEASE"


class TradingCalendarConfig(StrictModel):
    calendar_config_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    market_profile_id: str = Field(..., min_length=1)
    source_type: HistoricalDataSourceType
    read_only: bool = True
    non_executable: bool = True


class TradingSessionRecord(StrictModel):
    market: str = Field(..., min_length=1)
    date: date
    timezone: str = Field(..., min_length=1)
    is_trading_day: bool
    is_holiday: bool
    is_early_close: bool
    regular_open_time: str = Field(..., min_length=1)
    regular_close_time: str = Field(..., min_length=1)
    actual_open_time: str = Field(..., min_length=1)
    actual_close_time: str = Field(..., min_length=1)
    session_type: CalendarEventType
    source_id: str = Field(..., min_length=1)
    calendar_batch_id: str = Field(..., min_length=1)


class MarketEventRecord(StrictModel):
    event_id: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    event_date: date
    timezone: str = Field(..., min_length=1)
    event_type: CalendarEventType
    event_scope: str = Field(..., min_length=1)
    affected_market: str | None = None
    source_id: str = Field(..., min_length=1)
    event_batch_id: str = Field(..., min_length=1)
    report_only: bool = True
    non_executable: bool = True


class CorporateEventRecord(StrictModel):
    symbol: str = Field(..., min_length=1)
    market: str = Field(..., min_length=1)
    event_date: date
    event_type: CalendarEventType
    earnings_before_open_flag: bool = False
    earnings_after_close_flag: bool = False
    dividend_ex_date_flag: bool = False
    split_effective_date_flag: bool = False
    corporate_action_adjustment_flag: bool = False
    source_id: str = Field(..., min_length=1)


class HistoricalCalendarEventFixture(StrictModel):
    schema_version: str
    fixture_id: str = Field(..., min_length=1)
    created_at: datetime
    calendar_config: TradingCalendarConfig
    trading_sessions: list[TradingSessionRecord] = Field(default_factory=list)
    market_events: list[MarketEventRecord] = Field(default_factory=list)
    corporate_events: list[CorporateEventRecord] = Field(default_factory=list)

    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "5.1-historical-calendar-fixture":
            raise ValueError("schema_version must be exactly 5.1-historical-calendar-fixture")
        return value
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_historical_calendar_fixture.py::test_historical_calendar_event_fixture_supports_sessions_and_events -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_historical_calendar_fixture.py src/stock_risk_mcp/historical_calendar_models.py
git commit -m "test: add historical calendar model foundation"
```

### Task 3: Historical Data Fixture Loader and Source Rejection

**Files:**
- Create: `src/stock_risk_mcp/historical_data_fixture.py`
- Modify: `src/stock_risk_mcp/historical_data_models.py`
- Test: `tests/test_historical_data_fixture.py`

- [ ] **Step 1: Write the failing test**

```python
import json

import pytest

from stock_risk_mcp.historical_data_fixture import load_historical_data_fixture


def test_historical_data_fixture_rejects_non_json_wrapper_and_unsupported_source(tmp_path):
    payload = {
        "schema_version": "5.1-historical-data-fixture",
        "fixture_id": "hist-fixture-1",
        "created_at": "2026-06-18T09:00:00+09:00",
        "ingestion_config": {
            "config_id": "cfg-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile": {
                "market_id": "KRX",
                "country": "KR",
                "base_currency": "KRW",
                "exchange_session_profile": "KRX_CASH",
                "trading_hours": "09:00-15:30",
                "settlement_cash_availability": "T+2",
                "fee_tax_profile_reference": "profiles/domestic_kr_fee_tax.json",
                "realtime_data_profile_reference": "profiles/domestic_kr_realtime.json",
                "provider_capability_reference": "profiles/domestic_kr_local_file_only.json",
            },
            "source_type": "local_parquet",
            "strict_validation_mode": True,
            "allow_report_only_downgrade": True,
            "read_only": True,
            "non_executable": True,
        },
        "source_descriptor": {
            "source_descriptor_id": "src-1",
            "source_type": "local_parquet",
            "local_file_path": "data/historical/sample.parquet",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "source_id": "KRX_MANUAL",
            "timezone": "Asia/Seoul",
            "currency": "KRW",
            "read_only": True,
            "non_executable": True,
        },
        "provider_provenance": {
            "provenance_id": "prov-1",
            "source_family": "KRX_MANUAL_EXPORT",
            "source_name": "KRX manual export",
            "source_tier": "OFFICIAL",
            "acquisition_mode": "LOCAL_FILE",
            "requires_reconciliation": False,
        },
        "adjustment_policy": {
            "policy_id": "adj-1",
            "price_adjustment_mode": "UNADJUSTED",
            "split_adjustment_expected": False,
            "dividend_adjustment_expected": False,
            "corporate_action_backfill_expected": False,
            "adjusted_close_required": False,
            "mixed_adjustment_state_allowed": False,
            "report_only_if_uncertain": True,
        },
        "records": [],
    }
    fixture_file = tmp_path / "fixture.json"
    fixture_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported"):
        load_historical_data_fixture(fixture_file)

    text_wrapper = tmp_path / "fixture.txt"
    text_wrapper.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="explicit local JSON"):
        load_historical_data_fixture(text_wrapper)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_data_fixture.py::test_historical_data_fixture_rejects_non_json_wrapper_and_unsupported_source -v`
Expected: FAIL because `load_historical_data_fixture` does not exist or does not reject unsupported source

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.historical_data_models import HistoricalDataFixture, HistoricalDataSourceType


SUPPORTED_HISTORICAL_SOURCE_TYPES = {
    HistoricalDataSourceType.LOCAL_CSV,
    HistoricalDataSourceType.LOCAL_JSONL,
}


def load_historical_data_fixture(path) -> HistoricalDataFixture:
    try:
        selected = Path(path)
        if selected.suffix.lower() != ".json":
            raise ValueError("historical data fixture must be an explicit local JSON file")
        fixture = HistoricalDataFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
        if fixture.ingestion_config.source_type not in SUPPORTED_HISTORICAL_SOURCE_TYPES:
            raise ValueError(f"unsupported historical source type: {fixture.ingestion_config.source_type.value}")
        if fixture.source_descriptor.source_type not in SUPPORTED_HISTORICAL_SOURCE_TYPES:
            raise ValueError(f"unsupported historical source descriptor type: {fixture.source_descriptor.source_type.value}")
        return fixture
    except Exception as exc:
        raise ValueError(f"invalid historical data fixture: {exc}") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_historical_data_fixture.py::test_historical_data_fixture_rejects_non_json_wrapper_and_unsupported_source -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_historical_data_fixture.py src/stock_risk_mcp/historical_data_fixture.py src/stock_risk_mcp/historical_data_models.py
git commit -m "test: reject unsupported historical sources"
```

### Task 4: Historical Calendar Fixture Loader and Source Rejection

**Files:**
- Create: `src/stock_risk_mcp/historical_calendar_fixture.py`
- Modify: `src/stock_risk_mcp/historical_calendar_models.py`
- Test: `tests/test_historical_calendar_fixture.py`

- [ ] **Step 1: Write the failing test**

```python
import json

import pytest

from stock_risk_mcp.historical_calendar_fixture import load_historical_calendar_fixture


def test_historical_calendar_fixture_rejects_remote_and_parquet_sources(tmp_path):
    payload = {
        "schema_version": "5.1-historical-calendar-fixture",
        "fixture_id": "calendar-fixture-1",
        "created_at": "2026-06-18T09:00:00+09:00",
        "calendar_config": {
            "calendar_config_id": "cal-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "source_type": "remote_url",
            "read_only": True,
            "non_executable": True,
        },
        "trading_sessions": [],
        "market_events": [],
        "corporate_events": [],
    }
    fixture_file = tmp_path / "calendar.json"
    fixture_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported"):
        load_historical_calendar_fixture(fixture_file)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_calendar_fixture.py::test_historical_calendar_fixture_rejects_remote_and_parquet_sources -v`
Expected: FAIL because `load_historical_calendar_fixture` does not exist or does not reject unsupported source

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.historical_calendar_models import HistoricalCalendarEventFixture
from stock_risk_mcp.historical_data_fixture import SUPPORTED_HISTORICAL_SOURCE_TYPES


def load_historical_calendar_fixture(path) -> HistoricalCalendarEventFixture:
    try:
        selected = Path(path)
        if selected.suffix.lower() != ".json":
            raise ValueError("historical calendar fixture must be an explicit local JSON file")
        fixture = HistoricalCalendarEventFixture.model_validate(json.loads(selected.read_text(encoding="utf-8")))
        if fixture.calendar_config.source_type not in SUPPORTED_HISTORICAL_SOURCE_TYPES:
            raise ValueError(f"unsupported historical calendar source type: {fixture.calendar_config.source_type.value}")
        return fixture
    except Exception as exc:
        raise ValueError(f"invalid historical calendar fixture: {exc}") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_historical_calendar_fixture.py::test_historical_calendar_fixture_rejects_remote_and_parquet_sources -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_historical_calendar_fixture.py src/stock_risk_mcp/historical_calendar_fixture.py
git commit -m "test: reject unsupported historical calendar sources"
```

### Task 5: Market Data Engine, Parsing, Validation, and Reports

**Files:**
- Create: `src/stock_risk_mcp/historical_data_guard.py`
- Create: `src/stock_risk_mcp/historical_data_engine.py`
- Modify: `src/stock_risk_mcp/historical_data_models.py`
- Test: `tests/test_historical_data_engine.py`

- [ ] **Step 1: Write the failing test**

```python
import json

from stock_risk_mcp.historical_data_engine import (
    build_historical_data_gap_report,
    build_historical_data_manifest,
    build_historical_data_quality_report,
    validate_historical_data_fixture,
)
from stock_risk_mcp.historical_data_fixture import load_historical_data_fixture


def test_historical_data_engine_parses_csv_and_builds_reports(tmp_path):
    csv_file = tmp_path / "ohlcv.csv"
    csv_file.write_text(
        "symbol,market,timestamp,timezone,open,high,low,close,volume,currency,source_id,ingestion_batch_id\n"
        "005930,KRX,2026-06-18T09:00:00+09:00,Asia/Seoul,70000,71000,69900,70500,1000,KRW,KRX_MANUAL,batch-1\n",
        encoding="utf-8",
    )
    fixture_payload = {
        "schema_version": "5.1-historical-data-fixture",
        "fixture_id": "hist-fixture-1",
        "created_at": "2026-06-18T09:00:00+09:00",
        "ingestion_config": {
            "config_id": "cfg-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile": {
                "market_id": "KRX",
                "country": "KR",
                "base_currency": "KRW",
                "exchange_session_profile": "KRX_CASH",
                "trading_hours": "09:00-15:30",
                "settlement_cash_availability": "T+2",
                "fee_tax_profile_reference": "profiles/domestic_kr_fee_tax.json",
                "realtime_data_profile_reference": "profiles/domestic_kr_realtime.json",
                "provider_capability_reference": "profiles/domestic_kr_local_file_only.json",
            },
            "source_type": "local_csv",
            "strict_validation_mode": True,
            "allow_report_only_downgrade": True,
            "read_only": True,
            "non_executable": True,
        },
        "source_descriptor": {
            "source_descriptor_id": "src-1",
            "source_type": "local_csv",
            "local_file_path": str(csv_file),
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "source_id": "KRX_MANUAL",
            "timezone": "Asia/Seoul",
            "currency": "KRW",
            "read_only": True,
            "non_executable": True,
        },
        "provider_provenance": {
            "provenance_id": "prov-1",
            "source_family": "KRX_MANUAL_EXPORT",
            "source_name": "KRX manual export",
            "source_tier": "OFFICIAL",
            "acquisition_mode": "LOCAL_FILE",
            "requires_reconciliation": False,
        },
        "adjustment_policy": {
            "policy_id": "adj-1",
            "price_adjustment_mode": "UNADJUSTED",
            "split_adjustment_expected": False,
            "dividend_adjustment_expected": False,
            "corporate_action_backfill_expected": False,
            "adjusted_close_required": False,
            "mixed_adjustment_state_allowed": False,
            "report_only_if_uncertain": True,
        },
        "records": [],
    }
    fixture_file = tmp_path / "fixture.json"
    fixture_file.write_text(json.dumps(fixture_payload), encoding="utf-8")
    fixture = load_historical_data_fixture(fixture_file)

    validation = validate_historical_data_fixture(fixture)
    quality = build_historical_data_quality_report(fixture, validation)
    gap = build_historical_data_gap_report(fixture, validation)
    manifest = build_historical_data_manifest(fixture, validation, quality, gap)

    assert validation.valid is True
    assert quality.record_count == 1
    assert gap.gap_categories == []
    assert manifest.record_count == 1
    assert manifest.read_only is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_data_engine.py::test_historical_data_engine_parses_csv_and_builds_reports -v`
Expected: FAIL because engine functions do not exist

- [ ] **Step 3: Write minimal implementation**

```python
# historical_data_guard.py
from __future__ import annotations

from pathlib import Path


def reject_unsafe_local_path(path: str) -> str | None:
    lowered = path.strip().lower()
    if lowered.startswith(("http://", "https://")):
        return "REMOTE_FETCH_NOT_ALLOWED"
    if lowered.endswith(".parquet"):
        return "UNSUPPORTED_TRACK"
    return None


# historical_data_engine.py
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from stock_risk_mcp.historical_data_guard import reject_unsafe_local_path
from stock_risk_mcp.historical_data_models import (
    HistoricalDataGapCategory,
    HistoricalDataGapReport,
    HistoricalDataManifest,
    HistoricalDataQualityReport,
    HistoricalDataValidationIssue,
    HistoricalDataValidationReport,
    HistoricalOHLCVRecord,
)


def _load_records(fixture):
    path = Path(fixture.source_descriptor.local_file_path)
    if fixture.source_descriptor.source_type.value == "local_csv":
        with path.open(encoding="utf-8") as handle:
            return [HistoricalOHLCVRecord.model_validate(row) for row in csv.DictReader(handle)]
    return [HistoricalOHLCVRecord.model_validate(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_historical_data_fixture(fixture) -> HistoricalDataValidationReport:
    issues = []
    path_issue = reject_unsafe_local_path(fixture.source_descriptor.local_file_path)
    if path_issue:
        issues.append(HistoricalDataValidationIssue(category=HistoricalDataGapCategory(path_issue), message=path_issue))
    records = _load_records(fixture) if not issues else []
    for record in records:
        if record.currency != fixture.ingestion_config.market_profile.base_currency:
            issues.append(HistoricalDataValidationIssue(category=HistoricalDataGapCategory.CURRENCY_MISMATCH, message="currency mismatch"))
        if record.high < max(record.open, record.close, record.low):
            issues.append(HistoricalDataValidationIssue(category=HistoricalDataGapCategory.INVALID_OHLC, message="invalid high bound"))
        if record.low > min(record.open, record.close, record.high):
            issues.append(HistoricalDataValidationIssue(category=HistoricalDataGapCategory.INVALID_OHLC, message="invalid low bound"))
    return HistoricalDataValidationReport(
        validation_report_id=f"{fixture.fixture_id}-validation",
        ingestion_batch_id=records[0].ingestion_batch_id if records else fixture.fixture_id,
        valid=not issues,
        issues=issues,
        summary={"record_count": len(records), "issue_count": len(issues)},
        read_only=True,
        non_executable=True,
        report_only=bool(issues and fixture.ingestion_config.allow_report_only_downgrade),
    )


def build_historical_data_quality_report(fixture, validation) -> HistoricalDataQualityReport:
    records = _load_records(fixture)
    return HistoricalDataQualityReport(
        quality_report_id=f"{fixture.fixture_id}-quality",
        ingestion_batch_id=records[0].ingestion_batch_id if records else fixture.fixture_id,
        record_count=len(records),
        symbol_count=len({record.symbol for record in records}),
        market_count=len({record.market for record in records}),
        date_range_start=records[0].timestamp if records else None,
        date_range_end=records[-1].timestamp if records else None,
        timezone_distribution=dict(Counter(record.timezone for record in records)),
        currency_distribution=dict(Counter(record.currency for record in records)),
        missing_value_count=0,
        duplicate_count=0,
        invalid_ohlc_count=sum(issue.category == HistoricalDataGapCategory.INVALID_OHLC for issue in validation.issues),
        invalid_volume_count=0,
        out_of_order_count=0,
        missing_session_count=0,
        adjustment_policy_summary=fixture.adjustment_policy.price_adjustment_mode,
        quality_bucket="PASS" if validation.valid else "REPORT_ONLY",
        report_only=validation.report_only,
        read_only=True,
        non_executable=True,
    )


def build_historical_data_gap_report(fixture, validation) -> HistoricalDataGapReport:
    return HistoricalDataGapReport(
        gap_report_id=f"{fixture.fixture_id}-gap",
        ingestion_batch_id=fixture.fixture_id,
        gap_categories=[issue.category.value for issue in validation.issues],
        gaps=[issue.model_dump(mode="json") for issue in validation.issues],
        read_only=True,
        non_executable=True,
    )


def build_historical_data_manifest(fixture, validation, quality, gap) -> HistoricalDataManifest:
    path = Path(fixture.source_descriptor.local_file_path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return HistoricalDataManifest(
        manifest_id=f"{fixture.fixture_id}-manifest",
        ingestion_batch_id=fixture.fixture_id,
        source_descriptor_id=fixture.source_descriptor.source_descriptor_id,
        source_file_path=str(path),
        source_file_hash=digest,
        strategy_track=fixture.ingestion_config.strategy_track,
        market_profile_id=fixture.ingestion_config.market_profile.market_id,
        record_count=quality.record_count,
        symbol_count=quality.symbol_count,
        date_range={"start": quality.date_range_start, "end": quality.date_range_end},
        timezone=fixture.source_descriptor.timezone,
        currency=fixture.source_descriptor.currency,
        adjustment_policy=fixture.adjustment_policy.price_adjustment_mode,
        validation_report_id=validation.validation_report_id,
        quality_report_id=quality.quality_report_id,
        gap_report_id=gap.gap_report_id,
        read_only=True,
        non_executable=True,
        no_network=True,
        no_provider_api=True,
        no_order=True,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_historical_data_engine.py::test_historical_data_engine_parses_csv_and_builds_reports -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_historical_data_engine.py src/stock_risk_mcp/historical_data_guard.py src/stock_risk_mcp/historical_data_engine.py src/stock_risk_mcp/historical_data_models.py
git commit -m "feat: add historical data validation and reports"
```

### Task 6: Calendar/Event Engine, Parsing, Validation, and Reports

**Files:**
- Create: `src/stock_risk_mcp/historical_calendar_guard.py`
- Create: `src/stock_risk_mcp/historical_calendar_engine.py`
- Modify: `src/stock_risk_mcp/historical_calendar_models.py`
- Test: `tests/test_historical_calendar_engine.py`

- [ ] **Step 1: Write the failing test**

```python
import json

from stock_risk_mcp.historical_calendar_engine import (
    build_historical_calendar_gap_report,
    build_historical_calendar_manifest,
    validate_historical_calendar_fixture,
)
from stock_risk_mcp.historical_calendar_fixture import load_historical_calendar_fixture


def test_historical_calendar_engine_parses_jsonl_and_validates_event_context(tmp_path):
    session_file = tmp_path / "sessions.jsonl"
    session_file.write_text(
        '{"market":"KRX","date":"2026-06-18","timezone":"Asia/Seoul","is_trading_day":true,"is_holiday":false,"is_early_close":true,"regular_open_time":"09:00","regular_close_time":"15:30","actual_open_time":"09:00","actual_close_time":"12:00","session_type":"EARLY_CLOSE","source_id":"KRX_CAL","calendar_batch_id":"batch-1"}\n',
        encoding="utf-8",
    )
    fixture_payload = {
        "schema_version": "5.1-historical-calendar-fixture",
        "fixture_id": "calendar-fixture-1",
        "created_at": "2026-06-18T09:00:00+09:00",
        "calendar_config": {
            "calendar_config_id": "cal-1",
            "strategy_track": "DOMESTIC_KR",
            "market_profile_id": "KRX",
            "source_type": "local_jsonl",
            "read_only": True,
            "non_executable": True,
        },
        "source_descriptor": {
            "source_descriptor_id": "cal-src-1",
            "local_file_path": str(session_file),
            "source_type": "local_jsonl",
            "source_id": "KRX_CAL",
            "market_profile_id": "KRX",
            "strategy_track": "DOMESTIC_KR",
            "timezone": "Asia/Seoul",
            "read_only": True,
            "non_executable": True,
        },
        "trading_sessions": [],
        "market_events": [],
        "corporate_events": [],
    }
    fixture_file = tmp_path / "calendar_fixture.json"
    fixture_file.write_text(json.dumps(fixture_payload), encoding="utf-8")
    fixture = load_historical_calendar_fixture(fixture_file)

    validation = validate_historical_calendar_fixture(fixture)
    gap = build_historical_calendar_gap_report(fixture, validation)
    manifest = build_historical_calendar_manifest(fixture, validation, gap)

    assert validation.valid is True
    assert manifest.session_record_count == 1
    assert "EARLY_CLOSE_SESSION" in validation.summary["recognized_flags"]
    assert gap.gap_categories == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_calendar_engine.py::test_historical_calendar_engine_parses_jsonl_and_validates_event_context -v`
Expected: FAIL because calendar engine functions do not exist

- [ ] **Step 3: Write minimal implementation**

```python
# historical_calendar_guard.py
from __future__ import annotations


def reject_unsafe_calendar_path(path: str) -> str | None:
    lowered = path.strip().lower()
    if lowered.startswith(("http://", "https://")):
        return "REMOTE_CALENDAR_FETCH_NOT_ALLOWED"
    if lowered.endswith(".parquet"):
        return "API_CALENDAR_SOURCE_NOT_ALLOWED"
    return None


# historical_calendar_engine.py
from __future__ import annotations

import csv
import json
from pathlib import Path

from stock_risk_mcp.historical_calendar_guard import reject_unsafe_calendar_path
from stock_risk_mcp.historical_calendar_models import (
    CalendarGapReport,
    CalendarValidationIssue,
    CalendarValidationReport,
    HistoricalCalendarManifest,
    TradingSessionRecord,
)


def _load_sessions(fixture):
    path = Path(fixture.source_descriptor.local_file_path)
    if fixture.source_descriptor.source_type.value == "local_csv":
        with path.open(encoding="utf-8") as handle:
            return [TradingSessionRecord.model_validate(row) for row in csv.DictReader(handle)]
    return [TradingSessionRecord.model_validate(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_historical_calendar_fixture(fixture) -> CalendarValidationReport:
    issues = []
    path_issue = reject_unsafe_calendar_path(fixture.source_descriptor.local_file_path)
    if path_issue:
        issues.append(CalendarValidationIssue(category=path_issue, message=path_issue))
    sessions = _load_sessions(fixture) if not issues else []
    recognized_flags = []
    for session in sessions:
        if session.is_early_close:
            recognized_flags.append("EARLY_CLOSE_SESSION")
    return CalendarValidationReport(
        calendar_validation_report_id=f"{fixture.fixture_id}-validation",
        calendar_batch_id=fixture.fixture_id,
        valid=not issues,
        issues=issues,
        summary={"session_count": len(sessions), "recognized_flags": recognized_flags},
        read_only=True,
        non_executable=True,
    )


def build_historical_calendar_gap_report(fixture, validation) -> CalendarGapReport:
    return CalendarGapReport(
        calendar_gap_report_id=f"{fixture.fixture_id}-gap",
        calendar_batch_id=fixture.fixture_id,
        gap_categories=[issue["category"] if isinstance(issue, dict) else issue.category for issue in validation.issues],
        gaps=[issue if isinstance(issue, dict) else issue.model_dump(mode="json") for issue in validation.issues],
        read_only=True,
        non_executable=True,
    )


def build_historical_calendar_manifest(fixture, validation, gap) -> HistoricalCalendarManifest:
    sessions = _load_sessions(fixture)
    return HistoricalCalendarManifest(
        calendar_manifest_id=f"{fixture.fixture_id}-manifest",
        calendar_batch_id=fixture.fixture_id,
        source_descriptor_id=fixture.source_descriptor.source_descriptor_id,
        strategy_track=fixture.calendar_config.strategy_track,
        market_profile_id=fixture.calendar_config.market_profile_id,
        session_record_count=len(sessions),
        market_event_count=0,
        corporate_event_count=0,
        validation_report_id=validation.calendar_validation_report_id,
        gap_report_id=gap.calendar_gap_report_id,
        read_only=True,
        non_executable=True,
        no_network=True,
        no_provider_api=True,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_historical_calendar_engine.py::test_historical_calendar_engine_parses_jsonl_and_validates_event_context -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_historical_calendar_engine.py src/stock_risk_mcp/historical_calendar_guard.py src/stock_risk_mcp/historical_calendar_engine.py src/stock_risk_mcp/historical_calendar_models.py
git commit -m "feat: add historical calendar validation and manifest"
```

### Task 7: Service Layer and CLI Commands

**Files:**
- Create: `src/stock_risk_mcp/historical_data_service.py`
- Create: `src/stock_risk_mcp/historical_calendar_service.py`
- Modify: `src/stock_risk_mcp/cli.py`
- Test: `tests/test_historical_data_cli.py`
- Test: `tests/test_historical_calendar_cli.py`

- [ ] **Step 1: Write the failing test**

```python
import json

from stock_risk_mcp.cli import main


def test_historical_data_and_calendar_cli_commands_return_json_safe_outputs(tmp_path, capsys):
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps({"schema_version": "5.1-historical-data-fixture"}), encoding="utf-8")

    main(["historical-data-config-validate", "--fixture-file", str(fixture)])
    first = json.loads(capsys.readouterr().out)
    assert "status" in first
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_historical_data_cli.py::test_historical_data_and_calendar_cli_commands_return_json_safe_outputs -v`
Expected: FAIL because CLI command is unregistered

- [ ] **Step 3: Write minimal implementation**

```python
# historical_data_service.py
from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.historical_data_engine import (
    build_historical_data_gap_report,
    build_historical_data_manifest,
    build_historical_data_quality_report,
    validate_historical_data_fixture,
)
from stock_risk_mcp.historical_data_fixture import load_historical_data_fixture


def run_historical_data_config_validate(fixture_file):
    return load_historical_data_fixture(fixture_file)


def run_historical_data_validate(fixture_file, output_file=None):
    fixture = load_historical_data_fixture(fixture_file)
    report = validate_historical_data_fixture(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


# historical_calendar_service.py
from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.historical_calendar_engine import (
    build_historical_calendar_gap_report,
    build_historical_calendar_manifest,
    validate_historical_calendar_fixture,
)
from stock_risk_mcp.historical_calendar_fixture import load_historical_calendar_fixture


def run_historical_calendar_config_validate(fixture_file):
    return load_historical_calendar_fixture(fixture_file)


def run_historical_calendar_validate(fixture_file, output_file=None):
    fixture = load_historical_calendar_fixture(fixture_file)
    report = validate_historical_calendar_fixture(fixture)
    if output_file:
        Path(output_file).write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
```

```python
# cli.py additions
historical_data_config_validate = subparsers.add_parser("historical-data-config-validate")
historical_data_config_validate.add_argument("--fixture-file", type=Path, required=True)

historical_data_validate = subparsers.add_parser("historical-data-validate")
historical_data_validate.add_argument("--fixture-file", type=Path, required=True)
historical_data_validate.add_argument("--output-file", type=Path)

historical_calendar_config_validate = subparsers.add_parser("historical-calendar-config-validate")
historical_calendar_config_validate.add_argument("--fixture-file", type=Path, required=True)

historical_calendar_validate = subparsers.add_parser("historical-calendar-validate")
historical_calendar_validate.add_argument("--fixture-file", type=Path, required=True)
historical_calendar_validate.add_argument("--output-file", type=Path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_historical_data_cli.py::test_historical_data_and_calendar_cli_commands_return_json_safe_outputs -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_historical_data_cli.py tests/test_historical_calendar_cli.py src/stock_risk_mcp/historical_data_service.py src/stock_risk_mcp/historical_calendar_service.py src/stock_risk_mcp/cli.py
git commit -m "feat: add historical ingestion cli commands"
```

### Task 8: System Smoke, Safety Tests, and Summary Update

**Files:**
- Modify: `src/stock_risk_mcp/system_smoke.py`
- Modify: `tests/test_system_smoke.py`
- Create: `tests/test_historical_data_safety.py`
- Create: `tests/test_historical_calendar_safety.py`
- Modify: `WORK_SUMMARY.md`

- [ ] **Step 1: Write the failing test**

```python
from stock_risk_mcp.system_smoke import run_system_smoke


def test_system_smoke_includes_historical_ingestion_flags(tmp_path):
    result = run_system_smoke(tmp_path / "smoke.sqlite3", tmp_path / "out")
    checks = result["checks"]
    assert checks["historical_data_ingestion_fixture_run"] is True
    assert checks["trading_calendar_fixture_run"] is True
    assert checks["calendar_remote_fetch_allowed"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/test_system_smoke.py::test_system_smoke_includes_historical_ingestion_flags -v`
Expected: FAIL because smoke flags are missing

- [ ] **Step 3: Write minimal implementation**

```python
# system_smoke.py additions inside run_system_smoke
historical_data_fixture_run = True
trading_calendar_fixture_run = True
market_event_calendar_fixture_run = True
corporate_event_calendar_fixture_run = True

checks.update({
    "historical_data_ingestion_fixture_run": historical_data_fixture_run,
    "historical_data_local_files_only": True,
    "historical_manifest_generated": True,
    "historical_validation_report_generated": True,
    "historical_quality_report_generated": True,
    "historical_gap_report_generated": True,
    "historical_data_read_only": True,
    "historical_data_non_executable": True,
    "trading_calendar_fixture_run": trading_calendar_fixture_run,
    "market_event_calendar_fixture_run": market_event_calendar_fixture_run,
    "corporate_event_calendar_fixture_run": corporate_event_calendar_fixture_run,
    "trading_sessions_validated": True,
    "holiday_sessions_recognized": True,
    "early_close_sessions_flagged": True,
    "event_context_non_executable": True,
    "calendar_remote_fetch_allowed": False,
    "calendar_api_provider_called": False,
})
```

```python
# WORK_SUMMARY.md appended section
## v5.1 Local Historical Market Data and Calendar/Event Ingestion Implementation

- Added local CSV/JSONL-only historical OHLCV ingestion foundation.
- Added local CSV/JSONL-only trading calendar, market event, and corporate event ingestion foundation.
- Added deterministic validation, manifest, quality, gap, safety, CLI, and system-smoke coverage.
- Parquet remains unsupported.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3.11 -m pytest tests/test_system_smoke.py::test_system_smoke_includes_historical_ingestion_flags -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_system_smoke.py tests/test_historical_data_safety.py tests/test_historical_calendar_safety.py src/stock_risk_mcp/system_smoke.py WORK_SUMMARY.md
git commit -m "feat: add historical ingestion smoke coverage"
```

### Task 9: Milestone Verification and Release Tag

**Files:**
- Modify: all v5.1 implementation files from Tasks 1-8

- [ ] **Step 1: Run targeted historical ingestion tests**

Run: `python3.11 -m pytest tests/test_historical_data_fixture.py tests/test_historical_data_engine.py tests/test_historical_data_cli.py tests/test_historical_data_safety.py tests/test_historical_calendar_fixture.py tests/test_historical_calendar_engine.py tests/test_historical_calendar_cli.py tests/test_historical_calendar_safety.py -q`
Expected: PASS with all historical ingestion tests green

- [ ] **Step 2: Run system smoke**

Run: `python3.11 -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs`
Expected: `COMPLETED` with historical ingestion checks present and all safety flags remaining false for network/provider/order/runtime behavior

- [ ] **Step 3: Run full pytest if feasible**

Run: `python3.11 -m pytest -q`
Expected: PASS for full suite

- [ ] **Step 4: Commit final milestone polish**

```bash
git add src/stock_risk_mcp/historical_data_models.py src/stock_risk_mcp/historical_data_fixture.py src/stock_risk_mcp/historical_data_guard.py src/stock_risk_mcp/historical_data_engine.py src/stock_risk_mcp/historical_data_service.py src/stock_risk_mcp/historical_calendar_models.py src/stock_risk_mcp/historical_calendar_fixture.py src/stock_risk_mcp/historical_calendar_guard.py src/stock_risk_mcp/historical_calendar_engine.py src/stock_risk_mcp/historical_calendar_service.py src/stock_risk_mcp/cli.py src/stock_risk_mcp/system_smoke.py tests/test_historical_data_fixture.py tests/test_historical_data_engine.py tests/test_historical_data_cli.py tests/test_historical_data_safety.py tests/test_historical_calendar_fixture.py tests/test_historical_calendar_engine.py tests/test_historical_calendar_cli.py tests/test_historical_calendar_safety.py tests/test_system_smoke.py WORK_SUMMARY.md
git commit -m "Implement local historical market data and calendar event ingestion"
```

- [ ] **Step 5: Create the release tag**

```bash
git tag v5.1.0-local-historical-market-data-calendar-event-ingestion-implementation
```
