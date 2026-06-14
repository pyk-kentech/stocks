from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentials, KiwoomCredentialSource
from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomRealNetworkEnvironment
from stock_risk_mcp.kiwoom_sandbox_order_models import KiwoomSandboxOrderConfig
from stock_risk_mcp.kiwoom_sandbox_order_service import KiwoomSandboxOrderService
from stock_risk_mcp.kiwoom_sandbox_order_transport import FakeKiwoomSandboxOrderTransport
from stock_risk_mcp.order_intent import ExecutionMode
from stock_risk_mcp.order_intent_service import OrderIntentService
from stock_risk_mcp.order_risk_gate import RiskGateConfig
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.realtime_market_data import MarketRegion
from tests.test_order_risk_gate import _intent


def _approved(repository):
    intent_service = OrderIntentService(repository)
    intent = intent_service.create(_intent(ticker="005930", region=MarketRegion.KR, quantity=1))
    intent_service.evaluate(
        intent.order_intent_id, RiskGateConfig(), ExecutionMode.SANDBOX,
        enable_sandbox_order=True,
    )
    return intent


def _config(**changes):
    values = dict(
        enable_real_network=True, enable_sandbox_order=True,
        credential_source=KiwoomCredentialSource.ENV, allow_auth_token_request=True,
    )
    values.update(changes)
    return KiwoomSandboxOrderConfig(**values)


def _service(tmp_path, transport=None):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    transport = transport or FakeKiwoomSandboxOrderTransport()
    service = KiwoomSandboxOrderService(
        repository, credential_loader=lambda *args, **kwargs: KiwoomCredentials(
            appkey="fake", secretkey="fake", account_number="fake-account",
            source=KiwoomCredentialSource.ENV,
        ), transport_factory=lambda config, credentials: transport,
    )
    return repository, service, transport


def test_default_health_and_plan_are_offline(tmp_path):
    repository, service, transport = _service(tmp_path)
    intent = OrderIntentService(repository).create(_intent(ticker="005930", region=MarketRegion.KR))
    assert service.health().status == "DISABLED"
    assert service.plan(intent.order_intent_id).would_submit is False
    assert transport.calls == []


def test_dry_run_validates_approved_sandbox_without_credentials_or_transport(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    intent = _approved(repository)
    service = KiwoomSandboxOrderService(
        repository,
        credential_loader=lambda *args: (_ for _ in ()).throw(AssertionError("credentials read")),
        transport_factory=lambda *args: (_ for _ in ()).throw(AssertionError("transport built")),
    )
    result = service.submit(intent.order_intent_id, _config(), dry_run=True)
    assert result["receipt"].status == "DRY_RUN"


def test_submit_requires_sandbox_gate_and_rejects_duplicate_before_transport(tmp_path):
    repository, service, transport = _service(tmp_path)
    unapproved = OrderIntentService(repository).create(_intent(ticker="000660", region=MarketRegion.KR, quantity=1))
    assert service.submit(unapproved.order_intent_id, _config())["receipt"].status == "BLOCKED"
    intent = _approved(repository)
    first = service.submit(intent.order_intent_id, _config())
    second = service.submit(intent.order_intent_id, _config())
    assert first["receipt"].status == "ACCEPTED"
    assert second["receipt"].status == "REJECTED"
    assert "duplicate" in second["receipt"].sanitized_error
    assert len(transport.calls) == 1


def test_submit_blocks_sell_and_invalid_runtime_config(tmp_path):
    repository, service, transport = _service(tmp_path)
    intent = _approved(repository)
    sell = OrderIntentService(repository).create(_intent(
        ticker="005930", region=MarketRegion.KR, quantity=1, side="SELL", stop_loss_price=None,
    ))
    OrderIntentService(repository).evaluate(
        sell.order_intent_id, RiskGateConfig(), ExecutionMode.SANDBOX, enable_sandbox_order=True
    )
    assert service.submit(sell.order_intent_id, _config())["receipt"].status == "BLOCKED"
    assert "SELL_SANDBOX_ORDER_SCHEMA_NOT_VERIFIED" in service.plan(sell.order_intent_id).blocked_reasons
    assert service.submit(intent.order_intent_id, _config(enable_sandbox_order=False))["receipt"].status == "BLOCKED"
    assert transport.calls == []


def test_submit_blocks_non_mock_wrong_url_missing_credentials_and_auth(tmp_path):
    repository, service, transport = _service(tmp_path)
    intent = _approved(repository)
    configs = [
        _config(environment=KiwoomRealNetworkEnvironment.PROD_READONLY_DISABLED),
        _config(base_url="https://mockapi.kiwoom.com/"),
        _config(credential_source=KiwoomCredentialSource.NONE),
        _config(allow_auth_token_request=False),
    ]
    assert all(service.submit(intent.order_intent_id, config)["receipt"].status == "BLOCKED" for config in configs)
    assert transport.calls == []


def test_cancel_and_status_are_bounded_and_known_order_only(tmp_path):
    repository, service, _ = _service(tmp_path)
    intent = _approved(repository)
    submitted = service.submit(intent.order_intent_id, _config())
    order_id = submitted["receipt"].broker_order_id
    assert service.cancel([order_id], _config())[0].status == "CANCELLED"
    assert service.status([order_id])[0].broker_order_id == order_id
    assert service.status(["unknown"])[0].status == "BLOCKED"
    try:
        service.cancel(["a", "b", "c", "d"], _config())
        assert False
    except ValueError:
        pass
    try:
        service.status(["a", "b", "c", "d"])
        assert False
    except ValueError:
        pass
