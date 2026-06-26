import json

from stock_risk_mcp.account_read_fixture import load_account_read_fixture
from stock_risk_mcp.account_read_models import AccountReadPipelineInput


def account_read_payload():
    return {
        "pipeline_id": "account-read-test",
        "provider": "LOCAL_MANUAL",
        "mode": "MANUAL_FIXTURE",
        "requested_at": "2026-06-26T16:30:00+09:00",
        "snapshot_fixture": {
            "metadata": {
                "snapshot_id": "account-snapshot-test",
                "provider": "LOCAL_MANUAL",
                "mode": "MANUAL_FIXTURE",
                "account_ref": "acct-redacted-9d3f",
                "account_ref_policy": "REDACTED_TEXT_PLUS_HASH",
                "observed_at": "2026-06-26T15:35:00+09:00",
                "available_at": "2026-06-26T15:36:00+09:00",
                "account_base_currency": "KRW",
                "source_ref": {
                    "source_id": "account-read-source",
                    "source_kind": "MANUAL_ACCOUNT_SNAPSHOT_FIXTURE",
                    "sanitized_basename": "account_snapshot_test.json",
                    "relative_path": "fixtures/account_read/account_snapshot_test.json",
                    "available_at": "2026-06-26T15:36:00+09:00",
                },
                "metadata": {"capture_mode": "manual_fixture"},
            },
            "cash_balances": [{"currency": "KRW", "available_cash": 9800000.0, "settled_cash": 9800000.0}],
            "holdings": [
                {
                    "instrument_id": "005930",
                    "market": "KRX",
                    "currency": "KRW",
                    "quantity": 1.0,
                    "average_cost": 82450.0,
                    "last_price": 83100.0,
                    "market_value": 83100.0,
                    "source_ref": {
                        "source_id": "account-read-holding-source",
                        "source_kind": "MANUAL_ACCOUNT_SNAPSHOT_FIXTURE",
                        "sanitized_basename": "account_holding_test.json",
                        "relative_path": "fixtures/account_read/account_holding_test.json",
                        "available_at": "2026-06-26T15:36:00+09:00",
                    },
                }
            ],
            "total_market_value": 83100.0,
            "total_equity": 9883100.0,
        },
        "audit_records": [
            {
                "audit_record_id": "account-read-audit-test",
                "created_at": "2026-06-26T16:30:00+09:00",
                "source_path": "fixtures/account_read/account_read_fixture.json",
                "operator_context": "offline account read unit test",
                "redaction_applied": True,
                "contains_secret_material": False,
                "contains_token_material": False,
                "contains_account_material": False,
            }
        ],
    }


def test_account_read_pipeline_input_is_safe():
    loaded = AccountReadPipelineInput.model_validate(account_read_payload())
    assert loaded.no_network is True
    assert loaded.no_env_read is True
    assert loaded.no_account_mutation is True


def test_account_read_fixture_loader_reads_local_json(tmp_path):
    fixture_file = tmp_path / "account_read_fixture.json"
    fixture_file.write_text(json.dumps(account_read_payload()), encoding="utf-8")
    loaded = load_account_read_fixture(fixture_file)
    assert loaded.snapshot_fixture.metadata.account_ref.startswith("acct-redacted")
