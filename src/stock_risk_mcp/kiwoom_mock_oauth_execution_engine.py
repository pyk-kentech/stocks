from __future__ import annotations

import os
from datetime import datetime, timezone

from stock_risk_mcp.kiwoom_mock_oauth_execution_client import (
    TransportCallable,
    execute_kiwoom_mock_oauth_http_transport,
)
from stock_risk_mcp.kiwoom_mock_oauth_execution_models import (
    KiwoomMockOAuthExecutionConfig,
    KiwoomMockOAuthExecutionGapCategory,
    KiwoomMockOAuthExecutionGapReport,
    KiwoomMockOAuthExecutionMode,
    KiwoomMockOAuthExecutionResult,
    KiwoomMockOAuthExecutionSafetyReport,
    KiwoomMockOAuthTokenResult,
)


_BLOCKED_CAPABILITIES = [
    "PRODUCTION_DOMAIN_BLOCKED",
    "ACCOUNT_PATH_BLOCKED",
    "ORDER_PATH_BLOCKED",
    "QUOTE_PATH_BLOCKED",
    "WEBSOCKET_BLOCKED",
    "LIVE_PROD_BLOCKED",
]


def build_kiwoom_mock_oauth_execution_gap_report(
    config: KiwoomMockOAuthExecutionConfig,
) -> KiwoomMockOAuthExecutionGapReport:
    return config.gap_report.model_copy(
        update={
            "gap_categories": [
                KiwoomMockOAuthExecutionGapCategory.MOCK_QUOTE_API_STAGE_NOT_IMPLEMENTED,
                KiwoomMockOAuthExecutionGapCategory.MOCK_ACCOUNT_API_STAGE_NOT_IMPLEMENTED,
                KiwoomMockOAuthExecutionGapCategory.MOCK_ORDER_API_STAGE_NOT_IMPLEMENTED,
                KiwoomMockOAuthExecutionGapCategory.MOCK_WEBSOCKET_STAGE_NOT_IMPLEMENTED,
                KiwoomMockOAuthExecutionGapCategory.TOKEN_REFRESH_NOT_IMPLEMENTED,
                KiwoomMockOAuthExecutionGapCategory.TOKEN_PERSISTENCE_NOT_ALLOWED,
            ],
            "blocking_gap_count": 6,
            "report_only_gap_count": 0,
            "gaps": [
                "quote stage deferred",
                "account stage deferred",
                "order stage deferred",
                "websocket stage deferred",
                "token refresh deferred",
                "token persistence forbidden",
            ],
        }
    )


def build_kiwoom_mock_oauth_execution_safety_report(
    config: KiwoomMockOAuthExecutionConfig,
) -> KiwoomMockOAuthExecutionSafetyReport:
    return config.safety_report.model_copy(
        update={
            "blocked_capabilities": list(_BLOCKED_CAPABILITIES),
            "findings": [
                "mock_oauth_execution_only=true",
                "production_domain_blocked=true",
                "account_order_quote_websocket_paths_blocked=true",
                "redacted_output_only=true",
            ],
        }
    )


def _read_mock_credentials(config: KiwoomMockOAuthExecutionConfig) -> tuple[str, str]:
    app_key_name, secret_key_name = config.allowed_env_var_names
    app_key = os.environ.get(app_key_name)
    secret_key = os.environ.get(secret_key_name)
    if not app_key or not secret_key:
        raise ValueError("missing mock credentials (redacted)")
    return app_key, secret_key


def _build_request_payload(
    config: KiwoomMockOAuthExecutionConfig,
    *,
    app_key: str,
    secret_key: str,
) -> dict[str, object]:
    if config.execution_mode == KiwoomMockOAuthExecutionMode.TOKEN_REQUEST:
        path = "/oauth2/token"
        body = {
            "grant_type": "client_credentials",
            "appkey": app_key,
            "secretkey": secret_key,
        }
    else:
        path = "/oauth2/revoke"
        body = {
            "appkey": app_key,
            "secretkey": secret_key,
            "token": "IN_MEMORY_ONLY",
        }
    return {
        "url": f"{config.mock_domain}{path}",
        "headers": {"Content-Type": "application/json;charset=UTF-8"},
        "body": body,
        "timeout_seconds": config.timeout_seconds,
        "max_retry_count": config.max_retry_count,
        "retry_backoff_seconds": config.retry_backoff_seconds,
    }


def _validate_response(
    config: KiwoomMockOAuthExecutionConfig,
    response: dict[str, object],
) -> KiwoomMockOAuthTokenResult:
    if config.execution_mode == KiwoomMockOAuthExecutionMode.TOKEN_REQUEST:
        if not {"token_type", "token", "expires_dt"}.issubset(response):
            raise ValueError("mock oauth token response validation failed")
        return KiwoomMockOAuthTokenResult(
            token_result_id=f"{config.config_id}-TOKEN-RESULT",
            execution_mode=config.execution_mode,
            token_type=str(response["token_type"]),
            expires_at=datetime.now(timezone.utc),
            access_token_redacted="REDACTED",
            token_present=True,
            in_memory_only=True,
            persisted_to_disk=False,
            raw_token_exposed=False,
        )
    if not {"return_code", "return_msg"}.issubset(response):
        raise ValueError("mock oauth revoke response validation failed")
    return KiwoomMockOAuthTokenResult(
        token_result_id=f"{config.config_id}-TOKEN-RESULT",
        execution_mode=config.execution_mode,
        token_type="revoke",
        expires_at=None,
        access_token_redacted=None,
        token_present=False,
        in_memory_only=True,
        persisted_to_disk=False,
        raw_token_exposed=False,
        revoke_acknowledged=True,
    )


def execute_kiwoom_mock_oauth(
    config: KiwoomMockOAuthExecutionConfig,
    *,
    execute: bool,
    acknowledge_mock_oauth_execution: bool,
    mock_domain: bool,
    transport: TransportCallable | None = None,
) -> KiwoomMockOAuthExecutionResult:
    if not execute or not acknowledge_mock_oauth_execution or not mock_domain:
        raise ValueError("explicit opt-in flags are required")
    app_key, secret_key = _read_mock_credentials(config)
    request_payload = _build_request_payload(config, app_key=app_key, secret_key=secret_key)
    response = execute_kiwoom_mock_oauth_http_transport(request_payload, transport=transport)
    token_result = _validate_response(config, response)
    safety_report = build_kiwoom_mock_oauth_execution_safety_report(config)
    gap_report = build_kiwoom_mock_oauth_execution_gap_report(config)
    audit_record = config.audit_records[0].model_copy(
        update={
            "created_at": datetime.now(timezone.utc),
            "redaction_applied": True,
            "contains_secret_material": False,
            "contains_token_material": False,
        }
    )
    return KiwoomMockOAuthExecutionResult(
        execution_result_id=f"{config.config_id}-EXECUTION-RESULT",
        execution_mode=config.execution_mode,
        executed=True,
        mock_transport_used=transport is not None,
        real_network_performed=transport is None,
        env_vars_read=True,
        token_result=token_result,
        safety_report=safety_report,
        gap_report=gap_report,
        audit_records=[audit_record],
    )
