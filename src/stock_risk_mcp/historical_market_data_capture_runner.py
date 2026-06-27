from __future__ import annotations

from datetime import datetime

from stock_risk_mcp.historical_market_data_capture_plan_engine import build_historical_chart_capture_plan
from stock_risk_mcp.historical_market_data_coverage_engine import build_historical_market_data_coverage
from stock_risk_mcp.historical_market_data_credential_ref import redact_credential_ref_summary
from stock_risk_mcp.historical_market_data_guard import (
    is_pytest_runtime,
    validate_no_sensitive_markers,
    validate_profile_guard,
    validate_real_capture_opt_in,
    validate_safe_local_root,
)
from stock_risk_mcp.historical_market_data_manifest_engine import (
    build_historical_market_data_storage_capability_report,
    build_historical_ohlcv_dataset_manifest,
)
from stock_risk_mcp.historical_market_data_models import (
    HistoricalChartCaptureDecision,
    HistoricalChartCaptureRunAudit,
    HistoricalChartCaptureRunResult,
    HistoricalChartCaptureRunTaskResult,
    HistoricalChartRawResponse,
    HistoricalMarketDataCredentialPolicy,
    HistoricalMarketDataPipelineInput,
    HistoricalMarketDataProvider,
    HistoricalMarketDataReadinessStatus,
    HistoricalMarketDataRedactionStatus,
    HistoricalMarketDataSafetyReport,
)
from stock_risk_mcp.historical_market_data_normalizer import classify_chart_payload, extract_chart_rows, normalize_historical_ohlcv_rows
from stock_risk_mcp.historical_market_data_raw_lake import persist_historical_chart_raw_lake
from stock_risk_mcp.historical_market_data_real_capture import build_blocked_capture_run_result, build_capture_run_result_with_status
from stock_risk_mcp.historical_market_data_transport import HistoricalMarketDataTransport


def _header_value(headers: dict[str, object], *keys: str, default: str = "") -> str:
    lowered = {str(key).lower(): value for key, value in headers.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value not in (None, ""):
            return str(value).strip()
    return default


def _row_count_for_response(task, body_json: dict[str, object]) -> int:
    rows = extract_chart_rows(task.request_spec.api_id, body_json)
    return len(rows or [])


def _within_requested_window(task, observed_at: datetime) -> bool:
    if task.request_spec.start_at is not None and observed_at < task.request_spec.start_at:
        return False
    if task.request_spec.end_at is not None and observed_at > task.request_spec.end_at:
        return False
    return True


def _build_response(
    task,
    body_json: dict[str, object],
    *,
    response_headers: dict[str, object],
    page_index: int,
    base_url: str | None,
) -> HistoricalChartRawResponse:
    cont_yn = _header_value(response_headers, "cont-yn", "cont_yn", "contYn", default="N").upper() or "N"
    next_key = _header_value(response_headers, "next-key", "next_key", "nextKey", default="").upper()
    environment = "MOCK" if (base_url or "").startswith("https://mockapi.kiwoom.com") else "REAL" if (base_url or "").startswith("https://api.kiwoom.com") else "UNKNOWN"
    return HistoricalChartRawResponse(
        response_id=f"{task.request_spec.request_id}-RESPONSE",
        request_id=task.request_spec.request_id,
        api_id=task.request_spec.api_id,
        provider=HistoricalMarketDataProvider.KIWOOM_REST,
        provider_symbol=task.request_spec.provider_symbol,
        canonical_instrument_id=task.request_spec.canonical_instrument_id,
        imported_at=datetime.now().astimezone(),
        available_at=datetime.now().astimezone(),
        source_kind="RAW_LAKE_RECORD",
        source_ref=f"{task.request_spec.request_id}.json",
        cont_yn=cont_yn,
        next_key=next_key,
        payload_summary={
            "return_code": body_json.get("return_code", 0),
            "row_count": _row_count_for_response(task, body_json),
        },
        raw_payload_redacted=True,
        raw_payload={
            "_capture_meta": {
                "environment": environment,
                "base_url": base_url or "UNKNOWN_BASE_URL",
                "endpoint_path": task.request_preview.path,
                "api_id": task.request_preview.headers.get("api-id", "").lower(),
                "symbol": task.request_spec.provider_symbol,
                "base_dt": task.request_spec.base_dt,
                "upd_stkpc_tp": task.request_spec.upd_stkpc_tp,
                "continuation_page_index": page_index,
                "row_count": _row_count_for_response(task, body_json),
                "response_headers": {
                    "cont-yn": cont_yn,
                    "next-key": next_key,
                },
            },
            **body_json,
        },
    )


def run_historical_market_data_real_capture(
    pipeline_input: HistoricalMarketDataPipelineInput,
    *,
    transport: HistoricalMarketDataTransport,
    auth_header: str | None = None,
) -> HistoricalChartCaptureRunResult:
    real_capture_config = pipeline_input.real_capture_config
    blocked_reasons: list[str] = []
    blocked_reasons.extend(validate_real_capture_opt_in(pipeline_input.mode, pipeline_input.opt_in))
    blocked_reasons.extend(validate_profile_guard(pipeline_input.capture_profile))
    if real_capture_config is None:
        blocked_reasons.append("REAL_CAPTURE_CONFIG_MISSING")
    else:
        if real_capture_config.credential_ref is None:
            blocked_reasons.append("CREDENTIAL_REF_MISSING")
        if pipeline_input.capture_profile.value == "SMOKE_PROFILE":
            blocked_reasons.append("SMOKE_PROFILE_REAL_NETWORK_BLOCKED")
    try:
        validate_safe_local_root(pipeline_input.store_root)
        validate_safe_local_root(pipeline_input.raw_lake_root)
    except Exception as exc:
        blocked_reasons.append(f"UNSAFE_OUTPUT_ROOT:{exc}")
    if is_pytest_runtime() and transport.transport_kind == "REAL_KIWOOM_CHART":
        blocked_reasons.append("PYTEST_REAL_CAPTURE_BLOCKED")
    if transport.transport_kind == "MOCK" and is_pytest_runtime():
        blocked_reasons = [reason for reason in blocked_reasons if reason != "PYTEST_REAL_CAPTURE_BLOCKED"]
    for spec in pipeline_input.request_specs:
        validate_no_sensitive_markers(spec.provider_symbol, context="provider_symbol")

    api_catalog_report, capture_plan = build_historical_chart_capture_plan(pipeline_input)
    if transport.transport_kind == "MOCK" and is_pytest_runtime():
        capture_plan = capture_plan.model_copy(
            update={
                "tasks": [
                    task.model_copy(
                        update={
                            "blocking_reasons": [reason for reason in task.blocking_reasons if reason != "PYTEST_REAL_CAPTURE_BLOCKED"],
                            "execution_decision": "ALLOWED"
                            if not [reason for reason in task.blocking_reasons if reason != "PYTEST_REAL_CAPTURE_BLOCKED"]
                            else task.execution_decision,
                        }
                    )
                    for task in capture_plan.tasks
                ],
                "readiness_status": HistoricalMarketDataReadinessStatus.CAPTURE_PLAN_READY,
            }
        )
    if blocked_reasons:
        credential_ref_present = bool(real_capture_config and real_capture_config.credential_ref)
        return build_blocked_capture_run_result(
            pipeline_input.dataset_id,
            blocked_reasons=sorted(set(blocked_reasons)),
            transport_kind=transport.transport_kind,
            credential_ref_present=credential_ref_present,
        )

    credential_ref_present = bool(real_capture_config and real_capture_config.credential_ref)
    if transport.transport_kind == "REAL_KIWOOM_CHART" and not auth_header:
        return build_capture_run_result_with_status(
            pipeline_input.dataset_id,
            readiness_status=HistoricalMarketDataReadinessStatus.BLOCKED_AUTH_OR_TOKEN,
            blocked_reasons=["BLOCKED_AUTH_OR_TOKEN"],
            transport_kind=transport.transport_kind,
            credential_ref_present=credential_ref_present,
        )
    if transport.transport_kind == "MOCK":
        auth_header = "Bearer <MOCK_ONLY>"
    raw_responses: list[HistoricalChartRawResponse] = []
    valid_raw_responses: list[HistoricalChartRawResponse] = []
    task_results: list[HistoricalChartCaptureRunTaskResult] = []
    final_status = HistoricalMarketDataReadinessStatus.REAL_CAPTURE_EXECUTED
    for task in capture_plan.tasks[: real_capture_config.max_request_count]:
        if task.execution_decision != HistoricalChartCaptureDecision.ALLOWED:
            task_results.append(
                HistoricalChartCaptureRunTaskResult(
                    task_id=task.task_id,
                    request_id=task.request_spec.request_id,
                    execution_decision=task.execution_decision,
                    blocked_reasons=task.blocking_reasons,
                )
            )
            continue
        page_count = 0
        body_json: dict[str, object] = {}
        response_headers: dict[str, object] = {}
        task_status = HistoricalMarketDataReadinessStatus.REAL_CAPTURE_EXECUTED
        task_errors: list[str] = []
        next_cont_yn = str(task.request_spec.cont_yn or "N").upper()
        next_key = str(task.request_spec.next_key or "").upper()
        provider_return_code: int | None = None
        provider_return_msg: str | None = None
        chart_response_received = False
        try:
            while True:
                page_count += 1
                preview = task.request_preview.model_copy(
                    update={
                        "headers": {
                            **task.request_preview.headers,
                            "cont-yn": next_cont_yn,
                            "next-key": next_key,
                        }
                    }
                )
                response = transport.execute(preview, auth_header=auth_header)
                chart_response_received = True
                body_json = dict(response.get("body_json") or {})
                response_headers = dict(response.get("headers") or {})
                cont_yn = _header_value(response_headers, "cont-yn", "cont_yn", "contYn", default="N").upper() or "N"
                response_next_key = _header_value(response_headers, "next-key", "next_key", "nextKey", default="").upper()
                provider_return_code = int(body_json.get("return_code", 0) or 0)
                provider_return_msg = str(body_json.get("return_msg") or "").strip() or None
                task_status = HistoricalMarketDataReadinessStatus(classify_chart_payload(task.request_spec.api_id, body_json))
                if task_status == HistoricalMarketDataReadinessStatus.REAL_CAPTURE_EXECUTED:
                    built_response = _build_response(
                        task,
                        body_json,
                        response_headers=response_headers,
                        page_index=page_count,
                        base_url=getattr(transport, "base_url", None),
                    )
                    raw_responses.append(built_response)
                    valid_raw_responses.append(built_response)
                    next_cont_yn = "Y"
                    next_key = response_next_key
                elif task_status == HistoricalMarketDataReadinessStatus.PROVIDER_CHART_ERROR:
                    task_errors.append(provider_return_msg or "provider returned chart error")
                    break
                elif task_status == HistoricalMarketDataReadinessStatus.BLOCKED_AUTH_OR_TOKEN:
                    task_errors.append("provider returned auth or token error")
                    break
                elif task_status == HistoricalMarketDataReadinessStatus.PROVIDER_EMPTY_RESPONSE:
                    task_errors.append("provider returned no chart rows")
                    break
                else:
                    task_errors.append("chart row schema not implemented or not recognized")
                    break
                if cont_yn != "Y" or not response_next_key or page_count >= real_capture_config.max_continuation_pages:
                    break
        except Exception as exc:
            task_results.append(
                HistoricalChartCaptureRunTaskResult(
                    task_id=task.task_id,
                    request_id=task.request_spec.request_id,
                    execution_decision=HistoricalChartCaptureDecision.BLOCKED,
                    chart_response_received=chart_response_received,
                    errors=[str(exc)],
                )
            )
            continue
        if task_status != HistoricalMarketDataReadinessStatus.REAL_CAPTURE_EXECUTED:
            final_status = task_status
            task_results.append(
                HistoricalChartCaptureRunTaskResult(
                    task_id=task.task_id,
                    request_id=task.request_spec.request_id,
                    execution_decision=HistoricalChartCaptureDecision.BLOCKED,
                    page_count=page_count,
                    provider_return_code=provider_return_code,
                    provider_return_msg=provider_return_msg,
                    chart_response_received=chart_response_received,
                    row_count=_row_count_for_response(task, body_json),
                    blocked_reasons=[task_status.value],
                    errors=task_errors,
                )
            )
            continue
        task_results.append(
            HistoricalChartCaptureRunTaskResult(
                task_id=task.task_id,
                request_id=task.request_spec.request_id,
                execution_decision=HistoricalChartCaptureDecision.ALLOWED,
                success=True,
                page_count=page_count,
                raw_response_count=page_count,
                provider_return_code=provider_return_code,
                provider_return_msg=provider_return_msg,
                chart_response_received=chart_response_received,
                row_count=sum(_row_count_for_response(task, response.raw_payload) for response in valid_raw_responses if response.request_id == task.request_spec.request_id),
            )
        )

    if not valid_raw_responses and final_status != HistoricalMarketDataReadinessStatus.REAL_CAPTURE_EXECUTED:
        return build_capture_run_result_with_status(
            pipeline_input.dataset_id,
            readiness_status=final_status,
            blocked_reasons=[final_status.value],
            transport_kind=transport.transport_kind,
            credential_ref_present=credential_ref_present,
            task_results=task_results,
        )

    raw_lake_records = persist_historical_chart_raw_lake(pipeline_input, valid_raw_responses)
    ohlcv_rows = normalize_historical_ohlcv_rows(pipeline_input.dataset_id, valid_raw_responses) if valid_raw_responses else []
    task_by_request_id = {task.request_spec.request_id: task for task in capture_plan.tasks}
    ohlcv_rows = [
        row
        for row in ohlcv_rows
        if (task := task_by_request_id.get(row.source_ref.replace(".json", ""))) is None or _within_requested_window(task, row.observed_at)
    ]
    coverage_report, freshness_report, completeness_report, gap_report = build_historical_market_data_coverage(
        pipeline_input.dataset_id, valid_raw_responses, ohlcv_rows
    )
    manifest, _price_history_rows = build_historical_ohlcv_dataset_manifest(pipeline_input, ohlcv_rows)
    for result in task_results:
        if result.success:
            result.normalized_row_count = sum(1 for row in ohlcv_rows if row.row_id.startswith(result.request_id))
    audit_report = HistoricalChartCaptureRunAudit(
        audit_id=f"{pipeline_input.dataset_id}-REAL-CAPTURE-AUDIT",
        dataset_id=pipeline_input.dataset_id,
        transport_kind=transport.transport_kind,
        credential_ref_present=credential_ref_present,
        credential_policy=HistoricalMarketDataCredentialPolicy.KEY_REF_ONLY if credential_ref_present else HistoricalMarketDataCredentialPolicy.BLOCKED,
        redaction_status=HistoricalMarketDataRedactionStatus.PASSED,
        auth_header_present=credential_ref_present,
        task_results=task_results,
    )
    safety_summary = redact_credential_ref_summary(real_capture_config.credential_ref if credential_ref_present else None)
    safety_report = HistoricalMarketDataSafetyReport(
        report_id=f"{pipeline_input.dataset_id}-REAL-CAPTURE-SAFETY-REPORT",
        readiness_status=HistoricalMarketDataReadinessStatus.REAL_CAPTURE_EXECUTED if valid_raw_responses else HistoricalMarketDataReadinessStatus.DATA_GAP,
        findings=[
            "real chart capture is explicit opt-in only",
            "raw lake remains redacted",
            "no account/order endpoint support",
            f"credential_ref_present={str(safety_summary['credential_ref_present']).upper()}",
            "network boundary was user-initiated and bounded",
        ],
        real_capture_blocked=False,
    )
    return HistoricalChartCaptureRunResult(
        run_id=f"{pipeline_input.dataset_id}-REAL-CAPTURE-RUN",
        dataset_id=pipeline_input.dataset_id,
        readiness_status=HistoricalMarketDataReadinessStatus.REAL_CAPTURE_EXECUTED if valid_raw_responses else HistoricalMarketDataReadinessStatus.DATA_GAP,
        task_results=task_results,
        raw_response_count=len(valid_raw_responses),
        normalized_row_count=len(ohlcv_rows),
        manifest=manifest,
        coverage_report=coverage_report,
        freshness_report=freshness_report,
        completeness_report=completeness_report,
        gap_report=gap_report,
        safety_report=safety_report,
        audit_report=audit_report,
    )
