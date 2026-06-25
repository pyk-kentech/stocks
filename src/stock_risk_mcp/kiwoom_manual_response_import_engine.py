from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from stock_risk_mcp.kiwoom_manual_response_import_guard import validate_kiwoom_manual_response_import_metadata_safety
from stock_risk_mcp.kiwoom_manual_response_import_models import (
    KiwoomManualResponseApiClassification,
    KiwoomManualResponseAuditRecord,
    KiwoomManualResponseCanonicalOutputReport,
    KiwoomManualResponseFileClassification,
    KiwoomManualResponseFileClassificationReport,
    KiwoomManualResponseGapEntry,
    KiwoomManualResponseGapReport,
    KiwoomManualResponseImportFile,
    KiwoomManualResponseImportReadiness,
    KiwoomManualResponseImportRequest,
    KiwoomManualResponseImportResult,
    KiwoomManualResponseImportSummaryReport,
    KiwoomManualResponseParserResult,
    KiwoomManualResponseRoutingReport,
    KiwoomManualResponseRoutingResult,
    KiwoomManualResponseSafetyReport,
    KiwoomManualResponseSensitiveScan,
    KiwoomManualResponseSensitiveScanReport,
    KiwoomManualResponseSnapshotCompositionResult,
)
from stock_risk_mcp.kiwoom_readonly_snapshot_engine import build_kiwoom_readonly_domestic_stock_snapshot
from stock_risk_mcp.kiwoom_readonly_snapshot_models import (
    KiwoomReadonlySnapshotAuditRecord,
    KiwoomReadonlySnapshotConfig,
    KiwoomReadonlyDomesticStockSnapshotReport,
    KiwoomReadonlySnapshotSafetyReport,
)
from stock_risk_mcp.kiwoom_rest_readonly_chart_engine import build_kiwoom_rest_readonly_chart_adapter
from stock_risk_mcp.kiwoom_rest_readonly_chart_models import KiwoomRestChartApiId, KiwoomRestChartConfig
from stock_risk_mcp.kiwoom_rest_readonly_flow_engine import build_kiwoom_rest_readonly_flow_adapter
from stock_risk_mcp.kiwoom_rest_readonly_flow_models import KiwoomRestFlowApiId, KiwoomRestFlowConfig
from stock_risk_mcp.kiwoom_rest_readonly_quote_engine import build_kiwoom_rest_readonly_quote_adapter
from stock_risk_mcp.kiwoom_rest_readonly_quote_models import KiwoomRestQuoteApiId, KiwoomRestQuoteConfig
from stock_risk_mcp.kiwoom_rest_readonly_rank_engine import build_kiwoom_rest_readonly_rank_adapter
from stock_risk_mcp.kiwoom_rest_readonly_rank_models import KiwoomRestRankApiId, KiwoomRestRankConfig
from stock_risk_mcp.kiwoom_rest_readonly_sector_engine import build_kiwoom_rest_readonly_sector_adapter
from stock_risk_mcp.kiwoom_rest_readonly_sector_models import KiwoomRestSectorApiId, KiwoomRestSectorConfig


SAFE_FILE_SIZE_LIMIT = 2_000_000
_SENSITIVE_KEY_PATTERNS = (
    (re.compile(r"authorization", re.IGNORECASE), "AUTHORIZATION"),
    (re.compile(r"access[_ -]?token|refresh[_ -]?token|token", re.IGNORECASE), "TOKEN"),
    (re.compile(r"appkey|app[_ -]?key", re.IGNORECASE), "APPKEY"),
    (re.compile(r"secretkey|app_secret|client_secret|secret", re.IGNORECASE), "SECRET"),
    (re.compile(r"account|acct|계좌", re.IGNORECASE), "ACCOUNT"),
    (re.compile(r"password|passwd|pwd", re.IGNORECASE), "PASSWORD"),
    (re.compile(r"order[_ -]?id|broker[_ -]?order[_ -]?id", re.IGNORECASE), "ORDER_ID"),
)
_SENSITIVE_VALUE_PATTERNS = (
    (re.compile(r"^Bearer\s+", re.IGNORECASE), "AUTHORIZATION"),
    (re.compile(r"access[_ -]?token|refresh[_ -]?token", re.IGNORECASE), "TOKEN"),
    (re.compile(r"appkey|secretkey|app_secret|client_secret", re.IGNORECASE), "SECRET"),
)
_BLOCKED_PATH_PATTERNS = (
    (re.compile(r"^https?://", re.IGNORECASE), KiwoomManualResponseImportReadiness.BLOCKED_NETWORK_PATH, "remote http path is blocked"),
    (re.compile(r"^wss?://", re.IGNORECASE), KiwoomManualResponseImportReadiness.BLOCKED_NETWORK_PATH, "websocket path is blocked"),
    (re.compile(r"\$\{?[A-Z0-9_]+\}?"), KiwoomManualResponseImportReadiness.BLOCKED_CREDENTIAL_PATH, "environment variable references are blocked"),
    (re.compile(r"(^|/)\.env($|[^a-z])", re.IGNORECASE), KiwoomManualResponseImportReadiness.BLOCKED_CREDENTIAL_PATH, "credential-like paths are blocked"),
    (re.compile(r"credential|secret|token|account|acct|appkey|key", re.IGNORECASE), KiwoomManualResponseImportReadiness.BLOCKED_CREDENTIAL_PATH, "credential-like paths are blocked"),
    (re.compile(r"\.parquet$", re.IGNORECASE), KiwoomManualResponseImportReadiness.BLOCKED_UNSUPPORTED_FORMAT, "parquet remains unsupported"),
    (re.compile(r"[`|]|\$\("), KiwoomManualResponseImportReadiness.BLOCKED_UNSUPPORTED_FORMAT, "shell-like paths are blocked"),
)


IMPLEMENTED_API_IDS = {
    "KA10080",
    "KA10081",
    "KA00198",
    "KA10023",
    "KA10030",
    "KA10032",
    "KA10004",
    "KA10003",
    "KA10001",
    "KA10059",
    "KA90001",
    "KA90002",
    "KA40003",
}
SCHEMA_GAP_API_IDS = {"KA90003"}
ACCOUNT_BLOCKED_API_IDS = {"KA00001"}
ORDER_BLOCKED_API_IDS = {"00", "04", "KT00001", "KT10000", "KT10001", "KT10002", "KT10003"}
KNOWN_READONLY_API_IDS = (
    {item.value for item in KiwoomRestChartApiId}
    | {item.value for item in KiwoomRestRankApiId}
    | {item.value for item in KiwoomRestQuoteApiId}
    | {item.value for item in KiwoomRestFlowApiId}
    | {item.value for item in KiwoomRestSectorApiId}
)
CAPABILITY_ONLY_API_IDS = KNOWN_READONLY_API_IDS - IMPLEMENTED_API_IDS - SCHEMA_GAP_API_IDS


def _gap(request_id: str, suffix: str, category: str, severity: str, message: str) -> KiwoomManualResponseGapEntry:
    return KiwoomManualResponseGapEntry(
        gap_id=f"{request_id}-{suffix}",
        gap_category=category,
        severity=severity,
        message=message,
    )


def _now() -> datetime:
    return datetime.now().astimezone()


def _api_id(value: str) -> str:
    return str(value).strip().upper()


def _classify_api(api_id: str) -> KiwoomManualResponseApiClassification:
    api_id = _api_id(api_id)
    if api_id in ACCOUNT_BLOCKED_API_IDS:
        return KiwoomManualResponseApiClassification.ACCOUNT_BLOCKED
    if api_id in ORDER_BLOCKED_API_IDS or api_id.startswith("KT"):
        return KiwoomManualResponseApiClassification.ORDER_BLOCKED
    if api_id in IMPLEMENTED_API_IDS:
        return KiwoomManualResponseApiClassification.READONLY_IMPLEMENTED
    if api_id in SCHEMA_GAP_API_IDS:
        return KiwoomManualResponseApiClassification.READONLY_SCHEMA_GAP
    if api_id in CAPABILITY_ONLY_API_IDS:
        return KiwoomManualResponseApiClassification.READONLY_CAPABILITY_ONLY
    return KiwoomManualResponseApiClassification.UNKNOWN_BLOCKED


def _instrument_key(file: KiwoomManualResponseImportFile, payload: dict[str, object]) -> str:
    if file.canonical_instrument_key:
        return file.canonical_instrument_key
    symbol = file.provider_symbol or str(payload.get("stk_cd") or payload.get("symbol") or "").strip().upper()
    return f"{symbol}_KRX" if symbol else "UNKNOWN_KRX"


def _provider_symbol(file: KiwoomManualResponseImportFile, payload: dict[str, object]) -> str:
    return file.provider_symbol or str(payload.get("stk_cd") or payload.get("symbol") or "").strip().upper()


def _base_date(file: KiwoomManualResponseImportFile, payload: dict[str, object]) -> str:
    for candidate in (
        payload.get("base_dt"),
        payload.get("dt"),
        payload.get("cntr_dt"),
        file.observed_at.strftime("%Y%m%d") if file.observed_at else None,
        file.available_at.strftime("%Y%m%d") if file.available_at else None,
    ):
        if candidate:
            text = str(candidate).strip()
            if len(text) >= 8 and text[:8].isdigit():
                return text[:8]
    return "20260625"


def _safe_local_ref(file: KiwoomManualResponseImportFile) -> str:
    return Path(file.source_ref or file.file_path).name


def _wrap_list_payload(api_id: str, items: list[object]) -> dict[str, object]:
    key_map = {
        "KA10080": "stk_min_pole_chart_qry",
        "KA10081": "stk_day_pole_chart_qry",
        "KA00198": "item_inq_rank",
        "KA10023": "vol_surge_rank",
        "KA10030": "today_volume_rank",
        "KA10032": "trading_value_rank",
        "KA10059": "stk_invsr_orgn",
        "KA90001": "thema_grp",
        "KA90002": "thema_cmpst_stk",
        "KA40003": "etfdaly_trnsn",
    }
    if api_id not in key_map:
        raise ValueError("json list payload is unsupported for this api id")
    return {"return_code": 0, "return_msg": "MANUAL_RESPONSE_IMPORTED", key_map[api_id]: items}


def _load_json_file(file: KiwoomManualResponseImportFile):
    source = file.file_path
    lowered = source.lower()
    for pattern, readiness, message in _BLOCKED_PATH_PATTERNS:
        if pattern.search(source):
            raise ValueError(f"{readiness.value}:{message}")
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(source)
    if path.suffix.lower() != ".json":
        raise ValueError(f"{KiwoomManualResponseImportReadiness.BLOCKED_UNSUPPORTED_FORMAT.value}:only .json files are supported")
    raw = path.read_bytes()
    if b"\x00" in raw:
        raise ValueError(f"{KiwoomManualResponseImportReadiness.BLOCKED_UNSUPPORTED_FORMAT.value}:binary file is blocked")
    if len(raw) > SAFE_FILE_SIZE_LIMIT:
        raise ValueError(f"{KiwoomManualResponseImportReadiness.BLOCKED_UNSUPPORTED_FORMAT.value}:file exceeds safe local size limit")
    try:
        loaded = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"{KiwoomManualResponseImportReadiness.SCHEMA_GAP.value}:{exc}") from exc
    if isinstance(loaded, list):
        return _wrap_list_payload(file.declared_api_id, loaded)
    if not isinstance(loaded, dict):
        raise ValueError(f"{KiwoomManualResponseImportReadiness.SCHEMA_GAP.value}:json root must be an object")
    return loaded


def _iter_nodes(value):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key, nested
            yield from _iter_nodes(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_nodes(item)


def _scan_sensitive(file_path: str, payload: dict[str, object]) -> KiwoomManualResponseSensitiveScan:
    field_names: set[str] = set()
    for key, value in _iter_nodes(payload):
        key_text = str(key)
        for pattern, label in _SENSITIVE_KEY_PATTERNS:
            if pattern.search(key_text):
                field_names.add(label)
        if isinstance(value, str):
            for pattern, label in _SENSITIVE_VALUE_PATTERNS:
                if pattern.search(value):
                    field_names.add(label)
    blocked = bool(field_names)
    return KiwoomManualResponseSensitiveScan(
        file_path=file_path,
        blocked=blocked,
        sensitive_field_names=sorted(field_names),
        redaction_applied=True,
    )


def _make_adapter_safety_report(config_id: str) -> dict[str, object]:
    return {
        "safety_report_id": f"{config_id}-SAFETY-REPORT",
        "blocked_capabilities": [
            "ACCOUNT_API_BLOCKED",
            "ORDER_API_BLOCKED",
            "WEBSOCKET_BLOCKED",
            "NETWORK_BLOCKED",
            "TOKEN_LOADING_BLOCKED",
            "AUTH_HEADER_GENERATION_BLOCKED",
        ],
        "findings": [],
    }


def _make_adapter_audit(file: KiwoomManualResponseImportFile, config_id: str, sensitive_fields: list[str]) -> list[dict[str, object]]:
    return [
        {
            "audit_record_id": f"{config_id}-AUDIT",
            "created_at": _now().isoformat(),
            "source_path": _safe_local_ref(file),
            "operator_context": "offline kiwoom manual response import",
            "redaction_applied": True,
            "contains_secret_material": False,
            "contains_token_material": False,
            "contains_account_material": False,
        }
    ]


def _route_chart(file: KiwoomManualResponseImportFile, payload: dict[str, object]):
    api_id = KiwoomRestChartApiId(_api_id(file.declared_api_id))
    symbol = _provider_symbol(file, payload)
    config_id = f"MANUAL-IMPORT-{api_id.value}"
    result = build_kiwoom_rest_readonly_chart_adapter(
        KiwoomRestChartConfig.model_validate(
            {
                "config_id": config_id,
                "api_id": api_id.value,
                "provider_symbol": symbol,
                "canonical_instrument_key": _instrument_key(file, payload),
                "base_dt": _base_date(file, payload),
                "upd_stkpc_tp": "1",
                "tic_scope": "1" if api_id == KiwoomRestChartApiId.KA10080 else None,
                "available_at": file.available_at.isoformat() if file.available_at else None,
                "source_ref": _safe_local_ref(file),
                "mocked_response_payload": payload,
                "safety_report": _make_adapter_safety_report(config_id),
                "audit_records": _make_adapter_audit(file, config_id, []),
            }
        )
    )
    return result, ["CANONICAL_OHLCV"], len(result.canonical_ohlcv_report.records)


def _route_rank(file: KiwoomManualResponseImportFile, payload: dict[str, object]):
    api_id = KiwoomRestRankApiId(_api_id(file.declared_api_id))
    config_id = f"MANUAL-IMPORT-{api_id.value}"
    base = {
        "config_id": config_id,
        "api_id": api_id.value,
        "available_at": file.available_at.isoformat() if file.available_at else None,
        "source_ref": _safe_local_ref(file),
        "mocked_response_payload": payload,
        "safety_report": _make_adapter_safety_report(config_id),
        "audit_records": _make_adapter_audit(file, config_id, []),
    }
    if api_id == KiwoomRestRankApiId.KA00198:
        base["qry_tp"] = "0"
    if api_id == KiwoomRestRankApiId.KA10023:
        base.update({"mrkt_tp": "000", "sort_tp": "1", "tm_tp": "1", "trde_qty_tp": "10", "tm": "5", "stk_cnd": "3", "pric_tp": "0", "stex_tp": "3"})
    if api_id == KiwoomRestRankApiId.KA10030:
        base.update({"mrkt_tp": "000", "sort_tp": "1", "mang_stk_incls": "0", "crd_tp": "0", "trde_qty_tp": "10", "pric_tp": "0", "stex_tp": "3"})
    if api_id == KiwoomRestRankApiId.KA10032:
        base.update({"mrkt_tp": "000", "mang_stk_incls": "0", "stex_tp": "3"})
    result = build_kiwoom_rest_readonly_rank_adapter(KiwoomRestRankConfig.model_validate(base))
    count = len(result.canonical_rank_report.signals) + len(result.canonical_outlier_report.signals)
    return result, ["CANONICAL_RANK", "CANONICAL_OUTLIER"], count


def _route_quote(file: KiwoomManualResponseImportFile, payload: dict[str, object]):
    api_id = KiwoomRestQuoteApiId(_api_id(file.declared_api_id))
    config_id = f"MANUAL-IMPORT-{api_id.value}"
    result = build_kiwoom_rest_readonly_quote_adapter(
        KiwoomRestQuoteConfig.model_validate(
            {
                "config_id": config_id,
                "api_id": api_id.value,
                "provider_symbol": _provider_symbol(file, payload),
                "available_at": file.available_at.isoformat() if file.available_at else None,
                "request_date": _base_date(file, payload) if api_id == KiwoomRestQuoteApiId.KA10003 else None,
                "source_ref": _safe_local_ref(file),
                "mocked_response_payload": payload,
                "safety_report": _make_adapter_safety_report(config_id),
                "audit_records": _make_adapter_audit(file, config_id, []),
            }
        )
    )
    kinds = []
    count = 0
    if result.canonical_quote_report.records:
        kinds.append("CANONICAL_QUOTE")
        count += len(result.canonical_quote_report.records)
    if result.canonical_orderbook_report.records:
        kinds.append("CANONICAL_ORDERBOOK")
        count += len(result.canonical_orderbook_report.records)
    if result.liquidity_hint_report.records:
        kinds.append("CANONICAL_LIQUIDITY")
        count += len(result.liquidity_hint_report.records)
    if result.basic_info_report.records:
        kinds.append("CANONICAL_BASIC_INFO")
        count += len(result.basic_info_report.records)
    return result, kinds, count


def _route_flow(file: KiwoomManualResponseImportFile, payload: dict[str, object]):
    api_id = _api_id(file.declared_api_id)
    if api_id == "KA90003":
        return None, [], 0
    config_id = f"MANUAL-IMPORT-{api_id}"
    result = build_kiwoom_rest_readonly_flow_adapter(
        KiwoomRestFlowConfig.model_validate(
            {
                "config_id": config_id,
                "api_id": api_id,
                "provider_symbol": _provider_symbol(file, payload),
                "request_date": _base_date(file, payload),
                "amt_qty_tp": "1",
                "trde_tp": "0",
                "unit_tp": "1",
                "available_at": file.available_at.isoformat() if file.available_at else None,
                "source_ref": _safe_local_ref(file),
                "mocked_response_payload": payload,
                "safety_report": _make_adapter_safety_report(config_id),
                "audit_records": _make_adapter_audit(file, config_id, []),
            }
        )
    )
    kinds = []
    count = 0
    if result.canonical_investor_flow_report.signals:
        kinds.append("CANONICAL_INVESTOR_FLOW")
        count += len(result.canonical_investor_flow_report.signals)
    if result.canonical_program_flow_report.signals:
        kinds.append("CANONICAL_PROGRAM_FLOW")
        count += len(result.canonical_program_flow_report.signals)
    return result, kinds, count


def _route_sector(file: KiwoomManualResponseImportFile, payload: dict[str, object]):
    api_id = KiwoomRestSectorApiId(_api_id(file.declared_api_id))
    config_id = f"MANUAL-IMPORT-{api_id.value}"
    base = {
        "config_id": config_id,
        "api_id": api_id.value,
        "available_at": file.available_at.isoformat() if file.available_at else None,
        "source_ref": _safe_local_ref(file),
        "mocked_response_payload": payload,
        "safety_report": _make_adapter_safety_report(config_id),
        "audit_records": _make_adapter_audit(file, config_id, []),
    }
    if api_id == KiwoomRestSectorApiId.KA90001:
        base.update({"qry_tp": "0", "provider_symbol": _provider_symbol(file, payload) or "", "date_tp": "10", "theme_name": "", "flu_pl_amt_tp": "1", "stex_tp": "1"})
    if api_id == KiwoomRestSectorApiId.KA90002:
        rows = payload.get("thema_cmpst_stk") if isinstance(payload.get("thema_cmpst_stk"), list) else []
        theme_group_code = payload.get("thema_grp_cd") or (rows[0].get("thema_grp_cd") if rows and isinstance(rows[0], dict) else None) or "553"
        base.update({"date_tp": "10", "theme_group_code": str(theme_group_code), "stex_tp": "1"})
    if api_id == KiwoomRestSectorApiId.KA40003:
        base.update({"provider_symbol": _provider_symbol(file, payload)})
    result = build_kiwoom_rest_readonly_sector_adapter(KiwoomRestSectorConfig.model_validate(base))
    kinds = []
    count = 0
    if result.canonical_theme_leadership_report.signals:
        kinds.append("CANONICAL_THEME_LEADERSHIP")
        count += len(result.canonical_theme_leadership_report.signals)
    if result.canonical_theme_membership_report.signals:
        kinds.append("CANONICAL_THEME_MEMBERSHIP")
        count += len(result.canonical_theme_membership_report.signals)
    if result.canonical_etf_trend_report.signals:
        kinds.append("CANONICAL_ETF_TREND")
        count += len(result.canonical_etf_trend_report.signals)
    return result, kinds, count


def _route_file(file: KiwoomManualResponseImportFile, payload: dict[str, object]):
    api_id = _api_id(file.declared_api_id)
    if api_id in {"KA10080", "KA10081"}:
        return _route_chart(file, payload), "V8_1_CHART"
    if api_id in {"KA00198", "KA10023", "KA10030", "KA10032"}:
        return _route_rank(file, payload), "V8_2_RANK"
    if api_id in {"KA10004", "KA10003", "KA10001"}:
        return _route_quote(file, payload), "V8_3_QUOTE"
    if api_id in {"KA10059", "KA90003"}:
        return _route_flow(file, payload), "V8_4_FLOW"
    if api_id in {"KA90001", "KA90002", "KA40003"}:
        return _route_sector(file, payload), "V8_5_SECTOR"
    return (None, [], 0), "UNSUPPORTED"


def _readiness_from_classification(classification: KiwoomManualResponseApiClassification) -> KiwoomManualResponseImportReadiness:
    return {
        KiwoomManualResponseApiClassification.ACCOUNT_BLOCKED: KiwoomManualResponseImportReadiness.BLOCKED_ACCOUNT_API,
        KiwoomManualResponseApiClassification.ORDER_BLOCKED: KiwoomManualResponseImportReadiness.BLOCKED_ORDER_API,
        KiwoomManualResponseApiClassification.UNKNOWN_BLOCKED: KiwoomManualResponseImportReadiness.REJECTED,
        KiwoomManualResponseApiClassification.READONLY_SCHEMA_GAP: KiwoomManualResponseImportReadiness.READONLY_SCHEMA_GAP,
        KiwoomManualResponseApiClassification.READONLY_CAPABILITY_ONLY: KiwoomManualResponseImportReadiness.CAPABILITY_ONLY,
        KiwoomManualResponseApiClassification.READONLY_IMPLEMENTED: KiwoomManualResponseImportReadiness.IMPORT_READY,
    }[classification]


def build_kiwoom_manual_response_import_harness(request: KiwoomManualResponseImportRequest) -> KiwoomManualResponseImportResult:
    gaps: list[KiwoomManualResponseGapEntry] = []
    classifications: list[KiwoomManualResponseFileClassification] = []
    scans: list[KiwoomManualResponseSensitiveScan] = []
    routes: list[KiwoomManualResponseRoutingResult] = []
    parser_results: list[KiwoomManualResponseParserResult] = []
    audits: list[KiwoomManualResponseAuditRecord] = []
    findings: list[str] = []

    canonical_report = KiwoomManualResponseCanonicalOutputReport(report_id=f"{request.request_id}-CANONICAL-OUTPUT-REPORT")

    for index, file in enumerate(request.files, start=1):
        classification = _classify_api(file.declared_api_id)
        classifications.append(
            KiwoomManualResponseFileClassification(
                file_path=file.file_path,
                api_id=file.declared_api_id,
                classification=classification,
                blocked=classification
                in {
                    KiwoomManualResponseApiClassification.ACCOUNT_BLOCKED,
                    KiwoomManualResponseApiClassification.ORDER_BLOCKED,
                    KiwoomManualResponseApiClassification.UNKNOWN_BLOCKED,
                },
                parser_supported=classification == KiwoomManualResponseApiClassification.READONLY_IMPLEMENTED,
            )
        )
        audits.append(
            KiwoomManualResponseAuditRecord(
                audit_record_id=f"{request.request_id}-AUDIT-{index}",
                created_at=_now(),
                source_path=file.file_path,
                operator_context="offline kiwoom manual response import",
                redaction_applied=True,
                contains_secret_material=False,
                contains_token_material=False,
                contains_account_material=False,
                sensitive_field_names=[],
            )
        )
        if classification != KiwoomManualResponseApiClassification.READONLY_IMPLEMENTED:
            readiness = _readiness_from_classification(classification)
            routes.append(
                KiwoomManualResponseRoutingResult(
                    file_path=file.file_path,
                    api_id=file.declared_api_id,
                    route_target="CLASSIFICATION_ONLY",
                    readiness=readiness,
                )
            )
            parser_results.append(
                KiwoomManualResponseParserResult(
                    file_path=file.file_path,
                    api_id=file.declared_api_id,
                    readiness=readiness,
                    canonical_record_count=0,
                    canonical_output_kinds=[],
                )
            )
            if readiness in {KiwoomManualResponseImportReadiness.READONLY_SCHEMA_GAP, KiwoomManualResponseImportReadiness.CAPABILITY_ONLY}:
                gaps.append(_gap(request.request_id, f"CLASSIFICATION-{index}", readiness.value, "WARNING", f"{file.declared_api_id} remains classification-only"))
                continue
            gaps.append(_gap(request.request_id, f"BLOCKED-{index}", readiness.value, "BLOCKING", f"{file.declared_api_id} is blocked"))
            continue

        try:
            payload = _load_json_file(file)
        except FileNotFoundError:
            scans.append(KiwoomManualResponseSensitiveScan(file_path=file.file_path, blocked=False, sensitive_field_names=[], redaction_applied=True))
            routes.append(
                KiwoomManualResponseRoutingResult(
                    file_path=file.file_path,
                    api_id=file.declared_api_id,
                    route_target="FILE_LOAD",
                    readiness=KiwoomManualResponseImportReadiness.DATA_GAP,
                )
            )
            parser_results.append(
                KiwoomManualResponseParserResult(
                    file_path=file.file_path,
                    api_id=file.declared_api_id,
                    readiness=KiwoomManualResponseImportReadiness.DATA_GAP,
                    canonical_record_count=0,
                    canonical_output_kinds=[],
                )
            )
            gaps.append(_gap(request.request_id, f"MISSING-FILE-{index}", "DATA_GAP", "WARNING", "manual response file is missing"))
            continue
        except ValueError as exc:
            text = str(exc)
            readiness_name, _, message = text.partition(":")
            readiness = KiwoomManualResponseImportReadiness(readiness_name) if readiness_name in {item.value for item in KiwoomManualResponseImportReadiness} else KiwoomManualResponseImportReadiness.SCHEMA_GAP
            scans.append(KiwoomManualResponseSensitiveScan(file_path=file.file_path, blocked=False, sensitive_field_names=[], redaction_applied=True))
            routes.append(
                KiwoomManualResponseRoutingResult(
                    file_path=file.file_path,
                    api_id=file.declared_api_id,
                    route_target="FILE_LOAD",
                    readiness=readiness,
                )
            )
            parser_results.append(
                KiwoomManualResponseParserResult(
                    file_path=file.file_path,
                    api_id=file.declared_api_id,
                    readiness=readiness,
                    canonical_record_count=0,
                    canonical_output_kinds=[],
                )
            )
            gaps.append(_gap(request.request_id, f"LOAD-{index}", readiness.value, "BLOCKING" if readiness.name.startswith("BLOCKED") else "WARNING", message or text))
            continue

        scan = _scan_sensitive(file.file_path, payload)
        scans.append(scan)
        audits[-1] = audits[-1].model_copy(update={"sensitive_field_names": scan.sensitive_field_names})
        if scan.blocked:
            routes.append(
                KiwoomManualResponseRoutingResult(
                    file_path=file.file_path,
                    api_id=file.declared_api_id,
                    route_target="SENSITIVE_SCAN",
                    readiness=KiwoomManualResponseImportReadiness.BLOCKED_SENSITIVE_CONTENT,
                )
            )
            parser_results.append(
                KiwoomManualResponseParserResult(
                    file_path=file.file_path,
                    api_id=file.declared_api_id,
                    readiness=KiwoomManualResponseImportReadiness.BLOCKED_SENSITIVE_CONTENT,
                    canonical_record_count=0,
                    canonical_output_kinds=[],
                )
            )
            gaps.append(_gap(request.request_id, f"SENSITIVE-{index}", "BLOCKED_SENSITIVE_CONTENT", "BLOCKING", "sensitive markers were found in imported content"))
            findings.extend(scan.sensitive_field_names)
            if request.strict_mode:
                continue

        try:
            routed, route_target = _route_file(file, payload)
            adapter_result, kinds, count = routed
        except Exception as exc:
            routes.append(
                KiwoomManualResponseRoutingResult(
                    file_path=file.file_path,
                    api_id=file.declared_api_id,
                    route_target="PARSER",
                    readiness=KiwoomManualResponseImportReadiness.SCHEMA_GAP,
                )
            )
            parser_results.append(
                KiwoomManualResponseParserResult(
                    file_path=file.file_path,
                    api_id=file.declared_api_id,
                    readiness=KiwoomManualResponseImportReadiness.SCHEMA_GAP,
                    canonical_record_count=0,
                    canonical_output_kinds=[],
                )
            )
            gaps.append(_gap(request.request_id, f"PARSER-{index}", "SCHEMA_GAP", "WARNING", str(exc)))
            continue

        if adapter_result is None:
            readiness = KiwoomManualResponseImportReadiness.READONLY_SCHEMA_GAP
            routes.append(
                KiwoomManualResponseRoutingResult(
                    file_path=file.file_path,
                    api_id=file.declared_api_id,
                    route_target=route_target,
                    readiness=readiness,
                )
            )
            parser_results.append(
                KiwoomManualResponseParserResult(
                    file_path=file.file_path,
                    api_id=file.declared_api_id,
                    readiness=readiness,
                    canonical_record_count=0,
                    canonical_output_kinds=[],
                )
            )
            gaps.append(_gap(request.request_id, f"SCHEMA-GAP-{index}", "READONLY_SCHEMA_GAP", "WARNING", f"{file.declared_api_id} remains schema-gap"))
            continue

        routes.append(
            KiwoomManualResponseRoutingResult(
                file_path=file.file_path,
                api_id=file.declared_api_id,
                route_target=route_target,
                readiness=KiwoomManualResponseImportReadiness.PARSED_CANONICAL_READY if count else KiwoomManualResponseImportReadiness.DATA_GAP,
            )
        )
        parser_results.append(
            KiwoomManualResponseParserResult(
                file_path=file.file_path,
                api_id=file.declared_api_id,
                readiness=KiwoomManualResponseImportReadiness.PARSED_CANONICAL_READY if count else KiwoomManualResponseImportReadiness.DATA_GAP,
                canonical_record_count=count,
                canonical_output_kinds=kinds,
            )
        )
        if hasattr(adapter_result, "canonical_ohlcv_report"):
            canonical_report.canonical_ohlcv_records.extend(adapter_result.canonical_ohlcv_report.records)
        if hasattr(adapter_result, "canonical_rank_report"):
            canonical_report.canonical_rank_signals.extend(adapter_result.canonical_rank_report.signals)
            canonical_report.canonical_outlier_signals.extend(adapter_result.canonical_outlier_report.signals)
        if hasattr(adapter_result, "canonical_quote_report"):
            canonical_report.canonical_quote_records.extend(adapter_result.canonical_quote_report.records)
            canonical_report.canonical_orderbook_records.extend(adapter_result.canonical_orderbook_report.records)
            canonical_report.canonical_liquidity_hints.extend(adapter_result.liquidity_hint_report.records)
            canonical_report.canonical_basic_info_records.extend(adapter_result.basic_info_report.records)
        if hasattr(adapter_result, "canonical_investor_flow_report"):
            canonical_report.canonical_investor_flow_signals.extend(adapter_result.canonical_investor_flow_report.signals)
            canonical_report.canonical_program_flow_signals.extend(adapter_result.canonical_program_flow_report.signals)
        if hasattr(adapter_result, "canonical_theme_leadership_report"):
            canonical_report.canonical_theme_leadership_signals.extend(adapter_result.canonical_theme_leadership_report.signals)
            canonical_report.canonical_theme_membership_signals.extend(adapter_result.canonical_theme_membership_report.signals)
            canonical_report.canonical_etf_trend_signals.extend(adapter_result.canonical_etf_trend_report.signals)

    canonical_count = (
        len(canonical_report.canonical_ohlcv_records)
        + len(canonical_report.canonical_rank_signals)
        + len(canonical_report.canonical_outlier_signals)
        + len(canonical_report.canonical_quote_records)
        + len(canonical_report.canonical_orderbook_records)
        + len(canonical_report.canonical_liquidity_hints)
        + len(canonical_report.canonical_basic_info_records)
        + len(canonical_report.canonical_investor_flow_signals)
        + len(canonical_report.canonical_program_flow_signals)
        + len(canonical_report.canonical_theme_leadership_signals)
        + len(canonical_report.canonical_theme_membership_signals)
        + len(canonical_report.canonical_etf_trend_signals)
    )

    snapshot_result = KiwoomManualResponseSnapshotCompositionResult(
        report_id=f"{request.request_id}-SNAPSHOT-COMPOSITION-RESULT",
        compose_requested=request.compose_snapshot,
        composed=False,
        readiness=KiwoomManualResponseImportReadiness.DATA_GAP if request.compose_snapshot else KiwoomManualResponseImportReadiness.IMPORT_READY,
        snapshot_report=None,
    )
    if request.compose_snapshot:
        try:
            snapshot = build_kiwoom_readonly_domestic_stock_snapshot(
                KiwoomReadonlySnapshotConfig.model_validate(
                    {
                        "config_id": f"{request.request_id}-SNAPSHOT",
                        "available_at": request.files[0].available_at.isoformat() if request.files and request.files[0].available_at else None,
                        "source_ref": _safe_local_ref(request.files[0]),
                        "operator_context": "offline kiwoom manual response import",
                        "canonical_ohlcv_records": canonical_report.canonical_ohlcv_records,
                        "canonical_rank_signals": canonical_report.canonical_rank_signals,
                        "canonical_outlier_signals": canonical_report.canonical_outlier_signals,
                        "canonical_quote_records": canonical_report.canonical_quote_records,
                        "canonical_orderbook_records": canonical_report.canonical_orderbook_records,
                        "canonical_liquidity_hints": canonical_report.canonical_liquidity_hints,
                        "canonical_basic_info_records": canonical_report.canonical_basic_info_records,
                        "canonical_investor_flow_signals": canonical_report.canonical_investor_flow_signals,
                        "canonical_program_flow_signals": canonical_report.canonical_program_flow_signals,
                        "canonical_theme_leadership_signals": canonical_report.canonical_theme_leadership_signals,
                        "canonical_theme_membership_signals": canonical_report.canonical_theme_membership_signals,
                        "canonical_etf_trend_signals": canonical_report.canonical_etf_trend_signals,
                        "canonical_sector_capability_signals": [],
                        "safety_report": {"safety_report_id": f"{request.request_id}-SNAPSHOT-SAFETY"},
                        "audit_records": [
                            KiwoomReadonlySnapshotAuditRecord.model_validate(
                                {
                                    "audit_record_id": f"{request.request_id}-SNAPSHOT-AUDIT",
                                    "created_at": _now().isoformat(),
                                    "source_path": _safe_local_ref(request.files[0]),
                                    "operator_context": "offline kiwoom manual response import",
                                }
                            ).model_dump(mode="json")
                        ],
                    }
                )
            )
        except Exception as exc:
            gaps.append(_gap(request.request_id, "SNAPSHOT", "DATA_GAP", "WARNING", str(exc)))
        else:
            snapshot_report = KiwoomReadonlyDomesticStockSnapshotReport.model_validate(
                snapshot.domestic_stock_snapshot_report.model_dump(mode="json")
            )
            readiness = (
                KiwoomManualResponseImportReadiness.SNAPSHOT_COMPOSED
                if snapshot_report.snapshots
                else KiwoomManualResponseImportReadiness.DATA_GAP
            )
            snapshot_result = KiwoomManualResponseSnapshotCompositionResult(
                report_id=f"{request.request_id}-SNAPSHOT-COMPOSITION-RESULT",
                compose_requested=True,
                composed=bool(snapshot_report.snapshots),
                readiness=readiness,
                snapshot_report=snapshot_report,
            )

    if any(item.readiness == KiwoomManualResponseImportReadiness.BLOCKED_SENSITIVE_CONTENT for item in parser_results):
        readiness = KiwoomManualResponseImportReadiness.BLOCKED_SENSITIVE_CONTENT
    elif any(item.readiness == KiwoomManualResponseImportReadiness.BLOCKED_ACCOUNT_API for item in parser_results):
        readiness = KiwoomManualResponseImportReadiness.BLOCKED_ACCOUNT_API
    elif any(item.readiness == KiwoomManualResponseImportReadiness.BLOCKED_ORDER_API for item in parser_results):
        readiness = KiwoomManualResponseImportReadiness.BLOCKED_ORDER_API
    elif any(item.readiness == KiwoomManualResponseImportReadiness.BLOCKED_NETWORK_PATH for item in parser_results):
        readiness = KiwoomManualResponseImportReadiness.BLOCKED_NETWORK_PATH
    elif any(item.readiness == KiwoomManualResponseImportReadiness.BLOCKED_CREDENTIAL_PATH for item in parser_results):
        readiness = KiwoomManualResponseImportReadiness.BLOCKED_CREDENTIAL_PATH
    elif any(item.readiness == KiwoomManualResponseImportReadiness.BLOCKED_UNSUPPORTED_FORMAT for item in parser_results):
        readiness = KiwoomManualResponseImportReadiness.BLOCKED_UNSUPPORTED_FORMAT
    elif snapshot_result.composed:
        readiness = KiwoomManualResponseImportReadiness.SNAPSHOT_COMPOSED
    elif canonical_count:
        readiness = KiwoomManualResponseImportReadiness.PARSED_CANONICAL_READY
    elif any(item.readiness == KiwoomManualResponseImportReadiness.READONLY_SCHEMA_GAP for item in parser_results):
        readiness = KiwoomManualResponseImportReadiness.READONLY_SCHEMA_GAP
    elif any(item.readiness == KiwoomManualResponseImportReadiness.CAPABILITY_ONLY for item in parser_results):
        readiness = KiwoomManualResponseImportReadiness.CAPABILITY_ONLY
    elif any(item.readiness == KiwoomManualResponseImportReadiness.DATA_GAP for item in parser_results):
        readiness = KiwoomManualResponseImportReadiness.DATA_GAP
    elif any(item.readiness == KiwoomManualResponseImportReadiness.SCHEMA_GAP for item in parser_results):
        readiness = KiwoomManualResponseImportReadiness.SCHEMA_GAP
    else:
        readiness = KiwoomManualResponseImportReadiness.REJECTED

    return KiwoomManualResponseImportResult(
        adapter_result_id=f"{request.request_id}-ADAPTER-RESULT",
        summary_report=KiwoomManualResponseImportSummaryReport(
            report_id=f"{request.request_id}-SUMMARY-REPORT",
            readiness=readiness,
            imported_file_count=len(request.files),
            canonical_output_count=canonical_count,
            message="manual response import completed with redacted read-only validation reports",
        ),
        file_classification_report=KiwoomManualResponseFileClassificationReport(
            report_id=f"{request.request_id}-FILE-CLASSIFICATION-REPORT",
            files=classifications,
        ),
        sensitive_scan_report=KiwoomManualResponseSensitiveScanReport(
            report_id=f"{request.request_id}-SENSITIVE-SCAN-REPORT",
            scans=scans,
        ),
        routing_report=KiwoomManualResponseRoutingReport(
            report_id=f"{request.request_id}-ROUTING-REPORT",
            routes=routes,
            parser_results=parser_results,
        ),
        canonical_output_report=canonical_report,
        snapshot_composition_result=snapshot_result,
        safety_report=KiwoomManualResponseSafetyReport(
            safety_report_id=f"{request.request_id}-SAFETY-REPORT",
            blocked=readiness.name.startswith("BLOCKED"),
            findings=sorted(set(findings)),
        ),
        gap_report=KiwoomManualResponseGapReport(
            gap_report_id=f"{request.request_id}-GAP-REPORT",
            readiness=readiness,
            gap_entries=gaps
            + [
                _gap(
                    request.request_id,
                    "REPORT-GENERATED",
                    "MANUAL_RESPONSE_IMPORT_REPORT_GENERATED",
                    "REPORT_ONLY",
                    "kiwoom manual response import report generated",
                )
            ],
        ),
        audit_records=audits,
    )
