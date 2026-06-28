from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from stock_risk_mcp.kiwoom_official_manifest import (
    KiwoomOfficialEndpointClass,
    load_kiwoom_official_manifest,
)
from stock_risk_mcp.kiwoom_real_readonly_models import (
    KiwoomCredentials,
    KiwoomRealNetworkConfig,
    KiwoomRealNetworkEnvironment,
)


KIWOOM_MOCK_BASE_URL = "https://mockapi.kiwoom.com"
KIWOOM_REAL_BASE_URL = "https://api.kiwoom.com"
V214_READONLY_API_IDS = {"ka10001", "ka10004", "ka10020", "ka10008", "ka10080", "ka10081"}


class KiwoomRealReadOnlyPolicyError(RuntimeError):
    pass


class FakeKiwoomTokenProvider:
    def get_token(self, config: KiwoomRealNetworkConfig, credentials: KiwoomCredentials) -> str:
        return "fake-readonly-token"


class RealKiwoomTokenProvider:
    def __init__(self, client=None) -> None:
        self.client = client or StdlibKiwoomHttpClient()

    def get_token(self, config: KiwoomRealNetworkConfig, credentials: KiwoomCredentials) -> str:
        _validate_network_config(config)
        if not config.allow_auth_token_request:
            raise KiwoomRealReadOnlyPolicyError("auth token request is not explicitly allowed")
        if not credentials.loaded:
            raise KiwoomRealReadOnlyPolicyError("explicit credentials are required")
        endpoint = _manifest_endpoint("au10001")
        if endpoint.read_write_class != KiwoomOfficialEndpointClass.AUTH:
            raise KiwoomRealReadOnlyPolicyError("token endpoint classification mismatch")
        response = self.client.post(
            f"{config.base_url}{endpoint.path}",
            {"Content-Type": "application/json;charset=UTF-8"},
            {"grant_type": "client_credentials", "appkey": credentials.appkey, "secretkey": credentials.secretkey},
            config.timeout_seconds,
        )
        body = response.get("body", {})
        token = body.get("token") or body.get("access_token")
        if int(response.get("status_code", 0)) not in range(200, 300) or not token:
            raise KiwoomRealReadOnlyPolicyError("token request failed")
        return str(token)


class RealKiwoomReadOnlyHttpTransport:
    def __init__(self, config, credentials, token_provider, client=None) -> None:
        self.config = config
        self.credentials = credentials
        self.token_provider = token_provider
        self.client = client or StdlibKiwoomHttpClient()
        self.request_count = 0

    def post(self, api_id: str, body: dict) -> dict:
        _validate_network_config(self.config)
        if not self.credentials.loaded:
            raise KiwoomRealReadOnlyPolicyError("explicit credentials are required")
        if self.request_count >= self.config.max_requests_per_run:
            raise KiwoomRealReadOnlyPolicyError("per-run request limit reached")
        endpoint = _manifest_endpoint(api_id)
        if api_id not in V214_READONLY_API_IDS:
            raise KiwoomRealReadOnlyPolicyError("endpoint is not in v2.14 read-only allowlist")
        if endpoint.read_write_class != KiwoomOfficialEndpointClass.READ_ONLY:
            raise KiwoomRealReadOnlyPolicyError("only REST READ_ONLY endpoints are allowed")
        if "websocket" in endpoint.path.lower():
            raise KiwoomRealReadOnlyPolicyError("WebSocket endpoints are blocked in v2.14")
        token = self.token_provider.get_token(self.config, self.credentials)
        self.request_count += 1
        response = self.client.post(
            f"{self.config.base_url}{endpoint.path}",
            {"Content-Type": "application/json;charset=UTF-8", "Authorization": f"Bearer {token}", "api-id": api_id},
            body,
            self.config.timeout_seconds,
        )
        status_code = int(response.get("status_code", 0))
        if status_code not in range(200, 300):
            return {"status": "FAILED", "status_code": status_code, "error": "Kiwoom read-only request failed"}
        return {"status": "COMPLETED", "status_code": status_code, "data": response.get("body")}


class StdlibKiwoomHttpClient:
    def post(self, url: str, headers: dict, body: dict, timeout_seconds: float) -> dict:
        request = Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        opener = build_opener(ProxyHandler({}))
        try:
            response = opener.open(request, timeout=timeout_seconds)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read()
            return {"status_code": response.status, "body": json.loads(raw.decode("utf-8")) if raw else {}}


def _validate_network_config(config: KiwoomRealNetworkConfig) -> None:
    if not config.enabled:
        raise KiwoomRealReadOnlyPolicyError("real Kiwoom network is disabled")
    if config.environment == KiwoomRealNetworkEnvironment.PROD_READONLY_DISABLED:
        raise KiwoomRealReadOnlyPolicyError("PROD_READONLY_DISABLED is always blocked")
    if config.environment not in {KiwoomRealNetworkEnvironment.MOCK, KiwoomRealNetworkEnvironment.REAL_READONLY}:
        raise KiwoomRealReadOnlyPolicyError("unsupported read-only network environment")
    expected_base_url = KIWOOM_MOCK_BASE_URL
    if config.environment == KiwoomRealNetworkEnvironment.REAL_READONLY:
        expected_base_url = KIWOOM_REAL_BASE_URL
    if config.base_url != expected_base_url:
        raise KiwoomRealReadOnlyPolicyError(f"base URL must exactly match {expected_base_url}")


def _manifest_endpoint(api_id: str):
    endpoint = next((item for item in load_kiwoom_official_manifest().endpoints if item.api_id == api_id), None)
    if endpoint is None:
        raise KiwoomRealReadOnlyPolicyError("endpoint is not present in official manifest")
    return endpoint
