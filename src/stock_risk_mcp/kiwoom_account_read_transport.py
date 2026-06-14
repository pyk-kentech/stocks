from stock_risk_mcp.kiwoom_account_read_gate import ACCOUNT_READ_API_IDS
from stock_risk_mcp.kiwoom_official_manifest import KiwoomOfficialEndpointClass, load_kiwoom_official_manifest
from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomRealNetworkConfig
from stock_risk_mcp.kiwoom_real_readonly_transport import RealKiwoomTokenProvider, StdlibKiwoomHttpClient


class KiwoomAccountReadPolicyError(RuntimeError):
    pass


class FakeKiwoomAccountReadTransport:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def request(self, endpoint_id: str) -> dict:
        _validate_endpoint(endpoint_id)
        self.calls.append(endpoint_id)
        bodies = {
            "kt00001": {"currency": "KRW", "cash_balance": 1000000},
            "kt00018": {"currency": "KRW", "holdings": [{"symbol": "005930", "quantity": 1}, {"symbol": "000660", "quantity": 2}]},
            "kt00007": {"fills": [{"symbol": "005930"}]},
        }
        return {"status": "COMPLETED", "status_code": 200, "body": bodies[endpoint_id]}


class RealKiwoomAccountReadTransport:
    def __init__(self, config, credentials, token_provider=None, client=None) -> None:
        self.config = config
        self.credentials = credentials
        self.client = client or StdlibKiwoomHttpClient()
        self.token_provider = token_provider or RealKiwoomTokenProvider(self.client)
        self.request_count = 0

    def request(self, endpoint_id: str) -> dict:
        endpoint = _validate_endpoint(endpoint_id)
        if self.config.environment.value != "MOCK" or self.config.base_url != "https://mockapi.kiwoom.com":
            raise KiwoomAccountReadPolicyError("only exact MOCK account-read is allowed")
        if not self.credentials.loaded or not self.credentials.account_number:
            raise KiwoomAccountReadPolicyError("explicit credentials and account required")
        if self.request_count >= 2:
            raise KiwoomAccountReadPolicyError("maximum 2 account-read requests per run")
        token_config = KiwoomRealNetworkConfig(
            enabled=self.config.enable_real_network,
            environment=self.config.environment,
            base_url=self.config.base_url,
            timeout_seconds=self.config.timeout_seconds,
            max_requests_per_run=2,
            allow_auth_token_request=self.config.allow_auth_token_request,
            credential_source=self.config.credential_source,
            credential_file=self.config.credential_file,
        )
        token = self.token_provider.get_token(token_config, self.credentials)
        self.request_count += 1
        result = self.client.post(
            f"{self.config.base_url}{endpoint.path}",
            {"Content-Type": "application/json;charset=UTF-8", "Authorization": f"Bearer {token}", "api-id": endpoint_id},
            {"account_number": self.credentials.account_number},
            self.config.timeout_seconds,
        )
        status_code = int(result.get("status_code", 0))
        return {
            "status": "COMPLETED" if status_code in range(200, 300) else "FAILED",
            "status_code": status_code,
            "body": result.get("body", {}),
            "error": None if status_code in range(200, 300) else "Kiwoom account-read request failed",
        }


def _validate_endpoint(endpoint_id: str):
    endpoint = next((item for item in load_kiwoom_official_manifest().endpoints if item.api_id == endpoint_id), None)
    if endpoint is None or endpoint_id not in ACCOUNT_READ_API_IDS:
        raise KiwoomAccountReadPolicyError("endpoint is not in account-read allowlist")
    if endpoint.read_write_class != KiwoomOfficialEndpointClass.ACCOUNT_READ:
        raise KiwoomAccountReadPolicyError("only ACCOUNT_READ endpoints are allowed")
    if "websocket" in endpoint.path.lower():
        raise KiwoomAccountReadPolicyError("WebSocket endpoints are blocked")
    return endpoint
