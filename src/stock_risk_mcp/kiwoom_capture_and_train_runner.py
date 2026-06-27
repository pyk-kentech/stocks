from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
import time

from stock_risk_mcp.historical_market_data_capture_runner import run_historical_market_data_real_capture
from stock_risk_mcp.historical_market_data_manifest_engine import build_historical_ohlcv_dataset_manifest, load_historical_ohlcv_dataset_manifest
from stock_risk_mcp.historical_market_data_models import (
    HistoricalChartRawResponse,
    HistoricalChartRequestSpec,
    HistoricalChartCaptureRunResult,
    HistoricalOhlcvRow,
    HistoricalMarketDataPipelineInput,
    HistoricalMarketDataReadinessStatus,
    HistoricalMarketDataTransportKind,
)
from stock_risk_mcp.historical_market_data_normalizer import normalize_historical_ohlcv_rows
from stock_risk_mcp.historical_market_data_transport import RealKiwoomChartTransport
from stock_risk_mcp.historical_market_data_guard import validate_safe_local_root
from stock_risk_mcp.kiwoom_oauth_engine import build_kiwoom_oauth_request, issue_kiwoom_oauth_token
from stock_risk_mcp.kiwoom_oauth_models import KiwoomCredentialRef, KiwoomEnvironment, KiwoomOAuthStatus
from stock_risk_mcp.offline_strategy_template_catalog import build_offline_strategy_template_catalog
from stock_risk_mcp.offline_strategy_integration_engine import build_offline_strategy_pipeline
from stock_risk_mcp.offline_strategy_models import (
    OfflineStrategyDirection,
    OfflineStrategyPipelineInput,
    OfflineStrategyWalkForwardMode,
)


def _kiwoom_base_url(environment: KiwoomEnvironment) -> str:
    return "https://mockapi.kiwoom.com" if environment == KiwoomEnvironment.MOCK else "https://api.kiwoom.com"


def _read_bearer_header_from_token_ref(token_ref_path: str) -> str:
    payload = json.loads(Path(token_ref_path).read_text(encoding="utf-8"))
    token = str(payload.get("token") or "").strip()
    token_type = str(payload.get("token_type") or "Bearer").strip()
    if not token:
        raise ValueError("token ref did not contain token")
    return f"{token_type} {token}"


def _resolve_walk_forward_mode(value: str | None) -> OfflineStrategyWalkForwardMode:
    if not value:
        return OfflineStrategyWalkForwardMode.ANCHORED_CHRONOLOGICAL_WALK_FORWARD
    normalized = str(value).strip().upper()
    aliases = {
        "ANCHORED": OfflineStrategyWalkForwardMode.ANCHORED_CHRONOLOGICAL_WALK_FORWARD,
        "ANCHORED_CHRONOLOGICAL_WALK_FORWARD": OfflineStrategyWalkForwardMode.ANCHORED_CHRONOLOGICAL_WALK_FORWARD,
        "ROLLING": OfflineStrategyWalkForwardMode.ROLLING_CHRONOLOGICAL_WALK_FORWARD,
        "ROLLING_CHRONOLOGICAL_WALK_FORWARD": OfflineStrategyWalkForwardMode.ROLLING_CHRONOLOGICAL_WALK_FORWARD,
    }
    return aliases.get(normalized, OfflineStrategyWalkForwardMode.ANCHORED_CHRONOLOGICAL_WALK_FORWARD)


def _resolve_direction(value: str | None) -> OfflineStrategyDirection:
    if not value:
        return OfflineStrategyDirection.LONG_ONLY
    normalized = str(value).strip().upper()
    aliases = {
        "LONG_ONLY": OfflineStrategyDirection.LONG_ONLY,
        "SHORT_RESEARCH_ONLY": OfflineStrategyDirection.SHORT_RESEARCH_ONLY,
        "AVOID_LONG_ONLY": OfflineStrategyDirection.AVOID_LONG_ONLY,
    }
    return aliases.get(normalized, OfflineStrategyDirection.LONG_ONLY)


def _resolve_requested_templates(
    *,
    requested_template_ids: list[str] | None,
    strategy_families: list[str] | None,
    direction: OfflineStrategyDirection,
) -> tuple[list[str], dict[str, object]]:
    if requested_template_ids:
        normalized = [item.strip().upper() for item in requested_template_ids if item and item.strip()]
        return normalized, {
            "requested_strategy_families": sorted({item.strip().upper() for item in (strategy_families or []) if item and item.strip()}),
            "supported_strategy_families": [],
            "unsupported_strategy_families": [],
            "skipped_strategy_families": [],
        }
    catalog = build_offline_strategy_template_catalog()
    requested_families = sorted({item.strip().upper() for item in (strategy_families or []) if item and item.strip()})
    family_aliases = {
        "MACD_RSI": "MACD_RSI_MOMENTUM",
        "MACD_RSI_MOMENTUM": "MACD_RSI_MOMENTUM",
        "RSI_OVERSOLD_REBOUND": "RSI_OVERSOLD_REBOUND",
        "VOLUME_LONG_CANDLE_PULLBACK": "VOLUME_PULLBACK_LONG",
        "VOLUME_PULLBACK_LONG": "VOLUME_PULLBACK_LONG",
        "RANGE_BREAKOUT": None,
        "ADX_TREND_SCALPING": None,
    }
    supported_families: list[str] = []
    unsupported_families: list[str] = []
    skipped_strategy_families: list[str] = []
    family_filters: set[str] = set()
    for family in requested_families:
        mapped = family_aliases.get(family, family if family in {template.family.value for template in catalog} else None)
        if mapped is None:
            unsupported_families.append(family)
            skipped_strategy_families.append(f"{family}:UNSUPPORTED_TEMPLATE_FAMILY")
            continue
        family_filters.add(mapped)
        supported_families.append(family)
    template_ids: list[str] = []
    for template in catalog:
        if template.direction != direction:
            continue
        if family_filters and template.family.value not in family_filters:
            continue
        template_ids.append(template.template_id.value)
    return template_ids, {
        "requested_strategy_families": requested_families,
        "supported_strategy_families": sorted(supported_families),
        "unsupported_strategy_families": sorted(unsupported_families),
        "skipped_strategy_families": sorted(skipped_strategy_families),
    }


def _symbol_status_summary(
    pipeline_input: HistoricalMarketDataPipelineInput,
    capture_result: HistoricalChartCaptureRunResult,
    manifest_rows: list[HistoricalOhlcvRow],
) -> list[dict[str, object]]:
    task_by_symbol = {task.request_id.split("-")[1]: task for task in capture_result.task_results if "-" in task.request_id}
    rows_by_symbol: dict[str, list[HistoricalOhlcvRow]] = defaultdict(list)
    for row in manifest_rows:
        rows_by_symbol[row.provider_symbol].append(row)
    summaries: list[dict[str, object]] = []
    for spec in pipeline_input.request_specs:
        rows = sorted(rows_by_symbol.get(spec.provider_symbol, []), key=lambda item: item.observed_at)
        task = task_by_symbol.get(spec.provider_symbol)
        normalized_row_count = len(rows)
        partial = bool(normalized_row_count and task and task.blocked_reasons)
        status = (
            "PARTIAL_CAPTURE_COMPLETED"
            if partial
            else "COMPLETED"
            if normalized_row_count
            else "FAILED"
        )
        summaries.append(
            {
                "requested_symbol": spec.provider_symbol,
                "raw_lake_path": str(Path(pipeline_input.raw_lake_root) / f"{spec.request_id.lower()}-response.json"),
                "provider_row_count": int(getattr(task, "row_count", 0) or 0),
                "normalized_row_count": normalized_row_count,
                "date_min": rows[0].observed_at.date().isoformat() if rows else None,
                "date_max": rows[-1].observed_at.date().isoformat() if rows else None,
                "status": status,
                "provider_return_code": getattr(task, "provider_return_code", None),
                "provider_return_msg": getattr(task, "provider_return_msg", None),
            }
        )
    return summaries


def _provider_limit_hit(provider_return_code: int | None, provider_return_msg: str | None) -> bool:
    if provider_return_code == 5:
        return True
    return "허용된 요청 개수" in str(provider_return_msg or "")


def _capture_state_path(pipeline_input: HistoricalMarketDataPipelineInput) -> Path:
    dataset_dir = validate_safe_local_root(pipeline_input.store_root) / pipeline_input.dataset_id.lower()
    dataset_dir.mkdir(parents=True, exist_ok=True)
    return dataset_dir / "kiwoom_capture_state.json"


def _load_capture_state(path: str | None) -> dict[str, object] | None:
    if not path:
        return None
    state_path = Path(path)
    if not state_path.exists():
        return None
    return json.loads(state_path.read_text(encoding="utf-8"))


def _write_capture_state(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _build_single_symbol_pipeline(
    pipeline_input: HistoricalMarketDataPipelineInput,
    spec: HistoricalChartRequestSpec,
) -> HistoricalMarketDataPipelineInput:
    return pipeline_input.model_copy(
        update={
            "dataset_id": f"{pipeline_input.dataset_id}-{spec.provider_symbol}",
            "request_specs": [spec],
        }
    )


def _within_requested_window(spec: HistoricalChartRequestSpec, observed_at) -> bool:
    if spec.start_at is not None and observed_at < spec.start_at:
        return False
    if spec.end_at is not None and observed_at > spec.end_at:
        return False
    return True


def _raw_lake_path(pipeline_input: HistoricalMarketDataPipelineInput, spec: HistoricalChartRequestSpec) -> Path:
    return Path(pipeline_input.raw_lake_root) / f"{spec.request_id.lower()}-response.json"


def _iso_date_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.date().isoformat()


def _is_weekday(value: date) -> bool:
    return value.weekday() < 5


def _is_known_boundary_non_trading_day(value: date) -> bool:
    return (value.month, value.day) == (1, 1)


def _first_effective_trading_date(requested_start: date | None, cached_start: date | None) -> date | None:
    if requested_start is None:
        return cached_start
    if (
        _is_known_boundary_non_trading_day(requested_start)
        and cached_start is not None
        and 0 <= (cached_start - requested_start).days <= 4
    ):
        return cached_start or requested_start
    if _is_weekday(requested_start):
        return requested_start
    if cached_start is not None and 0 <= (cached_start - requested_start).days <= 4:
        return cached_start
    probe = requested_start
    for _ in range(7):
        if _is_weekday(probe):
            return probe
        probe += timedelta(days=1)
    return cached_start or requested_start


def _last_effective_trading_date(requested_end: date | None, cached_end: date | None) -> date | None:
    if requested_end is None:
        return cached_end
    if _is_weekday(requested_end):
        return requested_end
    if cached_end is not None and 0 <= (requested_end - cached_end).days <= 4:
        return cached_end
    probe = requested_end
    for _ in range(7):
        if _is_weekday(probe):
            return probe
        probe -= timedelta(days=1)
    return cached_end or requested_end


def _count_weekdays(start: date, end: date) -> int:
    if end < start:
        return 0
    days = 0
    probe = start
    while probe <= end:
        if _is_weekday(probe):
            days += 1
        probe += timedelta(days=1)
    return days


def _build_cache_coverage_summary(
    spec: HistoricalChartRequestSpec,
    rows: list[HistoricalOhlcvRow],
) -> dict[str, object]:
    requested_start = spec.start_at.date() if spec.start_at is not None else None
    requested_end = spec.end_at.date() if spec.end_at is not None else None
    cached_start = rows[0].observed_at.date() if rows else None
    cached_end = rows[-1].observed_at.date() if rows else None
    effective_requested_start = _first_effective_trading_date(requested_start, cached_start)
    effective_requested_end = _last_effective_trading_date(requested_end, cached_end)
    calendar_leading_gap_days = max((cached_start - requested_start).days, 0) if requested_start and cached_start else None
    calendar_trailing_gap_days = max((requested_end - cached_end).days, 0) if requested_end and cached_end else None
    trading_leading_gap_days = (
        _count_weekdays(effective_requested_start, cached_start - timedelta(days=1))
        if effective_requested_start and cached_start and cached_start > effective_requested_start
        else 0 if effective_requested_start and cached_start
        else None
    )
    trading_trailing_gap_days = (
        _count_weekdays(cached_end + timedelta(days=1), effective_requested_end)
        if effective_requested_end and cached_end and cached_end < effective_requested_end
        else 0 if effective_requested_end and cached_end
        else None
    )
    calendar_coverage_ratio = None
    trading_coverage_ratio = None
    if requested_start and requested_end and cached_start and cached_end:
        requested_days = max((requested_end - requested_start).days + 1, 1)
        covered_start = max(requested_start, cached_start)
        covered_end = min(requested_end, cached_end)
        covered_days = max((covered_end - covered_start).days + 1, 0) if covered_end >= covered_start else 0
        calendar_coverage_ratio = round(min(covered_days / requested_days, 1.0), 6)
    if effective_requested_start and effective_requested_end and cached_start and cached_end:
        requested_trading_days = max(_count_weekdays(effective_requested_start, effective_requested_end), 1)
        covered_trading_start = max(effective_requested_start, cached_start)
        covered_trading_end = min(effective_requested_end, cached_end)
        covered_trading_days = (
            _count_weekdays(covered_trading_start, covered_trading_end)
            if covered_trading_end >= covered_trading_start
            else 0
        )
        trading_coverage_ratio = round(min(covered_trading_days / requested_trading_days, 1.0), 6)
    if not rows:
        coverage_status = "CACHE_COVERAGE_GAP"
        reuse_reason = "CACHE_EXISTS_BUT_NO_NORMALIZED_ROWS_IN_REQUESTED_RANGE"
        reuse_warning = "CACHE_ROWS_MISSING_FOR_REQUESTED_DATE_RANGE"
        coverage_basis = "TRADING_DAYS"
    elif (trading_leading_gap_days or 0) == 0 and (trading_trailing_gap_days or 0) == 0:
        if (calendar_leading_gap_days or 0) > 0 or (calendar_trailing_gap_days or 0) > 0:
            coverage_status = "CALENDAR_EDGE_GAP_ONLY"
            reuse_reason = "CACHE_REUSED_WITH_FULL_TRADING_COVERAGE"
            reuse_warning = "CALENDAR_EDGE_NON_TRADING_GAPS_ONLY"
        else:
            coverage_status = "FULL_TRADING_COVERAGE"
            reuse_reason = "CACHE_REUSED_WITH_FULL_TRADING_COVERAGE"
            reuse_warning = None
        coverage_basis = "TRADING_DAYS"
    else:
        coverage_status = "TRADING_COVERAGE_GAP"
        reuse_reason = "CACHE_REUSED_WITH_PARTIAL_TRADING_COVERAGE"
        reuse_warning = "CACHE_TRADING_DATE_RANGE_DOES_NOT_FULLY_COVER_REQUEST"
        coverage_basis = "TRADING_DAYS"
    return {
        "cache_found": True,
        "cache_reused": bool(rows),
        "cache_coverage_status": coverage_status,
        "requested_date_min": requested_start.isoformat() if requested_start else None,
        "requested_date_max": requested_end.isoformat() if requested_end else None,
        "effective_requested_trading_date_min": effective_requested_start.isoformat() if effective_requested_start else None,
        "effective_requested_trading_date_max": effective_requested_end.isoformat() if effective_requested_end else None,
        "cached_date_min": cached_start.isoformat() if cached_start else None,
        "cached_date_max": cached_end.isoformat() if cached_end else None,
        "calendar_leading_gap_days": calendar_leading_gap_days,
        "calendar_trailing_gap_days": calendar_trailing_gap_days,
        "trading_leading_gap_days": trading_leading_gap_days,
        "trading_trailing_gap_days": trading_trailing_gap_days,
        "leading_gap_days": trading_leading_gap_days,
        "trailing_gap_days": trading_trailing_gap_days,
        "calendar_coverage_ratio": calendar_coverage_ratio,
        "trading_coverage_ratio": trading_coverage_ratio,
        "coverage_ratio": trading_coverage_ratio,
        "coverage_basis": coverage_basis,
        "cache_reuse_reason": reuse_reason,
        "cache_reuse_warning": reuse_warning,
    }


def _build_backfill_intervals(coverage_summary: dict[str, object]) -> list[dict[str, str]]:
    intervals: list[dict[str, str]] = []
    requested_min = coverage_summary.get("effective_requested_trading_date_min") or coverage_summary.get("requested_date_min")
    requested_max = coverage_summary.get("effective_requested_trading_date_max") or coverage_summary.get("requested_date_max")
    cached_min = coverage_summary.get("cached_date_min")
    cached_max = coverage_summary.get("cached_date_max")
    if requested_min and cached_min and coverage_summary.get("trading_leading_gap_days"):
        intervals.append({"interval_kind": "LEADING_GAP", "start_date": str(requested_min), "end_date": str(cached_min)})
    if cached_max and requested_max and coverage_summary.get("trading_trailing_gap_days"):
        intervals.append({"interval_kind": "TRAILING_GAP", "start_date": str(cached_max), "end_date": str(requested_max)})
    return intervals


def _merge_ohlcv_rows(existing_rows: list[HistoricalOhlcvRow], new_rows: list[HistoricalOhlcvRow]) -> list[HistoricalOhlcvRow]:
    merged: dict[tuple[str, datetime], HistoricalOhlcvRow] = {}
    for row in existing_rows + new_rows:
        merged[(row.provider_symbol, row.observed_at)] = row
    return sorted(merged.values(), key=lambda item: (item.instrument_id, item.observed_at))


def _score_ranking_row(
    *,
    actual_trade_count: int,
    signal_count_before_filters: int,
    rejection_reason_count: int,
    profit_factor: float | None,
    max_drawdown: float | None,
) -> float:
    return (
        float(actual_trade_count) * 100.0
        + float(signal_count_before_filters) * 1.0
        - float(rejection_reason_count) * 10.0
        + float(profit_factor or 0.0) * 5.0
        - float(max_drawdown or 0.0) * 100.0
    )


def _build_symbol_family_ranking_rows(
    *,
    training_symbols: list[str],
    training_result,
    symbol_results: list[dict[str, object]],
) -> list[dict[str, object]]:
    if training_result is None:
        return []
    coverage_by_symbol = {item["requested_symbol"]: item for item in symbol_results}
    candidates_by_id = {candidate.candidate_id: candidate for candidate in training_result.candidates}
    metrics_by_id = {metric.candidate_id: metric for metric in training_result.metric_summaries}
    rows: list[dict[str, object]] = []
    for decision in training_result.promotion_decisions:
        candidate = candidates_by_id.get(decision.candidate_id)
        metric = metrics_by_id.get(decision.candidate_id)
        diagnostics = dict(decision.diagnostics or {})
        for symbol in training_symbols or [None]:
            coverage = coverage_by_symbol.get(symbol) if symbol else None
            row = {
                "symbol": symbol,
                "strategy_family": decision.family.value,
                "internal_family": candidate.family.value if candidate is not None else decision.family.value,
                "candidate_id": decision.candidate_id,
                "promotion_status": decision.status.value,
                "rejection_reasons": list(decision.reasons),
                "actual_trade_count": int(diagnostics.get("actual_trade_count") or (metric.trade_count if metric else 0) or 0),
                "signal_count_before_filters": int(diagnostics.get("signal_count_before_filters") or 0),
                "entry_signal_count": int(diagnostics.get("entry_signal_count") or 0),
                "exit_signal_count": int(diagnostics.get("exit_signal_count") or 0),
                "profit_factor": float(metric.profit_factor) if metric is not None else None,
                "win_rate": float(metric.win_rate) if metric is not None else None,
                "max_drawdown": float(metric.max_drawdown) if metric is not None else None,
                "coverage_status": coverage.get("status") if coverage else None,
                "coverage_basis": coverage.get("coverage_basis") if coverage else None,
            }
            row["score"] = _score_ranking_row(
                actual_trade_count=row["actual_trade_count"],
                signal_count_before_filters=row["signal_count_before_filters"],
                rejection_reason_count=len(row["rejection_reasons"]),
                profit_factor=row["profit_factor"],
                max_drawdown=row["max_drawdown"],
            )
            rows.append(row)
    return sorted(rows, key=lambda item: (-float(item["score"]), item["candidate_id"], str(item.get("symbol") or "")))


def _load_cached_rows(
    pipeline_input: HistoricalMarketDataPipelineInput,
    spec: HistoricalChartRequestSpec,
) -> tuple[list[HistoricalOhlcvRow], dict[str, object] | None]:
    path = _raw_lake_path(pipeline_input, spec)
    if not path.exists():
        return [], None
    response = HistoricalChartRawResponse.model_validate_json(path.read_text(encoding="utf-8"))
    try:
        normalized = normalize_historical_ohlcv_rows(pipeline_input.dataset_id, [response])
    except Exception:
        return [], None
    rows = [
        row
        for row in normalized
        if row.provider_symbol == spec.provider_symbol and _within_requested_window(spec, row.observed_at)
    ]
    meta = response.raw_payload.get("_capture_meta") if isinstance(response.raw_payload, dict) else None
    return rows, meta if isinstance(meta, dict) else None


class _RateLimitedTransport:
    transport_kind = HistoricalMarketDataTransportKind.REAL_KIWOOM_CHART

    def __init__(self, delegate: RealKiwoomChartTransport, *, request_sleep_seconds: float) -> None:
        self._delegate = delegate
        self.base_url = getattr(delegate, "base_url", None)
        self._request_sleep_seconds = max(float(request_sleep_seconds), 0.0)
        self._request_count = 0

    def execute(self, preview, *, auth_header=None):
        if self._request_count > 0 and self._request_sleep_seconds > 0:
            time.sleep(self._request_sleep_seconds)
        self._request_count += 1
        return self._delegate.execute(preview, auth_header=auth_header)


def run_historical_market_data_real_capture_and_manifest(
    pipeline_input: HistoricalMarketDataPipelineInput,
    *,
    environment: KiwoomEnvironment,
    token_store_root: str,
    force_refresh_token: bool = False,
) -> tuple[HistoricalChartCaptureRunResult, dict[str, object]]:
    if pipeline_input.real_capture_config is None or pipeline_input.real_capture_config.credential_ref is None:
        raise ValueError("real capture credential ref is required")
    historical_ref = pipeline_input.real_capture_config.credential_ref
    oauth_credential_ref = KiwoomCredentialRef(
        credential_id=historical_ref.credential_ref_id,
        credential_ref_dir=historical_ref.credential_ref_dir,
        appkey_ref_path=historical_ref.appkey_ref_path,
        secretkey_ref_path=historical_ref.secretkey_ref_path,
    )
    oauth_request = build_kiwoom_oauth_request(
        environment=environment,
        credential_ref=oauth_credential_ref,
        token_store_root=token_store_root,
        allow_real_network=pipeline_input.opt_in.allow_real_chart_capture,
        allow_token_issue=True,
        acknowledge_readonly_only=pipeline_input.opt_in.acknowledge_readonly_only,
        acknowledge_user_initiated=pipeline_input.opt_in.acknowledge_user_initiated,
        acknowledge_credential_redaction=pipeline_input.opt_in.acknowledge_credential_redaction,
        force_refresh_token=force_refresh_token,
    )
    token_response = issue_kiwoom_oauth_token(oauth_request)
    if token_response.status not in {KiwoomOAuthStatus.TOKEN_ISSUED, KiwoomOAuthStatus.TOKEN_CACHE_HIT} or token_response.token_ref is None:
        blocked = HistoricalChartCaptureRunResult.model_validate(
            {
                "run_id": f"{pipeline_input.dataset_id}-REAL-CAPTURE-RUN",
                "dataset_id": pipeline_input.dataset_id,
                "readiness_status": HistoricalMarketDataReadinessStatus.BLOCKED_AUTH_OR_TOKEN.value,
                "task_results": [
                    {
                        "task_id": f"{pipeline_input.dataset_id}-BLOCKED",
                        "request_id": f"{pipeline_input.dataset_id}-BLOCKED",
                        "execution_decision": "BLOCKED",
                        "blocked_reasons": [token_response.status.value],
                    }
                ],
            }
        )
        return blocked, {
            "token_status": token_response.status.value,
            "stage": token_response.stage,
            "kiwoom_environment": token_response.kiwoom_environment.value,
            "endpoint_base_url": token_response.endpoint_base_url,
            "endpoint_path": token_response.endpoint_path,
            "http_status_code": token_response.http_status_code,
            "provider_return_code": token_response.provider_return_code,
            "provider_return_msg": token_response.provider_return_msg,
            "transport_error_type": token_response.transport_error_type,
            "transport_error_message_redacted": token_response.transport_error_message_redacted,
            "token_written": token_response.token_written,
            "chart_request_started": False,
            "manifest_written": False,
            "training_started": False,
        }
    transport = RealKiwoomChartTransport(
        timeout_seconds=pipeline_input.real_capture_config.timeout_seconds,
        base_url=_kiwoom_base_url(environment),
    )
    result = run_historical_market_data_real_capture(
        pipeline_input,
        transport=transport,
        auth_header=_read_bearer_header_from_token_ref(token_response.token_ref.token_ref_path),
    )
    return result, {
        "token_status": token_response.status.value,
        "stage": token_response.stage,
        "kiwoom_environment": token_response.kiwoom_environment.value,
        "endpoint_base_url": token_response.endpoint_base_url,
        "endpoint_path": token_response.endpoint_path,
        "http_status_code": token_response.http_status_code,
        "provider_return_code": token_response.provider_return_code,
        "provider_return_msg": token_response.provider_return_msg,
        "transport_error_type": token_response.transport_error_type,
        "transport_error_message_redacted": token_response.transport_error_message_redacted,
        "token_written": token_response.token_written,
        "chart_request_started": True,
        "token_ref_path": token_response.token_ref.token_ref_path,
    }


def run_kiwoom_ka10081_capture_and_train(
    pipeline_input: HistoricalMarketDataPipelineInput,
    *,
    environment: KiwoomEnvironment,
    token_store_root: str,
    training_output_root: str,
    training_handoff_mode: str = "persisted_manifest",
    requested_template_ids: list[str] | None = None,
    asset_liquidity_profile: str = "LARGE_CAP",
    strategy_families: list[str] | None = None,
    search_mode: str | None = None,
    walk_forward_mode: str | None = None,
    promotion_profile: str | None = None,
    fill_policy: str | None = None,
    direction: str | None = None,
    request_sleep_seconds: float = 0.25,
    symbol_sleep_seconds: float = 0.5,
    max_symbols_per_run: int = 0,
    stop_on_provider_limit: bool = True,
    resume_from_capture_state: str | None = None,
    reuse_existing_raw_lake: bool = False,
    allow_training_on_partial_capture: bool = True,
    backfill_cache_gaps: bool = False,
    max_backfill_pages_per_symbol: int | None = None,
    prefer_full_coverage_training: bool = True,
) -> dict[str, object]:
    resolved_direction = _resolve_direction(direction)
    resolved_walk_forward_mode = _resolve_walk_forward_mode(walk_forward_mode)
    resolved_template_ids, family_resolution = _resolve_requested_templates(
        requested_template_ids=requested_template_ids,
        strategy_families=strategy_families,
        direction=resolved_direction,
    )
    requested_specs = list(pipeline_input.request_specs)
    state_path = _capture_state_path(pipeline_input)
    prior_state = _load_capture_state(resume_from_capture_state)
    previous_completed = set(prior_state.get("completed_symbols", [])) if isinstance(prior_state, dict) else set()
    previous_partial = set(prior_state.get("partial_symbols", [])) if isinstance(prior_state, dict) else set()
    previous_failed = set(prior_state.get("failed_symbols", [])) if isinstance(prior_state, dict) else set()
    fetched_now: list[str] = []
    reused_from_cache: list[str] = []
    skipped_completed: list[str] = []
    retried: list[str] = []
    failed_again: list[str] = []
    completed_symbols: list[str] = []
    partial_symbols: list[str] = []
    failed_symbols: list[str] = []
    skipped_symbols: list[str] = []
    symbol_results: list[dict[str, object]] = []
    aggregate_rows: list[HistoricalOhlcvRow] = []
    raw_lake_paths: list[str] = []
    cache_coverage_gaps: list[str] = []
    symbols_with_full_coverage: list[str] = []
    symbols_with_partial_coverage: list[str] = []
    backfill_completed_symbols: list[str] = []
    backfill_partial_symbols: list[str] = []
    backfill_failed_symbols: list[str] = []
    backfill_intervals_by_symbol: dict[str, list[dict[str, str]]] = {}
    post_backfill_coverage_by_symbol: dict[str, str] = {}
    backfill_attempted_any = False
    oauth_summary: dict[str, object] = {
        "token_status": None,
        "stage": "NOT_STARTED",
        "kiwoom_environment": environment.value,
        "endpoint_base_url": _kiwoom_base_url(environment),
        "endpoint_path": "/oauth2/token",
        "http_status_code": None,
        "provider_return_code": None,
        "provider_return_msg": None,
        "transport_error_type": None,
        "transport_error_message_redacted": None,
        "token_written": False,
        "chart_request_started": False,
    }
    transport = _RateLimitedTransport(
        RealKiwoomChartTransport(
        timeout_seconds=pipeline_input.real_capture_config.timeout_seconds if pipeline_input.real_capture_config else 10,
        base_url=_kiwoom_base_url(environment),
        ),
        request_sleep_seconds=request_sleep_seconds,
    )
    auth_header: str | None = None
    token_ready = False
    provider_limit_hit = False
    partial_cache_used = False
    backfill_progress_made = False
    last_provider_return_code: int | None = None
    last_provider_return_msg: str | None = None
    can_resume = False

    def ensure_token() -> bool:
        nonlocal token_ready, auth_header, oauth_summary
        if token_ready:
            return True
        if pipeline_input.real_capture_config is None or pipeline_input.real_capture_config.credential_ref is None:
            return False
        historical_ref = pipeline_input.real_capture_config.credential_ref
        oauth_request = build_kiwoom_oauth_request(
            environment=environment,
            credential_ref=KiwoomCredentialRef(
                credential_id=historical_ref.credential_ref_id,
                credential_ref_dir=historical_ref.credential_ref_dir,
                appkey_ref_path=historical_ref.appkey_ref_path,
                secretkey_ref_path=historical_ref.secretkey_ref_path,
            ),
            token_store_root=token_store_root,
            allow_real_network=pipeline_input.opt_in.allow_real_chart_capture,
            allow_token_issue=True,
            acknowledge_readonly_only=pipeline_input.opt_in.acknowledge_readonly_only,
            acknowledge_user_initiated=pipeline_input.opt_in.acknowledge_user_initiated,
            acknowledge_credential_redaction=pipeline_input.opt_in.acknowledge_credential_redaction,
        )
        token_response = issue_kiwoom_oauth_token(oauth_request)
        oauth_summary = {
            "token_status": token_response.status.value,
            "stage": token_response.stage,
            "kiwoom_environment": token_response.kiwoom_environment.value,
            "endpoint_base_url": token_response.endpoint_base_url,
            "endpoint_path": token_response.endpoint_path,
            "http_status_code": token_response.http_status_code,
            "provider_return_code": token_response.provider_return_code,
            "provider_return_msg": token_response.provider_return_msg,
            "transport_error_type": token_response.transport_error_type,
            "transport_error_message_redacted": token_response.transport_error_message_redacted,
            "token_written": token_response.token_written,
            "chart_request_started": False,
            "token_ref_path": token_response.token_ref.token_ref_path if token_response.token_ref else None,
        }
        if token_response.status not in {KiwoomOAuthStatus.TOKEN_ISSUED, KiwoomOAuthStatus.TOKEN_CACHE_HIT} or token_response.token_ref is None:
            return False
        auth_header = _read_bearer_header_from_token_ref(str(token_response.token_ref.token_ref_path))
        token_ready = True
        return True

    specs_to_process = requested_specs
    if max_symbols_per_run and max_symbols_per_run > 0:
        specs_to_process = requested_specs[:max_symbols_per_run]
        skipped_symbols.extend(spec.provider_symbol for spec in requested_specs[max_symbols_per_run:])
    auto_backfill_cache_gaps = backfill_cache_gaps or bool(resume_from_capture_state and reuse_existing_raw_lake)

    for index, spec in enumerate(specs_to_process):
        if resume_from_capture_state or reuse_existing_raw_lake:
            cached_rows, _meta = _load_cached_rows(pipeline_input, spec)
            raw_lake_path = _raw_lake_path(pipeline_input, spec)
            if cached_rows or raw_lake_path.exists():
                cache_summary = _build_cache_coverage_summary(spec, cached_rows)
                backfill_intervals = _build_backfill_intervals(cache_summary)
                backfill_intervals_by_symbol[spec.provider_symbol] = backfill_intervals
                if cache_summary["cache_coverage_status"] in {"FULL_TRADING_COVERAGE", "CALENDAR_EDGE_GAP_ONLY"}:
                    raw_lake_paths.append(str(raw_lake_path))
                    if resume_from_capture_state and spec.provider_symbol in previous_completed:
                        skipped_completed.append(spec.provider_symbol)
                    else:
                        reused_from_cache.append(spec.provider_symbol)
                    symbols_with_full_coverage.append(spec.provider_symbol)
                    aggregate_rows.extend(cached_rows)
                    completed_symbols.append(spec.provider_symbol)
                    symbol_results.append(
                        {
                            "requested_symbol": spec.provider_symbol,
                            "raw_lake_path": str(raw_lake_path),
                            "provider_row_count": len(cached_rows),
                            "normalized_row_count": len(cached_rows),
                            "date_min": _iso_date_or_none(cached_rows[0].observed_at if cached_rows else None),
                            "date_max": _iso_date_or_none(cached_rows[-1].observed_at if cached_rows else None),
                            "status": "REUSED_FROM_CACHE_COMPLETED",
                            "provider_return_code": None,
                            "provider_return_msg": "REUSED_FROM_CACHE",
                            "backfill_required": False,
                            "backfill_intervals": [],
                            "backfill_reason": None,
                            "backfill_attempted": False,
                            "backfill_status": "NOT_REQUIRED",
                            "post_backfill_coverage_status": "FULL_TRADING_COVERAGE",
                            **cache_summary,
                        }
                    )
                    post_backfill_coverage_by_symbol[spec.provider_symbol] = "FULL_TRADING_COVERAGE"
                    continue
                cache_coverage_gaps.append(spec.provider_symbol)
                symbols_with_partial_coverage.append(spec.provider_symbol)
                backfill_required = bool(backfill_intervals or cache_summary["cache_coverage_status"] == "CACHE_COVERAGE_GAP")
                if auto_backfill_cache_gaps:
                    if spec.provider_symbol in previous_partial or spec.provider_symbol in previous_failed or (
                        resume_from_capture_state and spec.provider_symbol in previous_completed
                    ):
                        retried.append(spec.provider_symbol)
                    if not ensure_token():
                        backfill_attempted_any = True
                        backfill_failed_symbols.append(spec.provider_symbol)
                        failed_symbols.append(spec.provider_symbol)
                        failed_again.append(spec.provider_symbol)
                        symbol_results.append(
                            {
                                "requested_symbol": spec.provider_symbol,
                                "raw_lake_path": str(raw_lake_path),
                                "provider_row_count": len(cached_rows),
                                "normalized_row_count": len(cached_rows),
                                "date_min": _iso_date_or_none(cached_rows[0].observed_at if cached_rows else None),
                                "date_max": _iso_date_or_none(cached_rows[-1].observed_at if cached_rows else None),
                                "status": "BACKFILL_FAILED",
                                "provider_return_code": oauth_summary.get("provider_return_code"),
                                "provider_return_msg": oauth_summary.get("provider_return_msg"),
                                "backfill_required": backfill_required,
                                "backfill_intervals": backfill_intervals,
                                "backfill_reason": "CACHE_COVERAGE_GAP",
                                "backfill_attempted": True,
                                "backfill_status": "TOKEN_STAGE_FAILED",
                                "post_backfill_coverage_status": cache_summary["cache_coverage_status"],
                                **cache_summary,
                            }
                        )
                        break
                    backfill_attempted_any = True
                    fetched_now.append(spec.provider_symbol)
                    single_pipeline = _build_single_symbol_pipeline(pipeline_input, spec)
                    if max_backfill_pages_per_symbol:
                        single_pipeline = single_pipeline.model_copy(
                            update={
                                "real_capture_config": single_pipeline.real_capture_config.model_copy(
                                    update={"max_continuation_pages": int(max_backfill_pages_per_symbol)}
                                )
                            }
                        )
                    capture_result = run_historical_market_data_real_capture(single_pipeline, transport=transport, auth_header=auth_header)
                    first_task = capture_result.task_results[0] if capture_result.task_results else None
                    new_rows: list[HistoricalOhlcvRow] = []
                    if capture_result.manifest and capture_result.manifest.ohlcv_rows_path:
                        new_rows = [
                            HistoricalOhlcvRow.model_validate(item)
                            for item in json.loads(Path(capture_result.manifest.ohlcv_rows_path).read_text(encoding="utf-8"))
                        ]
                    merged_rows = _merge_ohlcv_rows(cached_rows, new_rows)
                    merged_coverage = _build_cache_coverage_summary(spec, merged_rows)
                    raw_lake_paths.append(str(raw_lake_path))
                    if merged_rows:
                        aggregate_rows.extend(merged_rows)
                    last_provider_return_code = getattr(first_task, "provider_return_code", None)
                    last_provider_return_msg = getattr(first_task, "provider_return_msg", None)
                    limit_now = _provider_limit_hit(last_provider_return_code, last_provider_return_msg)
                    provider_limit_hit = provider_limit_hit or limit_now
                    if len(merged_rows) > len(cached_rows):
                        backfill_progress_made = True
                    if merged_coverage["cache_coverage_status"] in {"FULL_TRADING_COVERAGE", "CALENDAR_EDGE_GAP_ONLY"}:
                        completed_symbols.append(spec.provider_symbol)
                        symbols_with_full_coverage.append(spec.provider_symbol)
                        backfill_completed_symbols.append(spec.provider_symbol)
                        status = "BACKFILL_COMPLETED"
                        post_backfill = merged_coverage["cache_coverage_status"]
                    elif merged_rows:
                        partial_symbols.append(spec.provider_symbol)
                        symbols_with_partial_coverage.append(spec.provider_symbol)
                        backfill_partial_symbols.append(spec.provider_symbol)
                        status = "BACKFILL_PARTIAL"
                        post_backfill = "TRADING_COVERAGE_GAP"
                    else:
                        failed_symbols.append(spec.provider_symbol)
                        failed_again.append(spec.provider_symbol)
                        backfill_failed_symbols.append(spec.provider_symbol)
                        status = "BACKFILL_FAILED"
                        post_backfill = "CACHE_COVERAGE_GAP"
                    post_backfill_coverage_by_symbol[spec.provider_symbol] = post_backfill
                    symbol_results.append(
                        {
                            "requested_symbol": spec.provider_symbol,
                            "raw_lake_path": str(raw_lake_path),
                            "provider_row_count": int(getattr(first_task, "row_count", 0) or len(new_rows)),
                            "normalized_row_count": len(merged_rows),
                            "date_min": _iso_date_or_none(merged_rows[0].observed_at if merged_rows else None),
                            "date_max": _iso_date_or_none(merged_rows[-1].observed_at if merged_rows else None),
                            "status": status,
                            "provider_return_code": last_provider_return_code,
                            "provider_return_msg": last_provider_return_msg or "BACKFILL_ATTEMPTED",
                            "last_successful_page": int(getattr(first_task, "last_successful_page", 0) or 0),
                            "last_next_key": getattr(first_task, "last_next_key", None),
                            "backfill_required": backfill_required,
                            "backfill_intervals": backfill_intervals,
                            "backfill_reason": "CACHE_COVERAGE_GAP",
                            "backfill_attempted": True,
                            "backfill_status": status,
                            "post_backfill_coverage_status": post_backfill,
                            **merged_coverage,
                        }
                    )
                    capture_state = {
                        "run_id": f"{pipeline_input.dataset_id}-CAPTURE-STATE",
                        "api_id": requested_specs[0].api_id.value if requested_specs else "UNKNOWN",
                        "requested_symbols": [item.provider_symbol for item in requested_specs],
                        "completed_symbols": completed_symbols,
                        "partial_symbols": partial_symbols,
                        "failed_symbols": failed_symbols,
                        "skipped_symbols": skipped_symbols,
                        "per_symbol_status": symbol_results,
                        "cache_coverage_gaps": cache_coverage_gaps,
                        "symbols_with_full_coverage": symbols_with_full_coverage,
                        "symbols_with_partial_coverage": symbols_with_partial_coverage,
                        "backfill_intervals_by_symbol": backfill_intervals_by_symbol,
                        "backfill_completed_symbols": backfill_completed_symbols,
                        "backfill_partial_symbols": backfill_partial_symbols,
                        "backfill_failed_symbols": backfill_failed_symbols,
                        "backfill_last_base_dt": spec.base_dt,
                        "backfill_last_next_key": getattr(first_task, "last_next_key", None),
                        "post_backfill_coverage_by_symbol": post_backfill_coverage_by_symbol,
                        "last_successful_page": int(getattr(first_task, "last_successful_page", 0) or 0),
                        "last_next_key": getattr(first_task, "last_next_key", None),
                        "raw_lake_paths": sorted(set(raw_lake_paths)),
                        "normalized_paths": [],
                        "provider_limit_hit": provider_limit_hit,
                        "last_provider_return_code": last_provider_return_code,
                        "last_provider_return_msg": last_provider_return_msg,
                        "partial_cache_used": partial_cache_used,
                        "can_resume": bool(provider_limit_hit or failed_symbols or partial_symbols or skipped_symbols or backfill_partial_symbols),
                    }
                    can_resume = bool(capture_state["can_resume"])
                    _write_capture_state(state_path, capture_state)
                    if limit_now and stop_on_provider_limit:
                        skipped_symbols.extend(item.provider_symbol for item in specs_to_process[index + 1 :])
                        break
                    if symbol_sleep_seconds > 0 and index < len(specs_to_process) - 1:
                        time.sleep(symbol_sleep_seconds)
                    continue
                if reuse_existing_raw_lake and cached_rows:
                    raw_lake_paths.append(str(raw_lake_path))
                    partial_cache_used = True
                    aggregate_rows.extend(cached_rows)
                    partial_symbols.append(spec.provider_symbol)
                    reused_from_cache.append(spec.provider_symbol)
                    symbol_results.append(
                        {
                            "requested_symbol": spec.provider_symbol,
                            "raw_lake_path": str(raw_lake_path),
                            "provider_row_count": len(cached_rows),
                            "normalized_row_count": len(cached_rows),
                            "date_min": _iso_date_or_none(cached_rows[0].observed_at if cached_rows else None),
                            "date_max": _iso_date_or_none(cached_rows[-1].observed_at if cached_rows else None),
                            "status": "REUSED_FROM_CACHE_PARTIAL",
                            "provider_return_code": None,
                            "provider_return_msg": "REUSED_FROM_CACHE",
                            "backfill_required": backfill_required,
                            "backfill_intervals": backfill_intervals,
                            "backfill_reason": "CACHE_COVERAGE_GAP",
                            "backfill_attempted": False,
                            "backfill_status": "NOT_ATTEMPTED",
                            "post_backfill_coverage_status": "TRADING_COVERAGE_GAP",
                            **cache_summary,
                        }
                    )
                    post_backfill_coverage_by_symbol[spec.provider_symbol] = "TRADING_COVERAGE_GAP"
                    continue
                if reuse_existing_raw_lake:
                    raw_lake_paths.append(str(raw_lake_path))
                    symbol_results.append(
                        {
                            "requested_symbol": spec.provider_symbol,
                            "raw_lake_path": str(raw_lake_path),
                            "provider_row_count": 0,
                            "normalized_row_count": 0,
                            "date_min": None,
                            "date_max": None,
                            "status": "CACHE_COVERAGE_GAP",
                            "provider_return_code": None,
                            "provider_return_msg": "CACHE_PRESENT_BUT_UNUSABLE",
                            "backfill_required": backfill_required,
                            "backfill_intervals": backfill_intervals,
                            "backfill_reason": "CACHE_COVERAGE_GAP",
                            "backfill_attempted": False,
                            "backfill_status": "NOT_ATTEMPTED",
                            "post_backfill_coverage_status": "CACHE_COVERAGE_GAP",
                            **cache_summary,
                        }
                    )
                    post_backfill_coverage_by_symbol[spec.provider_symbol] = "CACHE_COVERAGE_GAP"
                    failed_symbols.append(spec.provider_symbol)
                    continue
        if spec.provider_symbol in previous_partial or spec.provider_symbol in previous_failed or (
            resume_from_capture_state and spec.provider_symbol in previous_completed and spec.provider_symbol not in completed_symbols
        ):
            retried.append(spec.provider_symbol)
        if resume_from_capture_state and spec.provider_symbol in previous_completed and spec.provider_symbol in completed_symbols:
            continue
        if reuse_existing_raw_lake and spec.provider_symbol in failed_symbols:
            continue
        if not ensure_token():
            failed_symbols.append(spec.provider_symbol)
            failed_again.append(spec.provider_symbol)
            symbol_results.append(
                {
                    "requested_symbol": spec.provider_symbol,
                    "raw_lake_path": str(_raw_lake_path(pipeline_input, spec)),
                    "provider_row_count": 0,
                    "normalized_row_count": 0,
                    "date_min": None,
                    "date_max": None,
                    "status": "FAILED",
                    "provider_return_code": oauth_summary.get("provider_return_code"),
                    "provider_return_msg": oauth_summary.get("provider_return_msg"),
                    "backfill_required": False,
                    "backfill_intervals": [],
                    "backfill_reason": None,
                    "backfill_attempted": False,
                    "backfill_status": "NOT_REQUIRED",
                    "post_backfill_coverage_status": "FAILED",
                    "cache_found": False,
                    "cache_reused": False,
                    "cache_coverage_status": "NOT_USED",
                    "requested_date_min": _iso_date_or_none(spec.start_at),
                    "requested_date_max": _iso_date_or_none(spec.end_at),
                    "cached_date_min": None,
                    "cached_date_max": None,
                    "leading_gap_days": None,
                    "trailing_gap_days": None,
                    "coverage_ratio": None,
                    "cache_reuse_reason": "TOKEN_STAGE_FAILED",
                    "cache_reuse_warning": None,
                }
            )
            break
        fetched_now.append(spec.provider_symbol)
        single_pipeline = _build_single_symbol_pipeline(pipeline_input, spec)
        capture_result = run_historical_market_data_real_capture(single_pipeline, transport=transport, auth_header=auth_header)
        first_task = capture_result.task_results[0] if capture_result.task_results else None
        rows: list[HistoricalOhlcvRow] = []
        if capture_result.manifest and capture_result.manifest.ohlcv_rows_path:
            rows = [
                HistoricalOhlcvRow.model_validate(item)
                for item in json.loads(Path(capture_result.manifest.ohlcv_rows_path).read_text(encoding="utf-8"))
            ]
        aggregate_rows.extend(rows)
        last_provider_return_code = getattr(first_task, "provider_return_code", None)
        last_provider_return_msg = getattr(first_task, "provider_return_msg", None)
        limit_now = _provider_limit_hit(last_provider_return_code, last_provider_return_msg)
        provider_limit_hit = provider_limit_hit or limit_now
        if limit_now and rows:
            partial_symbols.append(spec.provider_symbol)
            status = "PARTIAL_CAPTURE_COMPLETED"
            symbols_with_partial_coverage.append(spec.provider_symbol)
        elif rows:
            completed_symbols.append(spec.provider_symbol)
            status = "COMPLETED"
            symbols_with_full_coverage.append(spec.provider_symbol)
        else:
            failed_symbols.append(spec.provider_symbol)
            failed_again.append(spec.provider_symbol)
            status = "FAILED"
        raw_lake_path = _raw_lake_path(pipeline_input, spec)
        if raw_lake_path.exists():
            raw_lake_paths.append(str(raw_lake_path))
        direct_coverage = _build_cache_coverage_summary(spec, rows) if rows else {}
        symbol_results.append(
            {
                "requested_symbol": spec.provider_symbol,
                "raw_lake_path": str(raw_lake_path),
                "provider_row_count": int(getattr(first_task, "row_count", 0) or 0),
                "normalized_row_count": len(rows),
                "date_min": rows[0].observed_at.date().isoformat() if rows else None,
                "date_max": rows[-1].observed_at.date().isoformat() if rows else None,
                "status": status,
                "provider_return_code": last_provider_return_code,
                "provider_return_msg": last_provider_return_msg,
                "last_successful_page": int(getattr(first_task, "last_successful_page", 0) or 0),
                "last_next_key": getattr(first_task, "last_next_key", None),
                "backfill_required": False,
                "backfill_intervals": [],
                "backfill_reason": None,
                "backfill_attempted": False,
                "backfill_status": "NOT_REQUIRED",
                "post_backfill_coverage_status": "FULL_TRADING_COVERAGE" if rows else "FAILED",
                **(
                    direct_coverage
                    if rows
                    else {
                        "cache_found": False,
                        "cache_reused": False,
                        "cache_coverage_status": "NOT_USED",
                        "requested_date_min": _iso_date_or_none(spec.start_at),
                        "requested_date_max": _iso_date_or_none(spec.end_at),
                        "effective_requested_trading_date_min": None,
                        "effective_requested_trading_date_max": None,
                        "cached_date_min": None,
                        "cached_date_max": None,
                        "calendar_leading_gap_days": None,
                        "calendar_trailing_gap_days": None,
                        "trading_leading_gap_days": None,
                        "trading_trailing_gap_days": None,
                        "leading_gap_days": None,
                        "trailing_gap_days": None,
                        "calendar_coverage_ratio": None,
                        "trading_coverage_ratio": None,
                        "coverage_ratio": None,
                        "coverage_basis": None,
                        "cache_reuse_reason": None,
                        "cache_reuse_warning": None,
                    }
                ),
            }
        )
        capture_state = {
            "run_id": f"{pipeline_input.dataset_id}-CAPTURE-STATE",
            "api_id": requested_specs[0].api_id.value if requested_specs else "UNKNOWN",
            "requested_symbols": [item.provider_symbol for item in requested_specs],
            "completed_symbols": completed_symbols,
            "partial_symbols": partial_symbols,
            "failed_symbols": failed_symbols,
            "skipped_symbols": skipped_symbols,
            "per_symbol_status": symbol_results,
            "cache_coverage_gaps": cache_coverage_gaps,
            "symbols_with_full_coverage": symbols_with_full_coverage,
            "symbols_with_partial_coverage": symbols_with_partial_coverage,
            "backfill_intervals_by_symbol": backfill_intervals_by_symbol,
            "backfill_completed_symbols": backfill_completed_symbols,
            "backfill_partial_symbols": backfill_partial_symbols,
            "backfill_failed_symbols": backfill_failed_symbols,
            "backfill_last_base_dt": spec.base_dt,
            "backfill_last_next_key": getattr(first_task, "last_next_key", None),
            "post_backfill_coverage_by_symbol": post_backfill_coverage_by_symbol,
            "last_successful_page": int(getattr(first_task, "last_successful_page", 0) or 0),
            "last_next_key": getattr(first_task, "last_next_key", None),
            "raw_lake_paths": sorted(set(raw_lake_paths)),
            "normalized_paths": [],
            "provider_limit_hit": provider_limit_hit,
            "last_provider_return_code": last_provider_return_code,
            "last_provider_return_msg": last_provider_return_msg,
            "partial_cache_used": partial_cache_used,
            "can_resume": bool(provider_limit_hit or failed_symbols or partial_symbols or skipped_symbols),
        }
        can_resume = bool(capture_state["can_resume"])
        _write_capture_state(state_path, capture_state)
        if limit_now and stop_on_provider_limit:
            skipped_symbols.extend(item.provider_symbol for item in specs_to_process[index + 1 :])
            break
        if symbol_sleep_seconds > 0 and index < len(specs_to_process) - 1:
            time.sleep(symbol_sleep_seconds)

    aggregate_rows.sort(key=lambda item: (item.instrument_id, item.observed_at))
    manifest = None
    if aggregate_rows:
        manifest, _ = build_historical_ohlcv_dataset_manifest(pipeline_input, aggregate_rows)
        capture_state = {
            "run_id": f"{pipeline_input.dataset_id}-CAPTURE-STATE",
            "api_id": requested_specs[0].api_id.value if requested_specs else "UNKNOWN",
            "requested_symbols": [item.provider_symbol for item in requested_specs],
            "completed_symbols": completed_symbols,
            "partial_symbols": partial_symbols,
            "failed_symbols": failed_symbols,
            "skipped_symbols": skipped_symbols,
            "per_symbol_status": symbol_results,
            "cache_coverage_gaps": cache_coverage_gaps,
            "symbols_with_full_coverage": sorted(set(symbols_with_full_coverage)),
            "symbols_with_partial_coverage": sorted(set(symbols_with_partial_coverage)),
            "backfill_intervals_by_symbol": backfill_intervals_by_symbol,
            "backfill_completed_symbols": sorted(set(backfill_completed_symbols)),
            "backfill_partial_symbols": sorted(set(backfill_partial_symbols)),
            "backfill_failed_symbols": sorted(set(backfill_failed_symbols)),
            "backfill_last_base_dt": next((item.base_dt for item in reversed(specs_to_process) if item.provider_symbol in backfill_intervals_by_symbol), None),
            "backfill_last_next_key": next((item.get("last_next_key") for item in reversed(symbol_results) if item.get("backfill_attempted") and item.get("last_next_key")), None),
            "post_backfill_coverage_by_symbol": post_backfill_coverage_by_symbol,
            "last_successful_page": max((item.get("last_successful_page", 0) for item in symbol_results), default=0),
            "last_next_key": next((item.get("last_next_key") for item in reversed(symbol_results) if item.get("last_next_key")), None),
            "raw_lake_paths": sorted(set(raw_lake_paths)),
            "normalized_paths": [path for path in [manifest.ohlcv_rows_path, manifest.manifest_path] if path],
            "provider_limit_hit": provider_limit_hit,
            "last_provider_return_code": last_provider_return_code,
            "last_provider_return_msg": last_provider_return_msg,
            "partial_cache_used": partial_cache_used,
            "can_resume": bool(provider_limit_hit or failed_symbols or partial_symbols or skipped_symbols),
        }
        can_resume = bool(capture_state["can_resume"])
        _write_capture_state(state_path, capture_state)

    request_status = "CHART_ROWS_EXTRACTED" if aggregate_rows else "FAILED"
    row_count = len(aggregate_rows)
    chart_response_received = bool(symbol_results)
    full_coverage_symbols = sorted(set(symbols_with_full_coverage))
    partial_coverage_symbols = sorted(set(symbols_with_partial_coverage) - set(full_coverage_symbols))
    gap_symbols = sorted({item.provider_symbol for item in requested_specs} - set(full_coverage_symbols) - set(partial_coverage_symbols))
    if prefer_full_coverage_training:
        training_input_symbols = full_coverage_symbols
    elif allow_training_on_partial_capture:
        training_input_symbols = sorted(set(full_coverage_symbols + partial_coverage_symbols))
    else:
        training_input_symbols = full_coverage_symbols
    training_input_coverage_by_symbol = {
        item["requested_symbol"]: item["status"]
        for item in symbol_results
        if item["requested_symbol"] in training_input_symbols
    }
    training_input_coverage_basis_by_symbol = {
        item["requested_symbol"]: item.get("coverage_basis")
        for item in symbol_results
        if item["requested_symbol"] in training_input_symbols
    }
    excluded_symbols = [item.provider_symbol for item in requested_specs if item.provider_symbol not in training_input_symbols]
    exclusion_reasons = {}
    for item in symbol_results:
        symbol = item["requested_symbol"]
        if symbol not in excluded_symbols:
            continue
        if symbol in gap_symbols:
            exclusion_reasons[symbol] = "NO_USABLE_COVERAGE"
        elif prefer_full_coverage_training:
            exclusion_reasons[symbol] = "PREFER_FULL_COVERAGE_TRAINING"
        else:
            exclusion_reasons[symbol] = "PARTIAL_COVERAGE_EXCLUDED"
    for symbol in excluded_symbols:
        if symbol not in exclusion_reasons:
            exclusion_reasons[symbol] = "SKIPPED_OR_NOT_CAPTURED"
    training_on_partial_coverage = any(symbol in partial_coverage_symbols for symbol in training_input_symbols)

    training_started = False
    training_completed = False
    training_result = None
    output_root = validate_safe_local_root(training_output_root) / pipeline_input.dataset_id.lower()
    reports_dir = output_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    training_plan_path = reports_dir / "offline_strategy_training_plan.json"
    promotion_gate_path = reports_dir / "offline_strategy_promotion_gate.json"
    summary_path = output_root / "capture_and_train_summary.json"
    manifest_path = Path(manifest.manifest_path) if manifest and manifest.manifest_path else None
    manifest_reloaded = False
    reloaded_manifest = None
    if manifest_path and manifest_path.exists():
        reloaded_manifest = load_historical_ohlcv_dataset_manifest(manifest_path)
        manifest_reloaded = True

    training_manifest_path = None
    training_manifest_id = None
    training_manifest = reloaded_manifest
    if training_input_symbols and set(training_input_symbols) != {row.provider_symbol for row in aggregate_rows}:
        filtered_rows = [row for row in aggregate_rows if row.provider_symbol in set(training_input_symbols)]
        training_pipeline_input = pipeline_input.model_copy(
            update={
                "dataset_id": f"{pipeline_input.dataset_id}-TRAINING-INPUT",
                "store_root": str(output_root / "training_input_store"),
            }
        )
        training_manifest, _ = build_historical_ohlcv_dataset_manifest(training_pipeline_input, filtered_rows)
        training_manifest_path = training_manifest.manifest_path
        training_manifest_id = training_manifest.manifest_id
    elif training_manifest is not None and training_input_symbols:
        training_manifest_path = training_manifest.manifest_path
        training_manifest_id = training_manifest.manifest_id

    if training_input_symbols and training_manifest is not None:
        pipeline = OfflineStrategyPipelineInput(
            pipeline_id=f"{pipeline_input.dataset_id}-OFFLINE-STRATEGY",
            dataset_id=pipeline_input.dataset_id,
            manifest=training_manifest,
            requested_template_ids=resolved_template_ids,
            asset_liquidity_profile=asset_liquidity_profile,
            primary_walk_forward_mode=resolved_walk_forward_mode,
            search_mode=str(search_mode or "BOUNDED_GRID").upper(),
        )
        if training_handoff_mode == "in_process" and training_manifest is not None:
            pipeline = pipeline.model_copy(update={"manifest": training_manifest})
        training_started = True
        training_result = build_offline_strategy_pipeline(pipeline)
        training_completed = True
        training_plan_path.write_text(training_result.training_plan.model_dump_json(indent=2), encoding="utf-8")
        promotion_gate_path.write_text(json.dumps([item.model_dump(mode="json") for item in training_result.promotion_decisions], indent=2), encoding="utf-8")

    candidate_count_by_family = (
        dict(sorted(Counter(candidate.family.value for candidate in training_result.candidates).items()))
        if training_result is not None
        else {}
    )
    generated_strategy_families = sorted(candidate_count_by_family)
    ranking_report_rows = _build_symbol_family_ranking_rows(
        training_symbols=training_input_symbols,
        training_result=training_result,
        symbol_results=symbol_results,
    )
    ranking_report_path = reports_dir / "offline_strategy_symbol_family_ranking.json"
    ranking_report_payload = {
        "dataset_id": pipeline_input.dataset_id,
        "dataset_symbols": sorted({item.provider_symbol for item in requested_specs}),
        "requested_strategy_families": family_resolution["requested_strategy_families"],
        "supported_strategy_families": family_resolution["supported_strategy_families"],
        "unsupported_strategy_families": family_resolution["unsupported_strategy_families"],
        "skipped_strategy_families": family_resolution["skipped_strategy_families"],
        "generated_strategy_families": generated_strategy_families,
        "candidate_count_by_family": candidate_count_by_family,
        "rows": ranking_report_rows,
    }
    if training_result is not None:
        ranking_report_path.write_text(json.dumps(ranking_report_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    all_symbols_completed = len(completed_symbols) >= len(requested_specs) and not partial_symbols and not failed_symbols
    used_any_cache = bool(reused_from_cache or skipped_completed)
    if not aggregate_rows:
        top_status = "FAILED"
    elif backfill_attempted_any and provider_limit_hit and not training_completed:
        top_status = "PARTIAL_BACKFILL_PROVIDER_LIMIT"
    elif not training_completed:
        top_status = "PARTIAL_CAPTURE_NO_TRAINING"
    elif backfill_attempted_any and provider_limit_hit:
        top_status = "COMPLETED_WITH_PROVIDER_LIMIT"
    elif backfill_attempted_any and backfill_progress_made:
        top_status = "COMPLETED_WITH_BACKFILL"
    elif provider_limit_hit and partial_cache_used:
        top_status = "COMPLETED_WITH_PROVIDER_LIMIT_AND_PARTIAL_CACHE"
    elif provider_limit_hit:
        top_status = "COMPLETED_WITH_PROVIDER_LIMIT"
    elif partial_cache_used:
        top_status = "COMPLETED_WITH_PARTIAL_CACHE"
    elif all_symbols_completed and used_any_cache:
        top_status = "COMPLETED_WITH_CACHE"
    else:
        top_status = "COMPLETED"

    summary = {
        "status": top_status,
        "dataset_id": pipeline_input.dataset_id,
        "dataset_symbols": sorted({item.provider_symbol for item in requested_specs}),
        "token_status": oauth_summary.get("token_status"),
        "stage": "TRAINING_COMPLETED" if training_completed else oauth_summary.get("stage", "CAPTURE_COMPLETED"),
        "kiwoom_environment": environment.value,
        "endpoint_base_url": oauth_summary.get("endpoint_base_url", _kiwoom_base_url(environment)),
        "endpoint_path": oauth_summary.get("endpoint_path"),
        "http_status_code": oauth_summary.get("http_status_code"),
        "provider_return_code": last_provider_return_code or oauth_summary.get("provider_return_code"),
        "provider_return_msg": last_provider_return_msg or oauth_summary.get("provider_return_msg"),
        "transport_error_type": oauth_summary.get("transport_error_type"),
        "transport_error_message_redacted": oauth_summary.get("transport_error_message_redacted"),
        "request_status": request_status,
        "training_handoff_mode": training_handoff_mode,
        "strategy_families": family_resolution["requested_strategy_families"],
        "requested_strategy_families": family_resolution["requested_strategy_families"],
        "supported_strategy_families": family_resolution["supported_strategy_families"],
        "unsupported_strategy_families": family_resolution["unsupported_strategy_families"],
        "skipped_strategy_families": family_resolution["skipped_strategy_families"],
        "generated_strategy_families": generated_strategy_families,
        "candidate_count_by_family": candidate_count_by_family,
        "search_mode": str(search_mode or "BOUNDED_GRID").upper(),
        "walk_forward_mode": resolved_walk_forward_mode.value,
        "promotion_profile": str(promotion_profile or "STABILITY_FIRST").upper(),
        "fill_policy": str(fill_policy or "NEXT_BAR_CONSERVATIVE").upper(),
        "direction": resolved_direction.value,
        "token_written": bool(oauth_summary.get("token_written")),
        "chart_request_started": bool(fetched_now or token_ready),
        "chart_response_received": chart_response_received,
        "row_count": row_count,
        "provider_limit_hit": provider_limit_hit,
        "partial_cache_used": partial_cache_used,
        "partial_capture": bool(partial_symbols),
        "completed_symbols": sorted(set(completed_symbols)),
        "partial_symbols": sorted(set(partial_symbols)),
        "failed_symbols": sorted(set(failed_symbols)),
        "skipped_symbols": skipped_symbols,
        "cache_coverage_gaps": sorted(set(cache_coverage_gaps)),
        "symbols_with_full_coverage": full_coverage_symbols,
        "symbols_with_partial_coverage": partial_coverage_symbols,
        "full_coverage_symbols": full_coverage_symbols,
        "partial_coverage_symbols": partial_coverage_symbols,
        "gap_symbols": gap_symbols,
        "symbol_results": symbol_results,
        "per_symbol_row_count": {item["requested_symbol"]: item["normalized_row_count"] for item in symbol_results},
        "per_symbol_date_min": {item["requested_symbol"]: item["date_min"] for item in symbol_results},
        "per_symbol_date_max": {item["requested_symbol"]: item["date_max"] for item in symbol_results},
        "per_symbol_coverage_status": {
            item["requested_symbol"]: (
                item.get("cache_coverage_status")
                if item.get("cache_coverage_status") not in {None, "NOT_USED"}
                else item.get("post_backfill_coverage_status") or item["status"]
            )
            for item in symbol_results
        },
        "per_symbol_coverage_basis": {item["requested_symbol"]: item.get("coverage_basis") for item in symbol_results},
        "fetched_now": fetched_now,
        "reused_from_cache": reused_from_cache,
        "backfilled_symbols": sorted(set(backfill_completed_symbols + backfill_partial_symbols)),
        "skipped_completed": skipped_completed,
        "retried": retried,
        "failed_again": failed_again,
        "backfill_intervals_by_symbol": backfill_intervals_by_symbol,
        "backfill_completed_symbols": sorted(set(backfill_completed_symbols)),
        "backfill_partial_symbols": sorted(set(backfill_partial_symbols)),
        "backfill_failed_symbols": sorted(set(backfill_failed_symbols)),
        "post_backfill_coverage_by_symbol": post_backfill_coverage_by_symbol,
        "manifest_written": manifest is not None,
        "manifest_path": str(manifest_path) if manifest_path else None,
        "manifest_id": manifest.manifest_id if manifest else None,
        "manifest_reloaded": manifest_reloaded,
        "training_manifest_path": training_manifest_path,
        "training_manifest_id": training_manifest_id,
        "raw_lake_paths": sorted(set(raw_lake_paths)),
        "normalized_ohlcv_paths": [path for path in ([manifest.ohlcv_rows_path, manifest.manifest_path] if manifest else []) if path],
        "training_started": training_started,
        "training_completed": training_completed,
        "training_input_symbols": training_input_symbols,
        "training_input_coverage_by_symbol": training_input_coverage_by_symbol,
        "training_input_coverage_basis_by_symbol": training_input_coverage_basis_by_symbol,
        "training_on_partial_coverage": training_on_partial_coverage,
        "excluded_symbols": excluded_symbols,
        "exclusion_reasons": exclusion_reasons,
        "offline_strategy_output_root": str(output_root),
        "promotion_gate_output_path": str(promotion_gate_path) if training_completed else None,
        "training_plan_output_path": str(training_plan_path) if training_completed else None,
        "ranking_report_path": str(ranking_report_path) if training_result is not None else None,
        "candidate_count": len(training_result.candidates) if training_result is not None else 0,
        "promotion_decision_count": len(training_result.promotion_decisions) if training_result is not None else 0,
        "capture_state_path": str(state_path),
        "capture_state_root": str(state_path.parent),
        "can_resume": can_resume,
        "request_sleep_seconds": request_sleep_seconds,
        "symbol_sleep_seconds": symbol_sleep_seconds,
        "max_symbols_per_run": max_symbols_per_run,
        "stop_on_provider_limit": stop_on_provider_limit,
        "allow_training_on_partial_capture": allow_training_on_partial_capture,
        "backfill_cache_gaps": auto_backfill_cache_gaps,
        "max_backfill_pages_per_symbol": max_backfill_pages_per_symbol,
        "prefer_full_coverage_training": prefer_full_coverage_training,
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
