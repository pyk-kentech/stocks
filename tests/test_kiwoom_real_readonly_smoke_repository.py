from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentialSource, KiwoomRealNetworkEnvironment
from stock_risk_mcp.kiwoom_real_readonly_smoke_models import (
    KiwoomRealReadOnlySmokeRun,
    KiwoomRealReadOnlySmokeStatus,
    KiwoomRealReadOnlySmokeStep,
)
from stock_risk_mcp.repository import RiskRepository


def test_smoke_report_save_list_show_is_redacted(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    run = KiwoomRealReadOnlySmokeRun(
        enabled=True, dry_run=False, environment=KiwoomRealNetworkEnvironment.MOCK,
        base_url_allowed=True, credential_source=KiwoomCredentialSource.FILE_EXPLICIT,
        endpoint_ids=["ka10001"], status=KiwoomRealReadOnlySmokeStatus.FAILED,
        errors=[
            "authorization Bearer token-value secretkey secret-value",
            "failed to load explicit credential file: C:/secret-dir/key.json",
        ],
        metadata_json={"credential_file": "secret-dir/key.json", "appkey": "app-value", "safe": "kept"},
    )
    step = KiwoomRealReadOnlySmokeStep(
        smoke_run_id=run.smoke_run_id, endpoint_id="ka10001",
        endpoint_path="/api/dostk/stkinfo", endpoint_classification="READ_ONLY",
        request_status="FAILED", sanitized_error="account_number 123-45 token token-value",
        metadata_json={"authorization": "Bearer token-value", "status_code": 401},
    )
    run.steps = [step]

    repository.save_kiwoom_real_readonly_smoke_report(run)

    listed = repository.list_kiwoom_real_readonly_smoke_runs()
    shown = repository.get_kiwoom_real_readonly_smoke_report(run.smoke_run_id)
    serialized = str(listed) + str(shown)
    for forbidden in ("token-value", "secret-value", "app-value", "secret-dir", "123-45", "authorization"):
        assert forbidden not in serialized.lower()
    assert shown.metadata_json["safe"] == "kept"
    assert shown.steps[0].metadata_json["status_code"] == 401
