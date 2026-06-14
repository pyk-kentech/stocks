import pytest

from stock_risk_mcp.kiwoom_real_readonly_models import (
    KiwoomCredentialSource,
    KiwoomRealNetworkConfig,
    KiwoomRealNetworkEnvironment,
)
from stock_risk_mcp.kiwoom_real_readonly_smoke import (
    KiwoomRealReadOnlySmokeService,
    build_smoke_plan,
    select_smoke_endpoints,
)


def test_smoke_plan_is_offline_and_describes_safe_manual_run():
    plan = build_smoke_plan()
    assert plan["status"] == "PLANNED"
    assert plan["endpoint_sets"]["minimal"] == ["ka10001"]
    assert plan["environment"] == "MOCK"
    assert plan["base_url"] == "https://mockapi.kiwoom.com"
    assert plan["network_called"] is False
    assert plan["credentials_read"] is False


def test_endpoint_selection_deduplicates_and_enforces_hard_maximum():
    assert select_smoke_endpoints(["ka10001", "ka10004", "ka10001"], None) == ["ka10001", "ka10004"]
    with pytest.raises(ValueError, match="maximum"):
        select_smoke_endpoints(["ka10001", "ka10004", "ka10020", "ka10008"], None)


@pytest.mark.parametrize("endpoint_id", ["ka10171", "kt10000", "kt00001", "au10001", "missing"])
def test_endpoint_selection_rejects_websocket_order_account_auth_and_unknown(endpoint_id):
    with pytest.raises(ValueError):
        select_smoke_endpoints([endpoint_id], None)


def _valid_config(**changes):
    values = {
        "enabled": True,
        "credential_source": KiwoomCredentialSource.ENV,
        "allow_auth_token_request": True,
    }
    values.update(changes)
    return KiwoomRealNetworkConfig(**values)


@pytest.mark.parametrize(
    ("config", "message"),
    [
        (KiwoomRealNetworkConfig(credential_source=KiwoomCredentialSource.ENV, allow_auth_token_request=True), "enable"),
        (_valid_config(environment=KiwoomRealNetworkEnvironment.PROD_READONLY_DISABLED), "MOCK"),
        (_valid_config(base_url="https://mockapi.kiwoom.com/"), "exact"),
        (KiwoomRealNetworkConfig(enabled=True, allow_auth_token_request=True), "credential"),
        (KiwoomRealNetworkConfig(enabled=True, credential_source=KiwoomCredentialSource.ENV), "auth"),
    ],
)
def test_smoke_run_blocks_invalid_preflight_without_dependencies(tmp_path, config, message):
    service = KiwoomRealReadOnlySmokeService()
    result = service.run(config, ["ka10001"], dry_run=True)
    assert result.status.value == "BLOCKED"
    assert message.lower() in " ".join(result.errors).lower()


def test_explicit_file_source_requires_exact_file_selection(tmp_path):
    config = _valid_config(credential_source=KiwoomCredentialSource.FILE_EXPLICIT)
    result = KiwoomRealReadOnlySmokeService().run(config, ["ka10001"], dry_run=True)
    assert result.status.value == "BLOCKED"
    assert "credential file" in " ".join(result.errors)


def test_dry_run_validates_without_reading_credentials_or_calling_endpoint_service():
    calls = {"credentials": 0, "service": 0}

    def credential_loader(*args, **kwargs):
        calls["credentials"] += 1
        raise AssertionError("dry-run must not read credentials")

    def service_factory(*args, **kwargs):
        calls["service"] += 1
        raise AssertionError("dry-run must not construct endpoint service")

    smoke = KiwoomRealReadOnlySmokeService(
        credential_loader=credential_loader,
        service_factory=service_factory,
    )
    result = smoke.run(_valid_config(), endpoint_ids=None, endpoint_set="minimal", dry_run=True)

    assert result.status.value == "DRY_RUN"
    assert result.endpoint_ids == ["ka10001"]
    assert result.success_count == 1
    assert calls == {"credentials": 0, "service": 0}
