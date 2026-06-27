from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from stock_risk_mcp.local_oauth_http_client import LocalOAuthHttpClient
from stock_risk_mcp.kiwoom_oauth_credential_ref import build_credential_fingerprint_redacted, load_kiwoom_oauth_credentials
from stock_risk_mcp.kiwoom_oauth_guard import default_kiwoom_oauth_endpoint, validate_kiwoom_oauth_request
from stock_risk_mcp.kiwoom_oauth_models import (
    KiwoomEnvironment,
    KiwoomOAuthPreflightReport,
    KiwoomOAuthStatus,
    KiwoomOAuthStoredToken,
    KiwoomOAuthTokenIssueRequest,
    KiwoomOAuthTokenIssueResponse,
    KiwoomOAuthTokenRef,
)
from stock_risk_mcp.kiwoom_oauth_token_store import load_stored_token, persist_stored_token, stored_token_is_usable


def _response_common(request: KiwoomOAuthTokenIssueRequest, *, now: datetime, stage: str, credential_ref_status: str) -> dict[str, object]:
    return {
        "stage": stage,
        "kiwoom_environment": request.environment,
        "endpoint_base_url": request.endpoint.base_url,
        "endpoint_path": request.endpoint.token_path,
        "endpoint_method": "POST",
        "request_content_type": request.endpoint.content_type,
        "request_body_shape": ["grant_type", "appkey", "secretkey"],
        "credential_ref_status": credential_ref_status,
        "issued_at": now,
        "redaction_status": "PASSED",
    }


def build_kiwoom_oauth_request(
    *,
    environment: KiwoomEnvironment,
    credential_ref,
    token_store_root: str,
    allow_real_network: bool,
    allow_token_issue: bool,
    acknowledge_readonly_only: bool,
    acknowledge_user_initiated: bool,
    acknowledge_credential_redaction: bool,
    force_refresh_token: bool = False,
) -> KiwoomOAuthTokenIssueRequest:
    return KiwoomOAuthTokenIssueRequest(
        environment=environment,
        credential_ref=credential_ref,
        endpoint=default_kiwoom_oauth_endpoint(environment),
        token_store_root=token_store_root,
        allow_real_network=allow_real_network,
        allow_token_issue=allow_token_issue,
        acknowledge_readonly_only=acknowledge_readonly_only,
        acknowledge_user_initiated=acknowledge_user_initiated,
        acknowledge_credential_redaction=acknowledge_credential_redaction,
        force_refresh_token=force_refresh_token,
    )


def build_kiwoom_oauth_preflight(request: KiwoomOAuthTokenIssueRequest) -> KiwoomOAuthPreflightReport:
    findings = validate_kiwoom_oauth_request(request)
    return KiwoomOAuthPreflightReport(
        status=KiwoomOAuthStatus.TOKEN_PREFLIGHT_READY if not findings else KiwoomOAuthStatus.REJECTED,
        environment=request.environment,
        credential_ref_present=True,
        token_store_root=request.token_store_root,
        endpoint_base_url=request.endpoint.base_url,
        endpoint_path=request.endpoint.token_path,
        findings=findings,
    )


def issue_kiwoom_oauth_token(
    request: KiwoomOAuthTokenIssueRequest,
    *,
    client: LocalOAuthHttpClient | None = None,
    allow_pytest_fixture_read: bool = False,
) -> KiwoomOAuthTokenIssueResponse:
    now = datetime.now().astimezone()
    findings = validate_kiwoom_oauth_request(request)
    if findings:
        return KiwoomOAuthTokenIssueResponse(
            status=KiwoomOAuthStatus.REJECTED,
            **_response_common(request, now=now, stage="TOKEN_REQUEST_REJECTED", credential_ref_status="NOT_LOADED"),
            return_msg_redacted=";".join(findings),
            provider_return_msg=";".join(findings),
        )
    cached_token, cached_path = load_stored_token(request.token_store_root, request.environment, request.credential_ref)
    if cached_token is not None and not request.force_refresh_token and stored_token_is_usable(cached_token, now=now):
        return KiwoomOAuthTokenIssueResponse(
            status=KiwoomOAuthStatus.TOKEN_CACHE_HIT,
            **_response_common(request, now=cached_token.issued_at, stage="TOKEN_CACHE_HIT", credential_ref_status="CACHE_HIT"),
            token_written=False,
            token_type=cached_token.token_type,
            token_ref=KiwoomOAuthTokenRef(
                token_ref_path=str(cached_path),
                token_type=cached_token.token_type,
                expires_dt=cached_token.expires_dt,
                issued_at=cached_token.issued_at,
                environment=request.environment,
                credential_fingerprint_redacted=cached_token.credential_fingerprint_redacted,
            ),
            expires_dt=cached_token.expires_dt,
            expires_at=datetime.fromisoformat(cached_token.expires_dt) if cached_token.expires_dt else None,
            return_msg_redacted="TOKEN_CACHE_HIT",
            provider_return_msg="TOKEN_CACHE_HIT",
        )
    try:
        appkey, secretkey = load_kiwoom_oauth_credentials(request.credential_ref, allow_pytest_fixture_read=allow_pytest_fixture_read)
    except FileNotFoundError as error:
        return KiwoomOAuthTokenIssueResponse(
            status=KiwoomOAuthStatus.BLOCKED_CREDENTIAL_MISSING,
            **_response_common(request, now=now, stage="CREDENTIAL_LOAD", credential_ref_status="MISSING"),
            return_msg_redacted="credential ref file missing",
            provider_return_msg="credential ref file missing",
            transport_error_type=type(error).__name__,
            transport_error_message_redacted="credential ref file missing",
        )
    except ValueError as error:
        return KiwoomOAuthTokenIssueResponse(
            status=KiwoomOAuthStatus.BLOCKED_CREDENTIAL_FORMAT,
            **_response_common(request, now=now, stage="CREDENTIAL_LOAD", credential_ref_status="INVALID"),
            return_msg_redacted="credential ref format invalid",
            provider_return_msg="credential ref format invalid",
            transport_error_type=type(error).__name__,
            transport_error_message_redacted=str(error),
        )
    response = (client or LocalOAuthHttpClient()).issue_token(
        f"{request.endpoint.base_url}{request.endpoint.token_path}",
        content_type=request.endpoint.content_type,
        grant_type=request.grant_type,
        appkey=appkey,
        secretkey=secretkey,
        timeout_seconds=request.endpoint.timeout_seconds,
    )
    body_json = dict(response.get("body_json") or {})
    status_code = int(response.get("status_code")) if response.get("status_code") is not None else None
    transport_error_type = response.get("transport_error_type")
    transport_error_message_redacted = response.get("transport_error_message_redacted")
    token = body_json.get("token") or body_json.get("access_token")
    token_type = str(body_json.get("token_type") or "Bearer") if token else None
    return_code = body_json.get("return_code")
    return_msg = str(body_json.get("return_msg") or body_json.get("msg") or "").strip()
    response_common = _response_common(request, now=now, stage="TOKEN_ISSUE_HTTP", credential_ref_status="LOADED")
    if transport_error_type:
        return KiwoomOAuthTokenIssueResponse(
            status=KiwoomOAuthStatus.TRANSPORT_ERROR,
            **response_common,
            http_status_code=status_code,
            provider_return_code=return_code if isinstance(return_code, int) else None,
            provider_return_msg=return_msg or None,
            transport_error_type=str(transport_error_type),
            transport_error_message_redacted=str(transport_error_message_redacted or "transport error"),
            return_code=return_code if isinstance(return_code, int) else None,
            return_msg_redacted=return_msg or "TRANSPORT_ERROR",
        )
    if status_code not in range(200, 300):
        return KiwoomOAuthTokenIssueResponse(
            status=KiwoomOAuthStatus.PROVIDER_AUTH_ERROR if status_code in {401, 403} else KiwoomOAuthStatus.PROVIDER_TOKEN_ERROR,
            **response_common,
            http_status_code=status_code,
            provider_return_code=return_code if isinstance(return_code, int) else None,
            provider_return_msg=return_msg or (transport_error_message_redacted if transport_error_type else None),
            transport_error_type=transport_error_type,
            transport_error_message_redacted=transport_error_message_redacted,
            return_code=return_code if isinstance(return_code, int) else None,
            return_msg_redacted=return_msg or f"HTTP_{status_code}",
        )
    if not token:
        return KiwoomOAuthTokenIssueResponse(
            status=KiwoomOAuthStatus.PROVIDER_TOKEN_ERROR,
            **response_common,
            http_status_code=status_code,
            provider_return_code=return_code if isinstance(return_code, int) else None,
            provider_return_msg=return_msg or "TOKEN_MISSING",
            return_code=return_code if isinstance(return_code, int) else None,
            return_msg_redacted=return_msg or "TOKEN_MISSING",
        )
    expires_in_seconds = int(body_json.get("expires_in") or 86400)
    expires_at = now + timedelta(seconds=max(expires_in_seconds, 1))
    fingerprint = build_credential_fingerprint_redacted(appkey, secretkey)
    stored = KiwoomOAuthStoredToken(
        token=str(token),
        token_type=token_type,
        expires_dt=expires_at.isoformat(),
        issued_at=now,
        environment=request.environment,
        credential_fingerprint_redacted=fingerprint,
    )
    token_path = persist_stored_token(request.token_store_root, request.environment, request.credential_ref, stored)
    return KiwoomOAuthTokenIssueResponse(
        status=KiwoomOAuthStatus.TOKEN_ISSUED,
        **response_common,
        token_written=True,
        http_status_code=status_code,
        provider_return_code=return_code if isinstance(return_code, int) else None,
        provider_return_msg=return_msg or "TOKEN_ISSUED",
        token_type=token_type,
        token_ref=KiwoomOAuthTokenRef(
            token_ref_path=str(token_path),
            token_type=token_type,
            expires_dt=stored.expires_dt,
            issued_at=stored.issued_at,
            environment=request.environment,
            credential_fingerprint_redacted=fingerprint,
        ),
        expires_dt=stored.expires_dt,
        expires_at=expires_at,
        return_code=return_code if isinstance(return_code, int) else None,
        return_msg_redacted=return_msg or "TOKEN_ISSUED",
    )


def build_bearer_auth_header(token_response: KiwoomOAuthTokenIssueResponse) -> str | None:
    if token_response.token_ref is None:
        return None
    stored = KiwoomOAuthStoredToken.model_validate_json(Path(token_response.token_ref.token_ref_path).read_text(encoding="utf-8"))
    return f"{stored.token_type} {stored.token}"
