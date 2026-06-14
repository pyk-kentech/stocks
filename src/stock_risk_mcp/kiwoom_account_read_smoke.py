from stock_risk_mcp.kiwoom_account_read_gate import ACCOUNT_READ_API_IDS, select_account_read_endpoints
from stock_risk_mcp.kiwoom_account_read_models import KiwoomAccountReadConfig, KiwoomAccountReadStatus
from stock_risk_mcp.kiwoom_account_read_smoke_models import KiwoomAccountReadSmokeRun, KiwoomAccountReadSmokeStep


ACCOUNT_READ_SMOKE_ENDPOINT_SETS = {"minimal": ["kt00001"]}


def build_account_read_smoke_plan() -> dict:
    return {
        "status": "PLANNED",
        "endpoint_sets": ACCOUNT_READ_SMOKE_ENDPOINT_SETS,
        "allowed_endpoint_ids": sorted(ACCOUNT_READ_API_IDS),
        "hard_max_endpoints": 2,
        "environment": "MOCK",
        "base_url": "https://mockapi.kiwoom.com",
        "credentials_read": False,
        "network_called": False,
        "required_flags": [
            "--enable-real-network", "--enable-account-read", "--environment MOCK",
            "--base-url https://mockapi.kiwoom.com", "--credential-source ENV|FILE_EXPLICIT",
            "--allow-auth-token-request", "--confirm-account", "--account-fingerprint <confirmation>",
            "--i-understand-this-can-read-account-data", "--kill-switch-inactive",
        ],
        "warnings": ["PROD blocked", "LIVE blocked", "raw account data redacted"],
    }


def select_account_read_smoke_endpoints(endpoint_ids: list[str] | None, endpoint_set: str | None) -> list[str]:
    selected = list(endpoint_ids or [])
    if endpoint_set:
        if endpoint_set not in ACCOUNT_READ_SMOKE_ENDPOINT_SETS:
            raise ValueError("unknown account-read smoke endpoint set")
        selected.extend(ACCOUNT_READ_SMOKE_ENDPOINT_SETS[endpoint_set])
    if not selected:
        selected.extend(ACCOUNT_READ_SMOKE_ENDPOINT_SETS["minimal"])
    return select_account_read_endpoints(selected)


class KiwoomAccountReadSmokeService:
    def __init__(self, repository, account_read_service) -> None:
        self.repository = repository
        self.account_read_service = account_read_service

    def run(
        self,
        config: KiwoomAccountReadConfig,
        endpoint_ids: list[str] | None = None,
        endpoint_set: str | None = None,
        dry_run: bool = False,
    ) -> KiwoomAccountReadSmokeRun:
        try:
            selected = select_account_read_smoke_endpoints(endpoint_ids, endpoint_set)
        except ValueError as error:
            run = KiwoomAccountReadSmokeRun(
                status=KiwoomAccountReadStatus.BLOCKED, dry_run=dry_run,
                endpoint_set=endpoint_set, endpoint_ids=list(endpoint_ids or []),
                blocked_reasons=[str(error)],
                redacted_metadata_json={"network_called": False, "credentials_read": False},
            )
            self.repository.save_kiwoom_account_read_smoke_report(run)
            return run
        account_run = self.account_read_service.run(config, selected, dry_run)
        responses = {item.endpoint_id: item for item in account_run.responses}
        steps = []
        for request in account_run.requests:
            response = responses.get(request.endpoint_id)
            steps.append(KiwoomAccountReadSmokeStep(
                smoke_run_id="pending", endpoint_id=request.endpoint_id,
                request_status=request.request_status,
                response_status_code=response.response_status_code if response else None,
                success=request.request_status in {"DRY_RUN", "COMPLETED"},
                sanitized_error=response.sanitized_error if response else request.sanitized_error,
            ))
        run = KiwoomAccountReadSmokeRun(
            account_read_run_id=account_run.run_id, status=account_run.status,
            dry_run=dry_run, endpoint_set=endpoint_set, endpoint_ids=selected,
            success_count=sum(item.success for item in steps),
            failure_count=len(steps) - sum(item.success for item in steps),
            blocked_reasons=account_run.blocked_reasons, steps=steps,
            redacted_metadata_json={
                **account_run.redacted_metadata_json,
                "status_counts": {
                    "success": sum(item.success for item in steps),
                    "failed": len(steps) - sum(item.success for item in steps),
                },
            },
        )
        for step in run.steps:
            step.smoke_run_id = run.smoke_run_id
        self.repository.save_kiwoom_account_read_smoke_report(run)
        return run
