import json

from stock_risk_mcp.kiwoom_manual_response_import_engine import build_kiwoom_manual_response_import_harness
from stock_risk_mcp.kiwoom_manual_response_import_models import (
    KiwoomManualResponseImportReadiness,
    KiwoomManualResponseImportRequest,
)
from tests.test_kiwoom_manual_response_import_models import kiwoom_manual_response_import_payload
from tests.test_kiwoom_rest_readonly_chart_models import kiwoom_rest_readonly_chart_payload
from tests.test_kiwoom_rest_readonly_flow_models import kiwoom_rest_readonly_flow_payload
from tests.test_kiwoom_rest_readonly_quote_models import kiwoom_rest_readonly_quote_payload
from tests.test_kiwoom_rest_readonly_rank_models import kiwoom_rest_readonly_rank_payload
from tests.test_kiwoom_rest_readonly_sector_models import kiwoom_rest_readonly_sector_payload


def write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def _request(tmp_path, api_id: str, response_payload, **file_overrides):
    response_file = tmp_path / f"{api_id.lower()}_response.json"
    write_json(response_file, response_payload)
    payload = kiwoom_manual_response_import_payload(
        str(response_file),
        files=[
            {
                "file_path": str(response_file),
                "declared_api_id": api_id,
                "provider_symbol": file_overrides.pop("provider_symbol", "005930"),
                "canonical_instrument_key": file_overrides.pop("canonical_instrument_key", "005930_KRX"),
                "available_at": file_overrides.pop("available_at", "2026-06-25T15:35:00+09:00"),
                "observed_at": file_overrides.pop("observed_at", None),
                "source_ref": str(response_file),
                **file_overrides,
            }
        ],
    )
    return KiwoomManualResponseImportRequest.model_validate(payload)


def test_url_and_credential_and_parquet_paths_are_blocked(tmp_path):
    request = KiwoomManualResponseImportRequest.model_validate(
        {
            "request_id": "MANUAL-IMPORT-BLOCKED",
            "files": [{"file_path": "https://example.com/ka10081.json", "declared_api_id": "KA10081"}],
        }
    )
    result = build_kiwoom_manual_response_import_harness(request)
    assert result.summary_report.readiness == KiwoomManualResponseImportReadiness.BLOCKED_NETWORK_PATH

    request = KiwoomManualResponseImportRequest.model_validate(
        {
            "request_id": "MANUAL-IMPORT-CRED",
            "files": [{"file_path": "/tmp/access_token.json", "declared_api_id": "KA10081"}],
        }
    )
    result = build_kiwoom_manual_response_import_harness(request)
    assert result.summary_report.readiness == KiwoomManualResponseImportReadiness.BLOCKED_CREDENTIAL_PATH

    request = KiwoomManualResponseImportRequest.model_validate(
        {
            "request_id": "MANUAL-IMPORT-PARQUET",
            "files": [{"file_path": "/tmp/ka10081.parquet", "declared_api_id": "KA10081"}],
        }
    )
    result = build_kiwoom_manual_response_import_harness(request)
    assert result.summary_report.readiness == KiwoomManualResponseImportReadiness.BLOCKED_UNSUPPORTED_FORMAT


def test_missing_file_and_malformed_json_are_gap_aware(tmp_path):
    request = KiwoomManualResponseImportRequest.model_validate(
        {
            "request_id": "MANUAL-IMPORT-MISSING",
            "files": [{"file_path": str(tmp_path / "missing.json"), "declared_api_id": "KA10081"}],
        }
    )
    result = build_kiwoom_manual_response_import_harness(request)
    assert result.summary_report.readiness == KiwoomManualResponseImportReadiness.DATA_GAP

    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    request = KiwoomManualResponseImportRequest.model_validate(
        {"request_id": "MANUAL-IMPORT-BROKEN", "files": [{"file_path": str(broken), "declared_api_id": "KA10081"}]}
    )
    result = build_kiwoom_manual_response_import_harness(request)
    assert result.summary_report.readiness == KiwoomManualResponseImportReadiness.SCHEMA_GAP


def test_sensitive_markers_block_import(tmp_path):
    payload = {"authorization": "Bearer real-token", "return_code": 0, "return_msg": "ok"}
    request = _request(tmp_path, "KA10081", payload)
    result = build_kiwoom_manual_response_import_harness(request)
    assert result.summary_report.readiness == KiwoomManualResponseImportReadiness.BLOCKED_SENSITIVE_CONTENT
    assert result.sensitive_scan_report.scans[0].blocked is True


def test_account_order_and_unknown_apis_are_blocked(tmp_path):
    response_file = tmp_path / "ka00001_response.json"
    response_file.write_text("{}", encoding="utf-8")
    request = KiwoomManualResponseImportRequest.model_validate(
        {"request_id": "ACCOUNT-BLOCKED", "files": [{"file_path": str(response_file), "declared_api_id": "KA00001"}]}
    )
    assert build_kiwoom_manual_response_import_harness(request).summary_report.readiness == KiwoomManualResponseImportReadiness.BLOCKED_ACCOUNT_API

    response_file = tmp_path / "kt10000_response.json"
    response_file.write_text("{}", encoding="utf-8")
    request = KiwoomManualResponseImportRequest.model_validate(
        {"request_id": "ORDER-BLOCKED", "files": [{"file_path": str(response_file), "declared_api_id": "KT10000"}]}
    )
    assert build_kiwoom_manual_response_import_harness(request).summary_report.readiness == KiwoomManualResponseImportReadiness.BLOCKED_ORDER_API

    response_file = tmp_path / "unknown_response.json"
    response_file.write_text("{}", encoding="utf-8")
    request = KiwoomManualResponseImportRequest.model_validate(
        {"request_id": "UNKNOWN-BLOCKED", "files": [{"file_path": str(response_file), "declared_api_id": "ZZ99999"}]}
    )
    assert build_kiwoom_manual_response_import_harness(request).summary_report.readiness == KiwoomManualResponseImportReadiness.REJECTED


def test_chart_rank_quote_flow_sector_routes_produce_canonical_outputs(tmp_path):
    daily = build_kiwoom_manual_response_import_harness(_request(tmp_path, "KA10081", kiwoom_rest_readonly_chart_payload()["mocked_response_payload"]))
    minute_payload = {"stk_cd": "005930", "return_code": 0, "return_msg": "정상", "stk_min_pole_chart_qry": [{"dt": "20260625", "open_pric": "+78000", "high_pric": "+79000", "low_pric": "+77500", "cur_prc": "+78800", "trde_qty": "1000"}]}
    minute = build_kiwoom_manual_response_import_harness(_request(tmp_path, "KA10080", minute_payload))
    realtime_rank = {"return_code": 0, "return_msg": "정상", "item_inq_rank": [{"stk_cd": "005930", "stk_nm": "삼성전자", "bigd_rank": "1", "pred_rank": "2", "cur_prc": "+78800", "pred_pre": "+1000", "base_comp_chgr": "+1.2", "trde_qty": "1000", "trde_prica": "1000000", "dt": "20260625", "tm": "153000"}]}
    rank = build_kiwoom_manual_response_import_harness(_request(tmp_path, "KA00198", realtime_rank))
    surge = build_kiwoom_manual_response_import_harness(_request(tmp_path, "KA10023", kiwoom_rest_readonly_rank_payload()["mocked_response_payload"]))
    quote = build_kiwoom_manual_response_import_harness(_request(tmp_path, "KA10004", kiwoom_rest_readonly_quote_payload()["mocked_response_payload"]))
    execution = build_kiwoom_manual_response_import_harness(_request(tmp_path, "KA10003", {"stk_cd": "005930", "stk_nm": "삼성전자", "return_code": 0, "return_msg": "정상", "cntr_infr": [{"tm": "153000", "cur_prc": "+78800", "pred_pre": "+3900", "pre_rt": "+5.21", "pri_sel_bid_unit": "+78810", "pri_buy_bid_unit": "+78800", "cntr_trde_qty": "250", "sign": "2"}]}))
    flow = build_kiwoom_manual_response_import_harness(_request(tmp_path, "KA10059", kiwoom_rest_readonly_flow_payload()["mocked_response_payload"]))
    theme = build_kiwoom_manual_response_import_harness(_request(tmp_path, "KA90001", kiwoom_rest_readonly_sector_payload()["mocked_response_payload"], provider_symbol=""))
    etf = build_kiwoom_manual_response_import_harness(_request(tmp_path, "KA40003", {"return_code": 0, "return_msg": "정상", "etfdaly_trnsn": [{"cntr_dt": "20260625", "cur_prc": "+157.80", "pred_pre": "+1.25", "pre_rt": "+0.80"}]}, provider_symbol="069500", canonical_instrument_key="069500_KRX"))

    assert daily.canonical_output_report.canonical_ohlcv_records
    assert minute.canonical_output_report.canonical_ohlcv_records
    assert rank.canonical_output_report.canonical_rank_signals
    assert surge.canonical_output_report.canonical_outlier_signals
    assert quote.canonical_output_report.canonical_quote_records
    assert execution.canonical_output_report.canonical_liquidity_hints
    assert flow.canonical_output_report.canonical_investor_flow_signals
    assert theme.canonical_output_report.canonical_theme_leadership_signals
    assert etf.canonical_output_report.canonical_etf_trend_signals


def test_schema_gap_api_does_not_crash(tmp_path):
    response_file = tmp_path / "ka90003_response.json"
    response_file.write_text(json.dumps({"return_code": 0, "return_msg": "정상"}), encoding="utf-8")
    request = KiwoomManualResponseImportRequest.model_validate(
        {"request_id": "SCHEMA-GAP", "files": [{"file_path": str(response_file), "declared_api_id": "KA90003"}]}
    )
    result = build_kiwoom_manual_response_import_harness(request)
    assert result.summary_report.readiness == KiwoomManualResponseImportReadiness.READONLY_SCHEMA_GAP


def test_compose_snapshot_produces_snapshot_and_partial_gap_aware_report(tmp_path):
    chart_file = tmp_path / "ka10081_response.json"
    chart_payload = kiwoom_rest_readonly_chart_payload()["mocked_response_payload"]
    chart_payload["stk_day_pole_chart_qry"][0]["cur_prc"] = "-78800"
    chart_file.write_text(json.dumps(chart_payload), encoding="utf-8")
    quote_file = tmp_path / "ka10004_response.json"
    quote_payload = kiwoom_rest_readonly_quote_payload()["mocked_response_payload"]
    quote_payload["ask_price_1"] = "+78810"
    quote_payload["bid_price_1"] = "+78790"
    quote_file.write_text(json.dumps(quote_payload), encoding="utf-8")

    request = KiwoomManualResponseImportRequest.model_validate(
        {
            "request_id": "SNAPSHOT-COMPOSE",
            "files": [
                {"file_path": str(chart_file), "declared_api_id": "KA10081", "provider_symbol": "005930", "canonical_instrument_key": "005930_KRX", "available_at": "2026-06-25T15:35:00+09:00"},
                {"file_path": str(quote_file), "declared_api_id": "KA10004", "provider_symbol": "005930", "canonical_instrument_key": "005930_KRX", "available_at": "2026-06-25T15:35:00+09:00"},
            ],
            "compose_snapshot": True,
        }
    )
    result = build_kiwoom_manual_response_import_harness(request)
    assert result.snapshot_composition_result.compose_requested is True
    assert result.snapshot_composition_result.snapshot_report is not None
    assert result.snapshot_composition_result.snapshot_report.snapshots

    partial_request = KiwoomManualResponseImportRequest.model_validate(
        {
            "request_id": "SNAPSHOT-PARTIAL",
            "files": [{"file_path": str(chart_file), "declared_api_id": "KA10081", "provider_symbol": "005930", "canonical_instrument_key": "005930_KRX", "available_at": "2026-06-25T15:35:00+09:00"}],
            "compose_snapshot": True,
        }
    )
    partial = build_kiwoom_manual_response_import_harness(partial_request)
    assert partial.snapshot_composition_result.snapshot_report is not None
    assert partial.snapshot_composition_result.snapshot_report.snapshots[0].gap_reason == "SNAPSHOT_SOURCE_COVERAGE_PARTIAL"


def test_output_remains_readonly_and_redacted(tmp_path):
    result = build_kiwoom_manual_response_import_harness(_request(tmp_path, "KA10081", kiwoom_rest_readonly_chart_payload()["mocked_response_payload"]))
    dumped = result.model_dump_json()
    assert "order_id" not in dumped.lower()
    assert result.audit_records[0].redaction_applied is True
    assert result.canonical_output_report.canonical_ohlcv_records[0].report_only is True
