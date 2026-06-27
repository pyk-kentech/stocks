from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from stock_risk_mcp.historical_market_data_capture_runner import run_historical_market_data_real_capture
from stock_risk_mcp.historical_market_data_manifest_engine import load_historical_ohlcv_dataset_manifest
from stock_risk_mcp.historical_market_data_models import (
    HistoricalChartCaptureRunResult,
    HistoricalOhlcvRow,
    HistoricalMarketDataPipelineInput,
    HistoricalMarketDataReadinessStatus,
)
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
) -> dict[str, object]:
    capture_result, oauth_summary = run_historical_market_data_real_capture_and_manifest(
        pipeline_input,
        environment=environment,
        token_store_root=token_store_root,
    )
    resolved_direction = _resolve_direction(direction)
    resolved_walk_forward_mode = _resolve_walk_forward_mode(walk_forward_mode)
    resolved_template_ids, family_resolution = _resolve_requested_templates(
        requested_template_ids=requested_template_ids,
        strategy_families=strategy_families,
        direction=resolved_direction,
    )
    first_task = capture_result.task_results[0] if capture_result.task_results else None
    chart_response_received = bool(
        getattr(first_task, "chart_response_received", False)
        or capture_result.raw_response_count
        or capture_result.normalized_row_count
        or capture_result.readiness_status
        in {
            HistoricalMarketDataReadinessStatus.PROVIDER_EMPTY_RESPONSE,
            HistoricalMarketDataReadinessStatus.PROVIDER_CHART_ERROR,
            HistoricalMarketDataReadinessStatus.DEPENDENCY_GAP_KIWOOM_ENDPOINT_SCHEMA,
            HistoricalMarketDataReadinessStatus.REAL_CAPTURE_EXECUTED,
        }
    )
    request_status = "CHART_ROWS_EXTRACTED" if capture_result.manifest is not None else capture_result.readiness_status.value
    row_count = capture_result.normalized_row_count or int(getattr(first_task, "row_count", 0) or 0)
    if capture_result.manifest is None or not capture_result.manifest.manifest_path:
        return {
            "status": "FAILED",
            "token_status": oauth_summary.get("token_status"),
            "stage": oauth_summary.get("stage", "TOKEN_STAGE"),
            "kiwoom_environment": oauth_summary.get("kiwoom_environment", environment.value),
            "endpoint_base_url": oauth_summary.get("endpoint_base_url"),
            "endpoint_path": oauth_summary.get("endpoint_path"),
            "http_status_code": oauth_summary.get("http_status_code"),
            "provider_return_code": getattr(first_task, "provider_return_code", None) or oauth_summary.get("provider_return_code"),
            "provider_return_msg": getattr(first_task, "provider_return_msg", None) or oauth_summary.get("provider_return_msg"),
            "transport_error_type": oauth_summary.get("transport_error_type"),
            "transport_error_message_redacted": oauth_summary.get("transport_error_message_redacted"),
            "training_handoff_mode": training_handoff_mode,
            "strategy_families": family_resolution["requested_strategy_families"],
            "requested_strategy_families": family_resolution["requested_strategy_families"],
            "supported_strategy_families": family_resolution["supported_strategy_families"],
            "unsupported_strategy_families": family_resolution["unsupported_strategy_families"],
            "skipped_strategy_families": family_resolution["skipped_strategy_families"],
            "generated_strategy_families": [],
            "candidate_count_by_family": {},
            "search_mode": str(search_mode or "BOUNDED_GRID").upper(),
            "walk_forward_mode": resolved_walk_forward_mode.value,
            "promotion_profile": str(promotion_profile or "STABILITY_FIRST").upper(),
            "fill_policy": str(fill_policy or "NEXT_BAR_CONSERVATIVE").upper(),
            "direction": resolved_direction.value,
            "token_written": bool(oauth_summary.get("token_written")),
            "chart_request_started": bool(oauth_summary.get("chart_request_started", False)),
            "chart_response_received": chart_response_received,
            "row_count": row_count,
            "provider_limit_hit": bool(getattr(first_task, "provider_return_code", None) == 5),
            "partial_capture": bool(row_count and getattr(first_task, "provider_return_code", None) == 5),
            "completed_symbols": [],
            "partial_symbols": [],
            "failed_symbols": [spec.provider_symbol for spec in pipeline_input.request_specs],
            "symbol_results": [],
            "raw_lake_paths": [],
            "normalized_ohlcv_paths": [],
            "manifest_written": False,
            "manifest_reloaded": False,
            "training_started": False,
            "training_completed": False,
            "request_status": request_status,
        }
    manifest_path = Path(capture_result.manifest.manifest_path)
    if not manifest_path.exists():
        raise ValueError("persisted manifest file missing after capture")
    manifest = load_historical_ohlcv_dataset_manifest(manifest_path)
    pipeline = OfflineStrategyPipelineInput(
        pipeline_id=f"{pipeline_input.dataset_id}-OFFLINE-STRATEGY",
        dataset_id=pipeline_input.dataset_id,
        manifest=manifest,
        requested_template_ids=resolved_template_ids,
        asset_liquidity_profile=asset_liquidity_profile,
        primary_walk_forward_mode=resolved_walk_forward_mode,
        search_mode=str(search_mode or "BOUNDED_GRID").upper(),
    )
    if training_handoff_mode == "in_process":
        pipeline = pipeline.model_copy(update={"manifest": capture_result.manifest})
    output_root = validate_safe_local_root(training_output_root) / pipeline_input.dataset_id.lower()
    reports_dir = output_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    training_started = True
    training_result = build_offline_strategy_pipeline(pipeline)
    training_plan_path = reports_dir / "offline_strategy_training_plan.json"
    promotion_gate_path = reports_dir / "offline_strategy_promotion_gate.json"
    summary_path = output_root / "capture_and_train_summary.json"
    training_plan_path.write_text(training_result.training_plan.model_dump_json(indent=2), encoding="utf-8")
    promotion_gate_path.write_text(
        json.dumps([item.model_dump(mode="json") for item in training_result.promotion_decisions], indent=2),
        encoding="utf-8",
    )
    raw_lake_paths = sorted(
        str(Path(pipeline_input.raw_lake_root) / f"{spec.request_id.lower()}-response.json")
        for spec in pipeline_input.request_specs
        if (Path(pipeline_input.raw_lake_root) / f"{spec.request_id.lower()}-response.json").exists()
    )
    normalized_paths = [path for path in [manifest.ohlcv_rows_path, manifest.manifest_path] if path]
    manifest_rows = [
        HistoricalOhlcvRow.model_validate(item)
        for item in json.loads(Path(manifest.ohlcv_rows_path).read_text(encoding="utf-8"))
    ] if manifest.ohlcv_rows_path else []
    symbol_results = _symbol_status_summary(pipeline_input, capture_result, manifest_rows)
    candidate_count_by_family = dict(sorted(Counter(candidate.family.value for candidate in training_result.candidates).items()))
    generated_strategy_families = sorted(candidate_count_by_family)
    completed_symbols = [item["requested_symbol"] for item in symbol_results if item["status"] == "COMPLETED"]
    partial_symbols = [item["requested_symbol"] for item in symbol_results if item["status"] == "PARTIAL_CAPTURE_COMPLETED"]
    failed_symbols = [item["requested_symbol"] for item in symbol_results if item["status"] == "FAILED"]
    provider_limit_hit = any(item.get("provider_return_code") == 5 for item in symbol_results)
    partial_capture = bool(partial_symbols)
    summary = {
        "status": "COMPLETED_WITH_PROVIDER_LIMIT" if provider_limit_hit else "COMPLETED",
        "token_status": oauth_summary.get("token_status"),
        "stage": "TRAINING_COMPLETED",
        "kiwoom_environment": oauth_summary.get("kiwoom_environment", environment.value),
        "endpoint_base_url": oauth_summary.get("endpoint_base_url"),
        "endpoint_path": oauth_summary.get("endpoint_path"),
        "http_status_code": oauth_summary.get("http_status_code"),
        "provider_return_code": getattr(first_task, "provider_return_code", None) or oauth_summary.get("provider_return_code"),
        "provider_return_msg": getattr(first_task, "provider_return_msg", None) or oauth_summary.get("provider_return_msg"),
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
        "chart_request_started": True,
        "chart_response_received": chart_response_received,
        "row_count": row_count,
        "provider_limit_hit": provider_limit_hit,
        "partial_capture": partial_capture,
        "completed_symbols": completed_symbols,
        "partial_symbols": partial_symbols,
        "failed_symbols": failed_symbols,
        "symbol_results": symbol_results,
        "manifest_written": True,
        "manifest_path": str(manifest_path),
        "manifest_id": manifest.manifest_id,
        "manifest_reloaded": True,
        "raw_lake_paths": raw_lake_paths,
        "normalized_ohlcv_paths": normalized_paths,
        "training_started": training_started,
        "training_completed": True,
        "offline_strategy_output_root": str(output_root),
        "promotion_gate_output_path": str(promotion_gate_path),
        "training_plan_output_path": str(training_plan_path),
        "candidate_count": len(training_result.candidates),
        "promotion_decision_count": len(training_result.promotion_decisions),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
