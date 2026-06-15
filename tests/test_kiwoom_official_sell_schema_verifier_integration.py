from stock_risk_mcp.kiwoom_official_sell_schema_evidence import (
    OfficialSellSchemaEvidenceReviewStatus,
)
from stock_risk_mcp.kiwoom_official_sell_schema_evidence_service import (
    KiwoomOfficialSellSchemaEvidenceService,
)
from stock_risk_mcp.kiwoom_sandbox_sell_dry_run import KiwoomSandboxSellDryRunService
from stock_risk_mcp.kiwoom_sandbox_sell_schema import (
    SandboxSellDryRunStatus,
    SandboxSellSchemaVerificationStatus,
)
from stock_risk_mcp.kiwoom_sandbox_sell_schema_verifier import KiwoomSandboxSellSchemaVerifier
from stock_risk_mcp.local_ledger_service import LocalLedgerService
from stock_risk_mcp.order_intent import ExecutionMode, OrderSide
from stock_risk_mcp.order_intent_service import OrderIntentService
from stock_risk_mcp.order_risk_gate import RiskGateConfig
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.realtime_market_data import MarketRegion
from stock_risk_mcp.sell_safety_gate import SellSafetyGate
from tests.test_kiwoom_official_sell_schema_evidence import _payload, _write
from tests.test_order_risk_gate import _intent


def _import(repository, tmp_path):
    service = KiwoomOfficialSellSchemaEvidenceService(repository)
    service.import_evidence(_write(tmp_path / "evidence.json", _payload()))
    return service


def test_absent_and_unreviewed_evidence_remain_unverified(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    absent = KiwoomSandboxSellSchemaVerifier(repository).verify()
    _import(repository, tmp_path)
    unreviewed = KiwoomSandboxSellSchemaVerifier(repository).verify()

    assert absent.status == SandboxSellSchemaVerificationStatus.UNVERIFIED
    assert unreviewed.status == SandboxSellSchemaVerificationStatus.UNVERIFIED


def test_latest_validated_review_makes_schema_verified_but_v223_dry_run_stays_blocked(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    evidence_service = _import(repository, tmp_path)
    evidence_service.review("official-sell-1", OfficialSellSchemaEvidenceReviewStatus.VALIDATED, "reviewer")
    report = KiwoomSandboxSellSchemaVerifier(repository).verify()
    intent_service = OrderIntentService(repository)
    intent = intent_service.create(_intent(
        ticker="005930", region=MarketRegion.KR, side=OrderSide.SELL,
        quantity=1, stop_loss_price=None,
    ))
    LocalLedgerService(repository).upsert_position("005930", MarketRegion.KR, 2)
    SellSafetyGate(repository).evaluate(intent)
    intent_service.evaluate(intent.order_intent_id, RiskGateConfig(), ExecutionMode.SANDBOX, True)

    dry_run = KiwoomSandboxSellDryRunService(repository).run(intent.order_intent_id)

    assert report.status == SandboxSellSchemaVerificationStatus.VERIFIED
    assert report.metadata_json["official_evidence_id"] == "official-sell-1"
    assert "https://openapi.kiwoom.com/m/guide/apiguide?jobTpCode=13" in report.source_references
    assert dry_run.status == SandboxSellDryRunStatus.BLOCKED
    assert "SELL_DRY_RUN_APPROVAL_DISABLED_IN_V2_23" in dry_run.reasons_json


def test_rejected_or_superseded_latest_review_keeps_schema_unverified(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    service = _import(repository, tmp_path)
    service.review("official-sell-1", OfficialSellSchemaEvidenceReviewStatus.VALIDATED)
    service.review("official-sell-1", OfficialSellSchemaEvidenceReviewStatus.SUPERSEDED)

    report = KiwoomSandboxSellSchemaVerifier(repository).verify()
    assert report.status == SandboxSellSchemaVerificationStatus.UNVERIFIED
