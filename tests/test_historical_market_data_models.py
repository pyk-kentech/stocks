import json

from stock_risk_mcp.historical_market_data_models import (
    HistoricalMarketDataPipelineInput,
    HistoricalOhlcvRow,
    to_feature_store_price_bar,
)


def historical_market_data_payload(store_root: str, raw_lake_root: str, manual_payload_path: str) -> dict[str, object]:
    return {
        "pipeline_id": "historical-market-data-test",
        "dataset_id": "historical-market-data-test",
        "mode": "MANUAL_IMPORT_ONLY",
        "capture_profile": "SMOKE_PROFILE",
        "store_root": store_root,
        "raw_lake_root": raw_lake_root,
        "requested_storage_formats": ["IN_MEMORY", "JSON", "PARQUET"],
        "partition_spec": {"partition_keys": ["DATASET_ID", "INTERVAL", "DATE"]},
        "request_specs": [
            {
                "request_id": "ka10081-005930-test",
                "api_id": "KA10081",
                "provider_symbol": "005930",
                "canonical_instrument_id": "005930",
                "interval": "1D",
                "base_dt": "20260625",
                "upd_stkpc_tp": "1",
                "source_ref": "test-request",
            }
        ],
        "manual_response_files": [
            {
                "import_id": "historical-market-data-import-test",
                "file_path": manual_payload_path,
                "request_id": "ka10081-005930-test",
                "api_id": "KA10081",
                "provider_symbol": "005930",
                "canonical_instrument_id": "005930",
                "available_at": "2026-06-25T15:35:00+09:00",
            }
        ],
        "audit_records": [
            {
                "audit_record_id": "historical-market-data-audit-test",
                "created_at": "2026-06-26T16:00:00+09:00",
                "source_path": manual_payload_path,
                "operator_context": "offline historical market data test",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
    }


def write_manual_daily_payload(path) -> None:
    path.write_text(
        json.dumps(
            {
                "return_code": 0,
                "return_msg": "MANUAL_RESPONSE_IMPORTED",
                "stk_cd": "005930",
                "cont_yn": "N",
                "next_key": "",
                "stk_day_pole_chart_qry": [
                    {"dt": "20260623", "open_pric": "80000", "high_pric": "81300", "low_pric": "79800", "cur_prc": "81200", "trde_qty": "1000000"},
                    {"dt": "20260624", "open_pric": "81250", "high_pric": "82000", "low_pric": "80900", "cur_prc": "81800", "trde_qty": "980000"},
                    {"dt": "20260625", "open_pric": "81850", "high_pric": "82600", "low_pric": "81600", "cur_prc": "82400", "trde_qty": "1010000"},
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_historical_market_data_pipeline_input_validates(tmp_path) -> None:
    manual_file = tmp_path / "manual_daily.json"
    write_manual_daily_payload(manual_file)
    payload = historical_market_data_payload(
        store_root=str(tmp_path / "normalized"),
        raw_lake_root=str(tmp_path / "raw_lake"),
        manual_payload_path=str(manual_file),
    )

    validated = HistoricalMarketDataPipelineInput.model_validate(payload)

    assert validated.dataset_id == "HISTORICAL-MARKET-DATA-TEST"
    assert validated.request_specs[0].api_id.value == "KA10081"


def test_historical_market_data_to_feature_store_price_bar(tmp_path) -> None:
    row = HistoricalOhlcvRow.model_validate(
        {
            "row_id": "row-1",
            "dataset_id": "dataset-1",
            "instrument_id": "005930",
            "provider_symbol": "005930",
            "interval": "1D",
            "api_id": "KA10081",
            "observed_at": "2026-06-25T15:30:00+09:00",
            "available_at": "2026-06-25T15:35:00+09:00",
            "open_price": 81850,
            "high_price": 82600,
            "low_price": 81600,
            "close_price": 82400,
            "volume": 1010000,
            "adjusted": True,
            "adjustment_policy": "UPD_STKPC_TP_1",
            "source_ref": str(tmp_path / "manual_daily.json"),
        }
    )

    bar = to_feature_store_price_bar(row)

    assert bar.instrument_id == "005930"
    assert bar.close_price == 82400
    assert bar.source_ref.source_kind.value == "LOCAL_PRICE_HISTORY_FIXTURE"
