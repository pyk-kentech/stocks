from stock_risk_mcp.kiwoom_real_readonly_models import (
    KiwoomCredentials,
    KiwoomCredentialSource,
    KiwoomRealNetworkConfig,
)
from stock_risk_mcp.kiwoom_real_readonly_smoke import KiwoomRealReadOnlySmokeService
from stock_risk_mcp.repository import RiskRepository


class FakeEndpointService:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def request(self, endpoint_id, body):
        self.calls.append(endpoint_id)
        return self.results[endpoint_id]


def _config():
    return KiwoomRealNetworkConfig(
        enabled=True, credential_source=KiwoomCredentialSource.ENV,
        allow_auth_token_request=True,
    )


def _run(tmp_path, results):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    endpoint_service = FakeEndpointService(results)
    smoke = KiwoomRealReadOnlySmokeService(
        repository=repository,
        credential_loader=lambda *args, **kwargs: KiwoomCredentials(
            appkey="fake-app", secretkey="fake-secret", source=KiwoomCredentialSource.ENV
        ),
        service_factory=lambda config, credentials: endpoint_service,
    )
    run = smoke.run(_config(), list(results), dry_run=False)
    return run, endpoint_service, repository


def test_execution_aggregates_completed_and_persists_report(tmp_path):
    run, endpoint_service, repository = _run(tmp_path, {
        "ka10001": {"status": "COMPLETED", "status_code": 200},
        "ka10004": {"status": "COMPLETED", "status_code": 200},
    })
    assert run.status.value == "COMPLETED"
    assert run.success_count == 2
    assert run.failure_count == 0
    assert endpoint_service.calls == ["ka10001", "ka10004"]
    assert repository.get_kiwoom_real_readonly_smoke_report(run.smoke_run_id).steps


def test_execution_continues_after_failure_and_reports_partial(tmp_path):
    run, endpoint_service, _ = _run(tmp_path, {
        "ka10001": {"status": "FAILED", "status_code": 401, "error": "token auth failed"},
        "ka10004": {"status": "COMPLETED", "status_code": 200},
    })
    assert run.status.value == "PARTIAL"
    assert run.success_count == 1
    assert run.failure_count == 1
    assert endpoint_service.calls == ["ka10001", "ka10004"]
    assert run.steps[0].sanitized_error == "sensitive error redacted"


def test_execution_reports_failed_when_no_endpoint_completes(tmp_path):
    run, _, _ = _run(tmp_path, {
        "ka10001": {"status": "FAILED", "status_code": 500, "error": "network timeout"},
    })
    assert run.status.value == "FAILED"
    assert run.success_count == 0
    assert run.failure_count == 1
