from stock_risk_mcp.kiwoom_oauth_engine import build_kiwoom_oauth_preflight, build_kiwoom_oauth_request, issue_kiwoom_oauth_token
from stock_risk_mcp.kiwoom_oauth_models import KiwoomCredentialRef, KiwoomEnvironment


class FakeOAuthClient:
    def issue_token(self, url, *, content_type, grant_type, appkey, secretkey, timeout_seconds):
        del url, content_type, grant_type, appkey, secretkey, timeout_seconds
        return {
            "status_code": 200,
            "body_json": {
                "token": "TOKEN123",
                "token_type": "Bearer",
                "expires_in": 3600,
                "return_code": 0,
                "return_msg": "OK",
            },
        }


class FakeOAuthProviderErrorClient:
    def issue_token(self, url, *, content_type, grant_type, appkey, secretkey, timeout_seconds):
        del url, content_type, grant_type, appkey, secretkey, timeout_seconds
        return {
            "status_code": 200,
            "body_json": {
                "return_code": 5001,
                "return_msg": "mock provider token rejected",
            },
            "transport_error_type": None,
            "transport_error_message_redacted": None,
            "request_body_shape": ["grant_type", "appkey", "secretkey"],
        }


class FakeOAuthHttpErrorClient:
    def issue_token(self, url, *, content_type, grant_type, appkey, secretkey, timeout_seconds):
        del url, content_type, grant_type, appkey, secretkey, timeout_seconds
        return {
            "status_code": 401,
            "body_json": {
                "return_code": 4011,
                "return_msg": "mock auth denied",
            },
            "transport_error_type": None,
            "transport_error_message_redacted": None,
            "request_body_shape": ["grant_type", "appkey", "secretkey"],
        }


def _request(tmp_path):
    appkey_path = tmp_path / "appkey.txt"
    secretkey_path = tmp_path / "secretkey.txt"
    appkey_path.write_text("APPKEY", encoding="utf-8")
    secretkey_path.write_text("SECRETKEY", encoding="utf-8")
    credential_ref = KiwoomCredentialRef(
        credential_id="TEST_REF",
        appkey_ref_path=str(appkey_path),
        secretkey_ref_path=str(secretkey_path),
    )
    return build_kiwoom_oauth_request(
        environment=KiwoomEnvironment.MOCK,
        credential_ref=credential_ref,
        token_store_root=str(tmp_path / "local_data" / "tokens"),
        allow_real_network=True,
        allow_token_issue=True,
        acknowledge_readonly_only=True,
        acknowledge_user_initiated=True,
        acknowledge_credential_redaction=True,
    )


def test_kiwoom_oauth_preflight_ready(tmp_path) -> None:
    report = build_kiwoom_oauth_preflight(_request(tmp_path))
    assert report.status.value == "REJECTED"
    assert "BLOCKED_NETWORK_IN_TEST" in report.findings


def test_kiwoom_oauth_issue_persists_redacted_token_ref(tmp_path, monkeypatch) -> None:
    request = _request(tmp_path)
    monkeypatch.setattr("stock_risk_mcp.kiwoom_oauth_guard.is_pytest_runtime", lambda: False)
    monkeypatch.setattr("stock_risk_mcp.kiwoom_oauth_credential_ref.is_pytest_runtime", lambda: False)
    result = issue_kiwoom_oauth_token(request, client=FakeOAuthClient())
    assert result.status.value == "TOKEN_ISSUED"
    assert result.token_ref is not None
    token_payload = result.token_ref.token_ref_path
    assert "APPKEY" not in token_payload
    assert "SECRETKEY" not in token_payload
    assert result.token_written is True
    assert result.request_body_shape == ["grant_type", "appkey", "secretkey"]


def test_kiwoom_oauth_issue_reports_provider_token_error_without_fake_token_ref(tmp_path, monkeypatch) -> None:
    request = _request(tmp_path)
    monkeypatch.setattr("stock_risk_mcp.kiwoom_oauth_guard.is_pytest_runtime", lambda: False)
    monkeypatch.setattr("stock_risk_mcp.kiwoom_oauth_credential_ref.is_pytest_runtime", lambda: False)
    result = issue_kiwoom_oauth_token(request, client=FakeOAuthProviderErrorClient())
    assert result.status.value == "PROVIDER_TOKEN_ERROR"
    assert result.provider_return_code == 5001
    assert result.provider_return_msg == "mock provider token rejected"
    assert result.token_ref is None
    assert result.token_type is None
    assert result.token_written is False


def test_kiwoom_oauth_issue_captures_non_2xx_provider_error(tmp_path, monkeypatch) -> None:
    request = _request(tmp_path)
    monkeypatch.setattr("stock_risk_mcp.kiwoom_oauth_guard.is_pytest_runtime", lambda: False)
    monkeypatch.setattr("stock_risk_mcp.kiwoom_oauth_credential_ref.is_pytest_runtime", lambda: False)
    result = issue_kiwoom_oauth_token(request, client=FakeOAuthHttpErrorClient())
    assert result.status.value == "PROVIDER_AUTH_ERROR"
    assert result.http_status_code == 401
    assert result.provider_return_code == 4011
    assert result.provider_return_msg == "mock auth denied"
    assert result.token_ref is None
