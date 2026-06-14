import json

from stock_risk_mcp.kiwoom_account_read_models import KiwoomAccountReadConfig
from stock_risk_mcp.kiwoom_account_read_service import KiwoomAccountReadService
from stock_risk_mcp.kiwoom_account_read_transport import FakeKiwoomAccountReadTransport
from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentials, KiwoomCredentialSource
from stock_risk_mcp.repository import RiskRepository


def _run(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    service = KiwoomAccountReadService(
        repository,
        lambda *args: KiwoomCredentials(
            appkey="fake", secretkey="fake", account_number="fake-account",
            source=KiwoomCredentialSource.ENV,
        ),
        lambda *args: FakeKiwoomAccountReadTransport(),
    )
    config = KiwoomAccountReadConfig(
        enable_real_network=True, enable_account_read=True,
        credential_source=KiwoomCredentialSource.ENV, allow_auth_token_request=True,
        account_confirmed=True, account_fingerprint="mock", acknowledged_account_data_read=True,
        kill_switch_inactive=True,
    )
    return repository, service, service.run(config, ["kt00018"])


def test_reconcile_missing_local_ledger_is_safe_unavailable(tmp_path):
    _, service, run = _run(tmp_path)
    preview = service.reconcile_preview(run.run_id, kill_switch_inactive=True)
    assert preview.reconciliation_status == "LOCAL_LEDGER_UNAVAILABLE"
    assert preview.local_ledger_present is False
    assert preview.orders_submitted is False
    assert preview.live_execution_enabled is False


def test_reconcile_aggregate_counts_only_and_details_are_unavailable(tmp_path):
    repository, service, run = _run(tmp_path)
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"symbols": [{"symbol": "005930"}, {"symbol": "000660"}, {"symbol": "035420"}]}), encoding="utf-8")

    aggregate = service.reconcile_preview(run.run_id, True, ledger)
    details = service.reconcile_preview(run.run_id, True, ledger, include_redacted_symbol_details=True)
    stored = repository.list_kiwoom_account_read_reconcile_previews()
    text = json.dumps([item.model_dump(mode="json") for item in stored]).lower()

    assert aggregate.reconciliation_status == "COMPLETED_WITH_MISMATCHES"
    assert aggregate.symbol_count_compared == 2
    assert aggregate.missing_in_account_count == 1
    assert aggregate.symbol_details_json == []
    assert details.reconciliation_status == "ACCOUNT_DETAILS_UNAVAILABLE"
    assert details.symbol_details_json == []
    assert all(item.orders_submitted is False for item in stored)
    for forbidden in ("fake-account", "cash_balance", "raw_holdings", "authorization"):
        assert forbidden not in text


def test_reconcile_kill_switch_blocks_before_local_ledger_read(tmp_path):
    _, service, run = _run(tmp_path)
    missing = tmp_path / "would-not-be-read.json"
    preview = service.reconcile_preview(run.run_id, False, missing)
    assert preview.reconciliation_status == "BLOCKED"
    assert preview.local_ledger_present is False


def test_reconcile_invalid_local_ledger_returns_safe_unavailable(tmp_path):
    _, service, run = _run(tmp_path)
    ledger = tmp_path / "ledger.json"
    ledger.write_text("{invalid", encoding="utf-8")
    preview = service.reconcile_preview(run.run_id, True, ledger)
    assert preview.reconciliation_status == "LOCAL_LEDGER_UNAVAILABLE"
    assert preview.redacted_metadata_json["sanitized_error"] == "local ledger could not be read"
