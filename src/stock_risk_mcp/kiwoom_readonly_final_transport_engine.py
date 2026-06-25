from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from tempfile import mkstemp

from stock_risk_mcp.kiwoom_manual_response_import_engine import build_kiwoom_manual_response_import_harness
from stock_risk_mcp.kiwoom_manual_response_import_models import (
    KiwoomManualResponseImportFile,
    KiwoomManualResponseImportRequest,
    KiwoomManualResponseImportResult,
)
from stock_risk_mcp.kiwoom_readonly_final_transport_capture import write_kiwoom_readonly_final_capture
from stock_risk_mcp.kiwoom_readonly_final_transport_client import (
    TransportCallable,
    TokenProviderCallable,
    domain_base_url,
    execute_kiwoom_readonly_final_http_transport,
    resolve_kiwoom_readonly_final_token,
)
from stock_risk_mcp.kiwoom_readonly_final_transport_models import (
    KiwoomReadonlyFinalAllowlistReport,
    KiwoomReadonlyFinalAuditRecord,
    KiwoomReadonlyFinalCaptureIndex,
    KiwoomReadonlyFinalCaptureRecord,
    KiwoomReadonlyFinalCaptureStatus,
    KiwoomReadonlyFinalDomain,
    KiwoomReadonlyFinalExecutionDecision,
    KiwoomReadonlyFinalGapEntry,
    KiwoomReadonlyFinalGapReport,
    KiwoomReadonlyFinalParserRoutingResult,
    KiwoomReadonlyFinalRequest,
    KiwoomReadonlyFinalRequestPreview,
    KiwoomReadonlyFinalResponse,
    KiwoomReadonlyFinalResult,
    KiwoomReadonlyFinalSafetyReport,
    KiwoomReadonlyFinalSmokeResult,
    KiwoomReadonlyFinalSnapshotValidationResult,
    KiwoomReadonlyFinalStatus,
    KiwoomReadonlyFinalSummaryReport,
    KiwoomReadonlyFinalTokenProviderKind,
    KiwoomReadonlyFinalTokenProviderReport,
    KiwoomReadonlyFinalTransportMode,
    KiwoomReadonlyFinalReadinessReport,
)


ALLOWLIST_API_PATHS = {
    "KA10080": "/api/dostk/chart/minute",
    "KA10081": "/api/dostk/chart/daily",
    "KA00198": "/api/dostk/rank/realtime-item-inquiry",
    "KA10023": "/api/dostk/rank/volume-surge",
    "KA10030": "/api/dostk/rank/today-volume",
    "KA10032": "/api/dostk/rank/trading-value",
    "KA10004": "/api/dostk/quote/orderbook",
    "KA10003": "/api/dostk/quote/execution",
    "KA10001": "/api/dostk/quote/basic-info",
    "KA10059": "/api/dostk/flow/investor-institution",
    "KA90001": "/api/dostk/theme/group",
    "KA90002": "/api/dostk/theme/component",
    "KA40003": "/api/dostk/etf/daily-trend",
}
SCHEMA_GAP_API_IDS = {"KA90003"}
ACCOUNT_BLOCKED_API_IDS = {"KA00001"}
ORDER_BLOCKED_API_IDS = {"KT10000", "KT10001", "KT10002", "KT10003"}
BLOCKED_API_PREFIXES = ["KT", "ACCOUNT", "ORDER"]
_SENSITIVE_KEY_PATTERNS = (
    (re.compile(r"authorization", re.IGNORECASE), "authorization header in user input is blocked"),
    (re.compile(r"access[_ -]?token|refresh[_ -]?token|token", re.IGNORECASE), "raw token marker is blocked"),
    (re.compile(r"appkey|app[_ -]?key", re.IGNORECASE), "appkey marker is blocked"),
    (re.compile(r"secretkey|app_secret|client_secret|secret", re.IGNORECASE), "secret marker is blocked"),
    (re.compile(r"account|acct|계좌", re.IGNORECASE), "account marker is blocked"),
    (re.compile(r"order|ordr|주문|broker[_ -]?order[_ -]?id", re.IGNORECASE), "order marker is blocked"),
)
_BEARER_VALUE_PATTERN = re.compile(r"Bearer\s+\S+", re.IGNORECASE)


def _now() -> datetime:
    return datetime.now().astimezone()


def _status_priority(status: KiwoomReadonlyFinalStatus) -> int:
    order = [
        KiwoomReadonlyFinalStatus.BLOCKED_TOKEN_POLICY,
        KiwoomReadonlyFinalStatus.BLOCKED_ACCOUNT_API,
        KiwoomReadonlyFinalStatus.BLOCKED_ORDER_API,
        KiwoomReadonlyFinalStatus.BLOCKED_API_NOT_ALLOWLISTED,
        KiwoomReadonlyFinalStatus.BLOCKED_MISSING_OPT_IN,
        KiwoomReadonlyFinalStatus.BLOCKED_NETWORK_IN_TEST,
        KiwoomReadonlyFinalStatus.BLOCKED_CAPTURE_POLICY,
        KiwoomReadonlyFinalStatus.BLOCKED_UNSAFE_PATH,
        KiwoomReadonlyFinalStatus.BLOCKED_SENSITIVE_CONTENT,
        KiwoomReadonlyFinalStatus.REJECTED,
        KiwoomReadonlyFinalStatus.SCHEMA_GAP,
        KiwoomReadonlyFinalStatus.CAPTURE_GAP,
        KiwoomReadonlyFinalStatus.DATA_GAP,
        KiwoomReadonlyFinalStatus.PREVIEW_READY,
        KiwoomReadonlyFinalStatus.MOCKED_CALL_READY,
        KiwoomReadonlyFinalStatus.REAL_READONLY_READY,
        KiwoomReadonlyFinalStatus.REAL_READONLY_SINGLE_CALL_READY,
        KiwoomReadonlyFinalStatus.REAL_READONLY_EXECUTED,
        KiwoomReadonlyFinalStatus.RESPONSE_CAPTURED,
        KiwoomReadonlyFinalStatus.RESPONSE_ROUTED,
        KiwoomReadonlyFinalStatus.SNAPSHOT_VALIDATED,
        KiwoomReadonlyFinalStatus.V8_FINAL_READY,
    ]
    return order.index(status)


def _gap(request_id: str, suffix: str, category: str, severity: str, message: str) -> KiwoomReadonlyFinalGapEntry:
    return KiwoomReadonlyFinalGapEntry(
        gap_id=f"{request_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def _default_summary(status: KiwoomReadonlyFinalStatus) -> str:
    if status == KiwoomReadonlyFinalStatus.V8_FINAL_READY:
        return "kiwoom final readonly transport reports v8 completion without trading or account access"
    if status == KiwoomReadonlyFinalStatus.SNAPSHOT_VALIDATED:
        return "kiwoom final readonly transport executed report-only snapshot validation"
    if status == KiwoomReadonlyFinalStatus.RESPONSE_ROUTED:
        return "kiwoom final readonly transport routed a redacted response through existing parsers"
    if status == KiwoomReadonlyFinalStatus.RESPONSE_CAPTURED:
        return "kiwoom final readonly transport captured a redacted response safely"
    if status == KiwoomReadonlyFinalStatus.REAL_READONLY_EXECUTED:
        return "kiwoom final readonly transport executed a user-initiated single read-only call"
    if status == KiwoomReadonlyFinalStatus.MOCKED_CALL_READY:
        return "kiwoom final readonly transport mocked-call path is ready"
    if status == KiwoomReadonlyFinalStatus.PREVIEW_READY:
        return "kiwoom final readonly transport preview is ready"
    return "kiwoom final readonly transport is blocked or incomplete by design"


def _scan_sensitive(value) -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key)
            for pattern, message in _SENSITIVE_KEY_PATTERNS:
                if pattern.search(key_text):
                    findings.append(message)
            findings.extend(_scan_sensitive(nested))
    elif isinstance(value, list):
        for item in value:
            findings.extend(_scan_sensitive(item))
    elif isinstance(value, str):
        if _BEARER_VALUE_PATTERN.search(value):
            findings.append("raw bearer token marker is blocked")
        lowered = value.lower()
        if "wss://" in lowered or lowered.startswith("ws://"):
            findings.append("websocket path is rejected")
        if lowered.startswith("http://") or lowered.startswith("https://"):
            findings.append("non-Kiwoom URL override is blocked")
    return sorted(set(findings))


def _classify_api(api_id: str) -> KiwoomReadonlyFinalStatus:
    api_id = api_id.upper()
    if api_id in ACCOUNT_BLOCKED_API_IDS:
        return KiwoomReadonlyFinalStatus.BLOCKED_ACCOUNT_API
    if api_id in ORDER_BLOCKED_API_IDS or api_id.startswith("KT"):
        return KiwoomReadonlyFinalStatus.BLOCKED_ORDER_API
    if api_id in ALLOWLIST_API_PATHS or api_id in SCHEMA_GAP_API_IDS:
        return KiwoomReadonlyFinalStatus.PREVIEW_READY
    return KiwoomReadonlyFinalStatus.BLOCKED_API_NOT_ALLOWLISTED


def _build_request_preview(request: KiwoomReadonlyFinalRequest) -> KiwoomReadonlyFinalRequestPreview:
    base_url = domain_base_url(request.domain) or "BLOCKED_DOMAIN"
    path = ALLOWLIST_API_PATHS.get(request.api_id, "/blocked")
    return KiwoomReadonlyFinalRequestPreview(
        report_id=f"{request.request_id}-REQUEST-PREVIEW-REPORT",
        api_id=request.api_id,
        domain=request.domain,
        url=f"{base_url}{path}",
        method="POST",
        path=path,
        headers={
            "api-id": request.api_id,
            "authorization": request.token_provider.token_reference_label,
            "cont-yn": request.continuation.cont_yn,
            "next-key": request.continuation.next_key,
            "content-type": "application/json;charset=UTF-8",
        },
        body_json=request.body_json,
        continuation=request.continuation,
    )


def _build_allowlist_report(request_id: str) -> KiwoomReadonlyFinalAllowlistReport:
    return KiwoomReadonlyFinalAllowlistReport(
        report_id=f"{request_id}-ALLOWLIST-REPORT",
        allowed_api_ids=sorted(ALLOWLIST_API_PATHS),
        schema_gap_api_ids=sorted(SCHEMA_GAP_API_IDS),
        blocked_api_prefixes=BLOCKED_API_PREFIXES,
    )


def _build_token_provider_report(
    request: KiwoomReadonlyFinalRequest,
    *,
    token_loaded: bool,
    findings: list[str],
) -> KiwoomReadonlyFinalTokenProviderReport:
    return KiwoomReadonlyFinalTokenProviderReport(
        report_id=f"{request.request_id}-TOKEN-PROVIDER-REPORT",
        provider_kind=request.token_provider.provider_kind,
        enabled=request.token_provider.provider_kind != KiwoomReadonlyFinalTokenProviderKind.DISABLED,
        env_var_name=request.token_provider.env_var_name,
        token_loaded=token_loaded,
        reference_label=request.token_provider.token_reference_label,
        findings=findings,
    )


def _decision_for_request(
    request: KiwoomReadonlyFinalRequest,
    *,
    body_findings: list[str],
    running_in_pytest: bool,
) -> tuple[KiwoomReadonlyFinalStatus, list[str], bool]:
    reasons: list[str] = []
    classification = _classify_api(request.api_id)
    if classification != KiwoomReadonlyFinalStatus.PREVIEW_READY:
        return classification, [classification.value], False
    if request.domain == KiwoomReadonlyFinalDomain.UNKNOWN_BLOCKED:
        return KiwoomReadonlyFinalStatus.REJECTED, ["unknown domain is blocked"], False
    if body_findings:
        return KiwoomReadonlyFinalStatus.BLOCKED_TOKEN_POLICY, body_findings, False
    if request.mode == KiwoomReadonlyFinalTransportMode.BLOCKED_BY_DEFAULT:
        return KiwoomReadonlyFinalStatus.BLOCKED_DEFAULT, ["default transport remains blocked"], False
    if request.mode == KiwoomReadonlyFinalTransportMode.DRY_RUN_PREVIEW_ONLY:
        return KiwoomReadonlyFinalStatus.PREVIEW_READY, ["preview-only mode selected"], False
    if request.mode == KiwoomReadonlyFinalTransportMode.MOCKED_TRANSPORT_ONLY:
        if request.api_id in SCHEMA_GAP_API_IDS:
            reasons.append("schema-gap api remains routing-only")
        return KiwoomReadonlyFinalStatus.MOCKED_CALL_READY, reasons or ["mocked transport is ready"], True
    if request.mode in {
        KiwoomReadonlyFinalTransportMode.REAL_READONLY_OPT_IN,
        KiwoomReadonlyFinalTransportMode.REAL_READONLY_SINGLE_CALL_SMOKE,
    }:
        if running_in_pytest:
            return KiwoomReadonlyFinalStatus.BLOCKED_NETWORK_IN_TEST, ["real network attempt is blocked in pytest"], False
        if not request.opt_in.allow_real_readonly_network:
            reasons.append("allow_real_readonly_network is required")
        if not request.opt_in.acknowledge_readonly_only:
            reasons.append("acknowledge_readonly_only is required")
        if not request.opt_in.acknowledge_no_orders:
            reasons.append("acknowledge_no_orders is required")
        if not request.opt_in.acknowledge_user_initiated:
            reasons.append("acknowledge_user_initiated is required")
        if (
            request.mode == KiwoomReadonlyFinalTransportMode.REAL_READONLY_SINGLE_CALL_SMOKE
            and not request.opt_in.acknowledge_single_call_smoke
        ):
            reasons.append("acknowledge_single_call_smoke is required")
        if request.token_provider.provider_kind == KiwoomReadonlyFinalTokenProviderKind.DISABLED:
            reasons.append("token provider must be explicitly configured")
        if reasons:
            return KiwoomReadonlyFinalStatus.BLOCKED_MISSING_OPT_IN, reasons, False
        if request.mode == KiwoomReadonlyFinalTransportMode.REAL_READONLY_SINGLE_CALL_SMOKE:
            return KiwoomReadonlyFinalStatus.REAL_READONLY_SINGLE_CALL_READY, ["single-call smoke is opt-in gated"], True
        return KiwoomReadonlyFinalStatus.REAL_READONLY_READY, ["real readonly path is opt-in gated"], True
    return KiwoomReadonlyFinalStatus.REJECTED, ["unsupported transport mode"], False


def _build_execution_decision(
    request: KiwoomReadonlyFinalRequest,
    *,
    body_findings: list[str],
    running_in_pytest: bool,
) -> KiwoomReadonlyFinalExecutionDecision:
    status, reasons, execute_transport = _decision_for_request(
        request,
        body_findings=body_findings,
        running_in_pytest=running_in_pytest,
    )
    return KiwoomReadonlyFinalExecutionDecision(
        report_id=f"{request.request_id}-EXECUTION-DECISION-REPORT",
        status=status,
        allowed=execute_transport,
        execute_transport=execute_transport,
        capture_allowed=request.capture_policy.enabled and execute_transport,
        reasons=reasons,
    )


def _build_response(
    request: KiwoomReadonlyFinalRequest,
    *,
    payload: dict[str, object],
    headers: dict[str, object] | None = None,
    status_code: int = 200,
) -> KiwoomReadonlyFinalResponse:
    return KiwoomReadonlyFinalResponse(
        response_id=f"{request.request_id}-RESPONSE-REPORT",
        api_id=request.api_id,
        domain=request.domain,
        status_code=status_code,
        continuation=request.continuation,
        headers={
            "cont-yn": request.continuation.cont_yn,
            "next-key": request.continuation.next_key,
            **(headers or {}),
        },
        body_json=payload,
    )


def _build_capture_record(
    request: KiwoomReadonlyFinalRequest,
    *,
    response: KiwoomReadonlyFinalResponse | None,
    findings: list[str],
) -> KiwoomReadonlyFinalCaptureRecord:
    status = KiwoomReadonlyFinalCaptureStatus.CAPTURE_DISABLED
    if request.capture_policy.enabled:
        status = KiwoomReadonlyFinalCaptureStatus.CAPTURE_READY
        if findings:
            blocked_messages = " ".join(findings).lower()
            if "account" in blocked_messages or "order" in blocked_messages:
                status = KiwoomReadonlyFinalCaptureStatus.CAPTURE_BLOCKED_ACCOUNT_ORDER_CONTENT
            else:
                status = KiwoomReadonlyFinalCaptureStatus.CAPTURE_BLOCKED_SENSITIVE_CONTENT
    payload = response.body_json if response else {}
    return KiwoomReadonlyFinalCaptureRecord(
        report_id=f"{request.request_id}-CAPTURE-REPORT",
        status=status,
        api_id=request.api_id,
        domain=request.domain,
        provider_symbol=request.provider_symbol,
        canonical_instrument_key=request.canonical_instrument_key,
        captured_at=_now() if request.capture_policy.enabled else None,
        observed_at=request.observed_at,
        available_at=request.available_at,
        response_status_code=response.status_code if response else None,
        return_code=payload.get("return_code") if isinstance(payload.get("return_code"), int) else None,
        return_msg=str(payload.get("return_msg")) if payload.get("return_msg") is not None else None,
        source_ref=None,
        findings=findings,
    )


def _route_response_via_manual_import(
    request: KiwoomReadonlyFinalRequest,
    *,
    response_body: dict[str, object],
    source_file: str,
) -> KiwoomManualResponseImportResult:
    import_request = KiwoomManualResponseImportRequest(
        request_id=f"{request.request_id}-MANUAL-IMPORT",
        files=[
            KiwoomManualResponseImportFile(
                file_path=source_file,
                declared_api_id=request.api_id,
                provider_symbol=request.provider_symbol,
                canonical_instrument_key=request.canonical_instrument_key,
                observed_at=request.observed_at,
                available_at=request.available_at or _now(),
                source_ref=Path(source_file).name,
            )
        ],
        compose_snapshot=request.validate_snapshot,
    )
    return build_kiwoom_manual_response_import_harness(import_request)


def _write_response_to_tempfile(request: KiwoomReadonlyFinalRequest, response_body: dict[str, object]) -> str:
    fd, raw_path = mkstemp(prefix=f"{request.api_id.lower()}_", suffix="_response.json")
    os.close(fd)
    path = Path(raw_path)
    path.write_text(json.dumps(response_body, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _build_parser_routing_result(
    request: KiwoomReadonlyFinalRequest,
    *,
    import_result: KiwoomManualResponseImportResult | None,
    imported_file_path: str | None,
    status: KiwoomReadonlyFinalStatus,
) -> KiwoomReadonlyFinalParserRoutingResult:
    return KiwoomReadonlyFinalParserRoutingResult(
        report_id=f"{request.request_id}-RESPONSE-ROUTING-REPORT",
        status=status,
        imported_file_path=imported_file_path,
        import_result=import_result,
        routing_report=import_result.routing_report if import_result else None,
        canonical_output_report=import_result.canonical_output_report if import_result else None,
        safety_report=import_result.safety_report if import_result else None,
        gap_report=import_result.gap_report if import_result else None,
    )


def _build_snapshot_validation_result(
    request: KiwoomReadonlyFinalRequest,
    *,
    import_result: KiwoomManualResponseImportResult | None,
) -> KiwoomReadonlyFinalSnapshotValidationResult:
    if not request.validate_snapshot:
        return KiwoomReadonlyFinalSnapshotValidationResult(
            report_id=f"{request.request_id}-SNAPSHOT-VALIDATION-REPORT",
            status=KiwoomReadonlyFinalStatus.DATA_GAP,
            composed=False,
            findings=["snapshot validation not requested"],
        )
    if import_result is None or import_result.snapshot_composition_result.snapshot_report is None:
        return KiwoomReadonlyFinalSnapshotValidationResult(
            report_id=f"{request.request_id}-SNAPSHOT-VALIDATION-REPORT",
            status=KiwoomReadonlyFinalStatus.DATA_GAP,
            composed=False,
            findings=["snapshot validation had no imported canonical inputs"],
        )
    composed = bool(import_result.snapshot_composition_result.snapshot_report.snapshots)
    return KiwoomReadonlyFinalSnapshotValidationResult(
        report_id=f"{request.request_id}-SNAPSHOT-VALIDATION-REPORT",
        status=KiwoomReadonlyFinalStatus.SNAPSHOT_VALIDATED if composed else KiwoomReadonlyFinalStatus.DATA_GAP,
        snapshot_report=import_result.snapshot_composition_result.snapshot_report,
        composed=composed,
        findings=[] if composed else ["partial canonical coverage produced no full snapshot"],
    )


def _build_readiness_report(
    request: KiwoomReadonlyFinalRequest,
    *,
    parser_routing_result: KiwoomReadonlyFinalParserRoutingResult | None,
    snapshot_validation_result: KiwoomReadonlyFinalSnapshotValidationResult | None,
    final_status: KiwoomReadonlyFinalStatus,
) -> KiwoomReadonlyFinalReadinessReport:
    return KiwoomReadonlyFinalReadinessReport(
        report_id=f"{request.request_id}-V8-READINESS-REPORT",
        status=KiwoomReadonlyFinalStatus.V8_FINAL_READY
        if final_status
        in {
            KiwoomReadonlyFinalStatus.RESPONSE_ROUTED,
            KiwoomReadonlyFinalStatus.SNAPSHOT_VALIDATED,
            KiwoomReadonlyFinalStatus.RESPONSE_CAPTURED,
            KiwoomReadonlyFinalStatus.REAL_READONLY_EXECUTED,
            KiwoomReadonlyFinalStatus.MOCKED_CALL_READY,
        }
        else final_status,
        mocked_mode_ready=True,
        manual_response_import_ready=True,
        parser_routing_ready=parser_routing_result is not None and parser_routing_result.import_result is not None,
        snapshot_validation_ready=snapshot_validation_result is not None and request.validate_snapshot,
        real_readonly_single_call_path_defined=True,
        default_real_network_blocked=True,
        tests_use_real_network=False,
        account_order_apis_blocked=True,
        v8_complete=True,
        scope_notes=[
            "v8.1 chart/ohlcv covered",
            "v8.2 rank/outlier covered",
            "v8.3 quote/orderbook/liquidity covered",
            "v8.4 flow/program covered with schema-gap handling",
            "v8.5 sector/theme/etf covered",
            "v8.6 snapshot composer reused for validation",
            "v8.7 manual response import reused for routing",
            "v8.8 final transport/capture/smoke/validation added",
            "v9 next scope is external macro/regime data pipeline",
            "v10 next scope is feature store/cache pipeline",
            "v11 next scope is real-data paper trading",
            "v12 next scope is account-read and reconciliation",
            "v13 next scope is controlled execution and live order controls",
        ],
    )


def build_kiwoom_readonly_final_transport(
    request: KiwoomReadonlyFinalRequest,
    *,
    transport: TransportCallable | None = None,
    token_provider: TokenProviderCallable | None = None,
) -> KiwoomReadonlyFinalResult:
    running_in_pytest = "PYTEST_CURRENT_TEST" in getattr(os, "environ")
    body_findings = _scan_sensitive(request.body_json)
    preview = _build_request_preview(request)
    decision = _build_execution_decision(
        request,
        body_findings=body_findings,
        running_in_pytest=running_in_pytest,
    )
    token_value = None
    token_findings: list[str] = []
    if decision.execute_transport and request.token_provider.provider_kind != KiwoomReadonlyFinalTokenProviderKind.DISABLED:
        token_value = resolve_kiwoom_readonly_final_token(request.token_provider, token_provider=token_provider)
        if request.mode in {
            KiwoomReadonlyFinalTransportMode.REAL_READONLY_OPT_IN,
            KiwoomReadonlyFinalTransportMode.REAL_READONLY_SINGLE_CALL_SMOKE,
        } and not token_value:
            token_findings.append("missing token returns data gap")
            decision = decision.model_copy(
                update={
                    "status": KiwoomReadonlyFinalStatus.DATA_GAP,
                    "allowed": False,
                    "execute_transport": False,
                    "capture_allowed": False,
                    "reasons": decision.reasons + token_findings,
                }
            )
    token_provider_report = _build_token_provider_report(
        request,
        token_loaded=bool(token_value),
        findings=token_findings,
    )

    safety_findings = body_findings + token_findings
    response_report: KiwoomReadonlyFinalResponse | None = None
    capture_report = _build_capture_record(request, response=None, findings=safety_findings)
    parser_routing_report: KiwoomReadonlyFinalParserRoutingResult | None = None
    snapshot_validation_report: KiwoomReadonlyFinalSnapshotValidationResult | None = None
    smoke_result: KiwoomReadonlyFinalSmokeResult | None = None
    gap_entries: list[KiwoomReadonlyFinalGapEntry] = []
    import_result: KiwoomManualResponseImportResult | None = None
    imported_file_path: str | None = None

    if decision.execute_transport:
        if (
            request.mode == KiwoomReadonlyFinalTransportMode.MOCKED_TRANSPORT_ONLY
            and request.mocked_response_payload is None
            and transport is None
        ):
            gap_entries.append(
                _gap(
                    request.request_id,
                    "MOCKED-RESPONSE",
                    "DATA_GAP",
                    "WARNING",
                    "mocked transport mode requires mocked response payload or fake transport",
                )
            )
            decision = decision.model_copy(
                update={
                    "status": KiwoomReadonlyFinalStatus.DATA_GAP,
                    "allowed": False,
                    "execute_transport": False,
                    "capture_allowed": False,
                    "reasons": decision.reasons + ["mocked response payload is required for CLI-only mocked execution"],
                }
            )
        elif request.mode == KiwoomReadonlyFinalTransportMode.MOCKED_TRANSPORT_ONLY and request.mocked_response_payload is not None:
            payload = request.mocked_response_payload
            response_report = _build_response(request, payload=payload)
        else:
            raw_response = execute_kiwoom_readonly_final_http_transport(
                preview,
                token=token_value,
                transport=transport if request.mode != KiwoomReadonlyFinalTransportMode.REAL_READONLY_SINGLE_CALL_SMOKE else transport,
            )
            response_report = _build_response(
                request,
                payload=_normalize_response_body(raw_response),
                headers=_normalize_response_headers(raw_response),
                status_code=_normalize_status_code(raw_response),
            )
        if decision.execute_transport and response_report is not None:
            capture_findings = _scan_sensitive(response_report.body_json)
            capture_report = _build_capture_record(request, response=response_report, findings=capture_findings)
            if request.capture_policy.enabled and capture_report.status == KiwoomReadonlyFinalCaptureStatus.CAPTURE_READY:
                capture_report = write_kiwoom_readonly_final_capture(
                    request,
                    capture_report,
                    response_body=response_report.body_json,
                )
                if capture_report.status == KiwoomReadonlyFinalCaptureStatus.CAPTURE_FAILED:
                    gap_entries.append(_gap(request.request_id, "CAPTURE", "CAPTURE_FAILED", "WARNING", "capture write failed"))
            elif request.capture_policy.enabled and capture_report.status != KiwoomReadonlyFinalCaptureStatus.CAPTURE_READY:
                gap_entries.append(
                    _gap(
                        request.request_id,
                        "CAPTURE-BLOCKED",
                        capture_report.status.value,
                        "WARNING",
                        "capture was blocked by safety policy",
                    )
                )

            if capture_report.captured_files:
                imported_file_path = capture_report.captured_files[0].file_path
            else:
                imported_file_path = _write_response_to_tempfile(request, response_report.body_json)
            import_result = _route_response_via_manual_import(
                request,
                response_body=response_report.body_json,
                source_file=imported_file_path,
            )
            parser_status = KiwoomReadonlyFinalStatus.RESPONSE_ROUTED
            if import_result.summary_report.readiness.value.endswith("SCHEMA_GAP"):
                parser_status = KiwoomReadonlyFinalStatus.SCHEMA_GAP
            parser_routing_report = _build_parser_routing_result(
                request,
                import_result=import_result,
                imported_file_path=imported_file_path,
                status=parser_status,
            )
            snapshot_validation_report = _build_snapshot_validation_result(
                request,
                import_result=import_result,
            )
            smoke_status = KiwoomReadonlyFinalStatus.REAL_READONLY_EXECUTED
            if request.mode == KiwoomReadonlyFinalTransportMode.MOCKED_TRANSPORT_ONLY:
                smoke_status = KiwoomReadonlyFinalStatus.MOCKED_CALL_READY
            if snapshot_validation_report.composed:
                smoke_status = KiwoomReadonlyFinalStatus.SNAPSHOT_VALIDATED
            elif parser_routing_report.import_result is not None:
                smoke_status = KiwoomReadonlyFinalStatus.RESPONSE_ROUTED
            smoke_result = KiwoomReadonlyFinalSmokeResult(
                report_id=f"{request.request_id}-SINGLE-CALL-SMOKE-REPORT",
                status=smoke_status,
                executed=True,
                response=response_report,
                capture_record=capture_report,
                parser_routing_result=parser_routing_report,
                snapshot_validation_result=snapshot_validation_report,
            )
    else:
        reason_message = "; ".join(decision.reasons) or "transport execution was not allowed"
        gap_entries.append(_gap(request.request_id, "DECISION", decision.status.value, "BLOCKING", reason_message))

    final_status = decision.status
    if smoke_result is not None:
        final_status = smoke_result.status
    elif (
        request.mode == KiwoomReadonlyFinalTransportMode.DRY_RUN_PREVIEW_ONLY
        and decision.status == KiwoomReadonlyFinalStatus.PREVIEW_READY
    ):
        final_status = KiwoomReadonlyFinalStatus.PREVIEW_READY

    if snapshot_validation_report is not None and snapshot_validation_report.composed:
        final_status = KiwoomReadonlyFinalStatus.SNAPSHOT_VALIDATED
    elif parser_routing_report is not None and parser_routing_report.status == KiwoomReadonlyFinalStatus.SCHEMA_GAP:
        final_status = KiwoomReadonlyFinalStatus.SCHEMA_GAP
    elif parser_routing_report is not None and parser_routing_report.import_result is not None:
        final_status = KiwoomReadonlyFinalStatus.RESPONSE_ROUTED
    elif capture_report.status == KiwoomReadonlyFinalCaptureStatus.CAPTURE_WRITTEN:
        final_status = KiwoomReadonlyFinalStatus.RESPONSE_CAPTURED

    readiness_report = _build_readiness_report(
        request,
        parser_routing_result=parser_routing_report,
        snapshot_validation_result=snapshot_validation_report,
        final_status=final_status,
    )
    if final_status in {
        KiwoomReadonlyFinalStatus.RESPONSE_ROUTED,
        KiwoomReadonlyFinalStatus.SNAPSHOT_VALIDATED,
        KiwoomReadonlyFinalStatus.RESPONSE_CAPTURED,
        KiwoomReadonlyFinalStatus.REAL_READONLY_EXECUTED,
        KiwoomReadonlyFinalStatus.MOCKED_CALL_READY,
    }:
        final_status = KiwoomReadonlyFinalStatus.V8_FINAL_READY

    safety_report = KiwoomReadonlyFinalSafetyReport(
        safety_report_id=f"{request.request_id}-SAFETY-REPORT",
        blocked=final_status
        in {
            KiwoomReadonlyFinalStatus.BLOCKED_DEFAULT,
            KiwoomReadonlyFinalStatus.BLOCKED_MISSING_OPT_IN,
            KiwoomReadonlyFinalStatus.BLOCKED_API_NOT_ALLOWLISTED,
            KiwoomReadonlyFinalStatus.BLOCKED_ACCOUNT_API,
            KiwoomReadonlyFinalStatus.BLOCKED_ORDER_API,
            KiwoomReadonlyFinalStatus.BLOCKED_SENSITIVE_CONTENT,
            KiwoomReadonlyFinalStatus.BLOCKED_NETWORK_IN_TEST,
            KiwoomReadonlyFinalStatus.BLOCKED_TOKEN_POLICY,
            KiwoomReadonlyFinalStatus.BLOCKED_CAPTURE_POLICY,
            KiwoomReadonlyFinalStatus.BLOCKED_UNSAFE_PATH,
            KiwoomReadonlyFinalStatus.REJECTED,
        },
        findings=safety_findings + decision.reasons,
    )
    gap_entries.append(
        _gap(
            request.request_id,
            "REPORT-GENERATED",
            "KIWOOM_READONLY_FINAL_REPORT_GENERATED",
            "REPORT_ONLY",
            "kiwoom readonly final transport report generated",
        )
    )
    gap_report = KiwoomReadonlyFinalGapReport(
        gap_report_id=f"{request.request_id}-GAP-REPORT",
        status=final_status,
        gap_entries=gap_entries,
    )
    capture_index = KiwoomReadonlyFinalCaptureIndex(
        report_id=f"{request.request_id}-CAPTURE-INDEX-REPORT",
        capture_records=[capture_report],
    )
    audit_records = [
        KiwoomReadonlyFinalAuditRecord(
            audit_record_id=f"{request.request_id}-AUDIT-1",
            created_at=_now(),
            source_path=request.capture_policy.capture_dir,
            operator_context=request.operator_context,
            redaction_applied=True,
            contains_secret_material=False,
            contains_token_material=False,
            contains_account_material=False,
            findings=safety_findings + decision.reasons,
        )
    ]
    return KiwoomReadonlyFinalResult(
        adapter_result_id=f"{request.request_id}-ADAPTER-RESULT",
        summary_report=KiwoomReadonlyFinalSummaryReport(
            report_id=f"{request.request_id}-SUMMARY-REPORT",
            status=final_status,
            message=_default_summary(final_status),
        ),
        request_preview_report=preview,
        execution_decision_report=decision,
        allowlist_report=_build_allowlist_report(request.request_id),
        token_provider_report=token_provider_report,
        response_report=response_report,
        smoke_result=smoke_result,
        capture_report=capture_report,
        capture_index_report=capture_index,
        parser_routing_report=parser_routing_report,
        snapshot_validation_report=snapshot_validation_report,
        readiness_report=readiness_report,
        safety_report=safety_report,
        gap_report=gap_report,
        audit_records=audit_records,
    )


def _normalize_status_code(raw_response: dict[str, object]) -> int:
    status_code = raw_response.get("status_code")
    if isinstance(status_code, int):
        return status_code
    return 200


def _normalize_response_headers(raw_response: dict[str, object]) -> dict[str, object]:
    headers = raw_response.get("headers")
    if isinstance(headers, dict):
        redacted = {str(key): value for key, value in headers.items() if str(key).lower() != "authorization"}
        if "authorization" in {str(key).lower() for key in headers}:
            redacted["authorization"] = "<REDACTED_TOKEN_REF>"
        return redacted
    return {}


def _normalize_response_body(raw_response: dict[str, object]) -> dict[str, object]:
    body = raw_response.get("body_json")
    if isinstance(body, dict):
        return {str(key): value for key, value in body.items() if str(key).lower() != "authorization"}
    sanitized = {str(key): value for key, value in raw_response.items() if str(key) not in {"status_code", "headers"}}
    sanitized.pop("authorization", None)
    return sanitized
