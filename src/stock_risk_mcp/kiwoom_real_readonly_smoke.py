from __future__ import annotations

from datetime import datetime

from stock_risk_mcp.kiwoom_credentials import load_kiwoom_credentials
from stock_risk_mcp.kiwoom_official_manifest import KiwoomOfficialEndpointClass, load_kiwoom_official_manifest
from stock_risk_mcp.kiwoom_real_readonly_models import (
    KiwoomCredentialSource,
    KiwoomRealNetworkConfig,
    KiwoomRealNetworkEnvironment,
)
from stock_risk_mcp.kiwoom_real_readonly_smoke_models import (
    KiwoomRealReadOnlySmokeRun,
    KiwoomRealReadOnlySmokeStatus,
    KiwoomRealReadOnlySmokeStep,
    sanitized_smoke_run,
)
from stock_risk_mcp.kiwoom_real_readonly_transport import KIWOOM_MOCK_BASE_URL, V214_READONLY_API_IDS


SMOKE_ENDPOINT_SETS = {"minimal": ["ka10001"]}
SMOKE_MAX_ENDPOINTS = 3


def build_smoke_plan() -> dict:
    return {
        "status": KiwoomRealReadOnlySmokeStatus.PLANNED.value,
        "endpoint_sets": SMOKE_ENDPOINT_SETS,
        "allowed_endpoint_ids": sorted(V214_READONLY_API_IDS),
        "max_endpoints_per_run": SMOKE_MAX_ENDPOINTS,
        "environment": KiwoomRealNetworkEnvironment.MOCK.value,
        "base_url": KIWOOM_MOCK_BASE_URL,
        "required_flags": [
            "--enable-real-network", "--environment MOCK",
            "--base-url https://mockapi.kiwoom.com",
            "--credential-source ENV|FILE_EXPLICIT", "--allow-auth-token-request",
        ],
        "warnings": [
            "Manual MOCK read-only smoke only.",
            "No orders, account reads, WebSocket, PROD, or live trading.",
        ],
        "network_called": False,
        "credentials_read": False,
    }


def select_smoke_endpoints(endpoint_ids: list[str] | None, endpoint_set: str | None) -> list[str]:
    selected = list(endpoint_ids or [])
    if endpoint_set:
        if endpoint_set not in SMOKE_ENDPOINT_SETS:
            raise ValueError("unknown endpoint set")
        selected.extend(SMOKE_ENDPOINT_SETS[endpoint_set])
    if not selected:
        selected.extend(SMOKE_ENDPOINT_SETS["minimal"])
    deduped = list(dict.fromkeys(selected))
    if len(deduped) > SMOKE_MAX_ENDPOINTS:
        raise ValueError(f"maximum {SMOKE_MAX_ENDPOINTS} endpoints per smoke run")
    manifest = {item.api_id: item for item in load_kiwoom_official_manifest().endpoints}
    for endpoint_id in deduped:
        endpoint = manifest.get(endpoint_id)
        if endpoint_id not in V214_READONLY_API_IDS or endpoint is None:
            raise ValueError(f"endpoint is not in smoke READ_ONLY allowlist: {endpoint_id}")
        if endpoint.read_write_class != KiwoomOfficialEndpointClass.READ_ONLY or "websocket" in endpoint.path.lower():
            raise ValueError(f"endpoint is not an allowed REST READ_ONLY endpoint: {endpoint_id}")
    return deduped


class KiwoomRealReadOnlySmokeService:
    def __init__(self, repository=None, credential_loader=None, service_factory=None) -> None:
        self.repository = repository
        self.credential_loader = credential_loader or load_kiwoom_credentials
        self.service_factory = service_factory

    def run(
        self,
        config: KiwoomRealNetworkConfig,
        endpoint_ids: list[str] | None = None,
        endpoint_set: str | None = None,
        dry_run: bool = False,
    ) -> KiwoomRealReadOnlySmokeRun:
        errors = _preflight_errors(config)
        try:
            selected = select_smoke_endpoints(endpoint_ids, endpoint_set)
        except ValueError as error:
            selected = list(dict.fromkeys(endpoint_ids or []))
            errors.append(str(error))
        run = KiwoomRealReadOnlySmokeRun(
            enabled=config.enabled, dry_run=dry_run, environment=config.environment,
            base_url_allowed=config.base_url == KIWOOM_MOCK_BASE_URL,
            credential_source=config.credential_source, endpoint_set=endpoint_set,
            endpoint_ids=selected,
            status=KiwoomRealReadOnlySmokeStatus.BLOCKED if errors else KiwoomRealReadOnlySmokeStatus.DRY_RUN,
            failure_count=len(selected) if errors else 0, errors=errors,
            metadata_json={"redacted": True, "network_called": False, "credentials_read": False},
        )
        if errors:
            run.completed_at = datetime.now()
            return self._finish(run)
        if dry_run:
            run.steps = [_dry_run_step(run.smoke_run_id, endpoint_id) for endpoint_id in selected]
            run.success_count = len(run.steps)
            run.completed_at = datetime.now()
            return self._finish(run)
        credentials = self.credential_loader(config.credential_source, config.credential_file)
        if not credentials.loaded:
            run.status = KiwoomRealReadOnlySmokeStatus.FAILED
            run.errors = credentials.errors or ["explicit credentials could not be loaded"]
            run.failure_count = len(selected)
            run.completed_at = datetime.now()
            return self._finish(run)
        if self.service_factory is None:
            run.status = KiwoomRealReadOnlySmokeStatus.FAILED
            run.errors = ["manual smoke execution service not configured"]
            run.failure_count = len(selected)
            run.completed_at = datetime.now()
            return self._finish(run)
        endpoint_service = self.service_factory(config, credentials)
        run.metadata_json["credentials_read"] = True
        run.metadata_json["network_called"] = True
        for endpoint_id in selected:
            run.steps.append(_execute_step(run.smoke_run_id, endpoint_id, endpoint_service))
        run.success_count = sum(step.success for step in run.steps)
        run.failure_count = len(run.steps) - run.success_count
        if run.success_count == len(run.steps):
            run.status = KiwoomRealReadOnlySmokeStatus.COMPLETED
        elif run.success_count:
            run.status = KiwoomRealReadOnlySmokeStatus.PARTIAL
        else:
            run.status = KiwoomRealReadOnlySmokeStatus.FAILED
        run.completed_at = datetime.now()
        return self._finish(run)

    def _finish(self, run: KiwoomRealReadOnlySmokeRun) -> KiwoomRealReadOnlySmokeRun:
        safe = sanitized_smoke_run(run)
        if self.repository is not None:
            self.repository.save_kiwoom_real_readonly_smoke_report(safe)
        return safe


def _preflight_errors(config: KiwoomRealNetworkConfig) -> list[str]:
    errors: list[str] = []
    if not config.enabled:
        errors.append("--enable-real-network is required")
    if config.environment != KiwoomRealNetworkEnvironment.MOCK:
        errors.append("environment must be MOCK")
    if config.base_url != KIWOOM_MOCK_BASE_URL:
        errors.append("base URL must exactly match https://mockapi.kiwoom.com")
    if config.credential_source not in {KiwoomCredentialSource.ENV, KiwoomCredentialSource.FILE_EXPLICIT}:
        errors.append("explicit credential source is required")
    if config.credential_source == KiwoomCredentialSource.FILE_EXPLICIT and config.credential_file is None:
        errors.append("explicit credential file is required")
    if not config.allow_auth_token_request:
        errors.append("--allow-auth-token-request is required")
    return errors


def _dry_run_step(smoke_run_id: str, endpoint_id: str) -> KiwoomRealReadOnlySmokeStep:
    endpoint = next(item for item in load_kiwoom_official_manifest().endpoints if item.api_id == endpoint_id)
    return KiwoomRealReadOnlySmokeStep(
        smoke_run_id=smoke_run_id, endpoint_id=endpoint_id, endpoint_path=endpoint.path,
        endpoint_classification=endpoint.read_write_class.value, request_status="DRY_RUN",
        success=True, metadata_json={"redacted": True, "network_called": False},
    )


def _execute_step(smoke_run_id: str, endpoint_id: str, endpoint_service) -> KiwoomRealReadOnlySmokeStep:
    endpoint = next(item for item in load_kiwoom_official_manifest().endpoints if item.api_id == endpoint_id)
    try:
        result = endpoint_service.request(endpoint_id, _smoke_request_body(endpoint_id))
        success = result.get("status") == "COMPLETED"
        return KiwoomRealReadOnlySmokeStep(
            smoke_run_id=smoke_run_id, endpoint_id=endpoint_id, endpoint_path=endpoint.path,
            endpoint_classification=endpoint.read_write_class.value,
            request_status=str(result.get("status", "FAILED")),
            response_status_code=result.get("status_code"), success=success,
            sanitized_error=result.get("error"),
            metadata_json={"redacted": True, "response_status_code": result.get("status_code")},
        )
    except Exception as error:
        return KiwoomRealReadOnlySmokeStep(
            smoke_run_id=smoke_run_id, endpoint_id=endpoint_id, endpoint_path=endpoint.path,
            endpoint_classification=endpoint.read_write_class.value,
            request_status="FAILED", success=False, sanitized_error=str(error),
            metadata_json={"redacted": True},
        )


def _smoke_request_body(endpoint_id: str) -> dict:
    bodies = {
        "ka10001": {"stk_cd": "005930"},
        "ka10004": {"stk_cd": "005930"},
        "ka10020": {"mrkt_tp": "0", "sort_tp": "1"},
        "ka10008": {"stk_cd": "005930"},
        "ka10080": {"stk_cd": "005930"},
        "ka10081": {"stk_cd": "005930"},
    }
    return bodies[endpoint_id]
