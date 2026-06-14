from stock_risk_mcp.kiwoom_account_read_models import KiwoomAccountReadConfig
from stock_risk_mcp.kiwoom_official_manifest import KiwoomOfficialEndpointClass, load_kiwoom_official_manifest
from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentialSource, KiwoomRealNetworkEnvironment


ACCOUNT_READ_API_IDS = {"kt00001", "kt00018", "kt00007"}
ACCOUNT_READ_DEFAULT_ENDPOINT = "kt00018"
ACCOUNT_READ_HARD_MAX_ENDPOINTS = 2


def select_account_read_endpoints(endpoint_ids: list[str] | None) -> list[str]:
    selected = list(dict.fromkeys(endpoint_ids or [ACCOUNT_READ_DEFAULT_ENDPOINT]))
    if len(selected) > ACCOUNT_READ_HARD_MAX_ENDPOINTS:
        raise ValueError("maximum 2 account-read endpoints per run")
    manifest = {item.api_id: item for item in load_kiwoom_official_manifest().endpoints}
    for endpoint_id in selected:
        endpoint = manifest.get(endpoint_id)
        if endpoint_id not in ACCOUNT_READ_API_IDS or endpoint is None:
            raise ValueError(f"endpoint is not in account-read allowlist: {endpoint_id}")
        if endpoint.read_write_class != KiwoomOfficialEndpointClass.ACCOUNT_READ:
            raise ValueError(f"endpoint is not ACCOUNT_READ: {endpoint_id}")
        if "websocket" in endpoint.path.lower():
            raise ValueError("WebSocket account-read is blocked")
    return selected


def account_read_blocked_reasons(config: KiwoomAccountReadConfig) -> list[str]:
    reasons = []
    if config.kill_switch_inactive is not True:
        reasons.append("kill switch must be explicitly inactive")
    if not config.enable_real_network:
        reasons.append("--enable-real-network required")
    if not config.enable_account_read:
        reasons.append("--enable-account-read required")
    if config.environment != KiwoomRealNetworkEnvironment.MOCK:
        reasons.append("MOCK environment required")
    if config.base_url != "https://mockapi.kiwoom.com":
        reasons.append("exact MOCK base URL required")
    if config.credential_source not in {KiwoomCredentialSource.ENV, KiwoomCredentialSource.FILE_EXPLICIT}:
        reasons.append("explicit credentials required")
    if config.credential_source == KiwoomCredentialSource.FILE_EXPLICIT and config.credential_file is None:
        reasons.append("explicit credential file required")
    if not config.allow_auth_token_request:
        reasons.append("--allow-auth-token-request required")
    if not config.account_confirmed:
        reasons.append("explicit account confirmation required")
    if not config.account_fingerprint:
        reasons.append("account fingerprint confirmation required")
    if not config.acknowledged_account_data_read:
        reasons.append("account data read acknowledgement required")
    return reasons
