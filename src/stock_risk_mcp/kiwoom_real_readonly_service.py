from __future__ import annotations

from stock_risk_mcp.kiwoom_official_manifest import load_kiwoom_official_manifest
from stock_risk_mcp.kiwoom_real_readonly_models import (
    KiwoomCredentials,
    KiwoomCredentialSource,
    KiwoomRealNetworkConfig,
    KiwoomRealReadOnlyRequestAudit,
    KiwoomRealReadOnlyResponseAudit,
    KiwoomRealReadOnlyRun,
)
from stock_risk_mcp.kiwoom_real_readonly_transport import (
    KiwoomRealReadOnlyPolicyError,
    RealKiwoomReadOnlyHttpTransport,
    RealKiwoomTokenProvider,
)


class KiwoomRealReadOnlyService:
    def __init__(self, repository, config=None, credentials=None, transport=None) -> None:
        self.repository = repository
        self.config = config or KiwoomRealNetworkConfig()
        self.credentials = credentials or KiwoomCredentials(source=KiwoomCredentialSource.NONE)
        self.transport = transport or RealKiwoomReadOnlyHttpTransport(
            self.config, self.credentials, RealKiwoomTokenProvider()
        )

    def health(self) -> dict:
        status = "READY" if self.config.enabled and self.credentials.loaded else "DISABLED"
        run = self._save_run(status)
        return {
            "run_id": run.run_id,
            "status": status,
            "environment": self.config.environment.value,
            "base_url": self.config.base_url,
            **self.credentials.safe_summary(),
            "external_network_call_made": False,
        }

    def request(self, api_id: str, body: dict) -> dict:
        run = KiwoomRealReadOnlyRun(
            enabled=self.config.enabled, credential_source=self.credentials.source, status="RUNNING",
            metadata_json={
                "environment": self.config.environment.value,
                "base_url": self.config.base_url,
                "redacted": True,
            },
        )
        endpoint = next((item for item in load_kiwoom_official_manifest().endpoints if item.api_id == api_id), None)
        path = endpoint.path if endpoint else "<unknown>"
        try:
            result = self.transport.post(api_id, body)
            status = result["status"]
            error = result.get("error")
        except KiwoomRealReadOnlyPolicyError as exc:
            result = {"status": "BLOCKED", "error": str(exc)}
            status = "BLOCKED"
            error = str(exc)
        except Exception as exc:
            result = {"status": "FAILED", "error": str(exc)}
            status = "FAILED"
            error = str(exc)
        run.status = status
        self.repository.save_kiwoom_real_readonly_run(run)
        request = KiwoomRealReadOnlyRequestAudit(
            run_id=run.run_id, api_id=api_id, path=path,
            classification=endpoint.read_write_class.value if endpoint else "UNKNOWN_REVIEW_REQUIRED",
            status=status, error=error,
            metadata_json={"request_field_names": _safe_request_field_names(body), "redacted": True},
        )
        response = KiwoomRealReadOnlyResponseAudit(
            request_id=request.request_id, status=status, error=error,
            metadata_json={"status_code": result.get("status_code"), "redacted": True},
        )
        self.repository.save_kiwoom_real_readonly_request(request)
        self.repository.save_kiwoom_real_readonly_response(response)
        return {
            **result, "run_id": run.run_id, "request_id": request.request_id,
            "response_id": response.response_id, **self.credentials.safe_summary(),
        }

    def _save_run(self, status: str) -> KiwoomRealReadOnlyRun:
        run = KiwoomRealReadOnlyRun(
            enabled=self.config.enabled, credential_source=self.credentials.source, status=status,
            metadata_json={
                "environment": self.config.environment.value,
                "base_url": self.config.base_url,
                "redacted": True,
            },
        )
        self.repository.save_kiwoom_real_readonly_run(run)
        return run


def _safe_request_field_names(body: dict) -> list[str]:
    forbidden = ("secret", "token", "auth", "appkey", "account")
    return sorted(str(key) for key in body if not any(item in str(key).lower() for item in forbidden))
