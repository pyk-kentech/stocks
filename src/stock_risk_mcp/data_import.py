from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Callable

from stock_risk_mcp.compliance import ComplianceRecord
from stock_risk_mcp.import_run import ImportRun, ImportRunStatus, ImportSourceResult, ImportSourceType
from stock_risk_mcp.import_validators import load_import_records
from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.signal_scoring import calculate_signal_score
from stock_risk_mcp.signals import (
    SignalDirection,
    SignalSeverity,
    SignalType,
    TickerSignal,
    observed_date,
    parse_observed_at,
)


def import_price_history_file(repository: RiskRepository, path: str | Path) -> ImportSourceResult:
    result, records = _start_source(path, ImportSourceType.PRICE_HISTORY, {"ticker", "date", "close"})
    if records is None:
        return result
    existing = repository.list_price_bar_keys()
    seen: set[tuple[str, str]] = set()
    bars: list[PriceBar] = []
    for index, record in enumerate(records, 1):
        try:
            bar = PriceBar.model_validate(_empty_to_none(record))
            key = (bar.ticker, bar.date.isoformat())
            if key in existing or key in seen:
                result.skipped_duplicate_count += 1
                continue
            seen.add(key)
            bars.append(bar)
        except Exception as error:
            _row_error(result, index, error)
    result.saved_count = len(repository.save_price_bars(bars))
    if result.skipped_duplicate_count:
        result.warnings.append("duplicate price rows were skipped without updating existing values")
    return result


def import_compliance_file(
    repository: RiskRepository, path: str | Path, as_of_date: date | None = None
) -> ImportSourceResult:
    result, records = _start_source(path, ImportSourceType.COMPLIANCE, {"ticker"})
    if records is None:
        return result
    existing = repository.list_compliance_dedupe_keys()
    seen = set(existing)
    saved: list[ComplianceRecord] = []
    for index, record in enumerate(records, 1):
        try:
            notice_date = date.fromisoformat(str(record["notice_date"])) if record.get("notice_date") else None
            observed_at = (
                datetime.fromisoformat(str(record["observed_at"]))
                if record.get("observed_at")
                else datetime.combine(as_of_date, time.min) if as_of_date else datetime.now()
            )
            if as_of_date and ((notice_date and notice_date > as_of_date) or observed_at.date() > as_of_date):
                result.skipped_duplicate_count += 1
                result.warnings.append(f"row {index}: compliance record after as_of_date was skipped")
                continue
            item = ComplianceRecord(
                ticker=str(record["ticker"]), company_name=_optional(record, "company_name"),
                issue=_optional(record, "issue"), deficiency=_optional(record, "deficiency"),
                notice_date=notice_date, source_url=_optional(record, "source_url"),
                raw_reference=_optional(record, "raw_reference"), observed_at=observed_at,
            )
            key = (item.ticker, item.notice_date.isoformat() if item.notice_date else None, item.source_name, item.issue, item.deficiency)
            if key in seen:
                result.skipped_duplicate_count += 1
                continue
            seen.add(key)
            saved.append(item)
        except Exception as error:
            _row_error(result, index, error)
    result.saved_count = len(repository.save_compliance_records(saved))
    return result


def import_signal_file(
    repository: RiskRepository,
    path: str | Path,
    source_type: ImportSourceType,
    as_of_date: date | None,
) -> ImportSourceResult:
    result, records = _start_source(path, source_type, {"ticker", "observed_at"})
    if records is None:
        return result
    cutoff = as_of_date or date.today()
    valid_records: list[tuple[int, dict[str, Any], date | datetime]] = []
    for index, record in enumerate(records, 1):
        try:
            observed_at = parse_observed_at(record["observed_at"])
            if observed_date(observed_at) > cutoff:
                result.skipped_duplicate_count += 1
                result.warnings.append(f"row {index}: signal after as_of_date was skipped")
                continue
            valid_records.append((index, record, observed_at))
        except Exception as error:
            _row_error(result, index, error)
    signals: list[TickerSignal] = []
    if source_type == ImportSourceType.TOSS_SIGNAL:
        try:
            signals = _toss_signals_from_records(valid_records, cutoff)
        except Exception as error:
            _row_error(result, valid_records[0][0] if valid_records else 0, error)
    else:
        for index, record, observed_at in valid_records:
            try:
                signals.append(_signal_from_record(source_type, record, cutoff, observed_at))
            except Exception as error:
                _row_error(result, index, error)
    ids = repository.save_ticker_signals(signals)
    result.saved_count = len(ids)
    result.skipped_duplicate_count += len(signals) - len(ids)
    return result


def run_unified_import(
    repository: RiskRepository,
    *,
    price_history_file: str | Path | None = None,
    nasdaq_noncompliant_file: str | Path | None = None,
    news_signal_file: str | Path | None = None,
    dilution_signal_file: str | Path | None = None,
    toss_signal_file: str | Path | None = None,
    flow_signal_file: str | Path | None = None,
    as_of_date: date | None = None,
) -> ImportRun:
    sources: list[tuple[str | Path | None, Callable[[], ImportSourceResult]]] = [
        (price_history_file, lambda: import_price_history_file(repository, price_history_file)),  # type: ignore[arg-type]
        (nasdaq_noncompliant_file, lambda: import_compliance_file(repository, nasdaq_noncompliant_file, as_of_date)),  # type: ignore[arg-type]
        (news_signal_file, lambda: import_signal_file(repository, news_signal_file, ImportSourceType.NEWS_SIGNAL, as_of_date)),  # type: ignore[arg-type]
        (dilution_signal_file, lambda: import_signal_file(repository, dilution_signal_file, ImportSourceType.DILUTION_SIGNAL, as_of_date)),  # type: ignore[arg-type]
        (toss_signal_file, lambda: import_signal_file(repository, toss_signal_file, ImportSourceType.TOSS_SIGNAL, as_of_date)),  # type: ignore[arg-type]
        (flow_signal_file, lambda: import_signal_file(repository, flow_signal_file, ImportSourceType.FLOW_SIGNAL, as_of_date)),  # type: ignore[arg-type]
    ]
    results = [loader() for path, loader in sources if path is not None]
    if not results:
        status = ImportRunStatus.FAILED
        notes = ["No import files were specified."]
    elif all(item.error_count == 0 for item in results):
        status, notes = ImportRunStatus.COMPLETED, []
    elif any(item.saved_count or item.skipped_duplicate_count or item.error_count == 0 for item in results):
        status, notes = ImportRunStatus.PARTIAL, []
    else:
        status, notes = ImportRunStatus.FAILED, []
    run = ImportRun(
        as_of_date=as_of_date, status=status, source_results=results, notes=notes,
        completed_at=datetime.now(),
    )
    repository.save_import_run(run)
    return run


def _start_source(path: str | Path, source_type: ImportSourceType, required: set[str]):
    result = ImportSourceResult(source_type=source_type, file_path=str(path))
    try:
        records = load_import_records(path, required)
        result.row_count = len(records)
        return result, records
    except Exception as error:
        result.error_count = 1
        result.errors.append(str(error))
        return result, None


def _signal_from_record(source_type: ImportSourceType, record: dict[str, Any], cutoff: date, observed_at):
    mapping = {
        ImportSourceType.NEWS_SIGNAL: SignalType.NEWS,
        ImportSourceType.DILUTION_SIGNAL: SignalType.DILUTION,
        ImportSourceType.TOSS_SIGNAL: SignalType.TOSS_PORTFOLIO,
        ImportSourceType.FLOW_SIGNAL: SignalType.FOREIGN_INSTITUTION_FLOW,
    }
    signal_type = mapping[source_type]
    event = str(record.get("event_type") or record.get("change_type") or "UNKNOWN").strip().upper()
    direction = SignalDirection.NEUTRAL
    severity = SignalSeverity.MEDIUM
    if source_type == ImportSourceType.NEWS_SIGNAL:
        negative_events = {"LAWSUIT", "REGULATORY", "INVESTIGATION"}
        positive_events = {"EARNINGS_BEAT", "GUIDANCE_RAISE", "CONTRACT", "FDA_APPROVAL", "PARTNERSHIP"}
        sentiment = str(record.get("sentiment") or "").upper()
        materiality = str(record.get("materiality") or "").upper()
        if event in negative_events or (materiality == "HIGH" and sentiment == "NEGATIVE"):
            direction, severity = SignalDirection.NEGATIVE, SignalSeverity.HIGH
        elif materiality == "HIGH" and sentiment == "POSITIVE":
            direction, severity = SignalDirection.POSITIVE, SignalSeverity.HIGH
        elif event in positive_events:
            direction, severity = SignalDirection.POSITIVE, SignalSeverity.MEDIUM
        else:
            direction, severity = SignalDirection.NEUTRAL, SignalSeverity.LOW
    elif source_type == ImportSourceType.DILUTION_SIGNAL:
        direction = SignalDirection.NEUTRAL if event == "OFFERING_CLOSED" else SignalDirection.NEGATIVE
        severity = SignalSeverity(str(record.get("severity") or ("MEDIUM" if event == "OFFERING_CLOSED" else "HIGH")).upper())
    else:
        foreign, institution = float(record.get("foreign_net_buy") or 0), float(record.get("institution_net_buy") or 0)
        direction = SignalDirection.POSITIVE if foreign > 0 and institution > 0 else SignalDirection.NEGATIVE if foreign < 0 and institution < 0 else SignalDirection.NEUTRAL
        event = "FLOW"
    source_names = {
        SignalType.NEWS: "news_signal_file", SignalType.DILUTION: "dilution_signal_file",
        SignalType.TOSS_PORTFOLIO: "toss_signal_file", SignalType.FOREIGN_INSTITUTION_FLOW: "flow_signal_file",
    }
    return TickerSignal(
        ticker=str(record["ticker"]), signal_type=signal_type, as_of_date=cutoff, observed_at=observed_at,
        direction=direction, severity=severity, score_delta=calculate_signal_score(direction, severity, signal_type),
        source_name=source_names[signal_type], title=_optional(record, "title") or event.replace("_", " ").title(),
        summary=_optional(record, "summary") or _optional(record, "details"), raw_event_type=event, metadata=dict(record),
        reasons=[f"{signal_type.value} signal: {event}"],
    )


def _toss_signals_from_records(
    records: list[tuple[int, dict[str, Any], date | datetime]], cutoff: date
) -> list[TickerSignal]:
    groups: dict[tuple[str, date | datetime], list[dict[str, Any]]] = defaultdict(list)
    for _, record, observed_at in records:
        groups[(str(record["ticker"]).strip().upper(), observed_at)].append(record)
    signals: list[TickerSignal] = []
    for (ticker, observed_at), items in groups.items():
        changes = [str(item.get("change_type") or "").strip().upper() for item in items]
        buy_count = sum(item in {"BUY", "ADD", "INCREASE"} for item in changes)
        exit_count = sum(item in {"EXIT", "SELL", "REDUCE"} for item in changes)
        holding_count = sum(float(item.get("holding_weight") or 0) > 0 for item in items)
        if exit_count >= 2:
            direction, severity, reason = SignalDirection.NEGATIVE, SignalSeverity.HIGH, "Multiple top investors reduced or exited"
        elif buy_count >= 2:
            direction, severity, reason = SignalDirection.POSITIVE, SignalSeverity.HIGH, "Multiple top investors added positions"
        elif holding_count >= 2:
            direction, severity, reason = SignalDirection.POSITIVE, SignalSeverity.MEDIUM, "Multiple top investors hold positions"
        else:
            direction, severity, reason = SignalDirection.NEUTRAL, SignalSeverity.LOW, "Single-investor Toss portfolio reference"
        signals.append(TickerSignal(
            ticker=ticker, signal_type=SignalType.TOSS_PORTFOLIO, as_of_date=cutoff, observed_at=observed_at,
            direction=direction, severity=severity,
            score_delta=calculate_signal_score(direction, severity, SignalType.TOSS_PORTFOLIO),
            source_name="toss_signal_file", title="Toss top investor portfolio aggregate",
            raw_event_type="TOSS_AGGREGATE", metadata={"records": items}, reasons=[reason],
        ))
    return signals


def _row_error(result: ImportSourceResult, index: int, error: Exception) -> None:
    result.error_count += 1
    result.errors.append(f"row {index}: {error}")


def _empty_to_none(record: dict[str, Any]) -> dict[str, Any]:
    return {key: None if value == "" else value for key, value in record.items()}


def _optional(record: dict[str, Any], key: str) -> str | None:
    value = record.get(key)
    return str(value).strip() or None if value is not None else None
