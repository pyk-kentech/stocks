from __future__ import annotations

from datetime import datetime, timezone

from stock_risk_mcp.kiwoom_mock_market_data_execution_client import (
    TransportCallable,
    execute_kiwoom_mock_market_data_http_transport,
)
from stock_risk_mcp.kiwoom_mock_market_data_execution_models import (
    KiwoomMockMarketDataExecutionConfig,
    KiwoomMockMarketDataExecutionGapCategory,
    KiwoomMockMarketDataExecutionGapReport,
    KiwoomMockMarketDataExecutionResult,
    KiwoomMockMarketDataExecutionSafetyReport,
    KiwoomMockMarketDataResponse,
)


_BLOCKED_CAPABILITIES = [
    "PRODUCTION_DOMAIN_BLOCKED",
    "ACCOUNT_PATH_BLOCKED",
    "ORDER_PATH_BLOCKED",
    "WEBSOCKET_BLOCKED",
    "LIVE_PROD_BLOCKED",
]


def build_kiwoom_mock_market_data_execution_gap_report(
    config: KiwoomMockMarketDataExecutionConfig,
) -> KiwoomMockMarketDataExecutionGapReport:
    return config.gap_report.model_copy(
        update={
            "gap_categories": [
                KiwoomMockMarketDataExecutionGapCategory.REAL_MARKET_DATA_STAGE_NOT_IMPLEMENTED,
                KiwoomMockMarketDataExecutionGapCategory.ACCOUNT_STAGE_NOT_IMPLEMENTED,
                KiwoomMockMarketDataExecutionGapCategory.ORDER_STAGE_NOT_IMPLEMENTED,
                KiwoomMockMarketDataExecutionGapCategory.WEBSOCKET_STAGE_NOT_IMPLEMENTED,
                KiwoomMockMarketDataExecutionGapCategory.LIVE_STAGE_NOT_IMPLEMENTED,
            ],
            "blocking_gap_count": 5,
            "report_only_gap_count": 0,
            "gaps": [
                "real market data stage deferred",
                "account stage deferred",
                "order stage deferred",
                "websocket stage deferred",
                "live stage deferred",
            ],
        }
    )


def build_kiwoom_mock_market_data_execution_safety_report(
    config: KiwoomMockMarketDataExecutionConfig,
) -> KiwoomMockMarketDataExecutionSafetyReport:
    return config.safety_report.model_copy(
        update={
            "blocked_capabilities": list(_BLOCKED_CAPABILITIES),
            "findings": [
                "mock_market_data_execution_only=true",
                "readonly_category_only=true",
                "redacted_output_only=true",
                "token_in_memory_only=true",
            ],
        }
    )


def build_kiwoom_mock_market_data_response_report(
    config: KiwoomMockMarketDataExecutionConfig,
) -> KiwoomMockMarketDataResponse:
    return KiwoomMockMarketDataResponse(
        response_object_id=f"{config.config_id}-RESPONSE",
        documented_category=config.documented_category,
        documented_path=config.documented_path,
        symbol="005930",
        payload={"last_price": 70000, "condition_match": True},
        sanitized=True,
        raw_token_exposed=False,
        persisted_to_disk=False,
    )


def _validate_execution_inputs(
    config: KiwoomMockMarketDataExecutionConfig,
    *,
    execute: bool,
    acknowledge_mock_market_data_execution: bool,
    mock_domain: bool,
    access_token: str | None,
) -> None:
    if not execute or not acknowledge_mock_market_data_execution or not mock_domain:
        raise ValueError("explicit opt-in flags are required")
    if config.documented_category == "ACCOUNT":
        raise ValueError("account endpoint is blocked")
    if config.documented_category == "ORDER":
        raise ValueError("order endpoint is blocked")
    if config.documented_category == "WEBSOCKET":
        raise ValueError("websocket endpoint is blocked")
    if config.documented_category == "UNKNOWN":
        raise ValueError("unknown endpoint is rejected")
    if not access_token:
        raise ValueError("missing in-memory access token (redacted)")


def _build_request_payload(
    config: KiwoomMockMarketDataExecutionConfig,
    *,
    access_token: str,
) -> dict[str, object]:
    return {
        "url": f"{config.mock_domain}{config.documented_path}",
        "headers": {
            "Content-Type": "application/json;charset=UTF-8",
            "Authorization": "Bearer REDACTED",
        },
        "body": {"symbol": "005930", "token_ref": config.token_reference_label},
        "timeout_seconds": config.timeout_seconds,
        "max_retry_count": config.max_retry_count,
        "retry_backoff_seconds": config.retry_backoff_seconds,
        "in_memory_token_supplied": bool(access_token),
    }


def _validate_response_payload(response: dict[str, object]) -> KiwoomMockMarketDataResponse:
    if "symbol" not in response:
        raise ValueError("market data response validation failed")
    return KiwoomMockMarketDataResponse(
        response_object_id="KIWOOM-MOCK-MARKET-DATA-RESPONSE",
        documented_category="QUOTE",
        documented_path="/api/dostk/mrkcond",
        symbol=str(response["symbol"]),
        payload={key: value for key, value in response.items() if key != "authorization"},
        sanitized=True,
        raw_token_exposed=False,
        persisted_to_disk=False,
    )


def execute_kiwoom_mock_market_data(
    config: KiwoomMockMarketDataExecutionConfig,
    *,
    execute: bool,
    acknowledge_mock_market_data_execution: bool,
    mock_domain: bool,
    access_token: str | None,
    transport: TransportCallable | None = None,
) -> KiwoomMockMarketDataExecutionResult:
    _validate_execution_inputs(
        config,
        execute=execute,
        acknowledge_mock_market_data_execution=acknowledge_mock_market_data_execution,
        mock_domain=mock_domain,
        access_token=access_token,
    )
    request_payload = _build_request_payload(config, access_token=access_token)
    response = execute_kiwoom_mock_market_data_http_transport(request_payload, transport=transport)
    sanitized_response = _validate_response_payload(response)
    safety_report = build_kiwoom_mock_market_data_execution_safety_report(config)
    gap_report = build_kiwoom_mock_market_data_execution_gap_report(config)
    audit_record = config.audit_records[0].model_copy(
        update={
            "created_at": datetime.now(timezone.utc),
            "redaction_applied": True,
            "contains_secret_material": False,
            "contains_token_material": False,
            "contains_account_material": False,
        }
    )
    return KiwoomMockMarketDataExecutionResult(
        execution_result_id=f"{config.config_id}-EXECUTION-RESULT",
        executed=True,
        mock_transport_used=transport is not None,
        real_network_performed=transport is None,
        token_used_in_memory_only=True,
        response=sanitized_response,
        safety_report=safety_report,
        gap_report=gap_report,
        audit_records=[audit_record],
    )
