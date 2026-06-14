import json
import sqlite3

import pytest

from stock_risk_mcp.kiwoom_account_read_gate import select_account_read_endpoints
from stock_risk_mcp.kiwoom_account_read_models import KiwoomAccountReadConfig, KiwoomAccountReadStatus
from stock_risk_mcp.kiwoom_account_read_service import KiwoomAccountReadService
from stock_risk_mcp.kiwoom_account_read_transport import FakeKiwoomAccountReadTransport
from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentials, KiwoomCredentialSource
from stock_risk_mcp.repository import RiskRepository


def _config(**changes):
    values = {
        "enable_real_network": True,
        "enable_account_read": True,
        "credential_source": KiwoomCredentialSource.ENV,
        "allow_auth_token_request": True,
        "account_confirmed": True,
        "account_fingerprint": "mock-fingerprint",
        "acknowledged_account_data_read": True,
        "kill_switch_inactive": True,
    }
    values.update(changes)
    return KiwoomAccountReadConfig(**values)


def _service(tmp_path, config=None):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    transport = FakeKiwoomAccountReadTransport()
    calls = {"credentials": 0, "transport": 0}

    def credentials(*args):
        calls["credentials"] += 1
        return KiwoomCredentials(
            appkey="fake-app", secretkey="fake-secret", account_number="fake-account",
            source=KiwoomCredentialSource.ENV,
        )

    def transport_factory(*args):
        calls["transport"] += 1
        return transport

    return repository, KiwoomAccountReadService(repository, credentials, transport_factory), transport, calls


def test_config_is_disabled_by_default_and_endpoint_selection_is_strict():
    assert KiwoomAccountReadConfig().enable_account_read is False
    assert select_account_read_endpoints(None) == ["kt00018"]
    assert select_account_read_endpoints(["kt00001", "kt00001", "kt00007"]) == ["kt00001", "kt00007"]
    for endpoint in ("ka10001", "kt10000", "missing"):
        with pytest.raises(ValueError):
            select_account_read_endpoints([endpoint])
    with pytest.raises(ValueError, match="maximum 2"):
        select_account_read_endpoints(["kt00001", "kt00018", "kt00007"])


def test_health_plan_and_dry_run_are_offline(tmp_path):
    _, service, transport, calls = _service(tmp_path)
    assert service.health().status == KiwoomAccountReadStatus.DISABLED
    assert service.plan(_config(), ["kt00018"])["would_run"] is True
    dry = service.run(_config(), ["kt00018"], dry_run=True)
    assert dry.status == KiwoomAccountReadStatus.DRY_RUN
    assert calls == {"credentials": 0, "transport": 0}
    assert transport.calls == []


@pytest.mark.parametrize(
    "changes",
    [
        {"enable_real_network": False},
        {"enable_account_read": False},
        {"base_url": "https://mockapi.kiwoom.com/"},
        {"credential_source": KiwoomCredentialSource.NONE},
        {"allow_auth_token_request": False},
        {"account_confirmed": False},
        {"account_fingerprint": None},
        {"acknowledged_account_data_read": False},
        {"kill_switch_inactive": False},
        {"kill_switch_inactive": None},
    ],
)
def test_run_blocks_before_credentials_and_transport_when_gate_missing(tmp_path, changes):
    _, service, transport, calls = _service(tmp_path)
    run = service.run(_config(**changes), ["kt00018"])
    assert run.status == KiwoomAccountReadStatus.BLOCKED
    assert calls == {"credentials": 0, "transport": 0}
    assert transport.calls == []


def test_fake_run_persists_only_redacted_summary_and_reconcile_is_count_only(tmp_path):
    repository, service, transport, calls = _service(tmp_path)
    run = service.run(_config(), ["kt00018"])
    shown = repository.get_kiwoom_account_read_report(run.run_id)
    blocked = service.reconcile_preview(run.run_id)
    assert blocked.reconciliation_status == "BLOCKED"
    preview = service.reconcile_preview(run.run_id, kill_switch_inactive=True)
    serialized = json.dumps({
        "run": shown.model_dump(mode="json"),
        "preview": preview.model_dump(mode="json"),
    }).lower()

    assert run.status == KiwoomAccountReadStatus.COMPLETED
    assert calls == {"credentials": 1, "transport": 1}
    assert transport.calls == ["kt00018"]
    assert shown.responses[0].normalized_summary_json["holding_count"] == 2
    assert shown.requests[0].request_status == "COMPLETED"
    assert shown.account_fingerprint != "mock-fingerprint"
    assert preview.mismatch_count == 0
    for forbidden in ("fake-account", "fake-app", "fake-secret", "authorization", "raw_response", "cash_balance"):
        assert forbidden not in serialized

    connection = sqlite3.connect(repository.db_path)
    stored = " ".join(
        str(value)
        for table, column in (
            ("kiwoom_account_read_runs", "run_json"),
            ("kiwoom_account_read_requests", "request_json"),
            ("kiwoom_account_read_responses", "response_json"),
            ("kiwoom_account_read_reconcile_previews", "preview_json"),
        )
        for (value,) in connection.execute(f"SELECT {column} FROM {table}").fetchall()
    ).lower()
    connection.close()
    for forbidden in ("fake-account", "fake-app", "fake-secret", "cash_balance", "raw_response"):
        assert forbidden not in stored
