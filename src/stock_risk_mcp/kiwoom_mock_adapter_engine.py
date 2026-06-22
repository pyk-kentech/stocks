from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.kiwoom_mock_adapter_guard import validate_kiwoom_mock_adapter_metadata_safety
from stock_risk_mcp.kiwoom_mock_adapter_models import (
    KiwoomMockAccountSnapshotDraft,
    KiwoomMockAdapterAuditRecord,
    KiwoomMockAdapterGapReport,
    KiwoomMockAdapterInput,
    KiwoomMockAdapterSafetyReport,
    KiwoomMockCapabilityRef,
    KiwoomMockExecutionDraft,
    KiwoomMockGapCategory,
    KiwoomMockOrderDraft,
    KiwoomMockOrderRequestDraft,
    KiwoomMockOrderResponseDraft,
    KiwoomMockPositionSnapshotDraft,
)


_UNSAFE_GAP_MAP = (
    ("real order", KiwoomMockGapCategory.KIWOOM_MOCK_REAL_ORDER_NOT_ALLOWED, "real order not allowed"),
    ("real account mutation", KiwoomMockGapCategory.KIWOOM_MOCK_REAL_ACCOUNT_MUTATION_NOT_ALLOWED, "real account mutation not allowed"),
    ("oauth token", KiwoomMockGapCategory.KIWOOM_MOCK_OAUTH_TOKEN_REQUEST_NOT_ALLOWED, "oauth token request not allowed"),
    ("authorization", KiwoomMockGapCategory.KIWOOM_MOCK_CREDENTIALS_NOT_ALLOWED, "authorization metadata not allowed"),
    ("credentials", KiwoomMockGapCategory.KIWOOM_MOCK_CREDENTIALS_NOT_ALLOWED, "credentials not allowed"),
    ("mockapi", KiwoomMockGapCategory.KIWOOM_MOCK_MOCKAPI_CALL_NOT_ALLOWED, "mockapi call not allowed"),
    ("broker api", KiwoomMockGapCategory.KIWOOM_MOCK_BROKER_API_CALL_NOT_ALLOWED, "broker api call not allowed"),
    ("order api", KiwoomMockGapCategory.KIWOOM_MOCK_ORDER_API_CALL_NOT_ALLOWED, "order api call not allowed"),
    ("account api", KiwoomMockGapCategory.KIWOOM_MOCK_ACCOUNT_API_CALL_NOT_ALLOWED, "account api call not allowed"),
    ("provider api", KiwoomMockGapCategory.KIWOOM_MOCK_PROVIDER_API_CALL_NOT_ALLOWED, "provider api call not allowed"),
    ("api call", KiwoomMockGapCategory.KIWOOM_MOCK_API_CALL_NOT_ALLOWED, "api call not allowed"),
    ("websocket", KiwoomMockGapCategory.KIWOOM_MOCK_WEBSOCKET_NOT_ALLOWED, "websocket not allowed"),
    ("network", KiwoomMockGapCategory.KIWOOM_MOCK_NETWORK_CALL_NOT_ALLOWED, "network call not allowed"),
    ("live trading", KiwoomMockGapCategory.KIWOOM_MOCK_LIVE_TRADING_NOT_ALLOWED, "live trading not allowed"),
    ("live/prod", KiwoomMockGapCategory.KIWOOM_MOCK_LIVE_PROD_NOT_ALLOWED, "live/prod not allowed"),
    ("cloud llm", KiwoomMockGapCategory.KIWOOM_MOCK_CLOUD_LLM_NOT_ALLOWED, "cloud llm not allowed"),
    ("local llm runtime", KiwoomMockGapCategory.KIWOOM_MOCK_LOCAL_LLM_RUNTIME_NOT_ALLOWED, "local llm runtime not allowed"),
    ("parquet", KiwoomMockGapCategory.KIWOOM_MOCK_PARQUET_NOT_ALLOWED, "parquet not allowed"),
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_kiwoom_mock_capability_matrix(path: str | Path) -> dict[str, object]:
    resolved = Path(path)
    lowered = str(resolved).lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError("capability matrix path must be local")
    if lowered.endswith(".parquet"):
        raise ValueError("parquet remains unsupported")
    return json.loads(resolved.read_text(encoding="utf-8"))


def run_kiwoom_mock_adapter_draft_mapping(adapter_input: KiwoomMockAdapterInput) -> KiwoomMockAdapterInput:
    gap_entries: list[dict[str, object]] = []
    matrix_path = _repo_root() / adapter_input.adapter_config.capability_matrix_ref
    capability_matrix = load_kiwoom_mock_capability_matrix(matrix_path)

    capability_ref = _validate_capability_ref(adapter_input.capability_ref, capability_matrix, gap_entries)
    order_draft = _build_order_draft(adapter_input.order_draft, capability_ref, gap_entries)
    order_request = _build_order_request_draft(adapter_input.order_request_draft, order_draft, capability_ref)
    order_response = _build_order_response_draft(adapter_input.order_response_draft, order_request, gap_entries)
    execution_draft = _build_execution_draft(adapter_input.execution_draft, order_draft, order_request, order_response)
    account_snapshot = _build_account_snapshot_draft(adapter_input.account_snapshot_draft)
    safety_report = _build_safety_report(adapter_input.safety_report, gap_entries)
    gap_report = _build_gap_report(adapter_input.gap_report, gap_entries)
    audit_records = _build_audit_records(adapter_input.audit_records, capability_ref, gap_entries)

    return adapter_input.model_copy(
        update={
            "capability_ref": capability_ref,
            "order_draft": order_draft,
            "order_request_draft": order_request,
            "order_response_draft": order_response,
            "execution_draft": execution_draft,
            "account_snapshot_draft": account_snapshot,
            "safety_report": safety_report,
            "gap_report": gap_report,
            "audit_records": audit_records,
        }
    )


def _validate_capability_ref(
    capability_ref: KiwoomMockCapabilityRef,
    capability_matrix: dict[str, object],
    gap_entries: list[dict[str, object]],
) -> KiwoomMockCapabilityRef:
    endpoint = _find_endpoint(capability_matrix, capability_ref.evidence_endpoint_ref)
    if endpoint is None:
        gap_entries.append(
            _gap(
                f"{capability_ref.capability_ref_id}-missing-endpoint-evidence",
                KiwoomMockGapCategory.KIWOOM_MOCK_MISSING_EVIDENCE_ENDPOINT_REF,
                "BLOCKING",
                "missing endpoint evidence",
            )
        )
        return capability_ref

    if str(endpoint.get("mock_domain", "")).strip() != "https://mockapi.kiwoom.com":
        gap_entries.append(
            _gap(
                f"{capability_ref.capability_ref_id}-mock-domain-required",
                KiwoomMockGapCategory.KIWOOM_MOCK_MOCK_DOMAIN_REQUIRED,
                "BLOCKING",
                "mock domain is required",
            )
        )

    if "krx-only" not in str(endpoint.get("mock_krx_only_note", "")).lower():
        gap_entries.append(
            _gap(
                f"{capability_ref.capability_ref_id}-krx-only",
                KiwoomMockGapCategory.KIWOOM_MOCK_KRX_ONLY_CONSTRAINT,
                "REPORT_ONLY",
                "krx-only constraint should remain represented",
            )
        )

    if not bool(endpoint.get("order_capable")):
        gap_entries.append(
            _gap(
                f"{capability_ref.capability_ref_id}-unsupported-capability",
                KiwoomMockGapCategory.KIWOOM_MOCK_UNSUPPORTED_CAPABILITY,
                "BLOCKING",
                "capability is not an order-capable mock-safe endpoint",
            )
        )

    try:
        validate_kiwoom_mock_adapter_metadata_safety(
            {
                "capability_ref_id": capability_ref.capability_ref_id,
                "evidence_endpoint_ref": capability_ref.evidence_endpoint_ref,
                "endpoint_path": capability_ref.endpoint_path,
                "http_method": capability_ref.http_method,
                "documented_request_fields": capability_ref.documented_request_fields,
                "documented_response_fields": capability_ref.documented_response_fields,
            },
            context="kiwoom mock capability ref",
        )
    except ValueError as exc:
        gap_entries.append(_unsafe_gap(f"{capability_ref.capability_ref_id}-unsafe", str(exc)))

    return capability_ref.model_copy(
        update={
            "documented_request_fields": [item["item_id"] for item in endpoint.get("request_fields", [])],
            "documented_response_fields": [item["item_id"] for item in endpoint.get("response_fields", [])],
        }
    )


def _build_order_draft(
    order_draft: KiwoomMockOrderDraft,
    capability_ref: KiwoomMockCapabilityRef,
    gap_entries: list[dict[str, object]],
) -> KiwoomMockOrderDraft:
    if order_draft.order_type not in capability_ref.supported_order_types:
        gap_entries.append(
            _gap(
                f"{order_draft.order_draft_id}-unsupported-order-type",
                KiwoomMockGapCategory.KIWOOM_MOCK_UNSUPPORTED_ORDER_TYPE,
                "BLOCKING",
                "unsupported order type",
            )
        )

    if order_draft.market != "KRX":
        gap_entries.append(
            _gap(
                f"{order_draft.order_draft_id}-krx-only",
                KiwoomMockGapCategory.KIWOOM_MOCK_KRX_ONLY_CONSTRAINT,
                "BLOCKING",
                "kiwoom mock draft is KRX-only",
            )
        )

    try:
        validate_kiwoom_mock_adapter_metadata_safety(
            {
                "metadata": order_draft.metadata,
                "documented_api_id": order_draft.documented_api_id,
                "documented_endpoint_path": order_draft.documented_endpoint_path,
            },
            context="kiwoom mock order draft",
        )
    except ValueError as exc:
        gap_entries.append(_unsafe_gap(f"{order_draft.order_draft_id}-unsafe", str(exc)))

    return order_draft.model_copy(
        update={
            "metadata": {
                **order_draft.metadata,
                "draft_status": "EVIDENCE_BACKED_DRAFT_ONLY",
                "mock_domain": capability_ref.mock_domain,
                "mock_krx_only": capability_ref.mock_krx_only,
                "transport_classification": "REST_METADATA_ONLY",
                "request_execution_enabled": False,
            }
        }
    )


def _build_order_request_draft(
    order_request: KiwoomMockOrderRequestDraft,
    order_draft: KiwoomMockOrderDraft,
    capability_ref: KiwoomMockCapabilityRef,
) -> KiwoomMockOrderRequestDraft:
    request_fields = {
        **order_request.request_body_fields,
        "dmst_stex_tp": order_draft.market,
        "stk_cd": order_draft.symbol,
        "ord_qty": int(order_draft.quantity),
        "ord_uv": int(order_draft.price),
        "trde_tp": order_draft.order_type,
    }
    return order_request.model_copy(
        update={
            "request_body_fields": request_fields,
            "metadata": {
                **order_request.metadata,
                "draft_status": "REQUEST_SHAPE_ONLY",
                "documented_endpoint_path": capability_ref.endpoint_path,
                "documented_request_fields": capability_ref.documented_request_fields,
                "draft_side": order_draft.side.value,
                "symbol": order_draft.symbol,
                "simulated_quantity": order_draft.quantity,
                "request_execution_enabled": False,
            },
        }
    )


def _build_order_response_draft(
    order_response: KiwoomMockOrderResponseDraft,
    order_request: KiwoomMockOrderRequestDraft,
    gap_entries: list[dict[str, object]],
) -> KiwoomMockOrderResponseDraft:
    blocking = _has_blocking_gaps(gap_entries)
    return order_response.model_copy(
        update={
            "metadata": {
                **order_response.metadata,
                "draft_status": "RESPONSE_SHAPE_ONLY",
                "draft_request_ref": order_request.request_draft_id,
                "draft_status_code": "REJECTED" if blocking else "ACCEPTED",
                "boundary_message": "Draft-only boundary response. No Kiwoom or mockapi request was executed.",
                "real_kiwoom_response": False,
                "mockapi_response_received": False,
            }
        }
    )


def _build_execution_draft(
    execution_draft: KiwoomMockExecutionDraft,
    order_draft: KiwoomMockOrderDraft,
    order_request: KiwoomMockOrderRequestDraft,
    order_response: KiwoomMockOrderResponseDraft,
) -> KiwoomMockExecutionDraft:
    return execution_draft.model_copy(
        update={
            "metadata": {
                **execution_draft.metadata,
                "draft_execution_only": True,
                "real_execution": False,
                "draft_order_ref": order_draft.order_draft_id,
                "draft_request_ref": order_request.request_draft_id,
                "draft_response_ref": order_response.response_draft_id,
            }
        }
    )


def _build_account_snapshot_draft(account_snapshot: KiwoomMockAccountSnapshotDraft) -> KiwoomMockAccountSnapshotDraft:
    positions = [_build_position_snapshot_draft(position) for position in account_snapshot.position_snapshots]
    return account_snapshot.model_copy(
        update={
            "position_snapshots": positions,
            "metadata": {
                **account_snapshot.metadata,
                "draft_account_only": True,
                "real_account_number_present": False,
            },
        }
    )


def _build_position_snapshot_draft(position: KiwoomMockPositionSnapshotDraft) -> KiwoomMockPositionSnapshotDraft:
    return position.model_copy(
        update={
            "metadata": {
                **position.metadata,
                "draft_position_only": True,
                "real_position_state": False,
            }
        }
    )


def _build_safety_report(
    safety_report: KiwoomMockAdapterSafetyReport,
    gap_entries: list[dict[str, object]],
) -> KiwoomMockAdapterSafetyReport:
    findings = [entry["message"] for entry in gap_entries]
    return safety_report.model_copy(
        update={
            "blocked": _has_blocking_gaps(gap_entries),
            "findings": findings,
        }
    )


def _build_gap_report(
    gap_report: KiwoomMockAdapterGapReport,
    gap_entries: list[dict[str, object]],
) -> KiwoomMockAdapterGapReport:
    base_categories = [
        KiwoomMockGapCategory.KIWOOM_MOCK_DRAFT_GENERATED,
        KiwoomMockGapCategory.KIWOOM_MOCK_EVIDENCE_BACKED,
        KiwoomMockGapCategory.KIWOOM_MOCK_DRAFT_ONLY,
        KiwoomMockGapCategory.KIWOOM_MOCK_LOCAL_ONLY,
        KiwoomMockGapCategory.KIWOOM_MOCK_OFFLINE_ONLY,
        KiwoomMockGapCategory.KIWOOM_MOCK_DISABLED_BY_DEFAULT,
        KiwoomMockGapCategory.KIWOOM_MOCK_EXPLICIT_OPT_IN_REQUIRED,
        KiwoomMockGapCategory.KIWOOM_MOCK_NON_EXECUTABLE,
    ]
    categories = base_categories + [entry["category"] for entry in gap_entries]
    blocking = sum(1 for entry in gap_entries if entry["severity"] == "BLOCKING")
    report_only = sum(1 for entry in gap_entries if entry["severity"] != "BLOCKING")
    return gap_report.model_copy(
        update={
            "gap_status": "BLOCKING_GAPS" if blocking else "NO_GAPS",
            "gap_categories": categories,
            "blocking_gap_count": blocking,
            "report_only_gap_count": report_only,
            "gaps": [entry["message"] for entry in gap_entries],
        }
    )


def _build_audit_records(
    audit_records: list[KiwoomMockAdapterAuditRecord],
    capability_ref: KiwoomMockCapabilityRef,
    gap_entries: list[dict[str, object]],
) -> list[KiwoomMockAdapterAuditRecord]:
    return [
        record.model_copy(
            update={
                "operator_context": f"{record.operator_context}|{capability_ref.evidence_endpoint_ref}|GAPS:{len(gap_entries)}"
            }
        )
        for record in audit_records
    ]


def _find_endpoint(capability_matrix: dict[str, object], evidence_endpoint_ref: str) -> dict[str, object] | None:
    target = str(evidence_endpoint_ref).strip().upper()
    for endpoint in capability_matrix.get("endpoints", []):
        if str(endpoint.get("api_id", "")).strip().upper() == target:
            return endpoint
    return None


def _has_blocking_gaps(gap_entries: list[dict[str, object]]) -> bool:
    return any(entry["severity"] == "BLOCKING" for entry in gap_entries)


def _gap(gap_id: str, category: KiwoomMockGapCategory, severity: str, message: str) -> dict[str, object]:
    return {
        "gap_id": gap_id,
        "category": category,
        "severity": severity,
        "message": message,
    }


def _unsafe_gap(gap_id: str, reason: str) -> dict[str, object]:
    lowered = reason.lower()
    for needle, category, message in _UNSAFE_GAP_MAP:
        if needle in lowered:
            return _gap(gap_id, category, "BLOCKING", message)
    return _gap(
        gap_id,
        KiwoomMockGapCategory.KIWOOM_MOCK_API_CALL_NOT_ALLOWED,
        "BLOCKING",
        f"unsafe metadata rejected: {reason}",
    )
