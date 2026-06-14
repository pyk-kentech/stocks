from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from stock_risk_mcp.kiwoom_account_read_gate import account_read_blocked_reasons, select_account_read_endpoints
from stock_risk_mcp.kiwoom_account_read_models import (
    KiwoomAccountReadConfig,
    KiwoomAccountReadReconcilePreview,
    KiwoomAccountReadRequest,
    KiwoomAccountReadResponse,
    KiwoomAccountReadRun,
    KiwoomAccountReadStatus,
    sanitize_account_error,
)
from stock_risk_mcp.kiwoom_credentials import load_kiwoom_credentials
from stock_risk_mcp.kiwoom_official_manifest import load_kiwoom_official_manifest
from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentialSource, KiwoomRealNetworkEnvironment


class KiwoomAccountReadService:
    def __init__(self, repository, credential_loader=None, transport_factory=None) -> None:
        self.repository = repository
        self.credential_loader = credential_loader or load_kiwoom_credentials
        self.transport_factory = transport_factory

    def health(self) -> KiwoomAccountReadRun:
        return KiwoomAccountReadRun(
            status=KiwoomAccountReadStatus.DISABLED, account_read_enabled=False,
            redacted_metadata_json={
                "network_called": False, "credentials_read": False,
                "supported_environment": "MOCK", "exact_base_url": "https://mockapi.kiwoom.com",
            },
        )

    def plan(self, config: KiwoomAccountReadConfig, endpoint_ids: list[str] | None = None) -> dict:
        reasons = account_read_blocked_reasons(config)
        try:
            selected = select_account_read_endpoints(endpoint_ids)
        except ValueError as error:
            selected, reasons = list(endpoint_ids or []), [*reasons, str(error)]
        return {
            "status": "BLOCKED" if reasons else "PLANNED", "would_run": not reasons,
            "endpoint_ids": selected, "blocked_reasons": reasons,
            "credentials_read": False, "network_called": False,
        }

    def run(self, config: KiwoomAccountReadConfig, endpoint_ids: list[str] | None = None, dry_run: bool = False) -> KiwoomAccountReadRun:
        plan = self.plan(config, endpoint_ids)
        run = KiwoomAccountReadRun(
            status=KiwoomAccountReadStatus.BLOCKED if plan["blocked_reasons"] else KiwoomAccountReadStatus.PLANNED,
            account_read_enabled=config.enable_real_network and config.enable_account_read, dry_run=dry_run,
            environment=config.environment, credential_source=config.credential_source,
            account_fingerprint=_fingerprint(config.account_fingerprint), endpoint_ids=plan["endpoint_ids"],
            blocked_reasons=plan["blocked_reasons"],
            redacted_metadata_json={"network_called": False, "credentials_read": False},
        )
        if run.blocked_reasons:
            return self._finish(run)
        run.requests = [self._request(run.run_id, endpoint_id, "DRY_RUN" if dry_run else "PLANNED") for endpoint_id in run.endpoint_ids]
        if dry_run:
            run.status = KiwoomAccountReadStatus.DRY_RUN
            return self._finish(run)
        credentials = self.credential_loader(config.credential_source, config.credential_file)
        if not credentials.loaded or not credentials.account_number:
            run.status = KiwoomAccountReadStatus.FAILED
            run.blocked_reasons = ["explicit credentials and account required"]
            return self._finish(run)
        if self.transport_factory is None:
            run.status = KiwoomAccountReadStatus.FAILED
            run.blocked_reasons = ["account-read transport not configured"]
            return self._finish(run)
        run.account_loaded = True
        run.redacted_metadata_json["credentials_read"] = True
        transport = self.transport_factory(config, credentials)
        run.redacted_metadata_json["network_called"] = True
        for request in run.requests:
            try:
                result = transport.request(request.endpoint_id)
                request.request_status = result.get("status", "FAILED")
                run.responses.append(KiwoomAccountReadResponse(
                    request_id=request.request_id, run_id=run.run_id, endpoint_id=request.endpoint_id,
                    response_status=result.get("status", "FAILED"),
                    response_status_code=result.get("status_code"),
                    normalized_summary_json=_normalize_summary(request.endpoint_id, result.get("body", {})),
                    sanitized_error=sanitize_account_error(result.get("error")),
                ))
            except Exception as error:
                request.request_status = "FAILED"
                run.responses.append(KiwoomAccountReadResponse(
                    request_id=request.request_id, run_id=run.run_id, endpoint_id=request.endpoint_id,
                    response_status="FAILED", sanitized_error=sanitize_account_error(str(error)),
                ))
        completed = sum(item.response_status == "COMPLETED" for item in run.responses)
        run.status = KiwoomAccountReadStatus.COMPLETED if completed == len(run.responses) else (
            KiwoomAccountReadStatus.PARTIAL if completed else KiwoomAccountReadStatus.FAILED
        )
        return self._finish(run)

    def reconcile_preview(
        self,
        run_id: str,
        kill_switch_inactive: bool = False,
        local_ledger_file: Path | None = None,
        include_redacted_symbol_details: bool = False,
    ) -> KiwoomAccountReadReconcilePreview:
        if not kill_switch_inactive:
            return self._save_preview(KiwoomAccountReadReconcilePreview(
                run_id=run_id, reconciliation_status="BLOCKED",
                redacted_metadata_json={"redacted": True, "blocked_reason": "kill switch must be explicitly inactive"},
            ))
        run = self.repository.get_kiwoom_account_read_report(run_id)
        remote = max((int(item.normalized_summary_json.get("symbol_count", 0)) for item in run.responses), default=0)
        if not run.responses:
            return self._save_preview(KiwoomAccountReadReconcilePreview(
                run_id=run_id, account_fingerprint=run.account_fingerprint,
                account_fingerprint_present=bool(run.account_fingerprint),
                reconciliation_status="ACCOUNT_DATA_UNAVAILABLE",
            ))
        if local_ledger_file is None or not Path(local_ledger_file).exists():
            return self._save_preview(KiwoomAccountReadReconcilePreview(
                run_id=run_id, account_fingerprint=run.account_fingerprint,
                account_fingerprint_present=bool(run.account_fingerprint),
                remote_symbol_count=remote, reconciliation_status="LOCAL_LEDGER_UNAVAILABLE",
            ))
        try:
            local_count = _local_ledger_symbol_count(Path(local_ledger_file))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return self._save_preview(KiwoomAccountReadReconcilePreview(
                run_id=run_id, account_fingerprint=run.account_fingerprint,
                account_fingerprint_present=bool(run.account_fingerprint),
                reconciliation_status="LOCAL_LEDGER_UNAVAILABLE",
                redacted_metadata_json={"redacted": True, "sanitized_error": "local ledger could not be read"},
            ))
        if include_redacted_symbol_details:
            return self._save_preview(KiwoomAccountReadReconcilePreview(
                run_id=run_id, account_fingerprint=run.account_fingerprint,
                account_fingerprint_present=bool(run.account_fingerprint), local_ledger_present=True,
                remote_symbol_count=remote, local_symbol_count=local_count,
                reconciliation_status="ACCOUNT_DETAILS_UNAVAILABLE",
            ))
        missing_local = max(remote - local_count, 0)
        missing_account = max(local_count - remote, 0)
        preview = KiwoomAccountReadReconcilePreview(
            run_id=run_id, account_fingerprint=run.account_fingerprint,
            account_fingerprint_present=bool(run.account_fingerprint), local_ledger_present=True,
            reconciliation_status="COMPLETED" if remote == local_count else "COMPLETED_WITH_MISMATCHES",
            remote_symbol_count=remote, local_symbol_count=local_count,
            symbol_count_compared=min(remote, local_count),
            missing_in_local_count=missing_local, missing_in_account_count=missing_account,
            mismatch_count=missing_local + missing_account,
            redacted_metadata_json={"redacted": True, "network_called": False},
        )
        return self._save_preview(preview)

    def _save_preview(self, preview: KiwoomAccountReadReconcilePreview) -> KiwoomAccountReadReconcilePreview:
        self.repository.save_kiwoom_account_read_reconcile_preview(preview)
        return preview

    def _finish(self, run: KiwoomAccountReadRun) -> KiwoomAccountReadRun:
        self.repository.save_kiwoom_account_read_report(run)
        return run

    @staticmethod
    def _request(run_id: str, endpoint_id: str, status: str) -> KiwoomAccountReadRequest:
        endpoint = next(item for item in load_kiwoom_official_manifest().endpoints if item.api_id == endpoint_id)
        return KiwoomAccountReadRequest(
            run_id=run_id, endpoint_id=endpoint_id, endpoint_path=endpoint.path,
            request_status=status,
        )


def _normalize_summary(endpoint_id: str, body: dict) -> dict:
    holdings = body.get("holdings") if isinstance(body.get("holdings"), list) else []
    fills = body.get("fills") if isinstance(body.get("fills"), list) else []
    symbols = {str(item.get("symbol")) for item in [*holdings, *fills] if isinstance(item, dict) and item.get("symbol")}
    return {
        "endpoint_id": endpoint_id,
        "currency": body.get("currency") if body.get("currency") in {"KRW", "USD"} else None,
        "symbol_count": len(symbols),
        "holding_count": len(holdings),
        "fill_count": len(fills),
    }


def _fingerprint(value: str | None) -> str | None:
    return sha256(value.encode("utf-8")).hexdigest()[:16] if value else None


def _local_ledger_symbol_count(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("symbols", []) if isinstance(payload, dict) else payload
    return len({
        str(item.get("symbol")).strip().upper()
        for item in records
        if isinstance(item, dict) and item.get("symbol")
    })
