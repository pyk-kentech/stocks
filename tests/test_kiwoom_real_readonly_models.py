from stock_risk_mcp.kiwoom_real_readonly_models import (
    KiwoomCredentialSource,
    KiwoomRealNetworkConfig,
    KiwoomRealNetworkEnvironment,
)


def test_kiwoom_real_network_config_defaults_disabled_and_mock_host_only() -> None:
    config = KiwoomRealNetworkConfig()
    assert config.enabled is False
    assert config.environment == KiwoomRealNetworkEnvironment.MOCK
    assert config.base_url == "https://mockapi.kiwoom.com"
    assert config.allow_auth_token_request is False
    assert config.max_requests_per_run == 5
    assert config.credential_source == KiwoomCredentialSource.NONE
