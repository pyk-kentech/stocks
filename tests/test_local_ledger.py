import pytest

from stock_risk_mcp.local_ledger import LocalLedgerPosition
from stock_risk_mcp.local_ledger_service import LocalLedgerService
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.realtime_market_data import MarketRegion


def test_local_ledger_upsert_list_transaction_and_snapshot_are_offline(tmp_path):
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    service = LocalLedgerService(repository)
    position = service.upsert_position("005930", MarketRegion.KR, 10, reserved_quantity=3, average_price=70000)
    listed = service.list_positions()
    snapshot = service.create_snapshot()
    transactions = service.list_transactions()

    assert position.available_quantity == 7
    assert listed[0].symbol == "005930"
    assert snapshot.position_count == 1
    assert transactions[0].transaction_type == "UPSERT"
    assert snapshot.metadata_json["network_called"] is False


@pytest.mark.parametrize("quantity", [-1, 1.5])
def test_local_ledger_rejects_negative_and_fractional_quantity(tmp_path, quantity):
    with pytest.raises(ValueError):
        LocalLedgerService(RiskRepository(tmp_path / "risk.sqlite3")).upsert_position(
            "005930", MarketRegion.KR, quantity
        )


def test_position_reservation_is_conservative():
    position = LocalLedgerPosition(symbol="005930", region=MarketRegion.KR, quantity=2, reserved_quantity=5)
    assert position.available_quantity == 0
