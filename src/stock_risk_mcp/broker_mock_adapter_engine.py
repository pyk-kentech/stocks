from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json

from stock_risk_mcp.broker_mock_adapter_guard import validate_broker_mock_adapter_metadata_safety
from stock_risk_mcp.broker_mock_adapter_models import (
    BrokerMockAccountSnapshot,
    BrokerMockAdapterAuditRecord,
    BrokerMockAdapterGapReport,
    BrokerMockAdapterInput,
    BrokerMockAdapterSafetyReport,
    BrokerMockCapability,
    BrokerMockExecutionReport,
    BrokerMockGapCategory,
    BrokerMockOrderIntent,
    BrokerMockOrderRequest,
    BrokerMockOrderResponse,
    BrokerMockOrderSide,
    BrokerMockPositionSnapshot,
)


_GAP_REASON_MAP = (
    ("real order", BrokerMockGapCategory.BROKER_MOCK_REAL_ORDER_NOT_ALLOWED, "real order not allowed"),
    ("real account mutation", BrokerMockGapCategory.BROKER_MOCK_REAL_ACCOUNT_MUTATION_NOT_ALLOWED, "real account mutation not allowed"),
    ("production broker", BrokerMockGapCategory.BROKER_MOCK_PRODUCTION_BROKER_NOT_ALLOWED, "production broker not allowed"),
    ("live trading", BrokerMockGapCategory.BROKER_MOCK_LIVE_TRADING_NOT_ALLOWED, "live trading not allowed"),
    ("live/prod", BrokerMockGapCategory.BROKER_MOCK_LIVE_PROD_NOT_ALLOWED, "live/prod not allowed"),
    ("credentials", BrokerMockGapCategory.BROKER_MOCK_CREDENTIALS_NOT_ALLOWED, "credentials not allowed"),
    ("api endpoint", BrokerMockGapCategory.BROKER_MOCK_NETWORK_CALL_NOT_ALLOWED, "api endpoint not allowed"),
    ("network", BrokerMockGapCategory.BROKER_MOCK_NETWORK_CALL_NOT_ALLOWED, "network not allowed"),
    ("kiwoom api", BrokerMockGapCategory.BROKER_MOCK_KIWOOM_API_CALL_NOT_ALLOWED, "kiwoom api call not allowed"),
    ("ls api", BrokerMockGapCategory.BROKER_MOCK_LS_API_CALL_NOT_ALLOWED, "ls api call not allowed"),
    ("broker api", BrokerMockGapCategory.BROKER_MOCK_BROKER_API_CALL_NOT_ALLOWED, "broker api call not allowed"),
    ("order api", BrokerMockGapCategory.BROKER_MOCK_ORDER_API_CALL_NOT_ALLOWED, "order api call not allowed"),
    ("account api", BrokerMockGapCategory.BROKER_MOCK_ACCOUNT_API_CALL_NOT_ALLOWED, "account api call not allowed"),
    ("provider api", BrokerMockGapCategory.BROKER_MOCK_PROVIDER_API_CALL_NOT_ALLOWED, "provider api call not allowed"),
    ("cloud llm", BrokerMockGapCategory.BROKER_MOCK_CLOUD_LLM_NOT_ALLOWED, "cloud llm not allowed"),
    ("local llm runtime", BrokerMockGapCategory.BROKER_MOCK_LOCAL_LLM_RUNTIME_NOT_ALLOWED, "local llm runtime not allowed"),
    ("parquet", BrokerMockGapCategory.BROKER_MOCK_PARQUET_NOT_ALLOWED, "parquet not allowed"),
)


def run_broker_mock_adapter_boundary(adapter_input: BrokerMockAdapterInput) -> BrokerMockAdapterInput:
    gap_entries: list[dict[str, object]] = []
    capability = _validate_capability(adapter_input.capability, gap_entries)
    order_intent = _build_order_intent(adapter_input.broker_mock_order_intent, capability, gap_entries)
    order_request = _build_order_request(adapter_input.broker_mock_order_request, order_intent, capability)
    order_response = _build_order_response(adapter_input.broker_mock_order_response, order_request, gap_entries)
    execution_report = _build_execution_report(adapter_input.broker_mock_execution_report, order_request, order_response)
    account_snapshot = _build_account_snapshot(adapter_input.broker_mock_account_snapshot)
    _validate_future_boundary(adapter_input.kiwoom_mock_adapter_boundary, "Kiwoom", gap_entries)
    _validate_future_boundary(adapter_input.ls_mock_adapter_boundary, "LS", gap_entries)
    safety_report = _build_safety_report(adapter_input.safety_report, gap_entries)
    gap_report = _build_gap_report(adapter_input.gap_report, gap_entries)
    audit_records = _build_audit_records(adapter_input.audit_records, gap_entries)

    return adapter_input.model_copy(
        update={
            "capability": capability,
            "broker_mock_order_intent": order_intent,
            "broker_mock_order_request": order_request,
            "broker_mock_order_response": order_response,
            "broker_mock_execution_report": execution_report,
            "broker_mock_account_snapshot": account_snapshot,
            "safety_report": safety_report,
            "gap_report": gap_report,
            "audit_records": audit_records,
        }
    )


def _validate_capability(capability: BrokerMockCapability, gap_entries: list[dict[str, object]]) -> BrokerMockCapability:
    if not capability.capability_id:
        gap_entries.append(_gap("missing-capability", BrokerMockGapCategory.BROKER_MOCK_MISSING_CAPABILITY, "BLOCKING", "missing capability"))
        return capability

    if capability.supports_mock_order_submission:
        gap_entries.append(
            _gap(
                f"{capability.capability_id}-unsupported-capability",
                BrokerMockGapCategory.BROKER_MOCK_UNSUPPORTED_CAPABILITY,
                "BLOCKING",
                "mock order submission capability is not allowed in v6.2 local boundary engine",
            )
        )

    if capability.supports_async_callback_simulation:
        gap_entries.append(
            _gap(
                f"{capability.capability_id}-network-not-allowed",
                BrokerMockGapCategory.BROKER_MOCK_NETWORK_CALL_NOT_ALLOWED,
                "BLOCKING",
                "async callback simulation implies transport and is not allowed",
            )
        )

    if not capability.supported_order_sides:
        gap_entries.append(
            _gap(
                f"{capability.capability_id}-missing-capability",
                BrokerMockGapCategory.BROKER_MOCK_MISSING_CAPABILITY,
                "BLOCKING",
                "missing supported order sides",
            )
        )

    try:
        validate_broker_mock_adapter_metadata_safety(
            {
                "capability_id": capability.capability_id,
                "supported_markets": capability.supported_markets,
                "supported_order_types": capability.supported_order_types,
            },
            context="broker mock capability",
        )
    except ValueError as exc:
        gap_entries.append(_unsafe_gap(f"{capability.capability_id}-unsafe", str(exc)))

    return capability


def _build_order_intent(
    order_intent: BrokerMockOrderIntent,
    capability: BrokerMockCapability,
    gap_entries: list[dict[str, object]],
) -> BrokerMockOrderIntent:
    if not order_intent.source_paper_order_intent_ref_id:
        gap_entries.append(
            _gap(
                "missing-paper-order-intent-ref",
                BrokerMockGapCategory.BROKER_MOCK_MISSING_PAPER_ORDER_INTENT_REF,
                "BLOCKING",
                "missing paper order intent ref",
            )
        )

    if order_intent.side not in capability.supported_order_sides:
        gap_entries.append(
            _gap(
                f"{order_intent.mock_order_intent_id}-unsupported-order-side",
                BrokerMockGapCategory.BROKER_MOCK_UNSUPPORTED_ORDER_SIDE,
                "BLOCKING",
                "unsupported order side",
            )
        )

    if capability.supported_order_types and order_intent.mock_order_type not in capability.supported_order_types:
        gap_entries.append(
            _gap(
                f"{order_intent.mock_order_intent_id}-unsupported-order-type",
                BrokerMockGapCategory.BROKER_MOCK_UNSUPPORTED_ORDER_TYPE,
                "BLOCKING",
                "unsupported order type",
            )
        )

    try:
        validate_broker_mock_adapter_metadata_safety(
            {
                "metadata": order_intent.metadata,
                "market": order_intent.market,
                "symbol": order_intent.symbol,
            },
            context="broker mock order intent",
        )
    except ValueError as exc:
        gap_entries.append(_unsafe_gap(f"{order_intent.mock_order_intent_id}-unsafe", str(exc)))

    return order_intent.model_copy(
        update={
            "metadata": {
                **order_intent.metadata,
                "boundary_status": "LOCAL_MOCK_ONLY",
                "execution_mode": "NON_EXECUTABLE_BY_DEFAULT",
            }
        }
    )


def _build_order_request(
    order_request: BrokerMockOrderRequest,
    order_intent: BrokerMockOrderIntent,
    capability: BrokerMockCapability,
) -> BrokerMockOrderRequest:
    return order_request.model_copy(
        update={
            "request_metadata": {
                **order_request.request_metadata,
                "capability_ref": capability.capability_id,
                "symbol": order_intent.symbol,
                "mock_side": order_intent.side.value,
                "simulated_quantity": order_intent.requested_quantity,
                "boundary_status": "REQUEST_SHAPE_ONLY",
                "transport_enabled": False,
            }
        }
    )


def _build_order_response(
    order_response: BrokerMockOrderResponse,
    order_request: BrokerMockOrderRequest,
    gap_entries: list[dict[str, object]],
) -> BrokerMockOrderResponse:
    blocking = _has_blocking_gaps(gap_entries)
    return order_response.model_copy(
        update={
            "mock_status": "MOCK_REJECTED" if blocking else "MOCK_ACCEPTED",
            "response_metadata": {
                **order_response.response_metadata,
                "mock_request_ref": order_request.mock_order_request_id,
                "boundary_message": "Boundary-only mock response. No broker execution performed.",
                "no_execution": True,
                "rejection_gap_count": len([g for g in gap_entries if g["severity"] == "BLOCKING"]),
            },
        }
    )


def _build_execution_report(
    execution_report: BrokerMockExecutionReport,
    order_request: BrokerMockOrderRequest,
    order_response: BrokerMockOrderResponse,
) -> BrokerMockExecutionReport:
    return execution_report.model_copy(
        update={
            "mock_status": "MOCK_REJECTED" if order_response.mock_status == "MOCK_REJECTED" else "MOCK_ACCEPTED",
            "execution_metadata": {
                **execution_report.execution_metadata,
                "mock_request_ref": order_request.mock_order_request_id,
                "mock_response_ref": order_response.mock_order_response_id,
                "real_execution": False,
                "exchange_confirmation": False,
                "broker_confirmation": False,
            },
        }
    )


def _build_account_snapshot(account_snapshot: BrokerMockAccountSnapshot) -> BrokerMockAccountSnapshot:
    positions = [
        position.model_copy(
            update={
                "metadata": {
                    **position.metadata,
                    "boundary_status": "POSITION_SNAPSHOT_ONLY",
                    "real_account_number_present": False,
                }
            }
        )
        for position in account_snapshot.position_snapshots
    ]
    return account_snapshot.model_copy(
        update={
            "position_snapshots": positions,
            "metadata": {
                **account_snapshot.metadata,
                "boundary_status": "ACCOUNT_SNAPSHOT_ONLY",
                "real_account_number_present": False,
                "credential_material_present": False,
            },
        }
    )


def _validate_future_boundary(boundary, label: str, gap_entries: list[dict[str, object]]) -> None:
    if not boundary.future_only or boundary.implementation_present or boundary.executable_transport_present:
        gap_entries.append(
            _gap(
                f"{boundary.boundary_id}-future-only",
                BrokerMockGapCategory.BROKER_MOCK_UNSUPPORTED_CAPABILITY,
                "BLOCKING",
                f"{label} boundary must remain future-only and non-executable",
            )
        )

    try:
        validate_broker_mock_adapter_metadata_safety(boundary.metadata, context=f"{label} boundary")
    except ValueError as exc:
        gap_entries.append(_unsafe_gap(f"{boundary.boundary_id}-unsafe", str(exc)))


def _build_safety_report(
    safety_report: BrokerMockAdapterSafetyReport,
    gap_entries: list[dict[str, object]],
) -> BrokerMockAdapterSafetyReport:
    blocking = [entry for entry in gap_entries if entry["severity"] == "BLOCKING"]
    return safety_report.model_copy(
        update={
            "blocked": bool(blocking),
            "findings": [entry["message"] for entry in blocking],
        }
    )


def _build_gap_report(
    gap_report: BrokerMockAdapterGapReport,
    gap_entries: list[dict[str, object]],
) -> BrokerMockAdapterGapReport:
    baseline = [
        _gap("boundary-generated", BrokerMockGapCategory.BROKER_MOCK_BOUNDARY_GENERATED, "REPORT_ONLY", "broker mock boundary generated"),
        _gap("local-only", BrokerMockGapCategory.BROKER_MOCK_LOCAL_ONLY, "REPORT_ONLY", "broker mock boundary remains local-only"),
        _gap("offline-only", BrokerMockGapCategory.BROKER_MOCK_OFFLINE_ONLY, "REPORT_ONLY", "broker mock boundary remains offline-only"),
        _gap("mock-only", BrokerMockGapCategory.BROKER_MOCK_MOCK_ONLY, "REPORT_ONLY", "broker mock boundary remains mock-only"),
        _gap("paper-only", BrokerMockGapCategory.BROKER_MOCK_PAPER_ONLY, "REPORT_ONLY", "broker mock boundary remains paper-only"),
        _gap("disabled-by-default", BrokerMockGapCategory.BROKER_MOCK_DISABLED_BY_DEFAULT, "REPORT_ONLY", "broker mock boundary remains disabled-by-default"),
        _gap("explicit-opt-in-required", BrokerMockGapCategory.BROKER_MOCK_EXPLICIT_OPT_IN_REQUIRED, "REPORT_ONLY", "broker mock boundary requires explicit opt-in"),
        _gap("non-executable-by-default", BrokerMockGapCategory.BROKER_MOCK_NON_EXECUTABLE_BY_DEFAULT, "REPORT_ONLY", "broker mock boundary remains non-executable-by-default"),
    ]
    all_gaps = gap_entries + baseline
    return gap_report.model_copy(
        update={
            "gap_status": _gap_status(all_gaps),
            "gap_categories": [entry["gap_category"] for entry in all_gaps],
            "blocking_gap_count": len([entry for entry in all_gaps if entry["severity"] == "BLOCKING"]),
            "report_only_gap_count": len([entry for entry in all_gaps if entry["severity"] != "BLOCKING"]),
            "gaps": [entry["message"] for entry in all_gaps],
        }
    )


def _build_audit_records(
    audit_records: list[BrokerMockAdapterAuditRecord],
    gap_entries: list[dict[str, object]],
) -> list[BrokerMockAdapterAuditRecord]:
    if not audit_records:
        return []

    updated_records = []
    for record in audit_records:
        updated_records.append(
            record.model_copy(
                update={
                    "operator_context": record.operator_context,
                    "source_path": record.source_path,
                }
            )
        )
    return updated_records


def _has_blocking_gaps(gap_entries: list[dict[str, object]]) -> bool:
    return any(entry["severity"] == "BLOCKING" for entry in gap_entries)


def _gap_status(gap_entries: list[dict[str, object]]) -> str:
    if _has_blocking_gaps(gap_entries):
        return "BLOCKING_GAPS"
    if gap_entries:
        return "REPORT_ONLY_GAPS"
    return "NO_GAPS"


def _gap(gap_id: str, category: BrokerMockGapCategory, severity: str, message: str) -> dict[str, object]:
    return {
        "gap_id": gap_id.upper(),
        "gap_category": category,
        "severity": severity,
        "message": message,
    }


def _unsafe_gap(gap_id: str, reason: str) -> dict[str, object]:
    lowered = reason.lower()
    for needle, category, message in _GAP_REASON_MAP:
        if needle in lowered:
            return _gap(gap_id, category, "BLOCKING", message)
    return _gap(gap_id, BrokerMockGapCategory.BROKER_MOCK_UNSUPPORTED_CAPABILITY, "BLOCKING", "unsafe metadata not allowed")


def load_broker_mock_capability_matrix(path: str | Path) -> dict[str, object]:
    source_path = Path(path)
    lowered = str(source_path).strip().lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError("capability matrix path must be local-only")
    if source_path.suffix.lower() != ".json":
        raise ValueError("capability matrix path must be a local JSON file")
    return json.loads(source_path.read_text(encoding="utf-8"))
