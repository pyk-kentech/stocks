from pathlib import Path
import json
from datetime import datetime

import pytest

from stock_risk_mcp.cli import _build_historical_market_data_real_capture_input, build_command_parser
from stock_risk_mcp.historical_market_data_capture_runner import run_historical_market_data_real_capture
from stock_risk_mcp import historical_market_data_capture_runner as capture_runner_module
from stock_risk_mcp import historical_market_data_guard as capture_guard_module
from stock_risk_mcp import kiwoom_capture_and_train_runner as wrapper_module
from stock_risk_mcp import kiwoom_watchlist_batch_runner as batch_runner_module
from stock_risk_mcp.historical_market_data_models import HistoricalChartRawResponse, HistoricalMarketDataPipelineInput, HistoricalMarketDataTransportKind
from stock_risk_mcp.historical_market_data_transport import MockHistoricalMarketDataTransport, RealKiwoomChartTransport
from stock_risk_mcp.kiwoom_tr_rate_limiter import KiwoomTrRateLimiter, resolve_kiwoom_tr_rate_limit_config
from stock_risk_mcp.kiwoom_oauth_models import KiwoomEnvironment, KiwoomOAuthStatus, KiwoomOAuthTokenIssueResponse, KiwoomOAuthTokenRef


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
    assert result.manifest.manifest_path is not None
    assert result.manifest.ohlcv_rows_path is not None
    assert (tmp_path / "raw_lake" / "ka10081-005930-test-response.json").exists()
    assert (tmp_path / "normalized" / "historical-market-data-test" / "historical_ohlcv_dataset_manifest.json").exists()


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


def _token_ref_file(tmp_path: Path) -> Path:
    token_store_root = tmp_path / "oauth_tokens"
    token_store_root.mkdir(exist_ok=True)
    token_ref_path = token_store_root / "mock_token.json"
    token_ref_path.write_text(
        """
        {
          "token": "REDACTED",
          "token_type": "Bearer",
          "expires_dt": "2099-01-01T00:00:00+00:00",
          "issued_at": "2026-06-27T00:00:00+00:00",
          "environment": "MOCK",
          "credential_fingerprint_redacted": "sha256:fixture"
        }
        """.strip(),
        encoding="utf-8",
    )
    return token_ref_path


def _cached_raw_lake_file(
    tmp_path: Path,
    fixture: HistoricalMarketDataPipelineInput,
    symbol: str,
    *,
    chart_rows: list[dict[str, str]] | None = None,
) -> Path:
    spec = next(item for item in fixture.request_specs if item.provider_symbol == symbol)
    raw_path = Path(fixture.raw_lake_root) / f"{spec.request_id.lower()}-response.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    rows = chart_rows or [
        {"dt": "20260623", "open_pric": "80000", "high_pric": "81300", "low_pric": "79800", "cur_prc": "81200", "trde_qty": "1000000"},
        {"dt": "20260624", "open_pric": "81200", "high_pric": "81800", "low_pric": "81000", "cur_prc": "81600", "trde_qty": "1100000"},
    ]
    response = HistoricalChartRawResponse.model_validate(
        {
            "response_id": f"{spec.request_id}-RESPONSE",
            "request_id": spec.request_id,
            "api_id": spec.api_id.value,
            "provider": "KIWOOM_REST",
            "provider_symbol": symbol,
            "canonical_instrument_id": symbol,
            "imported_at": "2026-06-27T00:00:00+09:00",
            "available_at": "2026-06-27T00:00:00+09:00",
            "source_kind": "RAW_LAKE_RECORD",
            "source_ref": f"{spec.request_id}.json",
            "cont_yn": "N",
            "next_key": "",
            "payload_summary": {"return_code": 0, "row_count": len(rows)},
            "raw_payload": {
                "_capture_meta": {"row_count": len(rows)},
                "return_code": 0,
                "return_msg": "OK",
                "stk_cd": symbol,
                "stk_dt_pole_chart_qry": rows,
            },
        }
    )
    raw_path.write_text(response.model_dump_json(indent=2), encoding="utf-8")
    return raw_path


def test_kiwoom_tr_rate_limiter_enforces_min_interval_and_persists_ledger(tmp_path) -> None:
    current_time = [100.0]
    sleeps: list[float] = []

    def now_fn() -> float:
        return current_time[0]

    def sleep_fn(seconds: float) -> None:
        sleeps.append(seconds)
        current_time[0] += seconds

    config = resolve_kiwoom_tr_rate_limit_config(
        profile_name="CONSERVATIVE",
        ledger_path=str(tmp_path / "local_data" / "kiwoom_rate_limit" / "ledger.json"),
        min_request_interval_seconds=4.0,
    )
    limiter = KiwoomTrRateLimiter(config, now_fn=now_fn, sleep_fn=sleep_fn)
    limiter.await_request_slot()
    limiter.record_request()
    current_time[0] = 101.0
    limiter.await_request_slot()
    limiter.record_request()
    ledger = json.loads(Path(config.ledger_path).read_text(encoding="utf-8"))
    assert sleeps == [3.0]
    assert len(ledger["request_timestamps"]) == 2
    assert "token" not in json.dumps(ledger).lower()
    assert "authorization" not in json.dumps(ledger).lower()


def test_kiwoom_tr_rate_limiter_enforces_second_minute_and_hour_windows(tmp_path) -> None:
    current_time = [3600.0]
    sleeps: list[float] = []

    def now_fn() -> float:
        return current_time[0]

    def sleep_fn(seconds: float) -> None:
        sleeps.append(seconds)
        current_time[0] += seconds

    config = resolve_kiwoom_tr_rate_limit_config(
        profile_name="TEST_FAST",
        ledger_path=str(tmp_path / "local_data" / "kiwoom_rate_limit" / "ledger.json"),
        max_tr_per_second=1,
        max_tr_per_minute=2,
        max_tr_per_hour=3,
        min_request_interval_seconds=0.0,
    )
    limiter = KiwoomTrRateLimiter(config, now_fn=now_fn, sleep_fn=sleep_fn)
    for requested_time in (3600.0, 3600.2, 3601.3, 3660.5):
        current_time[0] = requested_time
        limiter.await_request_slot()
        limiter.record_request()
    assert pytest.approx(sleeps, rel=0, abs=1e-6) == [0.8, 58.7, 3539.5]


def test_kiwoom_tr_rate_limiter_loads_persisted_ledger_across_restart(tmp_path) -> None:
    current_time = [200.0]

    def now_fn() -> float:
        return current_time[0]

    config = resolve_kiwoom_tr_rate_limit_config(
        profile_name="TEST_FAST",
        ledger_path=str(tmp_path / "local_data" / "kiwoom_rate_limit" / "ledger.json"),
        max_tr_per_second=10,
        max_tr_per_minute=10,
        max_tr_per_hour=10,
        min_request_interval_seconds=0.0,
    )
    first = KiwoomTrRateLimiter(config, now_fn=now_fn, sleep_fn=lambda _seconds: None)
    first.await_request_slot()
    first.record_request()
    second = KiwoomTrRateLimiter(config, now_fn=now_fn, sleep_fn=lambda _seconds: None)
    summary = second.build_summary()
    assert summary["tr_request_count_last_minute"] == 1
    assert summary["tr_request_count_last_hour"] == 1


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


def test_historical_market_data_capture_runner_returns_provider_chart_error(tmp_path) -> None:
    fixture = _fixture(tmp_path)
    result = run_historical_market_data_real_capture(
        fixture,
        transport=MockHistoricalMarketDataTransport(
            {
                "ka10081-005930-test": {
                    "status_code": 200,
                    "headers": {"cont-yn": "N", "next-key": ""},
                    "body_json": {
                        "return_code": 100,
                        "return_msg": "요청 전문 오류",
                    },
                }
            }
        ),
    )
    assert result.readiness_status.value == "PROVIDER_CHART_ERROR"
    assert result.task_results[0].provider_return_code == 100
    assert result.task_results[0].provider_return_msg == "요청 전문 오류"


def test_historical_market_data_capture_runner_uses_ka10081_schema_and_continuation(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path).model_copy(update={"real_capture_config": _fixture(tmp_path).real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART"})})
    seen_previews = []

    class FakeRealTransport:
        transport_kind = HistoricalMarketDataTransportKind.REAL_KIWOOM_CHART
        base_url = "https://mockapi.kiwoom.com"

        def execute(self, preview, *, auth_header=None):
            assert auth_header == "Bearer REDACTED"
            seen_previews.append(preview)
            if len(seen_previews) == 1:
                assert preview.path == "/api/dostk/chart"
                assert preview.headers["api-id"] == "ka10081"
                assert preview.body_json == {"stk_cd": "005930", "upd_stkpc_tp": "1", "base_dt": "20260624"}
                assert preview.headers["cont-yn"] == "N"
                assert preview.headers["next-key"] == ""
                return {
                    "status_code": 200,
                    "headers": {"cont-yn": "Y", "next-key": "PAGE2"},
                    "body_json": {
                        "return_code": 0,
                        "return_msg": "OK",
                        "stk_dt_pole_chart_qry": [
                            {"dt": "20260624", "open_pric": "81200", "high_pric": "81800", "low_pric": "81000", "cur_prc": "81600", "trde_qty": "1100000"}
                        ],
                    },
                }
            assert preview.headers["cont-yn"] == "Y"
            assert preview.headers["next-key"] == "PAGE2"
            return {
                "status_code": 200,
                "headers": {"cont-yn": "N", "next-key": ""},
                "body_json": {
                    "return_code": 0,
                    "return_msg": "OK",
                    "stk_dt_pole_chart_qry": [
                        {"dt": "20260623", "open_pric": "80000", "high_pric": "81300", "low_pric": "79800", "cur_prc": "81200", "trde_qty": "1000000"}
                    ],
                },
            }

    monkeypatch.setattr(capture_runner_module, "is_pytest_runtime", lambda: False)
    monkeypatch.setattr(capture_guard_module, "is_pytest_runtime", lambda: False)
    result = run_historical_market_data_real_capture(fixture, transport=FakeRealTransport(), auth_header="Bearer REDACTED")
    assert result.readiness_status.value == "REAL_CAPTURE_EXECUTED"
    assert result.raw_response_count == 2
    assert result.normalized_row_count == 2
    assert result.task_results[0].page_count == 2
    assert result.task_results[0].row_count == 2
    assert result.task_results[0].chart_response_received is True
    assert len(seen_previews) == 2


def test_build_historical_market_data_real_capture_input_carries_upd_stkpc_tp() -> None:
    parser = build_command_parser()
    args = parser.parse_args(
        [
            "kiwoom-ka10081-capture-and-train-run",
            "--kiwoom-environment",
            "MOCK",
            "--credential-ref",
            "/tmp/kiwoom",
            "--token-store-root",
            "local_data/kiwoom_tokens",
            "--api-id",
            "KA10081",
            "--symbols",
            "005930",
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2026-06-27",
            "--store-root",
            "local_data/historical_market_data/store",
            "--raw-lake-root",
            "local_data/historical_market_data/raw_lake",
            "--upd-stkpc-tp",
            "1",
        ]
    )
    pipeline = _build_historical_market_data_real_capture_input(args)
    assert pipeline.request_specs[0].upd_stkpc_tp == "1"
    assert pipeline.request_specs[0].base_dt == "20260627"


def test_build_historical_market_data_real_capture_input_uses_multi_symbol_dataset_id() -> None:
    parser = build_command_parser()
    args = parser.parse_args(
        [
            "kiwoom-ka10081-capture-and-train-run",
            "--kiwoom-environment",
            "MOCK",
            "--credential-ref",
            "/tmp/kiwoom",
            "--token-store-root",
            "local_data/kiwoom_tokens",
            "--api-id",
            "KA10081",
            "--symbols",
            "005930,000660",
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2026-06-27",
            "--store-root",
            "local_data/historical_market_data/store",
            "--raw-lake-root",
            "local_data/historical_market_data/raw_lake",
        ]
    )
    pipeline = _build_historical_market_data_real_capture_input(args)
    assert pipeline.dataset_id == "HISTORICAL-MARKET-DATA-KA10081-MULTI-2"
    assert [spec.provider_symbol for spec in pipeline.request_specs] == ["005930", "000660"]


def test_historical_market_data_capture_runner_blocks_without_auth_header(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path)
    fixture = fixture.model_copy(update={"real_capture_config": fixture.real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART"})})
    monkeypatch.setattr(capture_runner_module, "is_pytest_runtime", lambda: False)
    monkeypatch.setattr(capture_guard_module, "is_pytest_runtime", lambda: False)
    result = run_historical_market_data_real_capture(fixture, transport=RealKiwoomChartTransport.__new__(RealKiwoomChartTransport))
    assert result.readiness_status.value == "BLOCKED_AUTH_OR_TOKEN"


def test_capture_and_train_wrapper_reloads_persisted_manifest(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path).model_copy(
        update={
            "dataset_id": "historical-market-data-ka10081-multi-2",
            "request_specs": _fixture(tmp_path).request_specs
            + [
                _fixture(tmp_path).request_specs[0].model_copy(
                    update={
                        "request_id": "KA10081-000660-TEST",
                        "provider_symbol": "000660",
                        "canonical_instrument_id": "000660",
                    }
                )
            ],
        }
    )
    token_store_root = tmp_path / "oauth_tokens"
    token_store_root.mkdir()
    token_ref_path = token_store_root / "mock_token.json"
    token_ref_path.write_text(
        """
        {
          "token": "REDACTED",
          "token_type": "Bearer",
          "expires_dt": "2099-01-01T00:00:00+00:00",
          "issued_at": "2026-06-27T00:00:00+00:00",
          "environment": "MOCK",
          "credential_fingerprint_redacted": "sha256:fixture"
        }
        """.strip(),
        encoding="utf-8",
    )

    class FakeRealTransport:
        transport_kind = HistoricalMarketDataTransportKind.REAL_KIWOOM_CHART

        def __init__(self, **kwargs):
            del kwargs

        def execute(self, preview, *, auth_header=None):
            assert auth_header == "Bearer REDACTED"
            symbol = preview.body_json["stk_cd"]
            rows = []
            for index in range(40):
                close_price = 80000 + index * 120 + (200 if index % 6 == 0 else 0) - (150 if index % 5 == 0 else 0)
                rows.append(
                    {
                        "dt": f"2026{5 + ((index + 9) // 30):02d}{((index + 9) % 30) + 1:02d}",
                        "open_pric": str(close_price - (250 if index % 4 == 0 else 80)),
                        "high_pric": str(close_price + 260),
                        "low_pric": str(close_price - 220),
                        "cur_prc": str(close_price),
                        "trde_qty": str(900000 + index * 40000 + (300000 if index % 7 == 0 else 0)),
                    }
                )
            return {
                "status_code": 200,
                "headers": {"cont-yn": "N", "next-key": ""},
                "body_json": {
                    "return_code": 0,
                    "return_msg": "OK",
                    "stk_day_pole_chart_qry": rows,
                    "stk_cd": symbol,
                },
            }

    def fake_issue(_request):
        return KiwoomOAuthTokenIssueResponse(
            status=KiwoomOAuthStatus.TOKEN_CACHE_HIT,
            token_type="Bearer",
            token_ref=KiwoomOAuthTokenRef(
                token_ref_path=str(token_ref_path),
                token_type="Bearer",
                expires_dt="2099-01-01T00:00:00+00:00",
                issued_at="2026-06-27T00:00:00+00:00",
                environment=KiwoomEnvironment.MOCK,
                credential_fingerprint_redacted="sha256:fixture",
            ),
            expires_dt="2099-01-01T00:00:00+00:00",
            issued_at="2026-06-27T00:00:00+00:00",
            return_msg_redacted="TOKEN_CACHE_HIT",
        )

    monkeypatch.setattr(wrapper_module, "issue_kiwoom_oauth_token", fake_issue)
    monkeypatch.setattr(wrapper_module, "RealKiwoomChartTransport", FakeRealTransport)
    monkeypatch.setattr(capture_runner_module, "is_pytest_runtime", lambda: False)
    monkeypatch.setattr(capture_guard_module, "is_pytest_runtime", lambda: False)

    result = wrapper_module.run_kiwoom_ka10081_capture_and_train(
        fixture.model_copy(update={"real_capture_config": fixture.real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART"})}),
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(token_store_root),
        training_output_root=str(tmp_path / "local_data" / "offline_strategy"),
        strategy_families=["MACD_RSI", "RSI_OVERSOLD_REBOUND", "VOLUME_LONG_CANDLE_PULLBACK", "RANGE_BREAKOUT", "ADX_TREND_SCALPING"],
        search_mode="SMOKE_SEARCH",
        walk_forward_mode="ROLLING",
        promotion_profile="STABILITY_FIRST",
        fill_policy="NEXT_BAR_CONSERVATIVE",
        direction="LONG_ONLY",
    )
    assert result["manifest_written"] is True
    assert result["manifest_reloaded"] is True
    assert result["training_started"] is True
    assert result["training_completed"] is True
    assert Path(result["manifest_path"]).exists()
    assert result["strategy_families"] == ["ADX_TREND_SCALPING", "MACD_RSI", "RANGE_BREAKOUT", "RSI_OVERSOLD_REBOUND", "VOLUME_LONG_CANDLE_PULLBACK"]
    assert result["requested_strategy_families"] == result["strategy_families"]
    assert result["supported_strategy_families"] == ["MACD_RSI", "RSI_OVERSOLD_REBOUND", "VOLUME_LONG_CANDLE_PULLBACK"]
    assert result["unsupported_strategy_families"] == ["ADX_TREND_SCALPING", "RANGE_BREAKOUT"]
    assert result["generated_strategy_families"] == ["MACD_RSI_MOMENTUM", "RSI_OVERSOLD_REBOUND", "VOLUME_PULLBACK_LONG"]
    assert result["candidate_count_by_family"] == {"MACD_RSI_MOMENTUM": 1, "RSI_OVERSOLD_REBOUND": 1, "VOLUME_PULLBACK_LONG": 1}
    assert result["search_mode"] == "SMOKE_SEARCH"
    assert result["walk_forward_mode"] == "ROLLING_CHRONOLOGICAL_WALK_FORWARD"
    assert result["promotion_profile"] == "STABILITY_FIRST"
    assert result["fill_policy"] == "NEXT_BAR_CONSERVATIVE"
    assert result["direction"] == "LONG_ONLY"
    assert result["manifest_id"].startswith("HISTORICAL-MARKET-DATA-KA10081-MULTI-2")
    assert sorted(result["completed_symbols"]) == ["000660", "005930"]
    assert result["failed_symbols"] == []
    assert result["partial_symbols"] == []
    assert len(result["symbol_results"]) == 2
    assert sorted(item["requested_symbol"] for item in result["symbol_results"]) == ["000660", "005930"]
    promotion_payload = json.loads(Path(result["promotion_gate_output_path"]).read_text(encoding="utf-8"))
    assert all("family" in item for item in promotion_payload)
    for item in promotion_payload:
        if "NO_TRADES" in item["reasons"]:
            assert "diagnostics" in item
            assert "input_row_count" in item["diagnostics"]
            assert "signal_count_before_filters" in item["diagnostics"]
            assert "actual_trade_count" in item["diagnostics"]


def test_capture_and_train_wrapper_stops_before_chart_request_on_token_failure(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path)
    token_store_root = tmp_path / "oauth_tokens"
    token_store_root.mkdir()
    chart_called = {"value": False}

    class FakeRealTransport:
        transport_kind = HistoricalMarketDataTransportKind.REAL_KIWOOM_CHART

        def __init__(self, **kwargs):
            del kwargs

        def execute(self, preview, *, auth_header=None):
            del preview, auth_header
            chart_called["value"] = True
            return {}

    def fake_issue(_request):
        return KiwoomOAuthTokenIssueResponse(
            status=KiwoomOAuthStatus.PROVIDER_TOKEN_ERROR,
            stage="TOKEN_ISSUE_HTTP",
            kiwoom_environment=KiwoomEnvironment.MOCK,
            endpoint_base_url="https://mockapi.kiwoom.com",
            endpoint_path="/oauth2/token",
            request_content_type="application/json;charset=UTF-8",
            request_body_shape=["grant_type", "appkey", "secretkey"],
            credential_ref_status="LOADED",
            token_written=False,
            provider_return_code=5001,
            provider_return_msg="mock provider token rejected",
            issued_at="2026-06-27T00:00:00+00:00",
            return_msg_redacted="mock provider token rejected",
        )

    monkeypatch.setattr(wrapper_module, "issue_kiwoom_oauth_token", fake_issue)
    monkeypatch.setattr(wrapper_module, "RealKiwoomChartTransport", FakeRealTransport)
    monkeypatch.setattr(capture_runner_module, "is_pytest_runtime", lambda: False)
    monkeypatch.setattr(capture_guard_module, "is_pytest_runtime", lambda: False)

    result = wrapper_module.run_kiwoom_ka10081_capture_and_train(
        fixture.model_copy(update={"real_capture_config": fixture.real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART"})}),
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(token_store_root),
        training_output_root=str(tmp_path / "local_data" / "offline_strategy"),
    )
    assert result["status"] == "FAILED"
    assert result["token_status"] == "PROVIDER_TOKEN_ERROR"
    assert result["chart_request_started"] is False
    assert result["manifest_written"] is False
    assert result["training_started"] is False
    assert chart_called["value"] is False


def test_capture_and_train_wrapper_expanded_search_generates_more_candidates_and_ranking_summary(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path).model_copy(
        update={
            "request_specs": _fixture(tmp_path).request_specs
            + [
                _fixture(tmp_path).request_specs[0].model_copy(
                    update={"request_id": "KA10081-000660-TEST", "provider_symbol": "000660", "canonical_instrument_id": "000660"}
                )
            ],
        }
    )
    token_store_root = tmp_path / "oauth_tokens"
    token_store_root.mkdir()
    token_ref_path = token_store_root / "mock_token.json"
    token_ref_path.write_text(
        """
        {
          "token": "REDACTED",
          "token_type": "Bearer",
          "expires_dt": "2099-01-01T00:00:00+00:00",
          "issued_at": "2026-06-27T00:00:00+00:00",
          "environment": "MOCK",
          "credential_fingerprint_redacted": "sha256:fixture"
        }
        """.strip(),
        encoding="utf-8",
    )

    class FakeRealTransport:
        transport_kind = HistoricalMarketDataTransportKind.REAL_KIWOOM_CHART

        def __init__(self, **kwargs):
            del kwargs

        def execute(self, preview, *, auth_header=None):
            assert auth_header == "Bearer REDACTED"
            symbol = preview.body_json["stk_cd"]
            rows = []
            for index in range(40):
                close_price = 80000 + index * 120 + (200 if index % 6 == 0 else 0) - (150 if index % 5 == 0 else 0)
                rows.append(
                    {
                        "dt": f"2026{5 + ((index + 9) // 30):02d}{((index + 9) % 30) + 1:02d}",
                        "open_pric": str(close_price - (250 if index % 4 == 0 else 80)),
                        "high_pric": str(close_price + 260),
                        "low_pric": str(close_price - 220),
                        "cur_prc": str(close_price),
                        "trde_qty": str(900000 + index * 40000 + (300000 if index % 7 == 0 else 0)),
                    }
                )
            return {
                "status_code": 200,
                "headers": {"cont-yn": "N", "next-key": ""},
                "body_json": {
                    "return_code": 0,
                    "return_msg": "OK",
                    "stk_day_pole_chart_qry": rows,
                    "stk_cd": symbol,
                },
            }

    def fake_issue(_request):
        return KiwoomOAuthTokenIssueResponse(
            status=KiwoomOAuthStatus.TOKEN_CACHE_HIT,
            token_type="Bearer",
            token_ref=KiwoomOAuthTokenRef(
                token_ref_path=str(token_ref_path),
                token_type="Bearer",
                expires_dt="2099-01-01T00:00:00+00:00",
                issued_at="2026-06-27T00:00:00+00:00",
                environment=KiwoomEnvironment.MOCK,
                credential_fingerprint_redacted="sha256:fixture",
            ),
            expires_dt="2099-01-01T00:00:00+00:00",
            issued_at="2026-06-27T00:00:00+00:00",
            return_msg_redacted="TOKEN_CACHE_HIT",
        )

    monkeypatch.setattr(wrapper_module, "issue_kiwoom_oauth_token", fake_issue)
    monkeypatch.setattr(wrapper_module, "RealKiwoomChartTransport", FakeRealTransport)
    monkeypatch.setattr(capture_runner_module, "is_pytest_runtime", lambda: False)
    monkeypatch.setattr(capture_guard_module, "is_pytest_runtime", lambda: False)

    smoke_result = wrapper_module.run_kiwoom_ka10081_capture_and_train(
        fixture.model_copy(update={"real_capture_config": fixture.real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART"})}),
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(token_store_root),
        training_output_root=str(tmp_path / "local_data" / "offline_strategy_smoke"),
        strategy_families=["MACD_RSI", "RSI_OVERSOLD_REBOUND", "VOLUME_LONG_CANDLE_PULLBACK"],
        search_mode="SMOKE_SEARCH",
        direction="LONG_ONLY",
    )
    expanded_result = wrapper_module.run_kiwoom_ka10081_capture_and_train(
        fixture.model_copy(update={"real_capture_config": fixture.real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART"})}),
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(token_store_root),
        training_output_root=str(tmp_path / "local_data" / "offline_strategy_expanded"),
        strategy_families=["MACD_RSI", "RSI_OVERSOLD_REBOUND", "VOLUME_LONG_CANDLE_PULLBACK"],
        search_mode="EXPANDED_SEARCH",
        direction="LONG_ONLY",
    )
    assert smoke_result["candidate_count"] == 3
    assert expanded_result["search_mode"] == "EXPANDED_SEARCH"
    assert expanded_result["candidate_count"] == 24
    assert expanded_result["candidate_count_by_family"] == {"MACD_RSI_MOMENTUM": 8, "RSI_OVERSOLD_REBOUND": 8, "VOLUME_PULLBACK_LONG": 8}
    assert {key: len(value) for key, value in expanded_result["candidate_parameter_summary_by_family"].items()} == {
        "MACD_RSI_MOMENTUM": 8,
        "RSI_OVERSOLD_REBOUND": 8,
        "VOLUME_PULLBACK_LONG": 8,
    }
    ranking_payload = json.loads(Path(expanded_result["ranking_report_path"]).read_text(encoding="utf-8"))
    assert ranking_payload["candidate_count_by_family"] == expanded_result["candidate_count_by_family"]
    assert Path(expanded_result["trade_audit_artifact_path"]).exists()
    assert all("rank_score" in row and "rank_score_components" in row for row in ranking_payload["rows"])
    assert all("parameter_set_id" in row and "parameter_summary" in row for row in ranking_payload["rows"])
    assert all(row["rank_score"] is not None for row in ranking_payload["rows"])
    assert all("input_row_count" in row and "symbol_row_count" in row for row in ranking_payload["rows"])
    assert all("fill_policy" in row and row["fill_policy"] == "CONSERVATIVE_NEXT_BAR_FILL" for row in ranking_payload["rows"])
    assert all("same_bar_fill_detected" in row and "lookahead_detected" in row for row in ranking_payload["rows"])
    assert all("indicator_columns_available" in row and "required_indicator_columns" in row for row in ranking_payload["rows"])
    assert all("signal_count_before_filters" in row and "condition_pass_counts" in row and "condition_block_counts" in row for row in ranking_payload["rows"])
    assert any(row["signal_count_before_filters"] > 0 for row in ranking_payload["rows"])
    assert len({row["rank_score"] for row in ranking_payload["rows"]}) > 1
    ranking_summary = json.loads(Path(expanded_result["ranking_summary_path"]).read_text(encoding="utf-8"))
    assert "best_candidate_by_symbol" in ranking_summary
    assert "best_candidate_by_family" in ranking_summary
    assert "rejected_count_by_reason" in ranking_summary
    assert "zero_entry_signal_count" in ranking_summary
    assert "zero_entry_signal_count_by_family" in ranking_summary
    assert "missing_indicator_count_by_family" in ranking_summary
    assert "best_diagnostic_candidate_by_symbol" in ranking_summary
    assert "best_diagnostic_candidate_by_family" in ranking_summary
    assert "promotion_passed_count" in ranking_summary
    assert "promotion_rejected_count" in ranking_summary
    assert "promotion_status_count" in ranking_summary
    assert "PROMOTION_GATE_PASSED" not in ranking_summary["rejected_count_by_reason"]
    assert expanded_result["leakage_audit_status"] == "LEAKAGE_AUDIT_PASSED"
    assert expanded_result["same_bar_fill_count"] == 0
    assert expanded_result["lookahead_violation_count"] == 0
    audited_rows = [row for row in ranking_payload["rows"] if row["actual_trade_count"] > 0 and row["exit_signal_count"] == 0]
    assert audited_rows
    assert any((row["forced_exit_count"] + row["holding_period_exit_count"] + row["end_of_data_exit_count"]) > 0 for row in audited_rows)
    high_drawdown_rows = [row for row in ranking_payload["rows"] if "MAX_DRAWDOWN_CAP_EXCEEDED" in row["rejection_reasons"]]
    lower_drawdown_rows = [row for row in ranking_payload["rows"] if "MAX_DRAWDOWN_CAP_EXCEEDED" not in row["rejection_reasons"]]
    if high_drawdown_rows and lower_drawdown_rows:
        assert max(row["rank_score"] for row in lower_drawdown_rows) >= max(row["rank_score"] for row in high_drawdown_rows)
    dumped = json.dumps({"ranking": ranking_payload, "summary": ranking_summary}, ensure_ascii=False).lower()
    assert "secretkey" not in dumped
    assert "authorization" not in dumped
    assert "\"token\"" not in dumped


def test_capture_and_train_wrapper_isolates_run_artifacts_and_writes_comparison(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path).model_copy(
        update={
            "request_specs": _fixture(tmp_path).request_specs
            + [
                _fixture(tmp_path).request_specs[0].model_copy(
                    update={"request_id": "KA10081-000660-TEST", "provider_symbol": "000660", "canonical_instrument_id": "000660"}
                )
            ],
        }
    )
    token_store_root = tmp_path / "oauth_tokens"
    token_store_root.mkdir()
    token_ref_path = token_store_root / "mock_token.json"
    token_ref_path.write_text(
        json.dumps(
            {
                "token": "REDACTED",
                "token_type": "Bearer",
                "expires_dt": "2099-01-01T00:00:00+00:00",
                "issued_at": "2026-06-27T00:00:00+00:00",
                "environment": "MOCK",
                "credential_fingerprint_redacted": "sha256:fixture",
            }
        ),
        encoding="utf-8",
    )

    class FakeRealTransport:
        transport_kind = HistoricalMarketDataTransportKind.REAL_KIWOOM_CHART

        def __init__(self, **kwargs):
            del kwargs

        def execute(self, preview, *, auth_header=None):
            assert auth_header == "Bearer REDACTED"
            symbol = preview.body_json["stk_cd"]
            rows = []
            for index in range(24):
                close_price = 70000 + index * 100 + (50 if symbol == "000660" else 0)
                rows.append(
                    {
                        "dt": f"2026{5 + ((index + 9) // 30):02d}{((index + 9) % 30) + 1:02d}",
                        "open_pric": str(close_price - 100),
                        "high_pric": str(close_price + 140),
                        "low_pric": str(close_price - 120),
                        "cur_prc": str(close_price),
                        "trde_qty": str(800000 + index * 10000),
                    }
                )
            return {
                "status_code": 200,
                "headers": {"cont-yn": "N", "next-key": ""},
                "body_json": {"return_code": 0, "return_msg": "OK", "stk_day_pole_chart_qry": rows, "stk_cd": symbol},
            }

    def fake_issue(_request):
        return KiwoomOAuthTokenIssueResponse(
            status=KiwoomOAuthStatus.TOKEN_CACHE_HIT,
            token_type="Bearer",
            token_ref=KiwoomOAuthTokenRef(
                token_ref_path=str(token_ref_path),
                token_type="Bearer",
                expires_dt="2099-01-01T00:00:00+00:00",
                issued_at="2026-06-27T00:00:00+00:00",
                environment=KiwoomEnvironment.MOCK,
                credential_fingerprint_redacted="sha256:fixture",
            ),
            expires_dt="2099-01-01T00:00:00+00:00",
            issued_at="2026-06-27T00:00:00+00:00",
            return_msg_redacted="TOKEN_CACHE_HIT",
        )

    monkeypatch.setattr(wrapper_module, "issue_kiwoom_oauth_token", fake_issue)
    monkeypatch.setattr(wrapper_module, "RealKiwoomChartTransport", FakeRealTransport)
    monkeypatch.setattr(capture_runner_module, "is_pytest_runtime", lambda: False)
    monkeypatch.setattr(capture_guard_module, "is_pytest_runtime", lambda: False)

    first = wrapper_module.run_kiwoom_ka10081_capture_and_train(
        fixture.model_copy(update={"real_capture_config": fixture.real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART"})}),
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(token_store_root),
        training_output_root=str(tmp_path / "local_data" / "offline_strategy"),
        strategy_families=["MACD_RSI", "RSI_OVERSOLD_REBOUND"],
        search_mode="SMOKE_SEARCH",
    )
    second = wrapper_module.run_kiwoom_ka10081_capture_and_train(
        fixture.model_copy(update={"real_capture_config": fixture.real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART"})}),
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(token_store_root),
        training_output_root=str(tmp_path / "local_data" / "offline_strategy"),
        strategy_families=["MACD_RSI", "RSI_OVERSOLD_REBOUND"],
        search_mode="SMOKE_SEARCH",
    )

    assert first["offline_strategy_run_id"] != second["offline_strategy_run_id"]
    assert first["offline_strategy_output_root"] != second["offline_strategy_output_root"]
    assert Path(first["ranking_summary_path"]).exists()
    assert Path(second["ranking_summary_path"]).exists()
    assert Path(first["ranking_summary_path"]).read_text(encoding="utf-8")
    assert Path(second["ranking_summary_path"]).read_text(encoding="utf-8")
    assert Path(first["offline_strategy_artifact_manifest_path"]).exists()
    assert Path(second["offline_strategy_artifact_manifest_path"]).exists()
    assert Path(second["offline_strategy_run_comparison_path"]).exists()
    latest = json.loads(Path(second["offline_strategy_latest_run_pointer_path"]).read_text(encoding="utf-8"))
    assert latest["run_id"] == second["offline_strategy_run_id"]
    assert latest["ranking_summary_path"] == second["ranking_summary_path"]
    first_comparison = json.loads(Path(first["offline_strategy_run_comparison_path"]).read_text(encoding="utf-8"))
    second_comparison = json.loads(Path(second["offline_strategy_run_comparison_path"]).read_text(encoding="utf-8"))
    assert first_comparison["comparison_status"] == "NO_PREVIOUS_RUN"
    assert second_comparison["comparison_status"] == "COMPARISON_READY"
    manifest = json.loads(Path(second["offline_strategy_artifact_manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["paths"]["ranking_report_path"] == second["ranking_report_path"]
    assert manifest["paths"]["trade_audit_report_path"] == second["trade_audit_report_path"]
    dumped = json.dumps({"first": first, "second": second, "manifest": manifest, "comparison": second_comparison}, ensure_ascii=False).lower()
    assert "secretkey" not in dumped
    assert "authorization" not in dumped
    assert "\"token\"" not in dumped


def test_capture_and_train_wrapper_reports_partial_provider_limit(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path)
    token_store_root = tmp_path / "oauth_tokens"
    token_store_root.mkdir()
    token_ref_path = token_store_root / "mock_token.json"
    token_ref_path.write_text(
        """
        {
          "token": "REDACTED",
          "token_type": "Bearer",
          "expires_dt": "2099-01-01T00:00:00+00:00",
          "issued_at": "2026-06-27T00:00:00+00:00",
          "environment": "MOCK",
          "credential_fingerprint_redacted": "sha256:fixture"
        }
        """.strip(),
        encoding="utf-8",
    )

    class FakeRealTransport:
        transport_kind = HistoricalMarketDataTransportKind.REAL_KIWOOM_CHART

        def __init__(self, **kwargs):
            del kwargs
            self.calls = 0

        def execute(self, preview, *, auth_header=None):
            del auth_header
            self.calls += 1
            if self.calls == 1:
                return {
                    "status_code": 200,
                    "headers": {"cont-yn": "Y", "next-key": "PAGE2"},
                    "body_json": {
                        "return_code": 0,
                        "return_msg": "OK",
                        "stk_dt_pole_chart_qry": [
                            {"dt": "20260624", "open_pric": "81200", "high_pric": "81800", "low_pric": "81000", "cur_prc": "81600", "trde_qty": "1100000"}
                        ],
                    },
                }
            return {
                "status_code": 200,
                "headers": {"cont-yn": "N", "next-key": ""},
                "body_json": {"return_code": 5, "return_msg": "허용된 요청 개수를 초과하였습니다[1700:허용된 요청 개수를 초과하였습니다. API ID=ka10081]"},
            }

    def fake_issue(_request):
        return KiwoomOAuthTokenIssueResponse(
            status=KiwoomOAuthStatus.TOKEN_CACHE_HIT,
            token_type="Bearer",
            token_ref=KiwoomOAuthTokenRef(
                token_ref_path=str(token_ref_path),
                token_type="Bearer",
                expires_dt="2099-01-01T00:00:00+00:00",
                issued_at="2026-06-27T00:00:00+00:00",
                environment=KiwoomEnvironment.MOCK,
                credential_fingerprint_redacted="sha256:fixture",
            ),
            expires_dt="2099-01-01T00:00:00+00:00",
            issued_at="2026-06-27T00:00:00+00:00",
            return_msg_redacted="TOKEN_CACHE_HIT",
        )

    monkeypatch.setattr(wrapper_module, "issue_kiwoom_oauth_token", fake_issue)
    monkeypatch.setattr(wrapper_module, "RealKiwoomChartTransport", FakeRealTransport)
    monkeypatch.setattr(capture_runner_module, "is_pytest_runtime", lambda: False)
    monkeypatch.setattr(capture_guard_module, "is_pytest_runtime", lambda: False)

    result = wrapper_module.run_kiwoom_ka10081_capture_and_train(
        fixture.model_copy(update={"real_capture_config": fixture.real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART", "max_continuation_pages": 2})}),
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(token_store_root),
        training_output_root=str(tmp_path / "local_data" / "offline_strategy"),
        search_mode="SMOKE_SEARCH",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
    )
    assert result["status"] == "PARTIAL_CAPTURE_NO_TRAINING"
    assert result["provider_limit_hit"] is True
    assert result["provider_limit_despite_limiter"] is True
    assert result["partial_capture"] is True
    assert result["partial_symbols"] == ["005930"]
    assert result["completed_symbols"] == []
    assert result["tr_request_count"] == 2
    assert result["tr_rate_limit_profile"] == "CONSERVATIVE"
    assert Path(result["tr_rate_ledger_path"]).exists()
    assert Path(result["capture_state_path"]).exists()
    state = json.loads(Path(result["capture_state_path"]).read_text(encoding="utf-8"))
    assert state["provider_limit_hit"] is True
    assert state["partial_symbols"] == ["005930"]
    dumped = json.dumps(state, ensure_ascii=False).lower()
    assert "secretkey" not in dumped
    assert "authorization" not in dumped
    assert "\"token\"" not in dumped


def test_capture_and_train_wrapper_reuses_existing_raw_lake_without_provider_call(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path)
    _cached_raw_lake_file(tmp_path, fixture, "005930")
    called = {"value": False}

    class FakeRealTransport:
        transport_kind = HistoricalMarketDataTransportKind.REAL_KIWOOM_CHART

        def __init__(self, **kwargs):
            del kwargs

        def execute(self, preview, *, auth_header=None):
            del preview, auth_header
            called["value"] = True
            return {}

    monkeypatch.setattr(wrapper_module, "RealKiwoomChartTransport", FakeRealTransport)
    monkeypatch.setattr(capture_runner_module, "is_pytest_runtime", lambda: False)
    monkeypatch.setattr(capture_guard_module, "is_pytest_runtime", lambda: False)

    result = wrapper_module.run_kiwoom_ka10081_capture_and_train(
        fixture.model_copy(update={"real_capture_config": fixture.real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART"})}),
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(tmp_path / "oauth_tokens"),
        training_output_root=str(tmp_path / "local_data" / "offline_strategy"),
        reuse_existing_raw_lake=True,
        search_mode="SMOKE_SEARCH",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
    )
    assert result["status"] == "COMPLETED_WITH_CACHE"
    assert result["reused_from_cache"] == ["005930"]
    assert result["fetched_now"] == []
    assert called["value"] is False
    assert result["symbols_with_full_coverage"] == ["005930"]
    assert result["cache_coverage_gaps"] == []
    assert result["training_input_coverage_by_symbol"]["005930"] == "REUSED_FROM_CACHE_COMPLETED"
    assert Path(result["ranking_report_path"]).exists()


def test_capture_and_train_wrapper_partial_cache_is_not_completed_and_reports_coverage_gap(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path).model_copy(
        update={
            "request_specs": [
                _fixture(tmp_path).request_specs[0].model_copy(
                        update={
                            "request_id": "KA10081-005930-20200101-20260627",
                            "start_at": datetime.fromisoformat("2020-01-01T00:00:00+09:00"),
                            "end_at": datetime.fromisoformat("2026-06-27T23:59:59+09:00"),
                        }
                    )
                ]
            }
    )
    _cached_raw_lake_file(
        tmp_path,
        fixture,
        "005930",
        chart_rows=[
            {"dt": "20210729", "open_pric": "79000", "high_pric": "79500", "low_pric": "78500", "cur_prc": "79200", "trde_qty": "900000"},
            {"dt": "20240105", "open_pric": "78000", "high_pric": "78900", "low_pric": "77500", "cur_prc": "78600", "trde_qty": "850000"},
        ],
    )
    called = {"value": False}

    class FakeRealTransport:
        transport_kind = HistoricalMarketDataTransportKind.REAL_KIWOOM_CHART

        def __init__(self, **kwargs):
            del kwargs

        def execute(self, preview, *, auth_header=None):
            del preview, auth_header
            called["value"] = True
            return {}

    monkeypatch.setattr(wrapper_module, "RealKiwoomChartTransport", FakeRealTransport)
    monkeypatch.setattr(capture_runner_module, "is_pytest_runtime", lambda: False)
    monkeypatch.setattr(capture_guard_module, "is_pytest_runtime", lambda: False)

    result = wrapper_module.run_kiwoom_ka10081_capture_and_train(
        fixture.model_copy(update={"real_capture_config": fixture.real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART"})}),
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(tmp_path / "oauth_tokens"),
        training_output_root=str(tmp_path / "local_data" / "offline_strategy"),
        reuse_existing_raw_lake=True,
        allow_training_on_partial_capture=True,
        prefer_full_coverage_training=False,
        search_mode="SMOKE_SEARCH",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
    )
    assert result["status"] == "COMPLETED_WITH_PARTIAL_CACHE"
    assert result["completed_symbols"] == []
    assert result["partial_symbols"] == ["005930"]
    assert result["partial_cache_used"] is True
    assert result["cache_coverage_gaps"] == ["005930"]
    assert result["symbols_with_partial_coverage"] == ["005930"]
    assert result["symbol_results"][0]["status"] == "REUSED_FROM_CACHE_PARTIAL"
    assert result["symbol_results"][0]["leading_gap_days"] > 0
    assert result["symbol_results"][0]["calendar_trailing_gap_days"] > 0
    assert result["training_input_coverage_by_symbol"]["005930"] == "REUSED_FROM_CACHE_PARTIAL"
    assert called["value"] is False


def test_capture_and_train_wrapper_partial_cache_blocks_training_when_not_allowed(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path).model_copy(
        update={
            "request_specs": [
                _fixture(tmp_path).request_specs[0].model_copy(
                        update={
                            "request_id": "KA10081-005930-20200101-20260627",
                            "start_at": datetime.fromisoformat("2020-01-01T00:00:00+09:00"),
                            "end_at": datetime.fromisoformat("2026-06-27T23:59:59+09:00"),
                        }
                    )
                ]
            }
    )
    _cached_raw_lake_file(
        tmp_path,
        fixture,
        "005930",
        chart_rows=[
            {"dt": "20210729", "open_pric": "79000", "high_pric": "79500", "low_pric": "78500", "cur_prc": "79200", "trde_qty": "900000"},
            {"dt": "20240105", "open_pric": "78000", "high_pric": "78900", "low_pric": "77500", "cur_prc": "78600", "trde_qty": "850000"},
        ],
    )

    class FakeRealTransport:
        transport_kind = HistoricalMarketDataTransportKind.REAL_KIWOOM_CHART

        def __init__(self, **kwargs):
            del kwargs

        def execute(self, preview, *, auth_header=None):
            del preview, auth_header
            return {}

    monkeypatch.setattr(wrapper_module, "RealKiwoomChartTransport", FakeRealTransport)
    monkeypatch.setattr(capture_runner_module, "is_pytest_runtime", lambda: False)
    monkeypatch.setattr(capture_guard_module, "is_pytest_runtime", lambda: False)

    result = wrapper_module.run_kiwoom_ka10081_capture_and_train(
        fixture.model_copy(update={"real_capture_config": fixture.real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART"})}),
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(tmp_path / "oauth_tokens"),
        training_output_root=str(tmp_path / "local_data" / "offline_strategy"),
        reuse_existing_raw_lake=True,
        allow_training_on_partial_capture=False,
        search_mode="SMOKE_SEARCH",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
    )
    assert result["status"] == "PARTIAL_CAPTURE_NO_TRAINING"
    assert result["training_started"] is False
    assert result["training_completed"] is False
    assert result["partial_cache_used"] is True
    assert result["symbol_results"][0]["status"] == "REUSED_FROM_CACHE_PARTIAL"


def test_capture_and_train_wrapper_backfills_partial_cache_to_full_coverage(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path).model_copy(
        update={
            "request_specs": [
                _fixture(tmp_path).request_specs[0].model_copy(
                    update={
                        "request_id": "KA10081-005930-20200101-20260627",
                        "start_at": datetime.fromisoformat("2020-01-01T00:00:00+09:00"),
                        "end_at": datetime.fromisoformat("2026-06-27T23:59:59+09:00"),
                        "base_dt": "20260627",
                    }
                )
            ]
        }
    )
    _cached_raw_lake_file(
        tmp_path,
        fixture,
        "005930",
        chart_rows=[
            {"dt": "20210729", "open_pric": "79000", "high_pric": "79500", "low_pric": "78500", "cur_prc": "79200", "trde_qty": "900000"},
            {"dt": "20240105", "open_pric": "78000", "high_pric": "78900", "low_pric": "77500", "cur_prc": "78600", "trde_qty": "850000"},
        ],
    )
    token_ref_path = _token_ref_file(tmp_path)

    class FakeRealTransport:
        transport_kind = HistoricalMarketDataTransportKind.REAL_KIWOOM_CHART

        def __init__(self, **kwargs):
            del kwargs

        def execute(self, preview, *, auth_header=None):
            assert auth_header == "Bearer REDACTED"
            assert preview.body_json["base_dt"] == "20260627"
            return {
                "status_code": 200,
                "headers": {"cont-yn": "N", "next-key": ""},
                "body_json": {
                    "return_code": 0,
                    "return_msg": "OK",
                    "stk_cd": preview.body_json["stk_cd"],
                    "stk_dt_pole_chart_qry": [
                        {"dt": "20200101", "open_pric": "56000", "high_pric": "56500", "low_pric": "55000", "cur_prc": "55800", "trde_qty": "1200000"},
                        {"dt": "20260627", "open_pric": "90000", "high_pric": "90500", "low_pric": "89500", "cur_prc": "90200", "trde_qty": "1500000"},
                    ],
                },
            }

    def fake_issue(_request):
        return KiwoomOAuthTokenIssueResponse(
            status=KiwoomOAuthStatus.TOKEN_CACHE_HIT,
            token_type="Bearer",
            token_ref=KiwoomOAuthTokenRef(
                token_ref_path=str(token_ref_path),
                token_type="Bearer",
                expires_dt="2099-01-01T00:00:00+00:00",
                issued_at="2026-06-27T00:00:00+00:00",
                environment=KiwoomEnvironment.MOCK,
                credential_fingerprint_redacted="sha256:fixture",
            ),
            expires_dt="2099-01-01T00:00:00+00:00",
            issued_at="2026-06-27T00:00:00+00:00",
            return_msg_redacted="TOKEN_CACHE_HIT",
        )

    monkeypatch.setattr(wrapper_module, "issue_kiwoom_oauth_token", fake_issue)
    monkeypatch.setattr(wrapper_module, "RealKiwoomChartTransport", FakeRealTransport)
    monkeypatch.setattr(capture_runner_module, "is_pytest_runtime", lambda: False)
    monkeypatch.setattr(capture_guard_module, "is_pytest_runtime", lambda: False)

    result = wrapper_module.run_kiwoom_ka10081_capture_and_train(
        fixture.model_copy(update={"real_capture_config": fixture.real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART"})}),
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(tmp_path / "oauth_tokens"),
        training_output_root=str(tmp_path / "local_data" / "offline_strategy"),
        reuse_existing_raw_lake=True,
        resume_from_capture_state=str(tmp_path / "resume_state.json"),
        backfill_cache_gaps=True,
        max_backfill_pages_per_symbol=1,
        prefer_full_coverage_training=True,
        search_mode="SMOKE_SEARCH",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
    )
    assert result["status"] == "COMPLETED_WITH_BACKFILL"
    assert result["symbol_results"][0]["status"] == "BACKFILL_COMPLETED"
    assert result["symbol_results"][0]["post_backfill_coverage_status"] == "FULL_TRADING_COVERAGE"
    assert result["full_coverage_symbols"] == ["005930"]
    assert result["training_input_symbols"] == ["005930"]
    assert result["training_on_partial_coverage"] is False
    assert result["training_input_coverage_basis_by_symbol"]["005930"] == "TRADING_DAYS"
    assert result["tr_request_count"] == 1


def test_capture_and_train_wrapper_backfill_provider_limit_blocks_full_coverage_training(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path).model_copy(
        update={
            "request_specs": [
                _fixture(tmp_path).request_specs[0].model_copy(
                    update={
                        "request_id": "KA10081-005930-20200101-20260627",
                        "start_at": datetime.fromisoformat("2020-01-01T00:00:00+09:00"),
                        "end_at": datetime.fromisoformat("2026-06-27T23:59:59+09:00"),
                        "base_dt": "20260627",
                    }
                )
            ]
        }
    )
    _cached_raw_lake_file(
        tmp_path,
        fixture,
        "005930",
        chart_rows=[
            {"dt": "20210729", "open_pric": "79000", "high_pric": "79500", "low_pric": "78500", "cur_prc": "79200", "trde_qty": "900000"},
            {"dt": "20240105", "open_pric": "78000", "high_pric": "78900", "low_pric": "77500", "cur_prc": "78600", "trde_qty": "850000"},
        ],
    )
    token_ref_path = _token_ref_file(tmp_path)

    class FakeRealTransport:
        transport_kind = HistoricalMarketDataTransportKind.REAL_KIWOOM_CHART

        def __init__(self, **kwargs):
            del kwargs

        def execute(self, preview, *, auth_header=None):
            assert auth_header == "Bearer REDACTED"
            return {
                "status_code": 200,
                "headers": {"cont-yn": "N", "next-key": ""},
                "body_json": {
                    "return_code": 5,
                    "return_msg": "허용된 요청 개수를 초과하였습니다[1700:허용된 요청 개수를 초과하였습니다. API ID=ka10081]",
                    "stk_cd": preview.body_json["stk_cd"],
                    "stk_dt_pole_chart_qry": [
                        {"dt": "20260627", "open_pric": "90000", "high_pric": "90500", "low_pric": "89500", "cur_prc": "90200", "trde_qty": "1500000"},
                    ],
                },
            }

    def fake_issue(_request):
        return KiwoomOAuthTokenIssueResponse(
            status=KiwoomOAuthStatus.TOKEN_CACHE_HIT,
            token_type="Bearer",
            token_ref=KiwoomOAuthTokenRef(
                token_ref_path=str(token_ref_path),
                token_type="Bearer",
                expires_dt="2099-01-01T00:00:00+00:00",
                issued_at="2026-06-27T00:00:00+00:00",
                environment=KiwoomEnvironment.MOCK,
                credential_fingerprint_redacted="sha256:fixture",
            ),
            expires_dt="2099-01-01T00:00:00+00:00",
            issued_at="2026-06-27T00:00:00+00:00",
            return_msg_redacted="TOKEN_CACHE_HIT",
        )

    monkeypatch.setattr(wrapper_module, "issue_kiwoom_oauth_token", fake_issue)
    monkeypatch.setattr(wrapper_module, "RealKiwoomChartTransport", FakeRealTransport)
    monkeypatch.setattr(capture_runner_module, "is_pytest_runtime", lambda: False)
    monkeypatch.setattr(capture_guard_module, "is_pytest_runtime", lambda: False)

    result = wrapper_module.run_kiwoom_ka10081_capture_and_train(
        fixture.model_copy(update={"real_capture_config": fixture.real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART"})}),
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(tmp_path / "oauth_tokens"),
        training_output_root=str(tmp_path / "local_data" / "offline_strategy"),
        reuse_existing_raw_lake=True,
        resume_from_capture_state=str(tmp_path / "resume_state.json"),
        backfill_cache_gaps=True,
        prefer_full_coverage_training=True,
        allow_training_on_partial_capture=False,
        search_mode="SMOKE_SEARCH",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
    )
    assert result["status"] == "PARTIAL_BACKFILL_PROVIDER_LIMIT"
    assert result["provider_limit_hit"] is True
    assert result["symbol_results"][0]["status"] == "BACKFILL_PARTIAL"
    assert result["training_input_symbols"] == []
    assert result["training_on_partial_coverage"] is False


def test_calendar_edge_only_gap_is_full_trading_coverage(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path).model_copy(
        update={
            "request_specs": [
                _fixture(tmp_path).request_specs[0].model_copy(
                    update={
                        "request_id": "KA10081-005930-20200101-20260627",
                        "start_at": datetime.fromisoformat("2020-01-01T00:00:00+09:00"),
                        "end_at": datetime.fromisoformat("2026-06-27T23:59:59+09:00"),
                    }
                )
            ]
        }
    )
    _cached_raw_lake_file(
        tmp_path,
        fixture,
        "005930",
        chart_rows=[
            {"dt": "20200102", "open_pric": "56000", "high_pric": "56500", "low_pric": "55000", "cur_prc": "55800", "trde_qty": "1200000"},
            {"dt": "20260626", "open_pric": "90000", "high_pric": "90500", "low_pric": "89500", "cur_prc": "90200", "trde_qty": "1500000"},
        ],
    )

    class FakeRealTransport:
        transport_kind = HistoricalMarketDataTransportKind.REAL_KIWOOM_CHART

        def __init__(self, **kwargs):
            del kwargs

        def execute(self, preview, *, auth_header=None):
            raise AssertionError("calendar-edge-only gap should not trigger backfill")

    monkeypatch.setattr(wrapper_module, "RealKiwoomChartTransport", FakeRealTransport)
    monkeypatch.setattr(capture_runner_module, "is_pytest_runtime", lambda: False)
    monkeypatch.setattr(capture_guard_module, "is_pytest_runtime", lambda: False)

    result = wrapper_module.run_kiwoom_ka10081_capture_and_train(
        fixture.model_copy(update={"real_capture_config": fixture.real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART"})}),
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(tmp_path / "oauth_tokens"),
        training_output_root=str(tmp_path / "local_data" / "offline_strategy"),
        reuse_existing_raw_lake=True,
        backfill_cache_gaps=True,
        prefer_full_coverage_training=True,
        search_mode="SMOKE_SEARCH",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
    )
    assert result["status"] == "COMPLETED_WITH_CACHE"
    assert result["symbol_results"][0]["status"] == "REUSED_FROM_CACHE_COMPLETED"
    assert result["symbol_results"][0]["cache_coverage_status"] == "CALENDAR_EDGE_GAP_ONLY"
    assert result["training_input_symbols"] == ["005930"]
    assert result["training_input_coverage_basis_by_symbol"]["005930"] == "TRADING_DAYS"


def test_actual_weekday_gap_remains_trading_coverage_gap(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path).model_copy(
        update={
            "request_specs": [
                _fixture(tmp_path).request_specs[0].model_copy(
                    update={
                        "request_id": "KA10081-005930-20200102-20200108",
                        "start_at": datetime.fromisoformat("2020-01-02T00:00:00+09:00"),
                        "end_at": datetime.fromisoformat("2020-01-08T23:59:59+09:00"),
                    }
                )
            ]
        }
    )
    _cached_raw_lake_file(
        tmp_path,
        fixture,
        "005930",
        chart_rows=[
            {"dt": "20200103", "open_pric": "56000", "high_pric": "56500", "low_pric": "55000", "cur_prc": "55800", "trde_qty": "1200000"},
            {"dt": "20200108", "open_pric": "57000", "high_pric": "57500", "low_pric": "56800", "cur_prc": "57200", "trde_qty": "1300000"},
        ],
    )

    class FakeRealTransport:
        transport_kind = HistoricalMarketDataTransportKind.REAL_KIWOOM_CHART

        def __init__(self, **kwargs):
            del kwargs

        def execute(self, preview, *, auth_header=None):
            del preview, auth_header
            return {}

    monkeypatch.setattr(wrapper_module, "RealKiwoomChartTransport", FakeRealTransport)
    monkeypatch.setattr(capture_runner_module, "is_pytest_runtime", lambda: False)
    monkeypatch.setattr(capture_guard_module, "is_pytest_runtime", lambda: False)

    result = wrapper_module.run_kiwoom_ka10081_capture_and_train(
        fixture.model_copy(update={"real_capture_config": fixture.real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART"})}),
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(tmp_path / "oauth_tokens"),
        training_output_root=str(tmp_path / "local_data" / "offline_strategy"),
        reuse_existing_raw_lake=True,
        allow_training_on_partial_capture=True,
        prefer_full_coverage_training=False,
        search_mode="SMOKE_SEARCH",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
    )
    assert result["symbol_results"][0]["cache_coverage_status"] == "TRADING_COVERAGE_GAP"
    assert result["symbol_results"][0]["trading_leading_gap_days"] == 1


def test_watchlist_txt_csv_json_parsing_and_merge(tmp_path) -> None:
    txt_path = tmp_path / "symbols.txt"
    txt_path.write_text("005930\n000660\n", encoding="utf-8")
    csv_path = tmp_path / "symbols.csv"
    csv_path.write_text("symbol,name,sector,priority\n035420,NAVER,IT,1\n005930,Samsung,Tech,2\n", encoding="utf-8")
    json_path = tmp_path / "symbols.json"
    json_path.write_text(json.dumps(["051910", {"symbol": "035720", "name": "Kakao"}]), encoding="utf-8")
    txt_entries = batch_runner_module.load_watchlist_symbols(str(txt_path))
    csv_entries = batch_runner_module.load_watchlist_symbols(str(csv_path))
    json_entries = batch_runner_module.load_watchlist_symbols(str(json_path))
    merged = batch_runner_module.merge_symbol_sources(["000660", "035420"], txt_entries + csv_entries + json_entries)
    assert [item["symbol"] for item in txt_entries] == ["005930", "000660"]
    assert [item["symbol"] for item in csv_entries] == ["035420", "005930"]
    assert [item["symbol"] for item in json_entries] == ["051910", "035720"]
    assert merged == ["000660", "035420", "005930", "051910", "035720"]


def test_watchlist_20_symbol_sample_parses_correctly() -> None:
    sample_path = Path("/home/yoonkeun/stocks/examples/kiwoom_watchlist_20_sample.csv")
    entries = batch_runner_module.load_watchlist_symbols(str(sample_path))
    assert len(entries) == 20
    assert entries[0]["symbol"] == "005930"
    assert entries[0]["name"] == "Samsung Electronics"
    assert entries[0]["sector"] == "Semiconductor"
    assert entries[0]["priority"] == "1"
    assert entries[-1]["symbol"] == "028260"


def test_watchlist_batch_splitting_and_resume_summary(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path).model_copy(
        update={
            "request_specs": _fixture(tmp_path).request_specs
            + [
                _fixture(tmp_path).request_specs[0].model_copy(
                    update={"request_id": "KA10081-000660-TEST", "provider_symbol": "000660", "canonical_instrument_id": "000660"}
                ),
                _fixture(tmp_path).request_specs[0].model_copy(
                    update={"request_id": "KA10081-035420-TEST", "provider_symbol": "035420", "canonical_instrument_id": "035420"}
                ),
            ]
        }
    )

    def fake_run(_pipeline, **kwargs):
        del kwargs
        state_path = tmp_path / f"{_pipeline.dataset_id.lower()}-state.json"
        state_path.write_text(
            json.dumps({"requested_symbols": [spec.provider_symbol for spec in _pipeline.request_specs]}),
            encoding="utf-8",
        )
        return {
            "status": "COMPLETED_WITH_PROVIDER_LIMIT",
            "provider_limit_hit": True,
            "can_resume": True,
            "capture_state_path": str(state_path),
            "capture_state_root": str(tmp_path),
            "dataset_id": _pipeline.dataset_id,
            "dataset_symbols": [spec.provider_symbol for spec in _pipeline.request_specs],
            "completed_symbols": [_pipeline.request_specs[0].provider_symbol],
            "full_coverage_symbols": [_pipeline.request_specs[0].provider_symbol],
            "partial_symbols": [],
            "failed_symbols": [],
            "skipped_symbols": [],
            "symbol_results": [
                {
                    "requested_symbol": _pipeline.request_specs[0].provider_symbol,
                    "cache_coverage_status": "FULL_TRADING_COVERAGE",
                    "post_backfill_coverage_status": "FULL_TRADING_COVERAGE",
                    "trading_coverage_ratio": 1.0,
                }
            ],
            "reused_from_cache": [],
            "fetched_now": [_pipeline.request_specs[0].provider_symbol],
            "backfilled_symbols": [],
            "manifest_path": "manifest.json",
            "per_symbol_row_count": {_pipeline.request_specs[0].provider_symbol: 10},
            "per_symbol_date_min": {_pipeline.request_specs[0].provider_symbol: "2020-01-02"},
            "per_symbol_date_max": {_pipeline.request_specs[0].provider_symbol: "2026-06-26"},
            "per_symbol_coverage_status": {_pipeline.request_specs[0].provider_symbol: "FULL_TRADING_COVERAGE"},
            "per_symbol_coverage_basis": {_pipeline.request_specs[0].provider_symbol: "TRADING_DAYS"},
            "excluded_symbols": [],
            "exclusion_reasons": {},
        }

    monkeypatch.setattr(batch_runner_module, "run_kiwoom_ka10081_capture_and_train", fake_run)
    result = batch_runner_module.run_kiwoom_watchlist_capture_and_train(
        fixture,
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(tmp_path / "oauth_tokens"),
        training_output_root=str(tmp_path / "offline"),
        training_handoff_mode="persisted_manifest",
        requested_template_ids=[],
        asset_liquidity_profile="LARGE_CAP",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
        search_mode="SMOKE_SEARCH",
        walk_forward_mode="ANCHORED_CHRONOLOGICAL_WALK_FORWARD",
        promotion_profile="STABILITY_FIRST",
        fill_policy="CONSERVERVATIVE_NEXT_BAR_FILL",
        direction="LONG_ONLY",
        request_sleep_seconds=0.25,
        symbol_sleep_seconds=0.5,
        max_symbols_per_run=0,
        stop_on_provider_limit=True,
        resume_from_capture_state=None,
        reuse_existing_raw_lake=True,
        allow_training_on_partial_capture=False,
        backfill_cache_gaps=True,
        max_backfill_pages_per_symbol=None,
        prefer_full_coverage_training=True,
        symbols=["005930", "000660", "035420"],
        symbols_file="examples/kiwoom_watchlist_sample.txt",
        batch_size=2,
        batch_index=1,
        max_batches=None,
        resume_all=False,
        capture_state_root=str(tmp_path / "capture_state"),
    )
    assert result["total_requested_symbols"] == 3
    assert result["batch_size"] == 2
    assert result["batch_index"] == 1
    assert result["batch_symbols"] == ["005930", "000660"]
    assert "resume-from-capture-state" in result["next_resume_command"]
    assert Path(result["watchlist_progress_path"]).exists()
    ledger = json.loads(Path(result["watchlist_progress_path"]).read_text(encoding="utf-8"))
    assert ledger["pending_symbols"] == ["000660", "035420"]
    assert ledger["skipped_symbols"] == []
    assert "resume-all" not in ledger["next_resume_command"]
    assert result["batch_identity_status"] == "BATCH_IDENTITY_OK"
    assert result["ledger_validation_status"] == "LEDGER_VALIDATION_OK"
    assert result["coverage_consistency_status"] == "COVERAGE_CONSISTENCY_OK"
    assert result["total_batches"] == 2
    assert result["completed_batches"] == 1
    assert result["pending_batches"] == 1
    assert result["watchlist_completion_ratio"] == 0.333333
    assert result["full_coverage_ratio"] == 0.333333
    ranking_payload = json.loads(Path(result["aggregate_ranking_report_path"]).read_text(encoding="utf-8"))
    assert {row["symbol"] for row in ranking_payload["rows"]} == {"005930", "000660", "035420"}
    assert any(row["symbol"] == "000660" and row["ranking_available"] is False for row in ranking_payload["rows"])
    assert any(row["symbol"] == "000660" and row["ranking_missing_reason"] for row in ranking_payload["rows"])
    assert any("rank_score" in row and "rank_score_components" in row for row in ranking_payload["rows"])
    ranking_summary = json.loads(Path(result["aggregate_ranking_summary_path"]).read_text(encoding="utf-8"))
    assert "best_candidate_by_symbol" in ranking_summary
    assert "best_diagnostic_candidate_by_symbol" in ranking_summary
    assert "rejected_count_by_reason" in ranking_summary
    assert "promotion_status_count" in ranking_summary
    assert "promoted_count_by_symbol" in ranking_summary
    assert "promoted_count_by_family" in ranking_summary
    assert "leakage_audit_status" in ranking_summary
    assert "same_bar_fill_count" in ranking_summary
    assert "lookahead_violation_count" in ranking_summary
    assert "drawdown_sanity_warning_count" in ranking_summary
    assert "ranking_available_symbol_count" in ranking_summary
    assert "ranking_missing_symbol_count" in ranking_summary
    assert result["watchlist_ranking_summary_path"] == result["aggregate_ranking_summary_path"]
    assert Path(result["watchlist_ranking_summary_path"]).exists()
    assert Path(result["offline_strategy_artifact_manifest_path"]).exists()
    assert result["offline_strategy_output_root"] != str(tmp_path / "offline")
    assert "estimated_tr_requests_remaining" in result
    assert "estimated_seconds_remaining_at_current_rate" in result
    assert "estimated_minutes_remaining_at_current_rate" in result
    assert "tr_request_count_this_run" in result
    assert "tr_request_count_last_hour" in result


def test_watchlist_resume_all_retries_pending_before_later_batches(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path).model_copy(
        update={
            "request_specs": _fixture(tmp_path).request_specs
            + [
                _fixture(tmp_path).request_specs[0].model_copy(
                    update={"request_id": "KA10081-000660-TEST", "provider_symbol": "000660", "canonical_instrument_id": "000660"}
                ),
                _fixture(tmp_path).request_specs[0].model_copy(
                    update={"request_id": "KA10081-035420-TEST", "provider_symbol": "035420", "canonical_instrument_id": "035420"}
                ),
                _fixture(tmp_path).request_specs[0].model_copy(
                    update={"request_id": "KA10081-035720-TEST", "provider_symbol": "035720", "canonical_instrument_id": "035720"}
                ),
            ]
        }
    )
    seen_batches: list[list[str]] = []
    batch1_calls = 0

    def fake_run(_pipeline, **kwargs):
        nonlocal batch1_calls
        del kwargs
        batch_symbols = [spec.provider_symbol for spec in _pipeline.request_specs]
        seen_batches.append(batch_symbols)
        state_path = tmp_path / f"{_pipeline.dataset_id.lower()}-state.json"
        state_path.write_text(json.dumps({"requested_symbols": batch_symbols}), encoding="utf-8")
        if batch_symbols == ["005930", "000660"]:
            batch1_calls += 1
            if batch1_calls == 1:
                return {
                    "status": "COMPLETED_WITH_PROVIDER_LIMIT",
                    "provider_limit_hit": True,
                    "can_resume": True,
                    "capture_state_path": str(state_path),
                    "capture_state_root": str(tmp_path),
                    "dataset_id": _pipeline.dataset_id,
                    "dataset_symbols": batch_symbols,
                    "completed_symbols": ["005930"],
                    "full_coverage_symbols": ["005930"],
                    "partial_symbols": [],
                    "failed_symbols": [],
                    "skipped_symbols": ["000660"],
                    "symbol_results": [
                        {
                            "requested_symbol": "005930",
                            "cache_coverage_status": "FULL_TRADING_COVERAGE",
                            "post_backfill_coverage_status": "FULL_TRADING_COVERAGE",
                            "trading_coverage_ratio": 1.0,
                        }
                    ],
                    "reused_from_cache": [],
                    "fetched_now": ["005930"],
                    "backfilled_symbols": [],
                    "ranking_report_path": str(tmp_path / "batch1-ranking.json"),
                    "manifest_path": "manifest.json",
                    "per_symbol_row_count": {"005930": 10},
                    "per_symbol_date_min": {"005930": "2020-01-02"},
                    "per_symbol_date_max": {"005930": "2026-06-26"},
                    "per_symbol_coverage_status": {"005930": "FULL_TRADING_COVERAGE"},
                    "per_symbol_coverage_basis": {"005930": "TRADING_DAYS"},
                    "excluded_symbols": ["000660"],
                    "exclusion_reasons": {"000660": "SKIPPED_OR_NOT_CAPTURED"},
                }
            return {
                "status": "COMPLETED",
                "provider_limit_hit": False,
                "can_resume": False,
                "capture_state_path": str(state_path),
                "capture_state_root": str(tmp_path),
                "dataset_id": _pipeline.dataset_id,
                "dataset_symbols": batch_symbols,
                "completed_symbols": batch_symbols,
                "full_coverage_symbols": batch_symbols,
                "partial_symbols": [],
                "failed_symbols": [],
                "skipped_symbols": [],
                "symbol_results": [
                    {
                        "requested_symbol": symbol,
                        "cache_coverage_status": "FULL_TRADING_COVERAGE",
                        "post_backfill_coverage_status": "FULL_TRADING_COVERAGE",
                        "trading_coverage_ratio": 1.0,
                    }
                    for symbol in batch_symbols
                ],
                "reused_from_cache": [],
                "fetched_now": batch_symbols,
                "backfilled_symbols": [],
                "ranking_report_path": str(tmp_path / "batch1-ranking.json"),
                "manifest_path": "manifest.json",
                "per_symbol_row_count": {symbol: 10 for symbol in batch_symbols},
                "per_symbol_date_min": {symbol: "2020-01-02" for symbol in batch_symbols},
                "per_symbol_date_max": {symbol: "2026-06-26" for symbol in batch_symbols},
                "per_symbol_coverage_status": {symbol: "FULL_TRADING_COVERAGE" for symbol in batch_symbols},
                "per_symbol_coverage_basis": {symbol: "TRADING_DAYS" for symbol in batch_symbols},
                "excluded_symbols": [],
                "exclusion_reasons": {},
            }
        return {
            "status": "COMPLETED",
            "provider_limit_hit": False,
            "can_resume": False,
            "capture_state_path": str(state_path),
            "capture_state_root": str(tmp_path),
            "dataset_id": _pipeline.dataset_id,
            "dataset_symbols": batch_symbols,
            "completed_symbols": batch_symbols,
            "full_coverage_symbols": batch_symbols,
            "partial_symbols": [],
            "failed_symbols": [],
            "skipped_symbols": [],
            "symbol_results": [
                {
                    "requested_symbol": symbol,
                    "cache_coverage_status": "FULL_TRADING_COVERAGE",
                    "post_backfill_coverage_status": "FULL_TRADING_COVERAGE",
                    "trading_coverage_ratio": 1.0,
                }
                for symbol in batch_symbols
            ],
            "reused_from_cache": [],
            "fetched_now": batch_symbols,
            "backfilled_symbols": [],
            "ranking_report_path": str(tmp_path / f"{'-'.join(batch_symbols)}-ranking.json"),
            "manifest_path": "manifest.json",
            "per_symbol_row_count": {symbol: 10 for symbol in batch_symbols},
            "per_symbol_date_min": {symbol: "2020-01-02" for symbol in batch_symbols},
            "per_symbol_date_max": {symbol: "2026-06-26" for symbol in batch_symbols},
            "per_symbol_coverage_status": {symbol: "FULL_TRADING_COVERAGE" for symbol in batch_symbols},
            "per_symbol_coverage_basis": {symbol: "TRADING_DAYS" for symbol in batch_symbols},
            "excluded_symbols": [],
            "exclusion_reasons": {},
        }

    (tmp_path / "batch1-ranking.json").write_text(json.dumps({"rows": []}), encoding="utf-8")
    (tmp_path / "035420-035720-ranking.json").write_text(json.dumps({"rows": []}), encoding="utf-8")
    monkeypatch.setattr(batch_runner_module, "run_kiwoom_ka10081_capture_and_train", fake_run)

    first = batch_runner_module.run_kiwoom_watchlist_capture_and_train(
        fixture,
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(tmp_path / "oauth_tokens"),
        training_output_root=str(tmp_path / "offline"),
        training_handoff_mode="persisted_manifest",
        requested_template_ids=[],
        asset_liquidity_profile="LARGE_CAP",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
        search_mode="SMOKE_SEARCH",
        walk_forward_mode="ANCHORED_CHRONOLOGICAL_WALK_FORWARD",
        promotion_profile="STABILITY_FIRST",
        fill_policy="CONSERVATIVE_NEXT_BAR_FILL",
        direction="LONG_ONLY",
        request_sleep_seconds=0.25,
        symbol_sleep_seconds=0.5,
        max_symbols_per_run=0,
        stop_on_provider_limit=True,
        resume_from_capture_state=None,
        reuse_existing_raw_lake=True,
        allow_training_on_partial_capture=False,
        backfill_cache_gaps=True,
        max_backfill_pages_per_symbol=None,
        prefer_full_coverage_training=True,
        symbols=["005930", "000660", "035420", "035720"],
        symbols_file="examples/kiwoom_watchlist_sample.txt",
        batch_size=2,
        batch_index=1,
        max_batches=None,
        resume_all=False,
        capture_state_root=str(tmp_path / "capture_state"),
    )
    second = batch_runner_module.run_kiwoom_watchlist_capture_and_train(
        fixture,
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(tmp_path / "oauth_tokens"),
        training_output_root=str(tmp_path / "offline"),
        training_handoff_mode="persisted_manifest",
        requested_template_ids=[],
        asset_liquidity_profile="LARGE_CAP",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
        search_mode="SMOKE_SEARCH",
        walk_forward_mode="ANCHORED_CHRONOLOGICAL_WALK_FORWARD",
        promotion_profile="STABILITY_FIRST",
        fill_policy="CONSERVATIVE_NEXT_BAR_FILL",
        direction="LONG_ONLY",
        request_sleep_seconds=0.25,
        symbol_sleep_seconds=0.5,
        max_symbols_per_run=0,
        stop_on_provider_limit=True,
        resume_from_capture_state=str(tmp_path / "batch1-state.json"),
        reuse_existing_raw_lake=True,
        allow_training_on_partial_capture=False,
        backfill_cache_gaps=True,
        max_backfill_pages_per_symbol=None,
        prefer_full_coverage_training=True,
        symbols=["005930", "000660", "035420", "035720"],
        symbols_file="examples/kiwoom_watchlist_sample.txt",
        batch_size=2,
        batch_index=1,
        max_batches=None,
        resume_all=True,
        capture_state_root=str(tmp_path / "capture_state"),
    )
    assert seen_batches[0] == ["005930", "000660"]
    assert seen_batches[1] == ["005930", "000660"]
    assert seen_batches[2] == ["035420", "035720"]
    assert second["watchlist_status"] == "WATCHLIST_COMPLETED"
    assert second["resume_all"] is True
    assert second["next_resume_command"] is None
    ledger = json.loads(Path(second["watchlist_progress_path"]).read_text(encoding="utf-8"))
    batch1_state = json.loads(Path(ledger["capture_state_paths_by_batch"]["001"]).read_text(encoding="utf-8"))
    batch2_state = json.loads(Path(ledger["capture_state_paths_by_batch"]["002"]).read_text(encoding="utf-8"))
    assert batch1_state["requested_symbols"] == ["005930", "000660"]
    assert batch2_state["requested_symbols"] == ["035420", "035720"]
    assert ledger["batch_identity_status"] == "BATCH_IDENTITY_OK"
    assert second["next_retry_batch_label"] is None


def test_watchlist_20_symbol_resume_all_preserves_batch_labels(tmp_path, monkeypatch) -> None:
    sample_entries = batch_runner_module.load_watchlist_symbols("/home/yoonkeun/stocks/examples/kiwoom_watchlist_20_sample.csv")
    sample_symbols = [entry["symbol"] for entry in sample_entries]
    base_fixture = _fixture(tmp_path)
    spec_template = base_fixture.request_specs[0]
    fixture = base_fixture.model_copy(
        update={
            "request_specs": [
                spec_template.model_copy(
                    update={
                        "request_id": f"KA10081-{symbol}-TEST",
                        "provider_symbol": symbol,
                        "canonical_instrument_id": symbol,
                    }
                )
                for symbol in sample_symbols
            ]
        }
    )
    seen_batches: list[list[str]] = []
    call_count_by_batch: dict[tuple[str, ...], int] = {}

    def fake_run(_pipeline, **kwargs):
        del kwargs
        batch_symbols = [spec.provider_symbol for spec in _pipeline.request_specs]
        seen_batches.append(batch_symbols)
        batch_key = tuple(batch_symbols)
        call_count_by_batch[batch_key] = call_count_by_batch.get(batch_key, 0) + 1
        batch_index = int(_pipeline.dataset_id.split("-BATCH-")[1].split("-")[0])
        state_path = tmp_path / f"{_pipeline.dataset_id.lower()}-state.json"
        ranking_path = tmp_path / f"{_pipeline.dataset_id.lower()}-ranking-{call_count_by_batch[batch_key]}.json"
        ranking_path.write_text(json.dumps({"rows": []}), encoding="utf-8")
        state_path.write_text(json.dumps({"requested_symbols": batch_symbols}), encoding="utf-8")
        if batch_index == 1 and call_count_by_batch[batch_key] == 1:
            completed_symbol = batch_symbols[0]
            return {
                "status": "COMPLETED_WITH_PROVIDER_LIMIT",
                "provider_limit_hit": True,
                "can_resume": True,
                "capture_state_path": str(state_path),
                "capture_state_root": str(tmp_path),
                "dataset_id": _pipeline.dataset_id,
                "dataset_symbols": batch_symbols,
                "completed_symbols": [completed_symbol],
                "full_coverage_symbols": [completed_symbol],
                "partial_symbols": [],
                "failed_symbols": [],
                "skipped_symbols": [symbol for symbol in batch_symbols if symbol != completed_symbol],
                "symbol_results": [
                    {
                        "requested_symbol": completed_symbol,
                        "cache_coverage_status": "FULL_TRADING_COVERAGE",
                        "post_backfill_coverage_status": "FULL_TRADING_COVERAGE",
                        "trading_coverage_ratio": 1.0,
                    }
                ],
                "reused_from_cache": [],
                "fetched_now": [completed_symbol],
                "backfilled_symbols": [],
                "ranking_report_path": str(ranking_path),
                "manifest_path": "manifest.json",
                "per_symbol_row_count": {completed_symbol: 10},
                "per_symbol_date_min": {completed_symbol: "2020-01-02"},
                "per_symbol_date_max": {completed_symbol: "2026-06-26"},
                "per_symbol_coverage_status": {completed_symbol: "FULL_TRADING_COVERAGE"},
                "per_symbol_coverage_basis": {completed_symbol: "TRADING_DAYS"},
                "excluded_symbols": [symbol for symbol in batch_symbols if symbol != completed_symbol],
                "exclusion_reasons": {symbol: "SKIPPED_OR_NOT_CAPTURED" for symbol in batch_symbols if symbol != completed_symbol},
            }
        return {
            "status": "COMPLETED",
            "provider_limit_hit": False,
            "can_resume": False,
            "capture_state_path": str(state_path),
            "capture_state_root": str(tmp_path),
            "dataset_id": _pipeline.dataset_id,
            "dataset_symbols": batch_symbols,
            "completed_symbols": batch_symbols,
            "full_coverage_symbols": batch_symbols,
            "partial_symbols": [],
            "failed_symbols": [],
            "skipped_symbols": [],
            "symbol_results": [
                {
                    "requested_symbol": symbol,
                    "cache_coverage_status": "FULL_TRADING_COVERAGE",
                    "post_backfill_coverage_status": "FULL_TRADING_COVERAGE",
                    "trading_coverage_ratio": 1.0,
                }
                for symbol in batch_symbols
            ],
            "reused_from_cache": [],
            "fetched_now": batch_symbols,
            "backfilled_symbols": [],
            "ranking_report_path": str(ranking_path),
            "manifest_path": "manifest.json",
            "per_symbol_row_count": {symbol: 10 for symbol in batch_symbols},
            "per_symbol_date_min": {symbol: "2020-01-02" for symbol in batch_symbols},
            "per_symbol_date_max": {symbol: "2026-06-26" for symbol in batch_symbols},
            "per_symbol_coverage_status": {symbol: "FULL_TRADING_COVERAGE" for symbol in batch_symbols},
            "per_symbol_coverage_basis": {symbol: "TRADING_DAYS" for symbol in batch_symbols},
            "excluded_symbols": [],
            "exclusion_reasons": {},
        }

    monkeypatch.setattr(batch_runner_module, "run_kiwoom_ka10081_capture_and_train", fake_run)
    first = batch_runner_module.run_kiwoom_watchlist_capture_and_train(
        fixture,
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(tmp_path / "oauth_tokens"),
        training_output_root=str(tmp_path / "offline"),
        training_handoff_mode="persisted_manifest",
        requested_template_ids=[],
        asset_liquidity_profile="LARGE_CAP",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
        search_mode="EXPANDED_SEARCH",
        walk_forward_mode="ANCHORED_CHRONOLOGICAL_WALK_FORWARD",
        promotion_profile="STABILITY_FIRST",
        fill_policy="CONSERVATIVE_NEXT_BAR_FILL",
        direction="LONG_ONLY",
        request_sleep_seconds=0.25,
        symbol_sleep_seconds=0.5,
        max_symbols_per_run=0,
        stop_on_provider_limit=True,
        resume_from_capture_state=None,
        reuse_existing_raw_lake=True,
        allow_training_on_partial_capture=False,
        backfill_cache_gaps=True,
        max_backfill_pages_per_symbol=None,
        prefer_full_coverage_training=True,
        symbols=sample_symbols,
        symbols_file="/home/yoonkeun/stocks/examples/kiwoom_watchlist_20_sample.csv",
        batch_size=3,
        batch_index=1,
        max_batches=None,
        resume_all=False,
        capture_state_root=str(tmp_path / "capture_state"),
    )
    second = batch_runner_module.run_kiwoom_watchlist_capture_and_train(
        fixture,
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(tmp_path / "oauth_tokens"),
        training_output_root=str(tmp_path / "offline"),
        training_handoff_mode="persisted_manifest",
        requested_template_ids=[],
        asset_liquidity_profile="LARGE_CAP",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
        search_mode="EXPANDED_SEARCH",
        walk_forward_mode="ANCHORED_CHRONOLOGICAL_WALK_FORWARD",
        promotion_profile="STABILITY_FIRST",
        fill_policy="CONSERVATIVE_NEXT_BAR_FILL",
        direction="LONG_ONLY",
        request_sleep_seconds=0.25,
        symbol_sleep_seconds=0.5,
        max_symbols_per_run=0,
        stop_on_provider_limit=True,
        resume_from_capture_state=str(tmp_path / "resume_state.json"),
        reuse_existing_raw_lake=True,
        allow_training_on_partial_capture=False,
        backfill_cache_gaps=True,
        max_backfill_pages_per_symbol=None,
        prefer_full_coverage_training=True,
        symbols=sample_symbols,
        symbols_file="/home/yoonkeun/stocks/examples/kiwoom_watchlist_20_sample.csv",
        batch_size=3,
        batch_index=1,
        max_batches=None,
        resume_all=True,
        capture_state_root=str(tmp_path / "capture_state"),
    )
    expected_batches = [sample_symbols[index : index + 3] for index in range(0, len(sample_symbols), 3)]
    assert seen_batches[0] == expected_batches[0]
    assert seen_batches[1] == expected_batches[0]
    assert seen_batches[2:] == expected_batches[1:]
    assert first["next_retry_batch_label"] == "001"
    assert second["batch_identity_status"] == "BATCH_IDENTITY_OK"
    assert second["watchlist_status"] == "WATCHLIST_COMPLETED"
    assert second["total_batches"] == len(expected_batches)
    assert second["pending_batches"] == 0


def test_watchlist_run_isolation_does_not_overwrite_previous_artifacts(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path).model_copy(
        update={
            "request_specs": _fixture(tmp_path).request_specs
            + [
                _fixture(tmp_path).request_specs[0].model_copy(
                    update={"request_id": "KA10081-000660-TEST", "provider_symbol": "000660", "canonical_instrument_id": "000660"}
                ),
            ]
        }
    )
    call_index = {"value": 0}

    def fake_run(_pipeline, **kwargs):
        del kwargs
        call_index["value"] += 1
        batch_symbols = [spec.provider_symbol for spec in _pipeline.request_specs]
        state_path = tmp_path / f"{_pipeline.dataset_id.lower()}-state-{call_index['value']}.json"
        ranking_path = tmp_path / f"{_pipeline.dataset_id.lower()}-ranking-{call_index['value']}.json"
        ranking_path.write_text(
            json.dumps(
                {
                    "rows": [
                        {
                            "symbol": batch_symbols[0],
                            "strategy_family": "RSI_OVERSOLD_REBOUND",
                            "candidate_id": f"CANDIDATE-{call_index['value']}",
                            "parameter_set_id": "P001",
                            "parameter_summary": "DEFAULT",
                            "promotion_status": "PROMOTED_OFFLINE_CANDIDATE",
                            "rank_score": 10.0 + call_index["value"],
                            "rejection_reasons": [],
                            "signal_count_before_filters": 1,
                            "entry_signal_count": 1,
                            "final_entry_condition_count": 1,
                            "missing_indicator_columns": [],
                            "same_bar_fill_count": 0,
                            "lookahead_violation_count": 0,
                            "drawdown_warning": False,
                            "leakage_audit_status": "LEAKAGE_AUDIT_PASSED",
                            "ranking_available": True,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        state_path.write_text(json.dumps({"requested_symbols": batch_symbols}), encoding="utf-8")
        return {
            "status": "COMPLETED",
            "provider_limit_hit": False,
            "can_resume": False,
            "capture_state_path": str(state_path),
            "capture_state_root": str(tmp_path),
            "dataset_id": _pipeline.dataset_id,
            "dataset_symbols": batch_symbols,
            "completed_symbols": batch_symbols,
            "full_coverage_symbols": batch_symbols,
            "partial_symbols": [],
            "failed_symbols": [],
            "skipped_symbols": [],
            "symbol_results": [
                {
                    "requested_symbol": symbol,
                    "cache_coverage_status": "FULL_TRADING_COVERAGE",
                    "post_backfill_coverage_status": "FULL_TRADING_COVERAGE",
                    "trading_coverage_ratio": 1.0,
                }
                for symbol in batch_symbols
            ],
            "reused_from_cache": [],
            "fetched_now": batch_symbols,
            "backfilled_symbols": [],
            "ranking_report_path": str(ranking_path),
            "manifest_path": "manifest.json",
            "per_symbol_row_count": {symbol: 10 for symbol in batch_symbols},
            "per_symbol_date_min": {symbol: "2020-01-02" for symbol in batch_symbols},
            "per_symbol_date_max": {symbol: "2026-06-26" for symbol in batch_symbols},
            "per_symbol_coverage_status": {symbol: "FULL_TRADING_COVERAGE" for symbol in batch_symbols},
            "per_symbol_coverage_basis": {symbol: "TRADING_DAYS" for symbol in batch_symbols},
            "excluded_symbols": [],
            "exclusion_reasons": {},
            "training_input_symbols": batch_symbols,
            "candidate_count": 1,
            "promotion_decision_count": 1,
            "leakage_audit_status": "LEAKAGE_AUDIT_PASSED",
        }

    monkeypatch.setattr(batch_runner_module, "run_kiwoom_ka10081_capture_and_train", fake_run)
    first = batch_runner_module.run_kiwoom_watchlist_capture_and_train(
        fixture,
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(tmp_path / "oauth_tokens"),
        training_output_root=str(tmp_path / "offline"),
        training_handoff_mode="persisted_manifest",
        requested_template_ids=[],
        asset_liquidity_profile="LARGE_CAP",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
        search_mode="EXPANDED_SEARCH",
        walk_forward_mode="ANCHORED_CHRONOLOGICAL_WALK_FORWARD",
        promotion_profile="STABILITY_FIRST",
        fill_policy="CONSERVATIVE_NEXT_BAR_FILL",
        direction="LONG_ONLY",
        request_sleep_seconds=0.25,
        symbol_sleep_seconds=0.5,
        max_symbols_per_run=0,
        stop_on_provider_limit=True,
        resume_from_capture_state=None,
        reuse_existing_raw_lake=True,
        allow_training_on_partial_capture=False,
        backfill_cache_gaps=True,
        max_backfill_pages_per_symbol=None,
        prefer_full_coverage_training=True,
        symbols=["005930", "000660"],
        symbols_file="examples/kiwoom_watchlist_sample.txt",
        batch_size=2,
        batch_index=1,
        max_batches=None,
        resume_all=False,
        capture_state_root=str(tmp_path / "capture_state"),
    )
    second = batch_runner_module.run_kiwoom_watchlist_capture_and_train(
        fixture,
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(tmp_path / "oauth_tokens"),
        training_output_root=str(tmp_path / "offline"),
        training_handoff_mode="persisted_manifest",
        requested_template_ids=[],
        asset_liquidity_profile="LARGE_CAP",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
        search_mode="EXPANDED_SEARCH",
        walk_forward_mode="ANCHORED_CHRONOLOGICAL_WALK_FORWARD",
        promotion_profile="STABILITY_FIRST",
        fill_policy="CONSERVATIVE_NEXT_BAR_FILL",
        direction="LONG_ONLY",
        request_sleep_seconds=0.25,
        symbol_sleep_seconds=0.5,
        max_symbols_per_run=0,
        stop_on_provider_limit=True,
        resume_from_capture_state=None,
        reuse_existing_raw_lake=True,
        allow_training_on_partial_capture=False,
        backfill_cache_gaps=True,
        max_backfill_pages_per_symbol=None,
        prefer_full_coverage_training=True,
        symbols=["005930", "000660"],
        symbols_file="examples/kiwoom_watchlist_sample.txt",
        batch_size=2,
        batch_index=1,
        max_batches=None,
        resume_all=False,
        capture_state_root=str(tmp_path / "capture_state"),
    )
    assert first["offline_strategy_run_id"] != second["offline_strategy_run_id"]
    assert first["offline_strategy_output_root"] != second["offline_strategy_output_root"]
    assert Path(first["watchlist_ranking_summary_path"]).exists()
    assert Path(second["watchlist_ranking_summary_path"]).exists()
    latest = json.loads(Path(second["offline_strategy_latest_run_pointer_path"]).read_text(encoding="utf-8"))
    comparison = json.loads(Path(second["offline_strategy_run_comparison_path"]).read_text(encoding="utf-8"))
    assert latest["run_id"] == second["offline_strategy_run_id"]
    assert comparison["comparison_status"] == "COMPARISON_READY"


def test_watchlist_ledger_validation_flags_batch_identity_error(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path).model_copy(
        update={
            "request_specs": _fixture(tmp_path).request_specs
            + [
                _fixture(tmp_path).request_specs[0].model_copy(
                    update={"request_id": "KA10081-000660-TEST", "provider_symbol": "000660", "canonical_instrument_id": "000660"}
                ),
            ]
        }
    )

    def fake_run(_pipeline, **kwargs):
        del kwargs
        state_path = tmp_path / "bad-state.json"
        state_path.write_text(json.dumps({"requested_symbols": ["035420", "035720"]}), encoding="utf-8")
        return {
            "status": "COMPLETED",
            "provider_limit_hit": False,
            "can_resume": False,
            "capture_state_path": str(state_path),
            "capture_state_root": str(tmp_path),
            "dataset_id": _pipeline.dataset_id,
            "dataset_symbols": [spec.provider_symbol for spec in _pipeline.request_specs],
            "completed_symbols": [spec.provider_symbol for spec in _pipeline.request_specs],
            "full_coverage_symbols": [spec.provider_symbol for spec in _pipeline.request_specs],
            "partial_symbols": [],
            "failed_symbols": [],
            "skipped_symbols": [],
            "symbol_results": [
                {
                    "requested_symbol": spec.provider_symbol,
                    "cache_coverage_status": "FULL_TRADING_COVERAGE",
                    "post_backfill_coverage_status": "FULL_TRADING_COVERAGE",
                    "trading_coverage_ratio": 1.0,
                }
                for spec in _pipeline.request_specs
            ],
            "reused_from_cache": [],
            "fetched_now": [spec.provider_symbol for spec in _pipeline.request_specs],
            "backfilled_symbols": [],
            "manifest_path": "manifest.json",
            "per_symbol_row_count": {spec.provider_symbol: 10 for spec in _pipeline.request_specs},
            "per_symbol_date_min": {spec.provider_symbol: "2020-01-02" for spec in _pipeline.request_specs},
            "per_symbol_date_max": {spec.provider_symbol: "2026-06-26" for spec in _pipeline.request_specs},
            "per_symbol_coverage_status": {spec.provider_symbol: "FULL_TRADING_COVERAGE" for spec in _pipeline.request_specs},
            "per_symbol_coverage_basis": {spec.provider_symbol: "TRADING_DAYS" for spec in _pipeline.request_specs},
            "excluded_symbols": [],
            "exclusion_reasons": {},
        }

    monkeypatch.setattr(batch_runner_module, "run_kiwoom_ka10081_capture_and_train", fake_run)
    result = batch_runner_module.run_kiwoom_watchlist_capture_and_train(
        fixture,
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(tmp_path / "oauth_tokens"),
        training_output_root=str(tmp_path / "offline"),
        training_handoff_mode="persisted_manifest",
        requested_template_ids=[],
        asset_liquidity_profile="LARGE_CAP",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
        search_mode="SMOKE_SEARCH",
        walk_forward_mode="ANCHORED_CHRONOLOGICAL_WALK_FORWARD",
        promotion_profile="STABILITY_FIRST",
        fill_policy="CONSERVATIVE_NEXT_BAR_FILL",
        direction="LONG_ONLY",
        request_sleep_seconds=0.25,
        symbol_sleep_seconds=0.5,
        max_symbols_per_run=0,
        stop_on_provider_limit=True,
        resume_from_capture_state=None,
        reuse_existing_raw_lake=True,
        allow_training_on_partial_capture=False,
        backfill_cache_gaps=True,
        max_backfill_pages_per_symbol=None,
        prefer_full_coverage_training=True,
        symbols=["005930", "000660"],
        symbols_file="examples/kiwoom_watchlist_sample.txt",
        batch_size=2,
        batch_index=1,
        max_batches=None,
        resume_all=False,
        capture_state_root=str(tmp_path / "capture_state"),
    )
    assert result["batch_identity_status"] == "BATCH_IDENTITY_ERROR"
    assert result["ledger_validation_status"] == "LEDGER_VALIDATION_ERROR"
    assert "CAPTURE_STATE_SYMBOLS_MISMATCH" in " ".join(result["ledger_validation_errors"])


def test_watchlist_coverage_consistency_error_blocks_success(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path)

    def fake_run(_pipeline, **kwargs):
        del kwargs
        state_path = tmp_path / "coverage-state.json"
        state_path.write_text(json.dumps({"requested_symbols": ["005930"]}), encoding="utf-8")
        return {
            "status": "COMPLETED",
            "provider_limit_hit": False,
            "can_resume": False,
            "capture_state_path": str(state_path),
            "capture_state_root": str(tmp_path),
            "dataset_id": _pipeline.dataset_id,
            "dataset_symbols": ["005930"],
            "completed_symbols": [],
            "full_coverage_symbols": [],
            "partial_symbols": ["005930"],
            "failed_symbols": [],
            "skipped_symbols": [],
            "symbol_results": [
                {
                    "requested_symbol": "005930",
                    "cache_coverage_status": "TRADING_COVERAGE_GAP",
                    "post_backfill_coverage_status": "FULL_TRADING_COVERAGE",
                    "trading_coverage_ratio": 0.38,
                }
            ],
            "reused_from_cache": [],
            "fetched_now": ["005930"],
            "backfilled_symbols": [],
            "manifest_path": "manifest.json",
            "per_symbol_row_count": {"005930": 10},
            "per_symbol_date_min": {"005930": "2024-01-08"},
            "per_symbol_date_max": {"005930": "2026-06-26"},
            "per_symbol_coverage_status": {"005930": "TRADING_COVERAGE_GAP"},
            "per_symbol_coverage_basis": {"005930": "TRADING_DAYS"},
            "excluded_symbols": ["005930"],
            "exclusion_reasons": {"005930": "PREFER_FULL_COVERAGE_TRAINING"},
        }

    monkeypatch.setattr(batch_runner_module, "run_kiwoom_ka10081_capture_and_train", fake_run)
    result = batch_runner_module.run_kiwoom_watchlist_capture_and_train(
        fixture,
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(tmp_path / "oauth_tokens"),
        training_output_root=str(tmp_path / "offline"),
        training_handoff_mode="persisted_manifest",
        requested_template_ids=[],
        asset_liquidity_profile="LARGE_CAP",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
        search_mode="SMOKE_SEARCH",
        walk_forward_mode="ANCHORED_CHRONOLOGICAL_WALK_FORWARD",
        promotion_profile="STABILITY_FIRST",
        fill_policy="CONSERVATIVE_NEXT_BAR_FILL",
        direction="LONG_ONLY",
        request_sleep_seconds=0.25,
        symbol_sleep_seconds=0.5,
        max_symbols_per_run=0,
        stop_on_provider_limit=True,
        resume_from_capture_state=None,
        reuse_existing_raw_lake=True,
        allow_training_on_partial_capture=False,
        backfill_cache_gaps=True,
        max_backfill_pages_per_symbol=None,
        prefer_full_coverage_training=True,
        symbols=["005930"],
        symbols_file="examples/kiwoom_watchlist_sample.txt",
        batch_size=1,
        batch_index=1,
        max_batches=None,
        resume_all=False,
        capture_state_root=str(tmp_path / "capture_state"),
    )
    assert result["coverage_consistency_status"] == "COVERAGE_CONSISTENCY_ERROR"
    assert result["watchlist_status"] == "WATCHLIST_FAILED"


def test_capture_and_train_wrapper_resume_skips_completed_and_retries_failed(tmp_path, monkeypatch) -> None:
    fixture = _fixture(tmp_path).model_copy(
        update={
            "dataset_id": "historical-market-data-ka10081-multi-2",
            "request_specs": _fixture(tmp_path).request_specs
            + [
                _fixture(tmp_path).request_specs[0].model_copy(
                    update={"request_id": "KA10081-000660-TEST", "provider_symbol": "000660", "canonical_instrument_id": "000660"}
                )
            ],
        }
    )
    _cached_raw_lake_file(tmp_path, fixture, "005930")
    state_path = tmp_path / "resume_state.json"
    state_path.write_text(
        json.dumps(
            {
                "completed_symbols": ["005930"],
                "partial_symbols": [],
                "failed_symbols": ["000660"],
            }
        ),
        encoding="utf-8",
    )
    token_ref_path = _token_ref_file(tmp_path)
    seen_symbols: list[str] = []

    class FakeRealTransport:
        transport_kind = HistoricalMarketDataTransportKind.REAL_KIWOOM_CHART

        def __init__(self, **kwargs):
            del kwargs

        def execute(self, preview, *, auth_header=None):
            assert auth_header == "Bearer REDACTED"
            seen_symbols.append(preview.body_json["stk_cd"])
            return {
                "status_code": 200,
                "headers": {"cont-yn": "N", "next-key": ""},
                "body_json": {
                    "return_code": 0,
                    "return_msg": "OK",
                    "stk_cd": preview.body_json["stk_cd"],
                    "stk_dt_pole_chart_qry": [
                        {"dt": "20260623", "open_pric": "80000", "high_pric": "81300", "low_pric": "79800", "cur_prc": "81200", "trde_qty": "1000000"},
                        {"dt": "20260624", "open_pric": "81200", "high_pric": "81800", "low_pric": "81000", "cur_prc": "81600", "trde_qty": "1100000"},
                    ],
                },
            }

    def fake_issue(_request):
        return KiwoomOAuthTokenIssueResponse(
            status=KiwoomOAuthStatus.TOKEN_CACHE_HIT,
            token_type="Bearer",
            token_ref=KiwoomOAuthTokenRef(
                token_ref_path=str(token_ref_path),
                token_type="Bearer",
                expires_dt="2099-01-01T00:00:00+00:00",
                issued_at="2026-06-27T00:00:00+00:00",
                environment=KiwoomEnvironment.MOCK,
                credential_fingerprint_redacted="sha256:fixture",
            ),
            expires_dt="2099-01-01T00:00:00+00:00",
            issued_at="2026-06-27T00:00:00+00:00",
            return_msg_redacted="TOKEN_CACHE_HIT",
        )

    monkeypatch.setattr(wrapper_module, "issue_kiwoom_oauth_token", fake_issue)
    monkeypatch.setattr(wrapper_module, "RealKiwoomChartTransport", FakeRealTransport)
    monkeypatch.setattr(capture_runner_module, "is_pytest_runtime", lambda: False)
    monkeypatch.setattr(capture_guard_module, "is_pytest_runtime", lambda: False)

    result = wrapper_module.run_kiwoom_ka10081_capture_and_train(
        fixture.model_copy(update={"real_capture_config": fixture.real_capture_config.model_copy(update={"transport_kind": "REAL_KIWOOM_CHART"})}),
        environment=KiwoomEnvironment.MOCK,
        token_store_root=str(tmp_path / "oauth_tokens"),
        training_output_root=str(tmp_path / "local_data" / "offline_strategy"),
        resume_from_capture_state=str(state_path),
        search_mode="SMOKE_SEARCH",
        strategy_families=["RSI_OVERSOLD_REBOUND"],
    )
    assert result["skipped_completed"] == ["005930"]
    assert result["retried"] == ["000660"]
    assert seen_symbols == ["000660"]
    assert sorted(result["training_input_symbols"]) == ["000660", "005930"]
    assert result["tr_request_count"] == 1
