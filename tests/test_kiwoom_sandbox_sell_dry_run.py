from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomRealNetworkEnvironment
from stock_risk_mcp.kiwoom_sandbox_sell_dry_run import KiwoomSandboxSellDryRunService
from stock_risk_mcp.kiwoom_sandbox_sell_schema import SandboxSellDryRunStatus
from stock_risk_mcp.kiwoom_sandbox_sell_schema import (
    SandboxSellSchemaVerificationReport,
    SandboxSellSchemaVerificationStatus,
)
from stock_risk_mcp.kiwoom_sandbox_sell_schema_verifier import KiwoomSandboxSellSchemaVerifier
from stock_risk_mcp.local_ledger_service import LocalLedgerService
from stock_risk_mcp.order_intent import ExecutionMode, OrderSide, OrderType
from stock_risk_mcp.order_intent_service import OrderIntentService
from stock_risk_mcp.order_risk_gate import RiskGateConfig
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.realtime_market_data import MarketRegion
from stock_risk_mcp.sell_safety_gate import SellSafetyGate
from tests.test_order_risk_gate import _intent


def _approved_sell(repository):
    service = OrderIntentService(repository)
    intent = service.create(_intent(
        ticker="005930", region=MarketRegion.KR, side=OrderSide.SELL,
        order_type=OrderType.LIMIT, quantity=1, limit_price=70000, stop_loss_price=None,
    ))
    LocalLedgerService(repository).upsert_position("005930", MarketRegion.KR, 2)
    SellSafetyGate(repository).evaluate(intent)
    service.evaluate(intent.order_intent_id, RiskGateConfig(), ExecutionMode.SANDBOX, True)
    return intent


def test_current_unverified_schema_blocks_sell_dry_run_without_network(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    intent = _approved_sell(repository)
    KiwoomSandboxSellSchemaVerifier(repository).verify()

    result = KiwoomSandboxSellDryRunService(repository).run(intent.order_intent_id)

    assert result.status == SandboxSellDryRunStatus.BLOCKED
    assert "SELL_SANDBOX_ORDER_SCHEMA_NOT_VERIFIED" in result.reasons_json
    assert result.metadata_json["network_called"] is False
    assert result.metadata_json["credentials_read"] is False
    assert result.metadata_json["orders_submitted"] is False


def test_sell_dry_run_blocks_missing_safety_risk_execution_and_insufficient_ledger(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    intent = OrderIntentService(repository).create(_intent(
        ticker="005930", region=MarketRegion.KR, side=OrderSide.SELL,
        quantity=2, stop_loss_price=None,
    ))
    LocalLedgerService(repository).upsert_position("005930", MarketRegion.KR, 1)

    result = KiwoomSandboxSellDryRunService(repository).run(intent.order_intent_id)

    assert "APPROVED_SELL_SAFETY_DECISION_REQUIRED" in result.reasons_json
    assert "APPROVED_RISK_GATE_DECISION_REQUIRED" in result.reasons_json
    assert "APPROVED_SANDBOX_EXECUTION_GATE_DECISION_REQUIRED" in result.reasons_json
    assert "INSUFFICIENT_LOCAL_LEDGER_QUANTITY" in result.reasons_json


def test_market_and_prod_sell_dry_run_are_blocked(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    intent = OrderIntentService(repository).create(_intent(
        ticker="005930", region=MarketRegion.KR, side=OrderSide.SELL,
        order_type=OrderType.MARKET, quantity=1, limit_price=None, stop_loss_price=None,
    ))

    result = KiwoomSandboxSellDryRunService(repository).run(
        intent.order_intent_id, environment=KiwoomRealNetworkEnvironment.PROD_READONLY_DISABLED
    )

    assert "LIMIT_ORDER_REQUIRED" in result.reasons_json
    assert "MOCK_ENVIRONMENT_REQUIRED" in result.reasons_json


def test_fractional_and_blocked_product_sell_dry_run_are_blocked(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    intent = OrderIntentService(repository).create(_intent(
        ticker="005930", region=MarketRegion.KR, side=OrderSide.SELL,
        quantity=1.5, stop_loss_price=None,
        metadata_json={"margin": True, "short": True, "instrument_type": "OPTION", "leverage": 2},
    ))

    result = KiwoomSandboxSellDryRunService(repository).run(intent.order_intent_id)

    assert "POSITIVE_INTEGER_QUANTITY_REQUIRED" in result.reasons_json
    assert "MARGIN_SHORT_OPTIONS_FUTURES_DISABLED" in result.reasons_json
    assert "LEVERAGE_DISABLED" in result.reasons_json


def test_explicit_verified_report_allows_dry_run_but_submits_no_order(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    intent = _approved_sell(repository)
    report = SandboxSellSchemaVerificationReport(
        status=SandboxSellSchemaVerificationStatus.VERIFIED,
        endpoint_id="verified-fixture",
        endpoint_path="/verified-fixture",
        endpoint_classification="ORDER",
    )
    repository.save_kiwoom_sandbox_sell_schema_report(report)

    result = KiwoomSandboxSellDryRunService(repository).run(intent.order_intent_id)

    assert result.status == SandboxSellDryRunStatus.APPROVED_FOR_DRY_RUN
    assert result.reasons_json == []
    assert result.metadata_json["orders_submitted"] is False
