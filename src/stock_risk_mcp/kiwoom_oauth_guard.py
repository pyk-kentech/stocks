from __future__ import annotations

import sys
from pathlib import Path

from stock_risk_mcp.kiwoom_oauth_models import (
    KiwoomEnvironment,
    KiwoomOAuthEndpointConfig,
    KiwoomOAuthStatus,
    KiwoomOAuthTokenIssueRequest,
)


KIWOOM_MOCK_BASE_URL = "https://mockapi.kiwoom.com"
KIWOOM_REAL_BASE_URL = "https://api.kiwoom.com"


def is_pytest_runtime() -> bool:
    return "pytest" in sys.modules or "pytest" in Path(sys.argv[0]).name.lower()


def default_kiwoom_oauth_endpoint(environment: KiwoomEnvironment) -> KiwoomOAuthEndpointConfig:
    return KiwoomOAuthEndpointConfig(
        environment=environment,
        base_url=KIWOOM_MOCK_BASE_URL if environment == KiwoomEnvironment.MOCK else KIWOOM_REAL_BASE_URL,
    )


def validate_kiwoom_oauth_request(request: KiwoomOAuthTokenIssueRequest) -> list[str]:
    reasons: list[str] = []
    if is_pytest_runtime():
        reasons.append(KiwoomOAuthStatus.BLOCKED_NETWORK_IN_TEST.value)
    if not request.allow_token_issue:
        reasons.append("TOKEN_ISSUE_OPT_IN_REQUIRED")
    if not request.acknowledge_readonly_only:
        reasons.append("READONLY_ACK_REQUIRED")
    if not request.acknowledge_user_initiated:
        reasons.append("USER_INITIATED_ACK_REQUIRED")
    if not request.acknowledge_credential_redaction:
        reasons.append("CREDENTIAL_REDACTION_ACK_REQUIRED")
    if request.environment == KiwoomEnvironment.REAL and not request.allow_real_network:
        reasons.append(KiwoomOAuthStatus.BLOCKED_REAL_OAUTH_OPT_IN_REQUIRED.value)
    expected_base_url = KIWOOM_MOCK_BASE_URL if request.environment == KiwoomEnvironment.MOCK else KIWOOM_REAL_BASE_URL
    if request.endpoint.base_url != expected_base_url:
        reasons.append(KiwoomOAuthStatus.BLOCKED_TOKEN_ENDPOINT_CONFIG.value)
    if request.endpoint.token_path != "/oauth2/token":
        reasons.append(KiwoomOAuthStatus.BLOCKED_TOKEN_ENDPOINT_CONFIG.value)
    return sorted(set(reasons))
