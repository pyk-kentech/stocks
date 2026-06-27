from stock_risk_mcp.historical_market_data_capture_runner import run_historical_market_data_real_capture
from stock_risk_mcp import historical_market_data_capture_runner as capture_runner_module
from stock_risk_mcp import historical_market_data_guard as capture_guard_module
from stock_risk_mcp.historical_market_data_models import HistoricalMarketDataPipelineInput
from stock_risk_mcp.historical_market_data_transport import MockHistoricalMarketDataTransport, RealKiwoomChartTransport


def test_historical_market_data_capture_runner_runs_with_mock_transport(tmp_path) -> None:
    (tmp_path / "appkey.txt").write_text("APPKEY", encoding="utf-8")
    (tmp_path / "secretkey.txt").write_text("SECRETKEY", encoding="utf-8")
    fixture = HistoricalMarketDataPipelineInput.model_validate(
        {
            "pipeline_id": "historical-market-data-test",
            "dataset_id": "historical-market-data-test",
            "mode": "REAL_OPT_IN_BOUNDARY",
            "capture_profile": "DAILY_RESEARCH_PROFILE",
            "store_root": str(tmp_path / "normalized"),
            "raw_lake_root": str(tmp_path / "raw_lake"),
            "requested_storage_formats": ["IN_MEMORY", "JSON"],
            "partition_spec": {"partition_keys": ["DATASET_ID", "INTERVAL", "DATE"]},
            "opt_in": {
                "allow_real_chart_capture": True,
                "acknowledge_readonly_only": True,
                "acknowledge_no_orders": True,
                "acknowledge_user_initiated": True,
                "acknowledge_rate_limit_and_capacity": True,
                "acknowledge_credential_redaction": True,
            },
            "real_capture_config": {
                "credential_ref": {
                    "credential_ref_id": "TEST_REF",
                    "appkey_ref_path": str(tmp_path / "appkey.txt"),
                    "secretkey_ref_path": str(tmp_path / "secretkey.txt"),
                },
                "transport_kind": "MOCK",
            },
            "request_specs": [
                {
                    "request_id": "ka10081-005930-test",
                    "api_id": "KA10081",
                    "provider_symbol": "005930",
                    "canonical_instrument_id": "005930",
                    "interval": "1D",
                    "base_dt": "20260624",
                    "upd_stkpc_tp": "1",
                    "source_ref": "TEST",
                }
            ],
        }
    )
    transport = MockHistoricalMarketDataTransport(
        {
            "ka10081-005930-test": {
                "status_code": 200,
                "headers": {"cont-yn": "N", "next-key": ""},
                "body_json": {
                    "return_code": 0,
                    "return_msg": "OK",
                    "stk_cd": "005930",
                    "cont_yn": "N",
                    "next_key": "",
                    "stk_day_pole_chart_qry": [
                        {"dt": "20260623", "open_pric": "80000", "high_pric": "81300", "low_pric": "79800", "cur_prc": "81200", "trde_qty": "1000000"}
                    ],
                },
            }
        }
    )
    result = run_historical_market_data_real_capture(fixture, transport=transport)
    assert result.normalized_row_count == 1
    assert result.manifest is not None
    assert (tmp_path / "raw_lake" / "ka10081-005930-test-response.json").exists()


def _fixture(tmp_path):
    (tmp_path / "appkey.txt").write_text("APPKEY", encoding="utf-8")
    (tmp_path / "secretkey.txt").write_text("SECRETKEY", encoding="utf-8")
    return HistoricalMarketDataPipelineInput.model_validate(
        {
            "pipeline_id": "historical-market-data-test",
            "dataset_id": "historical-market-data-test",
            "mode": "REAL_OPT_IN_BOUNDARY",
            "capture_profile": "DAILY_RESEARCH_PROFILE",
            "store_root": str(tmp_path / "normalized"),
            "raw_lake_root": str(tmp_path / "raw_lake"),
            "requested_storage_formats": ["IN_MEMORY", "JSON"],
            "partition_spec": {"partition_keys": ["DATASET_ID", "INTERVAL", "DATE"]},
            "opt_in": {
                "allow_real_chart_capture": True,
                "acknowledge_readonly_only": True,
                "acknowledge_no_orders": True,
                "acknowledge_user_initiated": True,
                "acknowledge_rate_limit_and_capacity": True,
                "acknowledge_credential_redaction": True,
            },
            "real_capture_config": {
                "credential_ref": {
                    "credential_ref_id": "TEST_REF",
                    "appkey_ref_path": str(tmp_path / "appkey.txt"),
                    "secretkey_ref_path": str(tmp_path / "secretkey.txt"),
                },
                "transport_kind": "MOCK",
            },
            "request_specs": [
                {
                    "request_id": "ka10081-005930-test",
                    "api_id": "KA10081",
                    "provider_symbol": "005930",
                    "canonical_instrument_id": "005930",
                    "interval": "1D",
                    "base_dt": "20260624",
                    "upd_stkpc_tp": "1",
                    "source_ref": "TEST",
                }
            ],
        }
    )


def test_historical_market_data_capture_runner_returns_provider_empty_response(tmp_path) -> None:
    fixture = _fixture(tmp_path)
    result = run_historical_market_data_real_capture(
        fixture,
        transport=MockHistoricalMarketDataTransport(
            {
                "ka10081-005930-test": {
                    "status_code": 200,
                    "headers": {"cont-yn": "N", "next-key": ""},
                    "body_json": {
                        "return_code": 0,
                        "return_msg": "OK",
                        "stk_day_pole_chart_qry": [],
                    },
                }
            }
        ),
    )
    assert result.readiness_status.value == "PROVIDER_EMPTY_RESPONSE"
    assert result.raw_response_count == 0
    assert not (tmp_path / "raw_lake" / "ka10081-005930-test-response.json").exists()


def test_historical_market_data_capture_runner_returns_blocked_auth_or_token(tmp_path) -> None:
    fixture = _fixture(tmp_path)
    result = run_historical_market_data_real_capture(
        fixture,
        transport=MockHistoricalMarketDataTransport(
            {
                "ka10081-005930-test": {
                    "status_code": 200,
                    "headers": {"cont-yn": "N", "next-key": ""},
                    "body_json": {
                        "return_code": 3,
                        "return_msg": "인증에 실패했습니다[8005:Token이 유효하지 않습니다]",
                    },
                }
            }
        ),
    )
    assert result.readiness_status.value == "BLOCKED_AUTH_OR_TOKEN"
    assert result.raw_response_count == 0


def test_historical_market_data_capture_runner_returns_dependency_gap_for_missing_schema(tmp_path) -> None:
    fixture = _fixture(tmp_path)
    result = run_historical_market_data_real_capture(
        fixture,
        transport=MockHistoricalMarketDataTransport(
            {
                "ka10081-005930-test": {
                    "status_code": 200,
                    "headers": {"cont-yn": "N", "next-key": ""},
                    "body_json": {
                        "return_code": 0,
                        "return_msg": "OK",
                        "unexpected_payload": [{"foo": "bar"}],
                    },
                }
            }
        ),
    )
    assert result.readiness_status.value == "DEPENDENCY_GAP_KIWOOM_ENDPOINT_SCHEMA"
    assert result.raw_response_count == 0


def test_historical_market_data_capture_runner_blocks_real_network_not_implemented(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path)
    fixture = fixture.model_copy(update={"real_capture_config": fixture.real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART"})})
    monkeypatch.setattr(capture_runner_module, "is_pytest_runtime", lambda: False)
    monkeypatch.setattr(capture_guard_module, "is_pytest_runtime", lambda: False)
    result = run_historical_market_data_real_capture(fixture, transport=RealKiwoomChartTransport.__new__(RealKiwoomChartTransport))
    assert result.readiness_status.value == "BLOCKED_REAL_NETWORK_NOT_IMPLEMENTED"
