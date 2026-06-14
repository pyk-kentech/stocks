from stock_risk_mcp.kiwoom_sandbox_sell_schema import (
    SandboxSellDryRunDecision,
    SandboxSellDryRunStatus,
)
from stock_risk_mcp.kiwoom_sandbox_sell_schema_verifier import KiwoomSandboxSellSchemaVerifier
from stock_risk_mcp.repository import RiskRepository


def test_sell_schema_report_fields_and_dry_run_are_persisted_safely(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    report = KiwoomSandboxSellSchemaVerifier(repository).verify()
    dry_run = SandboxSellDryRunDecision(
        order_intent_id="intent-1",
        status=SandboxSellDryRunStatus.BLOCKED,
        schema_report_id=report.report_id,
        reasons_json=["SELL_SANDBOX_ORDER_SCHEMA_NOT_VERIFIED"],
    )
    repository.save_kiwoom_sandbox_sell_dry_run(dry_run)

    loaded = repository.get_kiwoom_sandbox_sell_schema_report(report.report_id)
    payload = loaded.model_dump_json().lower()

    assert repository.list_kiwoom_sandbox_sell_schema_reports()
    assert repository.list_kiwoom_sandbox_sell_schema_fields(report.report_id)
    assert repository.list_kiwoom_sandbox_sell_dry_runs()
    assert all(item not in payload for item in ("12345678", "bearer real-token", "real-secret"))
