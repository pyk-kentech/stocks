from __future__ import annotations

from datetime import date, datetime, timedelta

from stock_risk_mcp.historical_outcome_guard import (
    validate_historical_outcome_metadata_safety,
    validate_historical_outcome_pre_outcome_boundary,
)
from stock_risk_mcp.historical_outcome_models import (
    HistoricalOutcomeGapCategory,
    HistoricalOutcomeGapEntry,
    HistoricalOutcomeLabel,
    HistoricalOutcomeLabelType,
    HistoricalOutcomeMetricSet,
    HistoricalOutcomeObservationInput,
    HistoricalOutcomeObservationRecord,
    HistoricalOutcomeObservationWindow,
)
from stock_risk_mcp.strategy_track_models import StrategyTrack


def build_historical_outcome_windows(
    observation_input: HistoricalOutcomeObservationInput,
    *,
    forward_window_sizes: tuple[int, ...] | None = None,
) -> HistoricalOutcomeObservationInput:
    requested_sizes = (
        sorted({int(size) for size in forward_window_sizes if int(size) > 0})
        if forward_window_sizes is not None
        else observation_input.observation_config.forward_window_sizes
    )
    if not requested_sizes:
        raise ValueError("forward_window_sizes must contain at least one positive integer")

    scanner_input_before = observation_input.scanner_replay_input.model_dump(mode="json")
    calendar_snapshot = observation_input.historical_calendar_event_snapshot
    gap_entries = []
    if calendar_snapshot is None:
        if observation_input.observation_config.allow_report_only_degraded_calendar:
            gap_entries.append(
                _gap_entry(
                    observation_input,
                    "missing-trading-calendar",
                    HistoricalOutcomeGapCategory.OUTCOME_MISSING_TRADING_CALENDAR,
                    "REPORT_ONLY",
                    "missing trading calendar",
                )
            )
            gap_entries.append(
                _gap_entry(
                    observation_input,
                    "outcome-report-only",
                    HistoricalOutcomeGapCategory.OUTCOME_REPORT_ONLY,
                    "REPORT_ONLY",
                    "outcome observation downgraded to report-only because trading calendar is unavailable",
                )
            )
            return _updated_input(observation_input, [], [], gap_entries)
        raise ValueError("missing trading calendar")

    session_by_date = {session.date: session for session in calendar_snapshot.session_records}
    windows = []
    records = []
    metric_sets = []
    next_record_id = 1
    next_metric_id = 1

    for replay_window in observation_input.replay_window_bundle.windows:
        anchor_record = _find_anchor_record(
            observation_input,
            replay_window.session_date,
            replay_window.event_ids,
        )
        if anchor_record is None:
            gap_entries.append(
                _gap_entry(
                    observation_input,
                    f"missing-anchor-price-{replay_window.window_id}",
                    HistoricalOutcomeGapCategory.OUTCOME_MISSING_ANCHOR_PRICE,
                    "BLOCKING",
                    f"missing anchor price for replay window {replay_window.window_id}",
                )
            )
            continue

        for window_size in requested_sizes:
            forward_sessions, missing_session_dates = _forward_trading_sessions(
                calendar_snapshot,
                replay_window.session_date,
                window_size,
            )
            if missing_session_dates:
                for missing_date in missing_session_dates:
                    gap_entries.append(
                        _gap_entry(
                            observation_input,
                            f"missing-forward-session-{replay_window.window_id}-{missing_date.isoformat()}",
                            HistoricalOutcomeGapCategory.OUTCOME_MISSING_FORWARD_SESSION,
                            "BLOCKING",
                            f"missing expected forward trading session {missing_date.isoformat()}",
                        )
                    )
                continue

            if len(forward_sessions) < window_size:
                gap_entries.append(
                    _gap_entry(
                        observation_input,
                        f"insufficient-forward-data-{replay_window.window_id}-{window_size}",
                        HistoricalOutcomeGapCategory.OUTCOME_INSUFFICIENT_FORWARD_DATA,
                        "REPORT_ONLY",
                        f"insufficient forward data for replay window {replay_window.window_id} and size {window_size}",
                    )
                )
                continue

            forward_price_records = _lookup_forward_price_records(
                observation_input,
                anchor_record.symbol,
                anchor_record.market,
                [session.date for session in forward_sessions],
            )
            missing_price_dates = [session.date for session in forward_sessions if session.date not in forward_price_records]
            if missing_price_dates:
                for missing_date in missing_price_dates:
                    gap_entries.append(
                        _gap_entry(
                            observation_input,
                            f"missing-forward-price-{replay_window.window_id}-{missing_date.isoformat()}",
                            HistoricalOutcomeGapCategory.OUTCOME_MISSING_FORWARD_PRICE,
                            "BLOCKING",
                            f"missing forward price for trading session {missing_date.isoformat()}",
                        )
                    )
                continue

            outcome_window = HistoricalOutcomeObservationWindow.model_validate(
                {
                    "window_id": f"{replay_window.window_id}-OUTCOME-{window_size}",
                    "replay_window_id": replay_window.window_id,
                    "symbol": anchor_record.symbol,
                    "market": anchor_record.market,
                    "window_size_sessions": window_size,
                    "reference_timestamp": anchor_record.timestamp,
                    "observation_start_timestamp": forward_price_records[forward_sessions[0].date].timestamp,
                    "observation_end_timestamp": forward_price_records[forward_sessions[-1].date].timestamp,
                    "window_session_dates": [session.date.isoformat() for session in forward_sessions],
                    "historical_market_snapshot_id": observation_input.historical_market_data_snapshot.snapshot_id,
                    "historical_calendar_snapshot_id": calendar_snapshot.snapshot_id,
                    "source_manifest_ids": replay_window.source_manifest_ids,
                    "source_audit_record_ids": replay_window.source_audit_record_ids,
                    "provider_provenance_ids": replay_window.provider_provenance_ids,
                }
            )
            windows.append(outcome_window)

            observation_record_ids = []
            record_prices = []
            record_volumes = []
            early_close_count = 0
            for session in forward_sessions:
                price_record = forward_price_records[session.date]
                observation_record = HistoricalOutcomeObservationRecord.model_validate(
                    {
                        "observation_record_id": f"OBSERVATION-RECORD-{next_record_id}",
                        "window_id": outcome_window.window_id,
                        "symbol": anchor_record.symbol,
                        "market": anchor_record.market,
                        "observation_timestamp": price_record.timestamp.isoformat(),
                        "close_price": float(price_record.close),
                        "volume": float(price_record.volume),
                        "return_from_reference_pct": _return_pct(anchor_record.close, price_record.close),
                        "source_manifest_ids": replay_window.source_manifest_ids,
                        "source_audit_record_ids": replay_window.source_audit_record_ids,
                        "provider_provenance_ids": replay_window.provider_provenance_ids,
                    }
                )
                next_record_id += 1
                records.append(observation_record)
                observation_record_ids.append(observation_record.observation_record_id)
                record_prices.append(float(price_record.close))
                record_volumes.append(float(price_record.volume))
                if session.is_early_close:
                    early_close_count += 1

            has_market_event_context = bool(getattr(replay_window, "market_event_contexts", []))
            has_corporate_event_context = bool(getattr(replay_window, "corporate_event_contexts", []))
            metric_sets.append(
                HistoricalOutcomeMetricSet.model_validate(
                    {
                        "metric_set_id": f"METRIC-SET-{next_metric_id}",
                        "window_id": outcome_window.window_id,
                        "observation_record_ids": observation_record_ids,
                        "reference_price": float(anchor_record.close),
                        "anchor_close_price": float(anchor_record.close),
                        "final_price": record_prices[-1],
                        "forward_close_price": record_prices[-1],
                        "forward_return_pct": _return_pct(anchor_record.close, record_prices[-1]),
                        "max_favorable_excursion_pct": _return_pct(anchor_record.close, max(record_prices)),
                        "max_adverse_excursion_pct": _return_pct(anchor_record.close, min(record_prices)),
                        "final_return_pct": _return_pct(anchor_record.close, record_prices[-1]),
                        "high_water_mark": max(record_prices),
                        "low_water_mark": min(record_prices),
                        "observed_volume_total": sum(record_volumes),
                        "observed_volume_average": sum(record_volumes) / len(record_volumes),
                        "sessions_observed": len(forward_sessions),
                        "missing_session_count": 0,
                        "early_close_count": early_close_count,
                        "has_market_event_context": has_market_event_context,
                        "has_corporate_event_context": has_corporate_event_context,
                        "observed_point_count": len(observation_record_ids),
                    }
                )
            )
            next_metric_id += 1

            if early_close_count:
                gap_entries.append(
                    _gap_entry(
                        observation_input,
                        f"early-close-{outcome_window.window_id}",
                        HistoricalOutcomeGapCategory.OUTCOME_REPORT_ONLY,
                        "REPORT_ONLY",
                        f"forward observation window {outcome_window.window_id} includes early-close sessions",
                    )
                )

    gap_entries.append(
        _gap_entry(
            observation_input,
            "observation-generated",
            HistoricalOutcomeGapCategory.OUTCOME_OBSERVATION_GENERATED,
            "REPORT_ONLY",
            "historical outcome observation generated",
        )
    )
    gap_entries.append(
        _gap_entry(
            observation_input,
            "report-only",
            HistoricalOutcomeGapCategory.OUTCOME_REPORT_ONLY,
            "REPORT_ONLY",
            "historical outcome metrics remain report-only and outcome-side only",
        )
    )

    updated = _updated_input(observation_input, windows, records, gap_entries, metric_sets)
    scanner_input_after = updated.scanner_replay_input.model_dump(mode="json")
    if scanner_input_before != scanner_input_after:
        raise ValueError("scanner_replay_input must remain unchanged during outcome observation")
    return updated


def build_historical_outcome_label_report(
    observation_input: HistoricalOutcomeObservationInput,
) -> HistoricalOutcomeObservationInput:
    scanner_input_before = observation_input.scanner_replay_input.model_dump(mode="json")
    gap_entries = list(observation_input.gap_report.gaps)
    warnings = list(observation_input.label_report.warnings)
    known_time_warnings, known_time_gaps = _known_time_metadata_findings(observation_input)
    warnings.extend(known_time_warnings)
    gap_entries.extend(known_time_gaps)

    safety_violation = _detect_label_safety_violation(observation_input)
    if safety_violation is not None:
        category, reason_code, message = safety_violation
        gap_entries.append(
            _gap_entry(
                observation_input,
                f"label-safety-{reason_code.lower()}",
                category,
                "BLOCKING",
                message,
            )
        )
        labels = _build_safety_blocked_labels(observation_input, reason_code)
        warnings.append("historical outcome label assignment remains report-only and safety-blocked")
        updated = _updated_input(
            observation_input,
            observation_input.observation_windows,
            observation_input.observation_records,
            gap_entries,
            observation_input.metric_sets,
            labels=labels,
            warnings=warnings,
        )
        scanner_input_after = updated.scanner_replay_input.model_dump(mode="json")
        if scanner_input_before != scanner_input_after:
            raise ValueError("scanner_replay_input must remain unchanged during outcome labeling")
        return updated

    labels = []
    windows_by_id = {window.window_id: window for window in observation_input.observation_windows}
    config = observation_input.observation_config
    threshold_tuple = (
        config.favorable_return_threshold_pct,
        config.adverse_return_threshold_pct,
        config.volatile_mfe_threshold_pct,
        config.volatile_mae_threshold_pct,
    )

    for index, metric_set in enumerate(observation_input.metric_sets, start=1):
        window = windows_by_id.get(metric_set.window_id)
        label_type = HistoricalOutcomeLabelType.OUTCOME_REPORT_ONLY
        reason_code = "OFFLINE_OBSERVATION_ONLY"
        if config.strategy_track != StrategyTrack.DOMESTIC_KR:
            gap_entries.append(
                _gap_entry(
                    observation_input,
                    f"unsupported-track-{metric_set.metric_set_id}",
                    HistoricalOutcomeGapCategory.OUTCOME_UNSUPPORTED_TRACK,
                    "BLOCKING",
                    f"unsupported strategy track for outcome labeling: {config.strategy_track.value}",
                )
            )
            label_type = HistoricalOutcomeLabelType.OUTCOME_BLOCKED_SAFETY
            reason_code = "UNSUPPORTED_TRACK"
        elif window is not None and window.market != "KRX":
            gap_entries.append(
                _gap_entry(
                    observation_input,
                    f"unsupported-market-{metric_set.metric_set_id}",
                    HistoricalOutcomeGapCategory.OUTCOME_UNSUPPORTED_MARKET,
                    "BLOCKING",
                    f"unsupported market for outcome labeling: {window.market}",
                )
            )
            label_type = HistoricalOutcomeLabelType.OUTCOME_BLOCKED_SAFETY
            reason_code = "UNSUPPORTED_MARKET"
        elif _has_gap_category(gap_entries, HistoricalOutcomeGapCategory.OUTCOME_INSUFFICIENT_FORWARD_DATA):
            label_type = HistoricalOutcomeLabelType.OUTCOME_INSUFFICIENT_FORWARD_DATA
            reason_code = "INSUFFICIENT_FORWARD_DATA"
        elif metric_set.sessions_observed <= 0 or metric_set.forward_close_price is None or metric_set.final_return_pct is None:
            gap_entries.append(
                _gap_entry(
                    observation_input,
                    f"missing-metrics-{metric_set.metric_set_id}",
                    HistoricalOutcomeGapCategory.OUTCOME_LABEL_INCONCLUSIVE,
                    "REPORT_ONLY",
                    f"missing outcome metrics for metric set {metric_set.metric_set_id}",
                )
            )
            label_type = HistoricalOutcomeLabelType.OUTCOME_INCONCLUSIVE
            reason_code = "MISSING_METRICS"
        elif any(value is None for value in threshold_tuple):
            gap_entries.append(
                _gap_entry(
                    observation_input,
                    f"missing-threshold-config-{metric_set.metric_set_id}",
                    HistoricalOutcomeGapCategory.OUTCOME_THRESHOLD_CONFIG_MISSING,
                    "REPORT_ONLY",
                    f"missing threshold config for metric set {metric_set.metric_set_id}",
                )
            )
            label_type = HistoricalOutcomeLabelType.OUTCOME_INCONCLUSIVE
            reason_code = "THRESHOLD_CONFIG_MISSING"
        elif (
            metric_set.max_favorable_excursion_pct is not None
            and metric_set.max_adverse_excursion_pct is not None
            and metric_set.max_favorable_excursion_pct >= float(config.volatile_mfe_threshold_pct)
            and abs(metric_set.max_adverse_excursion_pct) >= float(config.volatile_mae_threshold_pct)
        ):
            label_type = HistoricalOutcomeLabelType.OUTCOME_VOLATILE_MIXED
            reason_code = "VOLATILE_MIXED_THRESHOLD_MET"
        elif metric_set.final_return_pct >= float(config.favorable_return_threshold_pct):
            label_type = HistoricalOutcomeLabelType.OUTCOME_FAVORABLE
            reason_code = "FAVORABLE_RETURN_THRESHOLD_MET"
        elif metric_set.final_return_pct <= -float(config.adverse_return_threshold_pct):
            label_type = HistoricalOutcomeLabelType.OUTCOME_ADVERSE
            reason_code = "ADVERSE_RETURN_THRESHOLD_MET"
        else:
            label_type = HistoricalOutcomeLabelType.OUTCOME_NEUTRAL
            reason_code = "NEUTRAL_THRESHOLD_RANGE"

        labels.append(
            HistoricalOutcomeLabel.model_validate(
                {
                    "label_id": f"LABEL-{index}",
                    "window_id": metric_set.window_id,
                    "metric_set_id": metric_set.metric_set_id,
                    "label_type": label_type.value,
                    "reason_code": reason_code,
                    "symbol": window.symbol if window is not None else "UNKNOWN",
                    "market": window.market if window is not None else "UNKNOWN",
                    "final_return_pct": metric_set.final_return_pct,
                }
            )
        )

    warnings.append("historical outcome labels remain report-only offline observations and never trading signals")
    updated = _updated_input(
        observation_input,
        observation_input.observation_windows,
        observation_input.observation_records,
        gap_entries,
        observation_input.metric_sets,
        labels=labels,
        warnings=warnings,
    )
    scanner_input_after = updated.scanner_replay_input.model_dump(mode="json")
    if scanner_input_before != scanner_input_after:
        raise ValueError("scanner_replay_input must remain unchanged during outcome labeling")
    return updated


def _forward_trading_sessions(calendar_snapshot, anchor_date: date, window_size: int):
    sessions = sorted(calendar_snapshot.session_records, key=lambda item: item.date)
    session_by_date = {session.date: session for session in sessions}
    trading_sessions = [session for session in sessions if session.is_trading_day]
    next_sessions = [session for session in trading_sessions if session.date > anchor_date][:window_size]

    missing_open_days = []
    if next_sessions:
        cursor = anchor_date + timedelta(days=1)
        end_date = next_sessions[-1].date
        while cursor <= end_date:
            session = session_by_date.get(cursor)
            if session is None and cursor.weekday() < 5:
                missing_open_days.append(cursor)
            cursor += timedelta(days=1)
    return next_sessions, missing_open_days


def _lookup_forward_price_records(observation_input, symbol: str, market: str, session_dates: list[date]):
    records = {}
    for record in observation_input.historical_market_data_snapshot.records:
        if record.symbol == symbol and record.market == market and record.timestamp.date() in session_dates:
            records[record.timestamp.date()] = record
    return records


def _find_anchor_record(observation_input, anchor_date: date, event_ids: list[str]):
    stream_events = {event.replay_event_id: event for event in observation_input.replay_event_stream.events}
    symbol = None
    market = None
    for event_id in event_ids:
        event = stream_events.get(event_id)
        if event is not None:
            symbol = event.symbol
            market = event.market
            break
    for record in observation_input.historical_market_data_snapshot.records:
        if record.timestamp.date() != anchor_date:
            continue
        if symbol is not None and record.symbol != symbol:
            continue
        if market is not None and record.market != market:
            continue
        return record
    return None


def _gap_entry(observation_input, suffix: str, category: HistoricalOutcomeGapCategory, severity: str, message: str):
    return HistoricalOutcomeGapEntry.model_validate(
        {
            "gap_id": f"{observation_input.observation_input_id}-{suffix}",
            "gap_category": category.value,
            "severity": severity,
            "message": message,
            "source_manifest_id": observation_input.replay_window_bundle.source_manifest_ids[0]
            if observation_input.replay_window_bundle.source_manifest_ids
            else None,
            "source_audit_record_id": observation_input.replay_window_bundle.source_audit_record_ids[0]
            if observation_input.replay_window_bundle.source_audit_record_ids
            else None,
            "provider_provenance_id": observation_input.replay_window_bundle.provider_provenance_ids[0]
            if observation_input.replay_window_bundle.provider_provenance_ids
            else None,
        }
    )


def _updated_input(observation_input, windows, records, gap_entries, metric_sets=None, labels=None, warnings=None):
    report_only_count = sum(1 for gap in gap_entries if gap.severity == "REPORT_ONLY")
    blocking_count = sum(1 for gap in gap_entries if gap.severity != "REPORT_ONLY")
    gap_status = "NO_GAPS" if not gap_entries else ("BLOCKING_GAPS" if blocking_count else "REPORT_ONLY_GAPS")
    return observation_input.model_copy(
        update={
            "observation_windows": windows,
            "observation_records": records,
            "metric_sets": metric_sets or [],
            "gap_report": observation_input.gap_report.model_copy(
                update={
                    "gap_status": gap_status,
                    "gap_categories": [gap.gap_category for gap in gap_entries if gap.gap_category is not None],
                    "blocking_gap_count": blocking_count,
                    "report_only_gap_count": report_only_count,
                    "gaps": gap_entries,
                }
            ),
            "label_report": observation_input.label_report.model_copy(
                update={
                    "labels": labels if labels is not None else observation_input.label_report.labels,
                    "warning_count": len(warnings or observation_input.label_report.warnings),
                    "warnings": warnings if warnings is not None else observation_input.label_report.warnings,
                }
            ),
            "safety_report": observation_input.safety_report.model_copy(),
        }
    )


def _return_pct(anchor_close: float, price: float) -> float:
    return (float(price) - float(anchor_close)) / float(anchor_close)


def _has_gap_category(gap_entries: list[HistoricalOutcomeGapEntry], category: HistoricalOutcomeGapCategory) -> bool:
    return any(gap.gap_category == category for gap in gap_entries)


def _build_safety_blocked_labels(
    observation_input: HistoricalOutcomeObservationInput,
    reason_code: str,
) -> list[HistoricalOutcomeLabel]:
    windows_by_id = {window.window_id: window for window in observation_input.observation_windows}
    labels = []
    for index, metric_set in enumerate(observation_input.metric_sets, start=1):
        window = windows_by_id.get(metric_set.window_id)
        labels.append(
            HistoricalOutcomeLabel.model_validate(
                {
                    "label_id": f"LABEL-{index}",
                    "window_id": metric_set.window_id,
                    "metric_set_id": metric_set.metric_set_id,
                    "label_type": HistoricalOutcomeLabelType.OUTCOME_BLOCKED_SAFETY.value,
                    "reason_code": reason_code,
                    "symbol": window.symbol if window is not None else "UNKNOWN",
                    "market": window.market if window is not None else "UNKNOWN",
                    "final_return_pct": metric_set.final_return_pct,
                }
            )
        )
    return labels


def _detect_label_safety_violation(
    observation_input: HistoricalOutcomeObservationInput,
) -> tuple[HistoricalOutcomeGapCategory, str, str] | None:
    try:
        validate_historical_outcome_pre_outcome_boundary(
            observation_input.scanner_replay_input.model_dump(mode="json"),
            context="historical outcome label report",
        )
        validate_historical_outcome_metadata_safety(
            _label_metadata_strings(observation_input),
            context="historical outcome label report",
        )
    except ValueError as exc:
        error_text = str(exc)
        if "pre-outcome scanner input" in error_text:
            return (
                HistoricalOutcomeGapCategory.OUTCOME_LEAKAGE_RISK_DETECTED,
                "LEAKAGE_RISK_DETECTED",
                error_text,
            )
        if "buy_sell" in error_text:
            return (
                HistoricalOutcomeGapCategory.OUTCOME_BUY_SELL_WORDING_DETECTED,
                "BUY_SELL_WORDING_DETECTED",
                error_text,
            )
        if "order" in error_text:
            return (
                HistoricalOutcomeGapCategory.OUTCOME_ORDER_FIELD_DETECTED,
                "ORDER_FIELD_DETECTED",
                error_text,
            )
        if "remote" in error_text:
            return (
                HistoricalOutcomeGapCategory.OUTCOME_REMOTE_SOURCE_NOT_ALLOWED,
                "REMOTE_SOURCE_NOT_ALLOWED",
                error_text,
            )
        if "provider" in error_text:
            return (
                HistoricalOutcomeGapCategory.OUTCOME_PROVIDER_SOURCE_NOT_ALLOWED,
                "PROVIDER_SOURCE_NOT_ALLOWED",
                error_text,
            )
        if "api" in error_text:
            return (
                HistoricalOutcomeGapCategory.OUTCOME_API_SOURCE_NOT_ALLOWED,
                "API_SOURCE_NOT_ALLOWED",
                error_text,
            )
        if "network" in error_text:
            return (
                HistoricalOutcomeGapCategory.OUTCOME_NETWORK_SOURCE_NOT_ALLOWED,
                "NETWORK_SOURCE_NOT_ALLOWED",
                error_text,
            )
        if "llm" in error_text or "gemini" in error_text:
            return (
                HistoricalOutcomeGapCategory.OUTCOME_LLM_METADATA_NOT_ALLOWED,
                "LLM_METADATA_NOT_ALLOWED",
                error_text,
            )
        if "training" in error_text:
            return (
                HistoricalOutcomeGapCategory.OUTCOME_ML_TRAINING_TRIGGER_NOT_ALLOWED,
                "ML_TRAINING_TRIGGER_NOT_ALLOWED",
                error_text,
            )
        if "crawler" in error_text:
            return (
                HistoricalOutcomeGapCategory.OUTCOME_CRAWLER_TRIGGER_NOT_ALLOWED,
                "CRAWLER_TRIGGER_NOT_ALLOWED",
                error_text,
            )
        if "live_prod" in error_text:
            return (
                HistoricalOutcomeGapCategory.OUTCOME_LIVE_PROD_NOT_ALLOWED,
                "LIVE_PROD_NOT_ALLOWED",
                error_text,
            )
        if "parquet" in error_text:
            return (
                HistoricalOutcomeGapCategory.OUTCOME_PARQUET_NOT_ALLOWED,
                "PARQUET_NOT_ALLOWED",
                error_text,
            )
        return (
            HistoricalOutcomeGapCategory.OUTCOME_REPORT_ONLY,
            "REPORT_ONLY",
            error_text,
        )
    return None


def _label_metadata_strings(observation_input: HistoricalOutcomeObservationInput) -> list[str]:
    values: list[str] = []
    for audit_record in observation_input.audit_records:
        values.extend(
            [
                audit_record.operator_context,
                audit_record.source_path,
                audit_record.audit_record_id,
            ]
        )
    for event in observation_input.replay_event_stream.events:
        values.extend(
            [
                event.source_record_id or "",
                event.source_source_id,
                event.symbol,
                event.market,
            ]
        )
    for metric_set in observation_input.metric_sets:
        values.extend([metric_set.metric_set_id, metric_set.window_id])
    return values


def _known_time_metadata_findings(
    observation_input: HistoricalOutcomeObservationInput,
) -> tuple[list[str], list[HistoricalOutcomeGapEntry]]:
    warnings: list[str] = []
    gap_entries: list[HistoricalOutcomeGapEntry] = []
    for replay_window in observation_input.replay_window_bundle.windows:
        for context in list(getattr(replay_window, "market_event_contexts", [])) + list(
            getattr(replay_window, "corporate_event_contexts", [])
        ):
            if getattr(context, "known_at", None) is None or not getattr(context, "known_time_complete", False):
                warnings.append(
                    f"known-time metadata incomplete for attached event context {context.context_id}; outcome labels remain report-only"
                )
                gap_entries.append(
                    _gap_entry(
                        observation_input,
                        f"known-time-metadata-{context.context_id}",
                        HistoricalOutcomeGapCategory.OUTCOME_REPORT_ONLY,
                        "REPORT_ONLY",
                        f"missing known-time metadata for attached event context {context.context_id}",
                    )
                )
    return warnings, gap_entries
