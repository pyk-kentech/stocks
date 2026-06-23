import pytest

from stock_risk_mcp.kiwoom_mock_market_data_execution_engine import (
    execute_kiwoom_mock_market_data,
)
from stock_risk_mcp.kiwoom_mock_market_data_execution_models import (
    KiwoomMockMarketDataExecutionConfig,
)
from tests.test_kiwoom_mock_market_data_execution_models import (
    kiwoom_mock_market_data_execution_fixture_payload,
)


def _config(**kwargs):
    return KiwoomMockMarketDataExecutionConfig.model_validate(
        kiwoom_mock_market_data_execution_fixture_payload(**kwargs)
    )


def test_missing_explicit_opt_in_fails_closed():
    with pytest.raises(ValueError, match="explicit opt-in"):
        execute_kiwoom_mock_market_data(
            _config(),
            execute=False,
            acknowledge_mock_market_data_execution=False,
            mock_domain=False,
            access_token="in-memory-token",
            transport=lambda request: {"symbol": "005930", "last_price": 70000},
        )


def test_account_endpoint_is_blocked():
    with pytest.raises(ValueError, match="account"):
        execute_kiwoom_mock_market_data(
            _config(documented_category="ACCOUNT", documented_path="/api/dostk/acnt"),
            execute=True,
            acknowledge_mock_market_data_execution=True,
            mock_domain=True,
            access_token="in-memory-token",
            transport=lambda request: {"symbol": "005930", "last_price": 70000},
        )


def test_order_endpoint_is_blocked():
    with pytest.raises(ValueError, match="order"):
        execute_kiwoom_mock_market_data(
            _config(documented_category="ORDER", documented_path="/api/dostk/ordr"),
            execute=True,
            acknowledge_mock_market_data_execution=True,
            mock_domain=True,
            access_token="in-memory-token",
            transport=lambda request: {"symbol": "005930", "last_price": 70000},
        )


def test_websocket_endpoint_is_blocked():
    with pytest.raises(ValueError, match="websocket"):
        execute_kiwoom_mock_market_data(
            _config(documented_category="WEBSOCKET", documented_path="/api/websocket/quote"),
            execute=True,
            acknowledge_mock_market_data_execution=True,
            mock_domain=True,
            access_token="in-memory-token",
            transport=lambda request: {"symbol": "005930", "last_price": 70000},
        )


def test_unknown_endpoint_is_rejected():
    with pytest.raises(ValueError, match="unknown"):
        execute_kiwoom_mock_market_data(
            _config(documented_category="UNKNOWN", documented_path="/api/unknown"),
            execute=True,
            acknowledge_mock_market_data_execution=True,
            mock_domain=True,
            access_token="in-memory-token",
            transport=lambda request: {"symbol": "005930", "last_price": 70000},
        )


def test_request_execution_uses_mocked_http_transport_only():
    calls = []

    def transport(request):
        calls.append(request)
        return {"symbol": "005930", "last_price": 70000, "condition_match": True}

    result = execute_kiwoom_mock_market_data(
        _config(),
        execute=True,
        acknowledge_mock_market_data_execution=True,
        mock_domain=True,
        access_token="in-memory-token",
        transport=transport,
    )
    assert len(calls) == 1
    assert result.executed is True
    assert result.mock_transport_used is True
    assert result.real_network_performed is False


def test_token_value_is_never_printed_or_persisted():
    result = execute_kiwoom_mock_market_data(
        _config(),
        execute=True,
        acknowledge_mock_market_data_execution=True,
        mock_domain=True,
        access_token="super-secret-token",
        transport=lambda request: {"symbol": "005930", "last_price": 70000, "condition_match": True},
    )
    dumped = result.model_dump_json()
    assert "super-secret-token" not in dumped
    assert result.response.persisted_to_disk is False


def test_authorization_header_is_redacted_in_audit_output():
    result = execute_kiwoom_mock_market_data(
        _config(),
        execute=True,
        acknowledge_mock_market_data_execution=True,
        mock_domain=True,
        access_token="super-secret-token",
        transport=lambda request: {"symbol": "005930", "last_price": 70000, "condition_match": True},
    )
    dumped = result.audit_records[0].model_dump_json()
    assert "authorization" not in dumped.lower()
    assert "super-secret-token" not in dumped


def test_sanitized_response_object_is_returned():
    result = execute_kiwoom_mock_market_data(
        _config(),
        execute=True,
        acknowledge_mock_market_data_execution=True,
        mock_domain=True,
        access_token="in-memory-token",
        transport=lambda request: {"symbol": "005930", "last_price": 70000, "condition_match": True},
    )
    assert result.response.sanitized is True
    assert result.response.payload["last_price"] == 70000
