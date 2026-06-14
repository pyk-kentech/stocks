from __future__ import annotations

from stock_risk_mcp.kiwoom_official_manifest import KiwoomOfficialEndpointClass, load_kiwoom_official_manifest
from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentials
from stock_risk_mcp.kiwoom_real_readonly_transport import RealKiwoomTokenProvider, StdlibKiwoomHttpClient
from stock_risk_mcp.kiwoom_sandbox_order_models import KiwoomSandboxOrderConfig


SANDBOX_ORDER_ENDPOINTS = {"kt10000", "kt10003"}


class KiwoomSandboxOrderPolicyError(RuntimeError):
    pass


class FakeKiwoomSandboxOrderTransport:
    def __init__(self) -> None:
        self.calls = []

    def post(self, endpoint_id: str, body: dict) -> dict:
        _endpoint(endpoint_id)
        self.calls.append(endpoint_id)
        if endpoint_id == "kt10000":
            return {"status": "ACCEPTED", "status_code": 200, "broker_order_id": f"sandbox-{body.get('client_order_id', '1')}"}
        return {"status": "CANCELLED", "status_code": 200, "broker_order_id": body.get("broker_order_id")}


class RealKiwoomSandboxOrderTransport:
    def __init__(self, config: KiwoomSandboxOrderConfig, credentials: KiwoomCredentials, token_provider=None, client=None) -> None:
        self.config = config
        self.credentials = credentials
        self.token_provider = token_provider or RealKiwoomTokenProvider()
        self.client = client or StdlibKiwoomHttpClient()

    def post(self, endpoint_id: str, body: dict) -> dict:
        _validate_config(self.config)
        if not self.credentials.loaded or not self.credentials.account_number:
            raise KiwoomSandboxOrderPolicyError("explicit credentials and account required")
        endpoint = _endpoint(endpoint_id)
        token = self.token_provider.get_token(_readonly_config(self.config), self.credentials)
        response = self.client.post(
            f"{self.config.base_url}{endpoint.path}",
            {"Content-Type": "application/json;charset=UTF-8", "Authorization": f"Bearer {token}", "api-id": endpoint_id},
            body, self.config.timeout_seconds,
        )
        status_code = int(response.get("status_code", 0))
        payload = response.get("body", {})
        return {
            "status": "ACCEPTED" if endpoint_id == "kt10000" and 200 <= status_code < 300 else
                      "CANCELLED" if endpoint_id == "kt10003" and 200 <= status_code < 300 else "FAILED",
            "status_code": status_code,
            "broker_order_id": payload.get("ord_no"),
            "error": None if 200 <= status_code < 300 else "Kiwoom sandbox order request failed",
        }


def _endpoint(endpoint_id: str):
    endpoint = next((item for item in load_kiwoom_official_manifest().endpoints if item.api_id == endpoint_id), None)
    if endpoint_id not in SANDBOX_ORDER_ENDPOINTS or endpoint is None or endpoint.read_write_class != KiwoomOfficialEndpointClass.ORDER:
        raise KiwoomSandboxOrderPolicyError("endpoint is not an allowed sandbox ORDER endpoint")
    if "websocket" in endpoint.path.lower():
        raise KiwoomSandboxOrderPolicyError("WebSocket blocked")
    return endpoint


def _validate_config(config: KiwoomSandboxOrderConfig) -> None:
    from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentialSource, KiwoomRealNetworkEnvironment
    if not config.enable_real_network or not config.enable_sandbox_order:
        raise KiwoomSandboxOrderPolicyError("sandbox order is not explicitly enabled")
    if config.environment != KiwoomRealNetworkEnvironment.MOCK:
        raise KiwoomSandboxOrderPolicyError("MOCK environment required")
    if config.base_url != "https://mockapi.kiwoom.com":
        raise KiwoomSandboxOrderPolicyError("exact MOCK base URL required")
    if config.credential_source not in {KiwoomCredentialSource.ENV, KiwoomCredentialSource.FILE_EXPLICIT}:
        raise KiwoomSandboxOrderPolicyError("explicit credentials required")
    if not config.allow_auth_token_request:
        raise KiwoomSandboxOrderPolicyError("auth token request is not explicitly allowed")


def _readonly_config(config: KiwoomSandboxOrderConfig):
    from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomRealNetworkConfig
    return KiwoomRealNetworkConfig(
        enabled=config.enable_real_network, environment=config.environment, base_url=config.base_url,
        timeout_seconds=config.timeout_seconds, allow_auth_token_request=config.allow_auth_token_request,
        credential_source=config.credential_source, credential_file=config.credential_file,
    )
