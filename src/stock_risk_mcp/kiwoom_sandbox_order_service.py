from __future__ import annotations

from stock_risk_mcp.kiwoom_credentials import load_kiwoom_credentials
from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentialSource, KiwoomRealNetworkEnvironment
from stock_risk_mcp.kiwoom_sandbox_order_models import (
    KiwoomSandboxOrderConfig,
    KiwoomSandboxOrderPlan,
    KiwoomSandboxOrderReceipt,
    KiwoomSandboxOrderRequest,
    KiwoomSandboxOrderRun,
    KiwoomSandboxOrderStatus,
    KiwoomSandboxOrderStatusCheck,
    sanitize_sandbox_error,
)
from stock_risk_mcp.kiwoom_sandbox_order_transport import RealKiwoomSandboxOrderTransport
from stock_risk_mcp.kiwoom_sandbox_order_adapter import KiwoomSandboxOrderAdapter
from stock_risk_mcp.order_intent import ExecutionMode, OrderIntentStatus, OrderSide, OrderType
from stock_risk_mcp.realtime_market_data import MarketRegion


class KiwoomSandboxOrderService:
    def __init__(self, repository, credential_loader=None, transport_factory=None) -> None:
        self.repository = repository
        self.credential_loader = credential_loader or load_kiwoom_credentials
        self.transport_factory = transport_factory or (
            lambda config, credentials: KiwoomSandboxOrderAdapter(RealKiwoomSandboxOrderTransport(config, credentials))
        )

    def health(self) -> KiwoomSandboxOrderRun:
        return KiwoomSandboxOrderRun(
            operation="HEALTH", status=KiwoomSandboxOrderStatus.DISABLED, enabled=False,
            environment=KiwoomRealNetworkEnvironment.MOCK, credential_source=KiwoomCredentialSource.NONE,
            metadata_json={"network_called": False, "credentials_read": False, "base_url": "https://mockapi.kiwoom.com"},
        )

    def plan(self, intent_id: str) -> KiwoomSandboxOrderPlan:
        intent = self.repository.get_order_intent(intent_id)
        reasons = self._intent_reasons(intent)
        sell_safety = self.repository.get_latest_sell_safety_decision(intent_id)
        return KiwoomSandboxOrderPlan(
            intent_id=intent_id,
            risk_gate_status="APPROVED" if self._risk_approved(intent_id) else "BLOCKED",
            execution_gate_status="APPROVED" if self._execution_approved(intent_id) else "BLOCKED",
            order_type=intent.order_type, side=intent.side, quantity=intent.quantity,
            limit_price=intent.limit_price, stop_loss_present=intent.stop_loss_price is not None,
            blocked_reasons=reasons, would_submit=not reasons,
            sell_safety_status=sell_safety.status.value if sell_safety else None,
        )

    def submit(self, intent_id: str, config: KiwoomSandboxOrderConfig, dry_run: bool = False, client_order_id: str | None = None) -> dict:
        intent = self.repository.get_order_intent(intent_id)
        client_order_id = client_order_id or f"intent-{intent_id}"
        run = self._run("SUBMIT", config)
        request = self._request(run, intent, client_order_id)
        reasons = [*self._config_reasons(config), *self._intent_reasons(intent)]
        if self.repository.has_kiwoom_sandbox_client_order_id(client_order_id):
            reasons.append("duplicate client_order_id")
        if reasons:
            return self._finish(run, request, KiwoomSandboxOrderStatus.REJECTED if "duplicate client_order_id" in reasons else KiwoomSandboxOrderStatus.BLOCKED, reasons[0])
        if dry_run:
            return self._finish(run, request, KiwoomSandboxOrderStatus.DRY_RUN, None)
        credentials = self.credential_loader(config.credential_source, config.credential_file)
        if not credentials.loaded or not credentials.account_number:
            return self._finish(run, request, KiwoomSandboxOrderStatus.FAILED, "explicit credentials and account required")
        run.account_loaded = True
        adapter = self.transport_factory(config, credentials)
        body = {
            "client_order_id": client_order_id, "ticker": intent.ticker,
            "quantity": int(intent.quantity), "limit_price": intent.limit_price,
            "account_number": credentials.account_number,
        }
        result = adapter.submit(body) if hasattr(adapter, "submit") else adapter.post("kt10000", body)
        return self._finish(run, request, KiwoomSandboxOrderStatus(result["status"]), result.get("error"), result)

    def cancel(self, broker_order_ids: list[str], config: KiwoomSandboxOrderConfig) -> list[KiwoomSandboxOrderReceipt]:
        if len(broker_order_ids) > 3:
            raise ValueError("maximum 3 sandbox cancels per run")
        results = []
        for broker_order_id in broker_order_ids:
            prior = self.repository.get_kiwoom_sandbox_receipt_by_broker_order_id(broker_order_id)
            if prior is None:
                results.append(self._standalone(broker_order_id, KiwoomSandboxOrderStatus.BLOCKED, "known sandbox order required"))
                continue
            reasons = self._config_reasons(config)
            if reasons:
                results.append(self._standalone(broker_order_id, KiwoomSandboxOrderStatus.BLOCKED, reasons[0]))
                continue
            credentials = self.credential_loader(config.credential_source, config.credential_file)
            if not credentials.loaded or not credentials.account_number:
                results.append(self._standalone(broker_order_id, KiwoomSandboxOrderStatus.FAILED, "explicit credentials and account required"))
                continue
            adapter = self.transport_factory(config, credentials)
            body = {"broker_order_id": broker_order_id, "account_number": credentials.account_number}
            result = adapter.cancel(body) if hasattr(adapter, "cancel") else adapter.post("kt10003", body)
            receipt = self._standalone(broker_order_id, KiwoomSandboxOrderStatus(result["status"]), result.get("error"))
            self.repository.save_kiwoom_sandbox_order_receipt(receipt)
            results.append(receipt)
        return results

    def status(self, broker_order_ids: list[str]) -> list[KiwoomSandboxOrderStatusCheck]:
        if len(broker_order_ids) > 3:
            raise ValueError("maximum 3 sandbox status checks per run")
        checks = []
        for broker_order_id in broker_order_ids:
            receipt = self.repository.get_kiwoom_sandbox_receipt_by_broker_order_id(broker_order_id)
            check = KiwoomSandboxOrderStatusCheck(
                broker_order_id=broker_order_id,
                status=receipt.status if receipt else KiwoomSandboxOrderStatus.BLOCKED,
                metadata_json={"network_called": False},
            )
            self.repository.save_kiwoom_sandbox_order_status_check(check)
            checks.append(check)
        return checks

    def _intent_reasons(self, intent) -> list[str]:
        reasons = []
        if not self._risk_approved(intent.order_intent_id):
            reasons.append("approved risk gate decision required")
        if not self._execution_approved(intent.order_intent_id):
            reasons.append("approved SANDBOX execution gate decision required")
        if intent.status != OrderIntentStatus.EXECUTION_APPROVED:
            reasons.append("order intent is not execution approved")
        if intent.region != MarketRegion.KR:
            reasons.append("KR equity only")
        if intent.order_type != OrderType.LIMIT:
            reasons.append("LIMIT orders only")
        if intent.side != OrderSide.BUY:
            reasons.append("SELL_SANDBOX_ORDER_SCHEMA_NOT_VERIFIED")
        if intent.quantity is None or intent.quantity <= 0 or not float(intent.quantity).is_integer():
            reasons.append("positive integer quantity required")
        if intent.limit_price is None or intent.limit_price <= 0:
            reasons.append("positive limit price required")
        if intent.side == OrderSide.BUY and intent.stop_loss_price is None:
            reasons.append("BUY stop-loss required")
        metadata = intent.metadata_json
        if metadata.get("margin") or metadata.get("short") or str(metadata.get("instrument_type", "")).upper() in {"OPTION", "OPTIONS", "FUTURE", "FUTURES"}:
            reasons.append("margin/short/options/futures disabled")
        try:
            if float(metadata.get("leverage", 1)) > 1:
                reasons.append("leverage disabled")
        except (TypeError, ValueError):
            reasons.append("invalid leverage")
        return list(dict.fromkeys(reasons))

    def _config_reasons(self, config):
        reasons = []
        if not config.enable_real_network: reasons.append("--enable-real-network required")
        if not config.enable_sandbox_order: reasons.append("--enable-sandbox-order required")
        if config.environment != KiwoomRealNetworkEnvironment.MOCK: reasons.append("MOCK environment required")
        if config.base_url != "https://mockapi.kiwoom.com": reasons.append("exact MOCK base URL required")
        if config.credential_source not in {KiwoomCredentialSource.ENV, KiwoomCredentialSource.FILE_EXPLICIT}: reasons.append("explicit credentials required")
        if config.credential_source == KiwoomCredentialSource.FILE_EXPLICIT and config.credential_file is None: reasons.append("explicit credential file required")
        if not config.allow_auth_token_request: reasons.append("--allow-auth-token-request required")
        return reasons

    def _risk_approved(self, intent_id):
        decision = self.repository.get_latest_risk_gate_decision(intent_id)
        return bool(decision and decision.approved)

    def _execution_approved(self, intent_id):
        decision = self.repository.get_latest_execution_gate_decision(intent_id)
        return bool(decision and decision.approved and decision.execution_mode == ExecutionMode.SANDBOX)

    def _run(self, operation, config):
        return KiwoomSandboxOrderRun(
            operation=operation, status=KiwoomSandboxOrderStatus.PLANNED,
            enabled=config.enable_real_network and config.enable_sandbox_order,
            environment=config.environment, credential_source=config.credential_source,
            metadata_json={"redacted": True},
        )

    def _request(self, run, intent, client_order_id):
        return KiwoomSandboxOrderRequest(
            run_id=run.run_id, intent_id=intent.order_intent_id, client_order_id=client_order_id,
            endpoint_id="kt10000", endpoint_path="/api/dostk/ordr", order_side=intent.side,
            order_type=intent.order_type, quantity=int(intent.quantity or 0),
            limit_price=float(intent.limit_price or 0), request_status="CREATED", metadata_json={"redacted": True},
        )

    def _finish(self, run, request, status, error, result=None):
        result = result or {}
        run.status = status
        receipt = KiwoomSandboxOrderReceipt(
            request_id=request.request_id, run_id=run.run_id, intent_id=request.intent_id,
            client_order_id=request.client_order_id, status=status,
            success=status in {KiwoomSandboxOrderStatus.ACCEPTED, KiwoomSandboxOrderStatus.CANCELLED, KiwoomSandboxOrderStatus.DRY_RUN},
            broker_order_id=result.get("broker_order_id"), response_status_code=result.get("status_code"),
            sanitized_error=sanitize_sandbox_error(error), metadata_json={"redacted": True},
        )
        self.repository.save_kiwoom_sandbox_order_run(run)
        self.repository.save_kiwoom_sandbox_order_request(request)
        self.repository.save_kiwoom_sandbox_order_receipt(receipt)
        return {"run": run, "request": request, "receipt": receipt}

    @staticmethod
    def _standalone(broker_order_id, status, error):
        return KiwoomSandboxOrderReceipt(
            request_id="sandbox-operation", run_id="sandbox-operation", intent_id="sandbox-operation",
            client_order_id="sandbox-operation", status=status, success=status == KiwoomSandboxOrderStatus.CANCELLED,
            broker_order_id=broker_order_id, sanitized_error=sanitize_sandbox_error(error),
        )
