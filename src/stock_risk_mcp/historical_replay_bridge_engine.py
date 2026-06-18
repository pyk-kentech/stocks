from __future__ import annotations

from datetime import datetime

from stock_risk_mcp.historical_calendar_models import CalendarEventType
from stock_risk_mcp.historical_replay_bridge_fixture import HistoricalReplayBridgeFixture
from stock_risk_mcp.historical_replay_bridge_guard import (
    _is_allowed_safe_boundary_key,
    _iter_dict_keys,
    _iter_string_values,
    validate_historical_replay_bridge_fixture_safety,
    validate_historical_replay_metadata_safety,
    validate_historical_replay_source_type,
)
from stock_risk_mcp.historical_replay_bridge_models import (
    HistoricalReplayBridgeGapCategory,
    HistoricalReplayBridgeGapEntry,
    HistoricalReplayBridgeGapReport,
    HistoricalReplayEvent,
    HistoricalReplayEventContext,
    HistoricalReplayEventContextAttachmentReport,
    HistoricalReplayEventStream,
    HistoricalReplayWindow,
    HistoricalReplayWindowBundle,
)
from stock_risk_mcp.historical_scanner_replay_models import (
    HistoricalScannerReplayCandidateSeed,
    HistoricalScannerReplayContext,
    HistoricalScannerReplayGapEntry,
    HistoricalScannerReplayGapReport,
    HistoricalScannerReplayInput,
    HistoricalScannerReplayReport,
)
from stock_risk_mcp.strategy_track_models import StrategyTrack


_SUPPORTED_MARKET_EVENT_TYPES = {
    CalendarEventType.OPTIONS_EXPIRATION,
    CalendarEventType.FUTURES_EXPIRATION,
    CalendarEventType.QUADRUPLE_WITCHING,
    CalendarEventType.FOMC_DECISION,
    CalendarEventType.CPI_RELEASE,
    CalendarEventType.PPI_RELEASE,
    CalendarEventType.JOBS_REPORT,
    CalendarEventType.ELECTION_DAY,
}
_SUPPORTED_CORPORATE_EVENT_TYPES = {
    CalendarEventType.EARNINGS_BEFORE_OPEN,
    CalendarEventType.EARNINGS_AFTER_CLOSE,
    CalendarEventType.DIVIDEND_EX_DATE,
    CalendarEventType.SPLIT_EFFECTIVE_DATE,
    CalendarEventType.CORPORATE_ACTION,
}


def build_historical_replay_event_stream(fixture: HistoricalReplayBridgeFixture) -> HistoricalReplayEventStream:
    _validate_bridge_fixture_for_conversion(fixture)
    validate_historical_replay_bridge_fixture_safety(fixture)

    market_snapshot = fixture.historical_market_data_snapshot
    calendar_snapshot = fixture.historical_calendar_event_snapshot
    manifest_ids = _manifest_ids(fixture)
    audit_record_ids = [record.audit_record_id for record in market_snapshot.audit_records]
    provider_provenance_ids = [market_snapshot.provider_provenance.provenance_id]
    bridge_input_id = fixture.fixture_id
    records = sorted(
        market_snapshot.records,
        key=lambda record: (record.timestamp, record.symbol, record.market, record.source_id, record.ingestion_batch_id),
    )

    events = []
    seen_replay_event_ids: set[str] = set()
    for index, record in enumerate(records, start=1):
        replay_event_id = _build_replay_event_id(bridge_input_id=bridge_input_id, record=record, ordinal=index)
        if replay_event_id in seen_replay_event_ids:
            raise ValueError("duplicate replay event")
        seen_replay_event_ids.add(replay_event_id)
        events.append(
            HistoricalReplayEvent.model_validate(
                {
                    "replay_event_id": replay_event_id,
                    "bridge_input_id": bridge_input_id,
                    "symbol": record.symbol,
                    "market": record.market,
                    "session_date": record.timestamp.date().isoformat(),
                    "replay_timestamp": record.timestamp.isoformat(),
                    "source_record_id": _build_source_record_id(record),
                    "source_source_id": record.source_id,
                    "currency": record.currency,
                    "timezone": record.timezone,
                    "source_manifest_ids": manifest_ids,
                    "source_audit_record_ids": audit_record_ids,
                    "provider_provenance_ids": provider_provenance_ids,
                    "historical_market_snapshot_id": market_snapshot.snapshot_id,
                    "historical_calendar_snapshot_id": calendar_snapshot.snapshot_id if calendar_snapshot else None,
                }
            )
        )

    stream = HistoricalReplayEventStream.model_validate(
        {
            "stream_id": f"{bridge_input_id}-stream",
            "bridge_input_id": bridge_input_id,
            "strategy_track": fixture.bridge_config.strategy_track,
            "market_profile_id": market_snapshot.source_descriptor.market_profile_id,
            "source_type": getattr(market_snapshot.source_descriptor.source_type, "value", market_snapshot.source_descriptor.source_type),
            "source_file_path": market_snapshot.source_descriptor.local_file_path,
            "source_currency": market_snapshot.source_descriptor.currency,
            "source_timezone": market_snapshot.source_descriptor.timezone,
            "source_vendor_name": market_snapshot.source_descriptor.source_vendor_name,
            "source_notes": market_snapshot.provider_provenance.notes,
            "historical_market_snapshot_id": market_snapshot.snapshot_id,
            "historical_calendar_snapshot_id": calendar_snapshot.snapshot_id if calendar_snapshot else None,
            "source_manifest_ids": manifest_ids,
            "source_audit_record_ids": audit_record_ids,
            "provider_provenance_ids": provider_provenance_ids,
            "events": [event.model_dump(mode="json") for event in events],
        }
    )
    validate_historical_replay_event_stream(stream)
    return stream


def validate_historical_replay_event_stream(stream: HistoricalReplayEventStream) -> None:
    if not _clean_text(stream.historical_market_snapshot_id):
        raise ValueError("missing market snapshot")
    if not stream.source_manifest_ids or any(not _clean_text(value) for value in stream.source_manifest_ids):
        raise ValueError("missing source manifest")
    if stream.strategy_track != StrategyTrack.DOMESTIC_KR:
        raise ValueError("unsupported strategy track")
    if _clean_text(stream.market_profile_id).upper() != "KRX":
        raise ValueError("unsupported market")
    if not _clean_text(stream.source_currency):
        raise ValueError("currency mismatch")
    if not _clean_text(stream.source_timezone):
        raise ValueError("timezone mismatch")

    validate_historical_replay_source_type(stream.source_type, context="historical replay event stream")
    validate_historical_replay_metadata_safety(stream.model_dump(mode="json"), context="historical replay event stream")

    previous_key: tuple | None = None
    seen_event_ids: set[str] = set()
    seen_source_record_ids: set[str] = set()
    for event in stream.events:
        if event.replay_event_id in seen_event_ids:
            raise ValueError("duplicate replay event")
        seen_event_ids.add(event.replay_event_id)
        if not _clean_text(event.source_record_id):
            raise ValueError("duplicate replay event")
        if event.source_record_id in seen_source_record_ids:
            raise ValueError("duplicate replay event")
        seen_source_record_ids.add(event.source_record_id)
        if _clean_text(event.market).upper() != _clean_text(stream.market_profile_id).upper():
            raise ValueError("unsupported market")
        if _clean_text(event.currency).upper() != _clean_text(stream.source_currency).upper():
            raise ValueError("currency mismatch")
        if _clean_text(event.timezone) != _clean_text(stream.source_timezone):
            raise ValueError("timezone mismatch")

        event_key = (event.replay_timestamp, event.symbol, event.market, event.replay_event_id)
        if previous_key is not None and event_key < previous_key:
            raise ValueError("out-of-order replay event")
        previous_key = event_key


def build_historical_replay_windows(
    stream: HistoricalReplayEventStream,
    fixture: HistoricalReplayBridgeFixture,
    *,
    session_window_sizes: tuple[int, ...] = (1, 3, 5),
) -> HistoricalReplayWindowBundle:
    validate_historical_replay_event_stream(stream)

    requested_window_sizes = sorted({int(size) for size in session_window_sizes if int(size) > 0})
    if not requested_window_sizes:
        raise ValueError("session_window_sizes must contain at least one positive integer")

    calendar_snapshot = fixture.historical_calendar_event_snapshot
    if calendar_snapshot is None:
        if fixture.bridge_config.allow_report_only_degraded_calendar:
            return _degraded_window_bundle(
                stream,
                requested_window_sizes,
                gap_entries=[
                    _gap_entry(
                        stream,
                        gap_id_suffix="missing-trading-calendar",
                        gap_category=HistoricalReplayBridgeGapCategory.REPLAY_MISSING_TRADING_CALENDAR,
                        severity="REPORT_ONLY",
                        message="missing trading calendar",
                    ),
                    _gap_entry(
                        stream,
                        gap_id_suffix="window-degraded-report-only",
                        gap_category=HistoricalReplayBridgeGapCategory.REPLAY_WINDOW_DEGRADED_REPORT_ONLY,
                        severity="REPORT_ONLY",
                        message="window generation downgraded to report-only because trading calendar is unavailable",
                    ),
                ],
            )
        raise ValueError("missing trading calendar")

    if _clean_text(calendar_snapshot.manifest.timezone) != _clean_text(stream.source_timezone):
        return _fail_or_degrade_window_build(
            fixture,
            stream,
            requested_window_sizes,
            gap_id_suffix="calendar-timezone-mismatch",
            gap_category=HistoricalReplayBridgeGapCategory.REPLAY_CALENDAR_TIMEZONE_MISMATCH,
            message="calendar timezone mismatch",
        )

    if _clean_text(calendar_snapshot.manifest.market_profile_id).upper() != _clean_text(stream.market_profile_id).upper():
        return _fail_or_degrade_window_build(
            fixture,
            stream,
            requested_window_sizes,
            gap_id_suffix="market-profile-mismatch",
            gap_category=HistoricalReplayBridgeGapCategory.REPLAY_MARKET_PROFILE_MISMATCH,
            message="market profile mismatch",
        )

    ordered_sessions = sorted(calendar_snapshot.session_records, key=lambda record: (record.date, record.market, record.source_id))
    if any(_clean_text(session.timezone) != _clean_text(stream.source_timezone) for session in ordered_sessions):
        return _fail_or_degrade_window_build(
            fixture,
            stream,
            requested_window_sizes,
            gap_id_suffix="calendar-session-timezone-mismatch",
            gap_category=HistoricalReplayBridgeGapCategory.REPLAY_CALENDAR_TIMEZONE_MISMATCH,
            message="calendar timezone mismatch",
        )
    if any(_clean_text(session.market).upper() != _clean_text(stream.market_profile_id).upper() for session in ordered_sessions):
        return _fail_or_degrade_window_build(
            fixture,
            stream,
            requested_window_sizes,
            gap_id_suffix="calendar-session-market-profile-mismatch",
            gap_category=HistoricalReplayBridgeGapCategory.REPLAY_MARKET_PROFILE_MISMATCH,
            message="market profile mismatch",
        )
    gap_entries: list[HistoricalReplayBridgeGapEntry] = []
    if ordered_sessions != list(calendar_snapshot.session_records):
        gap_entries.append(
            _gap_entry(
                stream,
                gap_id_suffix="window-out-of-order",
                gap_category=HistoricalReplayBridgeGapCategory.REPLAY_WINDOW_OUT_OF_ORDER,
                severity="REPORT_ONLY",
                message="calendar sessions were out of order and were normalized before window generation",
            )
        )

    trading_sessions = [session for session in ordered_sessions if session.is_trading_day]
    trading_dates = [session.date for session in trading_sessions]
    events_by_session_date: dict = {}
    for event in stream.events:
        events_by_session_date.setdefault(event.session_date, []).append(event)

    _append_lineage_gap_if_needed(stream, gap_entries)
    _append_calendar_context_gaps(stream, ordered_sessions, gap_entries)
    _append_invalid_event_session_gaps(stream, ordered_sessions, events_by_session_date, gap_entries)
    _append_missing_trading_session_gaps(stream, trading_dates, events_by_session_date, gap_entries)
    _fail_closed_for_blocking_gaps(gap_entries)
    event_context_plan = _build_event_context_plan(stream, fixture, ordered_sessions, gap_entries)

    windows: list[HistoricalReplayWindow] = []
    trading_date_positions = {session.date: index for index, session in enumerate(trading_sessions)}
    for session in trading_sessions:
        events_for_anchor = events_by_session_date.get(session.date, [])
        if not events_for_anchor:
            continue
        anchor_position = trading_date_positions[session.date]
        for size in requested_window_sizes:
            start_position = anchor_position - size + 1
            if start_position < 0:
                continue
            window_sessions = trading_sessions[start_position : anchor_position + 1]
            window_dates = [window_session.date for window_session in window_sessions]
            window_events = [
                event
                for event in stream.events
                if event.session_date in set(window_dates)
            ]
            window_gap_categories = []
            window_warnings = []
            if any(window_session.is_early_close for window_session in window_sessions):
                window_gap_categories.append(HistoricalReplayBridgeGapCategory.REPLAY_EARLY_CLOSE_SESSION_FLAGGED)
                window_warnings.append("window includes an early-close trading session")
            window_id = f"{stream.stream_id}-{session.date.isoformat()}-{size:02d}S"
            market_event_contexts = _materialize_window_event_contexts(
                [
                    context
                    for context in _collect_window_event_contexts(event_context_plan["market_by_date"], window_dates)
                    if context.get("symbol") is None or context["symbol"] in {event.symbol for event in window_events}
                ],
                window_id=window_id,
            )
            corporate_event_contexts = _materialize_window_event_contexts(
                [
                    context
                    for context in _collect_window_event_contexts(event_context_plan["corporate_by_date"], window_dates)
                    if context["symbol"] in {event.symbol for event in window_events}
                ],
                window_id=window_id,
            )
            windows.append(
                HistoricalReplayWindow.model_validate(
                    {
                        "window_id": window_id,
                        "replay_event_stream_id": stream.stream_id,
                        "bridge_input_id": stream.bridge_input_id,
                        "strategy_track": stream.strategy_track,
                        "market_profile_id": stream.market_profile_id,
                        "session_date": session.date.isoformat(),
                        "window_size_sessions": size,
                        "window_session_dates": [window_date.isoformat() for window_date in window_dates],
                        "event_ids": [event.replay_event_id for event in window_events],
                        "market_event_contexts": market_event_contexts,
                        "corporate_event_contexts": corporate_event_contexts,
                        "early_close": any(window_session.is_early_close for window_session in window_sessions),
                        "gap_categories": [gap_category.value for gap_category in window_gap_categories],
                        "warnings": window_warnings,
                        "historical_market_snapshot_id": stream.historical_market_snapshot_id,
                        "historical_calendar_snapshot_id": stream.historical_calendar_snapshot_id,
                        "source_manifest_ids": stream.source_manifest_ids,
                        "source_audit_record_ids": stream.source_audit_record_ids,
                        "provider_provenance_ids": stream.provider_provenance_ids,
                        "report_only": True,
                        "read_only": stream.read_only,
                        "non_executable": stream.non_executable,
                        "local_file_only": stream.local_file_only,
                        "no_network": stream.no_network,
                        "no_provider_api": stream.no_provider_api,
                        "no_order": stream.no_order,
                        "no_llm_runtime": stream.no_llm_runtime,
                        "no_ml_training": stream.no_ml_training,
                    }
                )
            )

    windows.sort(key=lambda window: (window.session_date, window.window_size_sessions, window.window_id))
    gap_report = _build_gap_report(stream, gap_entries)
    event_context_report = _build_event_context_attachment_report(stream, windows)
    bundle = HistoricalReplayWindowBundle.model_validate(
        {
            "window_bundle_id": f"{stream.stream_id}-window-bundle",
            "replay_event_stream_id": stream.stream_id,
            "bridge_input_id": stream.bridge_input_id,
            "strategy_track": stream.strategy_track,
            "market_profile_id": stream.market_profile_id,
            "requested_window_sizes": requested_window_sizes,
            "historical_market_snapshot_id": stream.historical_market_snapshot_id,
            "historical_calendar_snapshot_id": stream.historical_calendar_snapshot_id,
            "source_manifest_ids": stream.source_manifest_ids,
            "source_audit_record_ids": stream.source_audit_record_ids,
            "provider_provenance_ids": stream.provider_provenance_ids,
            "windows": [window.model_dump(mode="json") for window in windows],
            "event_context_report": event_context_report.model_dump(mode="json"),
            "gap_report": gap_report.model_dump(mode="json"),
            "degraded_report_only": False,
            "read_only": stream.read_only,
            "non_executable": stream.non_executable,
            "local_file_only": stream.local_file_only,
            "no_network": stream.no_network,
            "no_provider_api": stream.no_provider_api,
            "no_order": stream.no_order,
            "no_llm_runtime": stream.no_llm_runtime,
            "no_ml_training": stream.no_ml_training,
        }
    )
    return bundle


def build_historical_scanner_replay_input(
    stream: HistoricalReplayEventStream | None,
    window_bundle: HistoricalReplayWindowBundle | None,
):
    gap_categories: list[str] = []
    gap_entries: list[HistoricalScannerReplayGapEntry] = []

    if stream is None:
        gap_categories.append("SCANNER_REPLAY_MISSING_EVENT_STREAM")
        return None, _empty_scanner_report(), _scanner_gap_report(
            replay_input_id="MISSING-REPLAY-INPUT",
            historical_calendar_snapshot_id=None,
            source_manifest_ids=[],
            source_audit_record_ids=[],
            provider_provenance_ids=[],
            gap_categories=gap_categories,
            gap_entries=gap_entries,
        )

    if window_bundle is None or not window_bundle.windows:
        gap_categories.append("SCANNER_REPLAY_MISSING_WINDOW")
        return None, _empty_scanner_report(
            replay_input_id=f"{stream.stream_id}-SCANNER-INPUT",
            strategy_track=stream.strategy_track,
            historical_calendar_snapshot_id=stream.historical_calendar_snapshot_id,
            source_manifest_ids=stream.source_manifest_ids,
            source_audit_record_ids=stream.source_audit_record_ids,
            provider_provenance_ids=stream.provider_provenance_ids,
        ), _scanner_gap_report(
            replay_input_id=f"{stream.stream_id}-SCANNER-INPUT",
            historical_calendar_snapshot_id=stream.historical_calendar_snapshot_id,
            source_manifest_ids=stream.source_manifest_ids,
            source_audit_record_ids=stream.source_audit_record_ids,
            provider_provenance_ids=stream.provider_provenance_ids,
            gap_categories=gap_categories,
            gap_entries=gap_entries,
        )

    replay_input_id = f"{stream.stream_id}-SCANNER-INPUT"
    gap_categories.extend(_scanner_blocking_categories(stream, window_bundle))
    if not stream.source_manifest_ids:
        gap_categories.append("SCANNER_REPLAY_SOURCE_LINEAGE_MISSING")

    categories = _unique_preserve_order(gap_categories)
    blocking_categories = {
        "SCANNER_REPLAY_MISSING_EVENT_STREAM",
        "SCANNER_REPLAY_MISSING_WINDOW",
        "SCANNER_REPLAY_MISSING_CONTEXT",
        "SCANNER_REPLAY_MISSING_STRATEGY_TRACK",
        "SCANNER_REPLAY_MISSING_MARKET_PROFILE",
        "SCANNER_REPLAY_UNSUPPORTED_TRACK",
        "SCANNER_REPLAY_UNSUPPORTED_MARKET",
        "SCANNER_REPLAY_SAFETY_MARKER_MISSING",
        "SCANNER_REPLAY_ORDER_FIELD_DETECTED",
        "SCANNER_REPLAY_EXECUTION_FIELD_DETECTED",
        "SCANNER_REPLAY_BUY_SELL_WORDING_DETECTED",
        "SCANNER_REPLAY_REMOTE_SOURCE_NOT_ALLOWED",
        "SCANNER_REPLAY_API_SOURCE_NOT_ALLOWED",
        "SCANNER_REPLAY_NETWORK_SOURCE_NOT_ALLOWED",
        "SCANNER_REPLAY_PROVIDER_SOURCE_NOT_ALLOWED",
        "SCANNER_REPLAY_LLM_METADATA_NOT_ALLOWED",
        "SCANNER_REPLAY_ML_TRAINING_TRIGGER_NOT_ALLOWED",
        "SCANNER_REPLAY_CRAWLER_TRIGGER_NOT_ALLOWED",
        "SCANNER_REPLAY_LIVE_PROD_NOT_ALLOWED",
        "SCANNER_REPLAY_PARQUET_NOT_ALLOWED",
    }
    has_blocking_gap = any(category in blocking_categories for category in categories)

    scanner_report = _empty_scanner_report(
        replay_input_id=replay_input_id,
        strategy_track=stream.strategy_track,
        historical_calendar_snapshot_id=stream.historical_calendar_snapshot_id,
        source_manifest_ids=stream.source_manifest_ids,
        source_audit_record_ids=stream.source_audit_record_ids,
        provider_provenance_ids=stream.provider_provenance_ids,
    )

    if has_blocking_gap:
        gap_report = _scanner_gap_report(
            replay_input_id=replay_input_id,
            historical_calendar_snapshot_id=stream.historical_calendar_snapshot_id,
            source_manifest_ids=stream.source_manifest_ids,
            source_audit_record_ids=stream.source_audit_record_ids,
            provider_provenance_ids=stream.provider_provenance_ids,
            gap_categories=categories,
            gap_entries=gap_entries,
        )
        return None, scanner_report, gap_report

    scanner_input = _build_scanner_input(stream, window_bundle, replay_input_id, categories)
    categories.extend(["SCANNER_REPLAY_INPUT_GENERATED", "SCANNER_REPLAY_REPORT_ONLY"])
    scanner_report = HistoricalScannerReplayReport.model_validate(
        {
            "report_id": f"{replay_input_id}-REPORT",
            "replay_input_id": replay_input_id,
            "strategy_track": stream.strategy_track,
            "historical_calendar_snapshot_id": stream.historical_calendar_snapshot_id,
            "source_manifest_ids": stream.source_manifest_ids,
            "source_audit_record_ids": stream.source_audit_record_ids,
            "provider_provenance_ids": stream.provider_provenance_ids,
            "candidate_seed_count": len(scanner_input.candidate_seeds),
            "scanner_window_count": len(scanner_input.scanner_window_ids),
            "warnings": sorted({warning for window in window_bundle.windows for warning in window.warnings}),
            "report_only": True,
            "read_only": True,
            "non_executable": True,
            "local_file_only": True,
            "no_network": True,
            "no_provider_api": True,
            "no_order": True,
            "no_llm_runtime": True,
            "no_ml_training": True,
        }
    )
    gap_report = _scanner_gap_report(
        replay_input_id=replay_input_id,
        historical_calendar_snapshot_id=stream.historical_calendar_snapshot_id,
        source_manifest_ids=stream.source_manifest_ids,
        source_audit_record_ids=stream.source_audit_record_ids,
        provider_provenance_ids=stream.provider_provenance_ids,
        gap_categories=categories,
        gap_entries=gap_entries,
    )
    return scanner_input, scanner_report, gap_report


def _validate_bridge_fixture_for_conversion(fixture: HistoricalReplayBridgeFixture) -> None:
    market_snapshot = fixture.historical_market_data_snapshot
    if market_snapshot is None:
        raise ValueError("missing market snapshot")

    strategy_track = getattr(fixture.bridge_config, "strategy_track", None)
    if strategy_track is None:
        raise ValueError("missing strategy track")
    if strategy_track != StrategyTrack.DOMESTIC_KR:
        raise ValueError("unsupported strategy track")

    market_profile_id = _clean_text(market_snapshot.source_descriptor.market_profile_id)
    if not market_profile_id:
        raise ValueError("missing market profile")
    if market_profile_id != "KRX":
        raise ValueError("unsupported market")

    manifest_ids = _manifest_ids(fixture)
    if not manifest_ids or any(not manifest_id for manifest_id in manifest_ids):
        raise ValueError("missing source manifest")

    if not market_snapshot.records:
        raise ValueError("missing market snapshot")

    source_currency = _clean_text(market_snapshot.source_descriptor.currency).upper()
    manifest_currency = _clean_text(market_snapshot.manifest.currency)
    if not source_currency or not manifest_currency:
        raise ValueError("currency mismatch")

    source_timezone = _clean_text(market_snapshot.source_descriptor.timezone)
    manifest_timezone = _clean_text(market_snapshot.manifest.timezone)
    if not source_timezone or not manifest_timezone:
        raise ValueError("timezone mismatch")

    seen_record_keys: set[tuple] = set()
    for record in market_snapshot.records:
        record_key = (record.timestamp, record.symbol, record.market, record.source_id, record.ingestion_batch_id)
        if record_key in seen_record_keys:
            raise ValueError("duplicate replay event")
        seen_record_keys.add(record_key)

        if _clean_text(record.market).upper() != market_profile_id:
            raise ValueError("unsupported market")
        if _clean_text(record.currency).upper() != source_currency:
            raise ValueError("currency mismatch")
        if _clean_text(record.currency).upper() != manifest_currency.upper():
            raise ValueError("currency mismatch")
        if _clean_text(record.timezone) != source_timezone:
            raise ValueError("timezone mismatch")
        if _clean_text(record.timezone) != manifest_timezone:
            raise ValueError("timezone mismatch")


def _manifest_ids(fixture: HistoricalReplayBridgeFixture) -> list[str]:
    manifest_ids = [_clean_text(fixture.historical_market_data_snapshot.manifest.manifest_id).upper()]
    calendar_snapshot = fixture.historical_calendar_event_snapshot
    if calendar_snapshot is not None:
        manifest_ids.append(_clean_text(calendar_snapshot.manifest.calendar_manifest_id).upper())
    return manifest_ids


def _build_replay_event_id(*, bridge_input_id: str, record, ordinal: int) -> str:
    timestamp_fragment = record.timestamp.strftime("%Y%m%dT%H%M%S%z")
    return (
        f"{bridge_input_id}-{timestamp_fragment}-{record.symbol}-{record.market}-"
        f"{record.source_id}-{record.ingestion_batch_id}-{ordinal:06d}"
    )


def _build_source_record_id(record) -> str:
    timestamp_fragment = record.timestamp.strftime("%Y%m%dT%H%M%S%z")
    return f"{record.symbol}-{record.market}-{timestamp_fragment}-{record.source_id}-{record.ingestion_batch_id}"


def _clean_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _build_gap_report(
    stream: HistoricalReplayEventStream,
    gap_entries: list[HistoricalReplayBridgeGapEntry],
) -> HistoricalReplayBridgeGapReport:
    categories = sorted({gap_entry.gap_category for gap_entry in gap_entries}, key=lambda item: item.value)
    blocking_gap_count = sum(1 for gap_entry in gap_entries if _clean_text(gap_entry.severity).upper() == "BLOCKING")
    report_only_gap_count = sum(1 for gap_entry in gap_entries if _clean_text(gap_entry.severity).upper() == "REPORT_ONLY")
    return HistoricalReplayBridgeGapReport.model_validate(
        {
            "gap_report_id": f"{stream.stream_id}-window-gap-report",
            "bridge_input_id": stream.bridge_input_id,
            "source_manifest_ids": stream.source_manifest_ids,
            "source_audit_record_ids": stream.source_audit_record_ids,
            "provider_provenance_ids": stream.provider_provenance_ids,
            "historical_market_snapshot_id": stream.historical_market_snapshot_id,
            "historical_calendar_snapshot_id": stream.historical_calendar_snapshot_id,
            "gap_categories": [category.value for category in categories],
            "blocking_gap_count": blocking_gap_count,
            "report_only_gap_count": report_only_gap_count,
            "gaps": [gap_entry.model_dump(mode="json") for gap_entry in gap_entries],
            "read_only": stream.read_only,
            "non_executable": stream.non_executable,
            "local_file_only": stream.local_file_only,
            "no_network": stream.no_network,
            "no_provider_api": stream.no_provider_api,
            "no_order": stream.no_order,
            "no_llm_runtime": stream.no_llm_runtime,
            "no_ml_training": stream.no_ml_training,
        }
    )


def _gap_entry(
    stream: HistoricalReplayEventStream,
    *,
    gap_id_suffix: str,
    gap_category: HistoricalReplayBridgeGapCategory,
    severity: str,
    message: str,
) -> HistoricalReplayBridgeGapEntry:
    return HistoricalReplayBridgeGapEntry.model_validate(
        {
            "gap_id": f"{stream.stream_id}-{gap_id_suffix}",
            "gap_category": gap_category.value,
            "severity": severity,
            "message": message,
            "source_manifest_id": stream.source_manifest_ids[0] if stream.source_manifest_ids else None,
            "source_audit_record_id": stream.source_audit_record_ids[0] if stream.source_audit_record_ids else None,
            "provider_provenance_id": stream.provider_provenance_ids[0] if stream.provider_provenance_ids else None,
        }
    )


def _append_calendar_context_gaps(
    stream: HistoricalReplayEventStream,
    ordered_sessions,
    gap_entries: list[HistoricalReplayBridgeGapEntry],
) -> None:
    seen_holiday_dates: set[str] = set()
    seen_early_close_dates: set[str] = set()
    for session in ordered_sessions:
        session_date = session.date.isoformat()
        if session.is_holiday and session_date not in seen_holiday_dates:
            gap_entries.append(
                _gap_entry(
                    stream,
                    gap_id_suffix=f"holiday-{session_date}",
                    gap_category=HistoricalReplayBridgeGapCategory.REPLAY_HOLIDAY_SESSION_RECOGNIZED,
                    severity="REPORT_ONLY",
                    message=f"calendar holiday recognized for {session_date}",
                )
            )
            seen_holiday_dates.add(session_date)
        if session.is_early_close and session_date not in seen_early_close_dates:
            gap_entries.append(
                _gap_entry(
                    stream,
                    gap_id_suffix=f"early-close-{session_date}",
                    gap_category=HistoricalReplayBridgeGapCategory.REPLAY_EARLY_CLOSE_SESSION_FLAGGED,
                    severity="REPORT_ONLY",
                    message=f"early-close session flagged for {session_date}",
                )
            )
            seen_early_close_dates.add(session_date)


def _append_missing_trading_session_gaps(
    stream: HistoricalReplayEventStream,
    trading_dates,
    events_by_session_date,
    gap_entries: list[HistoricalReplayBridgeGapEntry],
) -> None:
    if not trading_dates:
        return
    for trading_date in trading_dates:
        if events_by_session_date.get(trading_date):
            continue
        gap_entries.append(
            _gap_entry(
                stream,
                gap_id_suffix=f"missing-trading-session-{trading_date.isoformat()}",
                gap_category=HistoricalReplayBridgeGapCategory.REPLAY_MISSING_TRADING_SESSION,
                severity="BLOCKING",
                message=f"missing trading session for open calendar day {trading_date.isoformat()}",
            )
        )


def _append_invalid_event_session_gaps(
    stream: HistoricalReplayEventStream,
    ordered_sessions,
    events_by_session_date,
    gap_entries: list[HistoricalReplayBridgeGapEntry],
) -> None:
    valid_open_sessions = {
        session.date for session in ordered_sessions if session.is_trading_day and not session.is_holiday
    }
    known_session_dates = {session.date for session in ordered_sessions}
    for event_session_date in sorted(events_by_session_date):
        if event_session_date in valid_open_sessions:
            continue
        if event_session_date in known_session_dates:
            message = f"event falls on non-trading calendar session {event_session_date.isoformat()}"
        else:
            message = f"event session date {event_session_date.isoformat()} is absent from trading calendar"
        gap_entries.append(
            _gap_entry(
                stream,
                gap_id_suffix=f"invalid-event-session-{event_session_date.isoformat()}",
                gap_category=HistoricalReplayBridgeGapCategory.REPLAY_MISSING_TRADING_SESSION,
                severity="BLOCKING",
                message=message,
            )
        )


def _fail_closed_for_blocking_gaps(gap_entries: list[HistoricalReplayBridgeGapEntry]) -> None:
    blocking_gaps = [gap_entry for gap_entry in gap_entries if _clean_text(gap_entry.severity).upper() == "BLOCKING"]
    if not blocking_gaps:
        return
    messages = ", ".join(gap_entry.message for gap_entry in blocking_gaps)
    raise ValueError(f"blocking replay window gaps detected: {messages}")


def _append_lineage_gap_if_needed(
    stream: HistoricalReplayEventStream,
    gap_entries: list[HistoricalReplayBridgeGapEntry],
) -> None:
    if stream.source_manifest_ids and stream.provider_provenance_ids and _clean_text(stream.historical_market_snapshot_id):
        return
    gap_entries.append(
        _gap_entry(
            stream,
            gap_id_suffix="window-source-lineage-missing",
            gap_category=HistoricalReplayBridgeGapCategory.REPLAY_WINDOW_SOURCE_LINEAGE_MISSING,
            severity="REPORT_ONLY",
            message="window source lineage is incomplete",
        )
    )


def _fail_or_degrade_window_build(
    fixture: HistoricalReplayBridgeFixture,
    stream: HistoricalReplayEventStream,
    requested_window_sizes: list[int],
    *,
    gap_id_suffix: str,
    gap_category: HistoricalReplayBridgeGapCategory,
    message: str,
) -> HistoricalReplayWindowBundle:
    if fixture.bridge_config.allow_report_only_degraded_calendar:
        return _degraded_window_bundle(
            stream,
            requested_window_sizes,
            gap_entries=[
                _gap_entry(
                    stream,
                    gap_id_suffix=gap_id_suffix,
                    gap_category=gap_category,
                    severity="REPORT_ONLY",
                    message=message,
                ),
                _gap_entry(
                    stream,
                    gap_id_suffix="window-degraded-report-only",
                    gap_category=HistoricalReplayBridgeGapCategory.REPLAY_WINDOW_DEGRADED_REPORT_ONLY,
                    severity="REPORT_ONLY",
                    message=f"window generation downgraded to report-only because {message}",
                ),
            ],
        )
    raise ValueError(message)


def _degraded_window_bundle(
    stream: HistoricalReplayEventStream,
    requested_window_sizes: list[int],
    *,
    gap_entries: list[HistoricalReplayBridgeGapEntry],
) -> HistoricalReplayWindowBundle:
    gap_report = _build_gap_report(stream, gap_entries)
    return HistoricalReplayWindowBundle.model_validate(
        {
            "window_bundle_id": f"{stream.stream_id}-window-bundle",
            "replay_event_stream_id": stream.stream_id,
            "bridge_input_id": stream.bridge_input_id,
            "strategy_track": stream.strategy_track,
            "market_profile_id": stream.market_profile_id,
            "requested_window_sizes": requested_window_sizes,
            "historical_market_snapshot_id": stream.historical_market_snapshot_id,
            "historical_calendar_snapshot_id": stream.historical_calendar_snapshot_id,
            "source_manifest_ids": stream.source_manifest_ids,
            "source_audit_record_ids": stream.source_audit_record_ids,
            "provider_provenance_ids": stream.provider_provenance_ids,
            "windows": [],
            "event_context_report": _build_event_context_attachment_report(stream, []).model_dump(mode="json"),
            "gap_report": gap_report.model_dump(mode="json"),
            "degraded_report_only": True,
            "read_only": stream.read_only,
            "non_executable": stream.non_executable,
            "local_file_only": stream.local_file_only,
            "no_network": stream.no_network,
            "no_provider_api": stream.no_provider_api,
            "no_order": stream.no_order,
            "no_llm_runtime": stream.no_llm_runtime,
            "no_ml_training": stream.no_ml_training,
        }
    )


def _build_event_context_plan(
    stream: HistoricalReplayEventStream,
    fixture: HistoricalReplayBridgeFixture,
    ordered_sessions,
    gap_entries: list[HistoricalReplayBridgeGapEntry],
) -> dict[str, dict]:
    calendar_snapshot = fixture.historical_calendar_event_snapshot
    if calendar_snapshot is None:
        return {"market_by_date": {}, "corporate_by_date": {}}

    known_session_dates = {session.date for session in ordered_sessions}
    trading_session_dates = [session.date for session in ordered_sessions if session.is_trading_day and not session.is_holiday]
    _validate_market_event_context_records(stream, fixture, calendar_snapshot.market_events, gap_entries)
    _append_corporate_event_context_gaps(
        stream,
        calendar_snapshot.corporate_events,
        known_session_dates,
        trading_session_dates,
        gap_entries,
    )

    market_by_date: dict = {}
    for market_event in calendar_snapshot.market_events:
        context_payloads = _build_market_event_context_payload(stream, market_event, gap_entries)
        if not context_payloads:
            continue
        market_by_date.setdefault(market_event.event_date, []).extend(context_payloads)

    corporate_by_date: dict = {}
    for corporate_event in calendar_snapshot.corporate_events:
        effective_session_date = _resolve_corporate_event_session_date(corporate_event, trading_session_dates)
        context_payload = _build_corporate_event_context_payload(
            stream,
            corporate_event,
            trading_session_dates,
            gap_entries,
        )
        if context_payload is None or effective_session_date is None:
            continue
        corporate_by_date.setdefault(effective_session_date, []).append(context_payload)

    return {"market_by_date": market_by_date, "corporate_by_date": corporate_by_date}


def _validate_market_event_context_records(
    stream: HistoricalReplayEventStream,
    fixture: HistoricalReplayBridgeFixture,
    market_events,
    gap_entries: list[HistoricalReplayBridgeGapEntry],
) -> None:
    seen_event_ids: set[str] = set()
    previous_key: tuple | None = None
    for market_event in market_events:
        event_id = _clean_text(market_event.event_id).upper()
        if event_id in seen_event_ids:
            raise ValueError("duplicate replay event context")
        seen_event_ids.add(event_id)
        event_key = (
            market_event.event_date,
            market_event.event_time.isoformat() if market_event.event_time else "",
            event_id,
        )
        if previous_key is not None and event_key < previous_key:
            raise ValueError("out-of-order replay event context")
        previous_key = event_key
        if market_event.event_type not in _SUPPORTED_MARKET_EVENT_TYPES:
            gap_entries.append(
                _gap_entry(
                    stream,
                    gap_id_suffix=f"unsupported-market-event-{event_id}",
                    gap_category=HistoricalReplayBridgeGapCategory.REPLAY_UNSUPPORTED_EVENT_CONTEXT,
                    severity="REPORT_ONLY",
                    message=f"unsupported market event context type {market_event.event_type.value} for {event_id}",
                )
            )
        if _clean_text(market_event.timezone) != _clean_text(stream.source_timezone):
            gap_entries.append(
                _gap_entry(
                    stream,
                    gap_id_suffix=f"market-event-timezone-{event_id}",
                    gap_category=HistoricalReplayBridgeGapCategory.REPLAY_CALENDAR_TIMEZONE_MISMATCH,
                    severity="REPORT_ONLY",
                    message=f"market event timezone mismatch for {event_id}",
                )
            )
        if _clean_text(market_event.market).upper() != _clean_text(stream.market_profile_id).upper() or (
            market_event.affected_market and _clean_text(market_event.affected_market).upper() != _clean_text(stream.market_profile_id).upper()
        ):
            gap_entries.append(
                _gap_entry(
                    stream,
                    gap_id_suffix=f"market-event-market-mismatch-{event_id}",
                    gap_category=HistoricalReplayBridgeGapCategory.REPLAY_MARKET_PROFILE_MISMATCH,
                    severity="REPORT_ONLY",
                    message=f"market event market mismatch for {event_id}",
                )
            )


def _append_corporate_event_context_gaps(
    stream: HistoricalReplayEventStream,
    corporate_events,
    known_session_dates: set,
    trading_session_dates: list,
    gap_entries: list[HistoricalReplayBridgeGapEntry],
) -> None:
    for corporate_event in corporate_events:
        event_key = f"{corporate_event.symbol}-{corporate_event.event_date.isoformat()}-{corporate_event.event_type.value}"
        if corporate_event.event_type not in _SUPPORTED_CORPORATE_EVENT_TYPES:
            gap_entries.append(
                _gap_entry(
                    stream,
                    gap_id_suffix=f"unsupported-corporate-event-{event_key}",
                    gap_category=HistoricalReplayBridgeGapCategory.REPLAY_UNSUPPORTED_EVENT_CONTEXT,
                    severity="REPORT_ONLY",
                    message=f"unsupported corporate event context type {corporate_event.event_type.value} for {event_key}",
                )
            )
        if _clean_text(corporate_event.market).upper() != _clean_text(stream.market_profile_id).upper():
            gap_entries.append(
                _gap_entry(
                    stream,
                    gap_id_suffix=f"corporate-event-market-mismatch-{event_key}",
                    gap_category=HistoricalReplayBridgeGapCategory.REPLAY_MARKET_PROFILE_MISMATCH,
                    severity="REPORT_ONLY",
                    message=f"corporate event market mismatch for {event_key}",
                )
            )
        if corporate_event.event_date not in known_session_dates:
            gap_entries.append(
                _gap_entry(
                    stream,
                    gap_id_suffix=f"corporate-event-missing-session-{event_key}",
                    gap_category=HistoricalReplayBridgeGapCategory.REPLAY_MISSING_TRADING_SESSION,
                    severity="REPORT_ONLY",
                    message=f"corporate event session date {corporate_event.event_date.isoformat()} is absent from trading calendar",
                )
            )
        effective_session_date = _resolve_corporate_event_session_date(corporate_event, trading_session_dates)
        if effective_session_date is None:
            gap_entries.append(
                _gap_entry(
                    stream,
                    gap_id_suffix=f"corporate-event-effective-session-missing-{event_key}",
                    gap_category=HistoricalReplayBridgeGapCategory.REPLAY_MISSING_TRADING_SESSION,
                    severity="REPORT_ONLY",
                    message=f"effective trading session is unavailable for corporate event {event_key}",
                )
            )


def _build_market_event_context_payload(
    stream: HistoricalReplayEventStream,
    market_event,
    gap_entries: list[HistoricalReplayBridgeGapEntry],
):
    event_id = _clean_text(market_event.event_id).upper()
    if market_event.event_type not in _SUPPORTED_MARKET_EVENT_TYPES:
        return None
    if _clean_text(market_event.timezone) != _clean_text(stream.source_timezone):
        return None
    if _clean_text(market_event.market).upper() != _clean_text(stream.market_profile_id).upper():
        return None
    if market_event.affected_market and _clean_text(market_event.affected_market).upper() != _clean_text(stream.market_profile_id).upper():
        return None
    gap_entries.append(
        _gap_entry(
            stream,
            gap_id_suffix=f"market-event-known-time-{event_id}",
            gap_category=HistoricalReplayBridgeGapCategory.REPLAY_EVENT_KNOWN_TIME_INCOMPLETE,
            severity="REPORT_ONLY",
            message=f"known_at metadata is incomplete for market event {event_id}",
        )
    )
    affected_symbols = list(market_event.affected_symbols or [])
    if _clean_text(market_event.event_scope).upper() == "MARKET_WIDE" or not affected_symbols:
        return [
            _market_event_context_payload(
                stream,
                market_event,
                event_id=event_id,
                symbol=None,
                context_id_suffix=event_id,
            )
        ]
    return [
        _market_event_context_payload(
            stream,
            market_event,
            event_id=event_id,
            symbol=affected_symbol,
            context_id_suffix=f"{event_id}-{affected_symbol}",
        )
        for affected_symbol in affected_symbols
    ]


def _market_event_context_payload(
    stream: HistoricalReplayEventStream,
    market_event,
    *,
    event_id: str,
    symbol: str | None,
    context_id_suffix: str,
) -> dict:
    return {
        "context_id": f"{stream.stream_id}-MARKET-{context_id_suffix}",
        "replay_window_id": "",
        "replay_event_stream_id": stream.stream_id,
        "bridge_input_id": stream.bridge_input_id,
        "context_scope": "MARKET",
        "event_source_record_id": event_id,
        "event_source_id": market_event.source_id,
        "event_batch_id": market_event.event_batch_id,
        "market": market_event.market,
        "symbol": symbol,
        "event_type": market_event.event_type.value,
        "event_date": market_event.event_date.isoformat(),
        "event_time": market_event.event_time.isoformat() if market_event.event_time else None,
        "known_at": None,
        "known_time_complete": False,
        "historical_market_snapshot_id": stream.historical_market_snapshot_id,
        "historical_calendar_snapshot_id": stream.historical_calendar_snapshot_id,
        "source_manifest_ids": stream.source_manifest_ids,
        "source_audit_record_ids": stream.source_audit_record_ids,
        "provider_provenance_ids": stream.provider_provenance_ids,
        "report_only": True,
        "read_only": stream.read_only,
        "non_executable": stream.non_executable,
        "local_file_only": stream.local_file_only,
        "no_network": stream.no_network,
        "no_provider_api": stream.no_provider_api,
        "no_order": stream.no_order,
        "no_llm_runtime": stream.no_llm_runtime,
        "no_ml_training": stream.no_ml_training,
    }


def _build_corporate_event_context_payload(
    stream: HistoricalReplayEventStream,
    corporate_event,
    trading_session_dates: list,
    gap_entries: list[HistoricalReplayBridgeGapEntry],
):
    if corporate_event.event_type not in _SUPPORTED_CORPORATE_EVENT_TYPES:
        return None
    if _clean_text(corporate_event.market).upper() != _clean_text(stream.market_profile_id).upper():
        return None
    event_key = f"{corporate_event.symbol}-{corporate_event.event_date.isoformat()}-{corporate_event.event_type.value}"
    effective_session_date = _resolve_corporate_event_session_date(corporate_event, trading_session_dates)
    if effective_session_date is None:
        return None
    gap_entries.append(
        _gap_entry(
            stream,
            gap_id_suffix=f"corporate-event-known-time-{event_key}",
            gap_category=HistoricalReplayBridgeGapCategory.REPLAY_EVENT_KNOWN_TIME_INCOMPLETE,
            severity="REPORT_ONLY",
            message=f"known_at metadata is incomplete for corporate event {event_key}",
        )
    )
    return {
        "context_id": f"{stream.stream_id}-CORPORATE-{event_key}",
        "replay_window_id": "",
        "replay_event_stream_id": stream.stream_id,
        "bridge_input_id": stream.bridge_input_id,
        "context_scope": "CORPORATE",
        "event_source_record_id": event_key,
        "event_source_id": corporate_event.source_id,
        "event_batch_id": None,
        "market": corporate_event.market,
        "symbol": corporate_event.symbol,
        "event_type": corporate_event.event_type.value,
        "event_date": corporate_event.event_date.isoformat(),
        "event_time": None,
        "known_at": None,
        "known_time_complete": False,
        "historical_market_snapshot_id": stream.historical_market_snapshot_id,
        "historical_calendar_snapshot_id": stream.historical_calendar_snapshot_id,
        "source_manifest_ids": stream.source_manifest_ids,
        "source_audit_record_ids": stream.source_audit_record_ids,
        "provider_provenance_ids": stream.provider_provenance_ids,
        "report_only": True,
        "read_only": stream.read_only,
        "non_executable": stream.non_executable,
        "local_file_only": stream.local_file_only,
        "no_network": stream.no_network,
        "no_provider_api": stream.no_provider_api,
        "no_order": stream.no_order,
        "no_llm_runtime": stream.no_llm_runtime,
        "no_ml_training": stream.no_ml_training,
    }


def _build_event_context_attachment_report(
    stream: HistoricalReplayEventStream,
    windows: list[HistoricalReplayWindow],
) -> HistoricalReplayEventContextAttachmentReport:
    market_context_ids: set[str] = set()
    corporate_context_ids: set[str] = set()
    event_source_ids: set[str] = set()
    event_batch_ids: set[str] = set()
    for window in windows:
        for context in window.market_event_contexts:
            market_context_ids.add(context.context_id)
            event_source_ids.add(context.event_source_id)
            if context.event_batch_id:
                event_batch_ids.add(context.event_batch_id)
        for context in window.corporate_event_contexts:
            corporate_context_ids.add(context.context_id)
            event_source_ids.add(context.event_source_id)
            if context.event_batch_id:
                event_batch_ids.add(context.event_batch_id)
    return HistoricalReplayEventContextAttachmentReport.model_validate(
        {
            "attachment_report_id": f"{stream.stream_id}-event-context-report",
            "replay_event_stream_id": stream.stream_id,
            "bridge_input_id": stream.bridge_input_id,
            "historical_market_snapshot_id": stream.historical_market_snapshot_id,
            "historical_calendar_snapshot_id": stream.historical_calendar_snapshot_id,
            "source_manifest_ids": stream.source_manifest_ids,
            "source_audit_record_ids": stream.source_audit_record_ids,
            "provider_provenance_ids": stream.provider_provenance_ids,
            "attached_market_event_count": len(market_context_ids),
            "attached_corporate_event_count": len(corporate_context_ids),
            "event_source_ids": sorted(event_source_ids),
            "event_batch_ids": sorted(event_batch_ids),
            "read_only": stream.read_only,
            "non_executable": stream.non_executable,
            "local_file_only": stream.local_file_only,
            "no_network": stream.no_network,
            "no_provider_api": stream.no_provider_api,
            "no_order": stream.no_order,
            "no_llm_runtime": stream.no_llm_runtime,
            "no_ml_training": stream.no_ml_training,
        }
    )


def _materialize_window_event_contexts(context_payloads: list[dict], *, window_id: str) -> list[dict]:
    materialized_contexts: list[dict] = []
    for payload in context_payloads:
        materialized = dict(payload)
        materialized["replay_window_id"] = window_id
        materialized_contexts.append(materialized)
    return materialized_contexts


def _collect_window_event_contexts(contexts_by_date: dict, window_dates: list) -> list[dict]:
    collected_contexts: list[dict] = []
    for window_date in window_dates:
        collected_contexts.extend(contexts_by_date.get(window_date, []))
    return collected_contexts


def _resolve_corporate_event_session_date(corporate_event, trading_session_dates: list):
    if corporate_event.event_type == CalendarEventType.EARNINGS_AFTER_CLOSE:
        for trading_session_date in trading_session_dates:
            if trading_session_date > corporate_event.event_date:
                return trading_session_date
        return None
    return corporate_event.event_date


def _build_scanner_input(
    stream: HistoricalReplayEventStream,
    window_bundle: HistoricalReplayWindowBundle,
    replay_input_id: str,
    gap_categories: list[str],
) -> HistoricalScannerReplayInput:
    scanner_window_ids = [window.window_id for window in window_bundle.windows]
    bundle_event_source_ids = sorted(window_bundle.event_context_report.event_source_ids)
    stream_events_by_id = {event.replay_event_id: event for event in stream.events}
    ordered_window_events = []
    for window in window_bundle.windows:
        for event_id in window.event_ids:
            event = stream_events_by_id.get(event_id)
            if event is not None:
                ordered_window_events.append(event)
    if not ordered_window_events:
        raise ValueError("missing scanner replay context")
    ordered_window_events.sort(key=lambda event: (event.session_date, event.replay_timestamp, event.symbol, event.market, event.replay_event_id))
    primary_event = ordered_window_events[0]
    context_id = f"{replay_input_id}-CONTEXT"
    scanner_context = HistoricalScannerReplayContext.model_validate(
        {
            "context_id": context_id,
            "strategy_track": stream.strategy_track,
            "market_profile_id": stream.market_profile_id,
            "historical_market_snapshot_id": stream.historical_market_snapshot_id,
            "historical_calendar_snapshot_id": stream.historical_calendar_snapshot_id,
            "replay_event_stream_id": stream.stream_id,
            "source_window_bundle_id": window_bundle.window_bundle_id,
            "scanner_window_ids": scanner_window_ids,
            "symbol": primary_event.symbol,
            "market": primary_event.market,
            "early_close": any(window.early_close for window in window_bundle.windows),
            "holiday_session_gap": "REPLAY_HOLIDAY_SESSION_RECOGNIZED" in {
                gap.gap_category.value for gap in window_bundle.gap_report.gaps
            },
            "attached_market_event_count": window_bundle.event_context_report.attached_market_event_count,
            "attached_corporate_event_count": window_bundle.event_context_report.attached_corporate_event_count,
            "attached_event_context_summary": (
                f"MARKET_EVENTS={window_bundle.event_context_report.attached_market_event_count}"
                f"|CORPORATE_EVENTS={window_bundle.event_context_report.attached_corporate_event_count}"
            ),
            "event_source_ids": bundle_event_source_ids,
            "validation_gap_categories": gap_categories,
            "lineage_complete": bool(stream.source_manifest_ids and stream.source_audit_record_ids and stream.provider_provenance_ids),
            "report_only": True,
            "read_only": True,
            "non_executable": True,
            "local_file_only": True,
            "no_network": True,
            "no_provider_api": True,
            "no_order": True,
            "no_llm_runtime": True,
            "no_ml_training": True,
            "source_manifest_ids": stream.source_manifest_ids,
            "source_audit_record_ids": stream.source_audit_record_ids,
            "provider_provenance_ids": stream.provider_provenance_ids,
        }
    )
    candidate_seeds = []
    for index, window in enumerate(window_bundle.windows, start=1):
        window_event_source_ids = sorted(
            {
                context.event_source_id
                for context in (window.market_event_contexts + window.corporate_event_contexts)
            }
        )
        if not window_event_source_ids:
            window_event_source_ids = bundle_event_source_ids
        primary_window_event = min(
            (stream_events_by_id[event_id] for event_id in window.event_ids if event_id in stream_events_by_id),
            key=lambda event: (event.session_date, event.replay_timestamp, event.symbol, event.market, event.replay_event_id),
        )
        candidate_seeds.append(
            HistoricalScannerReplayCandidateSeed.model_validate(
                {
                    "seed_id": f"{replay_input_id}-SEED-{index:06d}",
                    "symbol": primary_window_event.symbol,
                    "market": primary_window_event.market,
                    "session_date": window.session_date.isoformat(),
                    "reason_code": "REPLAY_WINDOW_SEED",
                    "source_event_id": primary_window_event.replay_event_id,
                    "replay_event_stream_id": stream.stream_id,
                    "source_window_id": window.window_id,
                    "scanner_context_id": context_id,
                    "event_source_ids": window_event_source_ids,
                    "source_manifest_ids": stream.source_manifest_ids,
                    "source_audit_record_ids": stream.source_audit_record_ids,
                    "provider_provenance_ids": stream.provider_provenance_ids,
                    "is_order_candidate": False,
                    "report_only": True,
                    "read_only": True,
                    "non_executable": True,
                    "local_file_only": True,
                    "no_network": True,
                    "no_provider_api": True,
                    "no_order": True,
                    "no_llm_runtime": True,
                    "no_ml_training": True,
                }
            )
        )
    return HistoricalScannerReplayInput.model_validate(
        {
            "replay_input_id": replay_input_id,
            "strategy_track": stream.strategy_track,
            "replay_context": scanner_context.model_dump(mode="json"),
            "replay_event_stream_id": stream.stream_id,
            "source_window_bundle_id": window_bundle.window_bundle_id,
            "historical_market_snapshot_id": stream.historical_market_snapshot_id,
            "historical_calendar_snapshot_id": stream.historical_calendar_snapshot_id,
            "scanner_window_ids": scanner_window_ids,
            "event_source_ids": bundle_event_source_ids,
            "source_manifest_ids": stream.source_manifest_ids,
            "source_audit_record_ids": stream.source_audit_record_ids,
            "provider_provenance_ids": stream.provider_provenance_ids,
            "candidate_seeds": [seed.model_dump(mode="json") for seed in candidate_seeds],
            "report_only": True,
            "read_only": True,
            "non_executable": True,
            "local_file_only": True,
            "no_network": True,
            "no_provider_api": True,
            "no_order": True,
            "no_llm_runtime": True,
            "no_ml_training": True,
        }
    )


def _scanner_blocking_categories(stream: HistoricalReplayEventStream, window_bundle: HistoricalReplayWindowBundle) -> list[str]:
    categories: list[str] = []
    if getattr(stream, "strategy_track", None) is None:
        categories.append("SCANNER_REPLAY_MISSING_STRATEGY_TRACK")
    elif stream.strategy_track != StrategyTrack.DOMESTIC_KR:
        categories.append("SCANNER_REPLAY_UNSUPPORTED_TRACK")
    if not _clean_text(stream.market_profile_id):
        categories.append("SCANNER_REPLAY_MISSING_MARKET_PROFILE")
    elif _clean_text(stream.market_profile_id).upper() != "KRX":
        categories.append("SCANNER_REPLAY_UNSUPPORTED_MARKET")
    if not all(
        [
            stream.read_only,
            stream.non_executable,
            stream.local_file_only,
            stream.no_network,
            stream.no_provider_api,
            stream.no_order,
            stream.no_llm_runtime,
            stream.no_ml_training,
            window_bundle.read_only,
            window_bundle.non_executable,
            window_bundle.local_file_only,
            window_bundle.no_network,
            window_bundle.no_provider_api,
            window_bundle.no_order,
            window_bundle.no_llm_runtime,
            window_bundle.no_ml_training,
        ]
    ):
        categories.append("SCANNER_REPLAY_SAFETY_MARKER_MISSING")
    scanner_payload = {
        "stream": stream.model_dump(mode="json"),
        "window_bundle": window_bundle.model_dump(mode="json"),
    }
    for _path, key, item in _iter_dict_keys(scanner_payload):
        lowered = key.strip().lower()
        if not lowered or _is_allowed_safe_boundary_key(lowered, item):
            continue
        category = _scanner_category_for_text(lowered)
        if category:
            categories.append(category)
    for _path, value in _iter_string_values(scanner_payload):
        lowered = value.strip().lower()
        if not lowered:
            continue
        category = _scanner_category_for_text(lowered)
        if category:
            categories.append(category)
    return _unique_preserve_order(categories)


def _scanner_category_for_text(lowered: str) -> str | None:
    if lowered.startswith("http://") or lowered.startswith("https://") or lowered.startswith("//"):
        return "SCANNER_REPLAY_REMOTE_SOURCE_NOT_ALLOWED"
    if "parquet" in lowered:
        return "SCANNER_REPLAY_PARQUET_NOT_ALLOWED"
    if "provider_api" in lowered or lowered == "api":
        return "SCANNER_REPLAY_API_SOURCE_NOT_ALLOWED"
    if any(word in lowered for word in ("order", "order candidate", "order intent", "account", "broker")):
        return "SCANNER_REPLAY_ORDER_FIELD_DETECTED"
    if any(word in lowered for word in ("execute", "execution", "execution hint")):
        return "SCANNER_REPLAY_EXECUTION_FIELD_DETECTED"
    if any(word in lowered for word in ("buy", "sell", "entry", "exit", "target", "stop")):
        return "SCANNER_REPLAY_BUY_SELL_WORDING_DETECTED"
    if any(word in lowered for word in ("network", "socket", "websocket", "tcp", "udp")):
        return "SCANNER_REPLAY_NETWORK_SOURCE_NOT_ALLOWED"
    if "provider" in lowered:
        return "SCANNER_REPLAY_PROVIDER_SOURCE_NOT_ALLOWED"
    if any(word in lowered for word in ("gemini", "llm", "cloud model", "local model", "model runtime", "runtime")):
        return "SCANNER_REPLAY_LLM_METADATA_NOT_ALLOWED"
    if any(word in lowered for word in ("ml", "training")):
        return "SCANNER_REPLAY_ML_TRAINING_TRIGGER_NOT_ALLOWED"
    if "crawler" in lowered:
        return "SCANNER_REPLAY_CRAWLER_TRIGGER_NOT_ALLOWED"
    if "live" in lowered or "prod" in lowered:
        return "SCANNER_REPLAY_LIVE_PROD_NOT_ALLOWED"
    if "remote" in lowered:
        return "SCANNER_REPLAY_REMOTE_SOURCE_NOT_ALLOWED"
    return None


def _scanner_gap_report(
    *,
    replay_input_id: str,
    historical_calendar_snapshot_id: str | None,
    source_manifest_ids: list[str],
    source_audit_record_ids: list[str],
    provider_provenance_ids: list[str],
    gap_categories: list[str],
    gap_entries: list[HistoricalScannerReplayGapEntry],
) -> HistoricalScannerReplayGapReport:
    categories = _unique_preserve_order(gap_categories)
    blocking_gap_count = len(
        [
            category
            for category in categories
            if category
            not in {"SCANNER_REPLAY_INPUT_GENERATED", "SCANNER_REPLAY_REPORT_ONLY", "SCANNER_REPLAY_SOURCE_LINEAGE_MISSING"}
        ]
    )
    report_only_gap_count = len(categories) - blocking_gap_count
    return HistoricalScannerReplayGapReport.model_validate(
        {
            "gap_report_id": f"{replay_input_id}-GAP-REPORT",
            "replay_input_id": replay_input_id,
            "historical_calendar_snapshot_id": historical_calendar_snapshot_id,
            "gap_categories": categories,
            "source_manifest_ids": source_manifest_ids,
            "source_audit_record_ids": source_audit_record_ids,
            "provider_provenance_ids": provider_provenance_ids,
            "blocking_gap_count": blocking_gap_count,
            "report_only_gap_count": report_only_gap_count,
            "gaps": [gap.model_dump(mode="json") for gap in gap_entries],
            "report_only": True,
            "read_only": True,
            "non_executable": True,
            "local_file_only": True,
            "no_network": True,
            "no_provider_api": True,
            "no_order": True,
            "no_llm_runtime": True,
            "no_ml_training": True,
        }
    )


def _empty_scanner_report(
    *,
    replay_input_id: str = "MISSING-REPLAY-INPUT",
    strategy_track: StrategyTrack = StrategyTrack.DOMESTIC_KR,
    historical_calendar_snapshot_id: str | None = None,
    source_manifest_ids: list[str] | None = None,
    source_audit_record_ids: list[str] | None = None,
    provider_provenance_ids: list[str] | None = None,
) -> HistoricalScannerReplayReport:
    normalized_track = strategy_track if strategy_track in set(StrategyTrack) else StrategyTrack.DOMESTIC_KR
    return HistoricalScannerReplayReport.model_validate(
        {
            "report_id": f"{replay_input_id}-REPORT",
            "replay_input_id": replay_input_id,
            "strategy_track": normalized_track,
            "historical_calendar_snapshot_id": historical_calendar_snapshot_id,
            "source_manifest_ids": source_manifest_ids or [],
            "source_audit_record_ids": source_audit_record_ids or [],
            "provider_provenance_ids": provider_provenance_ids or [],
            "candidate_seed_count": 0,
            "scanner_window_count": 0,
            "warnings": [],
            "report_only": True,
            "read_only": True,
            "non_executable": True,
            "local_file_only": True,
            "no_network": True,
            "no_provider_api": True,
            "no_order": True,
            "no_llm_runtime": True,
            "no_ml_training": True,
        }
    )


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = _clean_text(value).upper()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered
