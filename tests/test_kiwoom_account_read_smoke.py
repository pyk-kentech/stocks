import json

import pytest

from stock_risk_mcp.kiwoom_account_read_models import KiwoomAccountReadConfig
from stock_risk_mcp.kiwoom_account_read_service import KiwoomAccountReadService
from stock_risk_mcp.kiwoom_account_read_smoke import (
    KiwoomAccountReadSmokeService,
    build_account_read_smoke_plan,
    select_account_read_smoke_endpoints,
)
from stock_risk_mcp.kiwoom_account_read_transport import FakeKiwoomAccountReadTransport
from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentials, KiwoomCredentialSource
from stock_risk_mcp.repository import RiskRepository


def _config(**changes):
    values = dict(
        enable_real_network=True, enable_account_read=True,
        credential_source=KiwoomCredentialSource.ENV, allow_auth_token_request=True,
        account_confirmed=True, account_fingerprint="mock", acknowledged_account_data_read=True,
        kill_switch_inactive=True,
    )
    values.update(changes)
    return KiwoomAccountReadConfig(**values)


def _smoke(tmp_path, calls):
    repository = RiskRepository(tmp_path / "risk.sqlite3")

    def credential_loader(*args):
        calls["credentials"] += 1
        return KiwoomCredentials(
            appkey="fake", secretkey="fake", account_number="fake-account",
            source=KiwoomCredentialSource.ENV,
        )

    def transport_factory(*args):
        calls["transport"] += 1
        return FakeKiwoomAccountReadTransport()

    account_service = KiwoomAccountReadService(repository, credential_loader, transport_factory)
    return repository, KiwoomAccountReadSmokeService(repository, account_service)


def test_smoke_plan_and_minimal_selection_are_offline():
    plan = build_account_read_smoke_plan()
    assert plan["endpoint_sets"]["minimal"] == ["kt00001"]
    assert plan["credentials_read"] is False
    assert plan["network_called"] is False
    assert select_account_read_smoke_endpoints(None, "minimal") == ["kt00001"]
    with pytest.raises(ValueError, match="maximum 2"):
        select_account_read_smoke_endpoints(["kt00001", "kt00018", "kt00007"], None)
    for endpoint_id in ("ka10001", "kt10000", "missing"):
        with pytest.raises(ValueError):
            select_account_read_smoke_endpoints([endpoint_id], None)


def test_smoke_dry_run_is_dependency_free_and_persists_redacted_report(tmp_path):
    calls = {"credentials": 0, "transport": 0}
    repository, smoke = _smoke(tmp_path, calls)
    run = smoke.run(_config(), endpoint_set="minimal", dry_run=True)
    shown = repository.get_kiwoom_account_read_smoke_report(run.smoke_run_id)
    text = json.dumps(shown.model_dump(mode="json")).lower()

    assert run.status == "DRY_RUN"
    assert calls == {"credentials": 0, "transport": 0}
    assert shown.steps[0].endpoint_id == "kt00001"
    for forbidden in ("account_number", "fake-account", "token", "authorization", "cash_balance", "raw_response"):
        assert forbidden not in text


@pytest.mark.parametrize(
    "changes",
    [
        {"enable_real_network": False}, {"enable_account_read": False},
        {"base_url": "https://mockapi.kiwoom.com/"}, {"credential_source": KiwoomCredentialSource.NONE},
        {"allow_auth_token_request": False}, {"account_confirmed": False},
        {"acknowledged_account_data_read": False}, {"kill_switch_inactive": False},
    ],
)
def test_smoke_invalid_gate_blocks_before_dependencies(tmp_path, changes):
    calls = {"credentials": 0, "transport": 0}
    _, smoke = _smoke(tmp_path, calls)
    run = smoke.run(_config(**changes), endpoint_set="minimal")
    assert run.status == "BLOCKED"
    assert calls == {"credentials": 0, "transport": 0}


def test_smoke_fake_execution_records_only_safe_status_summary(tmp_path):
    calls = {"credentials": 0, "transport": 0}
    repository, smoke = _smoke(tmp_path, calls)
    run = smoke.run(_config(), ["kt00001", "kt00018"])
    shown = repository.get_kiwoom_account_read_smoke_report(run.smoke_run_id)
    assert run.status == "COMPLETED"
    assert run.success_count == 2
    assert shown.steps[0].endpoint_classification == "ACCOUNT_READ"
    assert shown.redacted_metadata_json["status_counts"] == {"success": 2, "failed": 0}
    assert calls == {"credentials": 1, "transport": 1}
