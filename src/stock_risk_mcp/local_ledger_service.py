from stock_risk_mcp.local_ledger import LocalLedgerPosition, LocalLedgerSnapshot, LocalLedgerTransaction
from stock_risk_mcp.realtime_market_data import MarketRegion


class LocalLedgerService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def upsert_position(
        self,
        symbol: str,
        region: MarketRegion,
        quantity: int,
        reserved_quantity: int = 0,
        average_price: float | None = None,
    ) -> LocalLedgerPosition:
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 0:
            raise ValueError("quantity must be a non-negative integer")
        if not isinstance(reserved_quantity, int) or isinstance(reserved_quantity, bool) or reserved_quantity < 0:
            raise ValueError("reserved quantity must be a non-negative integer")
        existing = self.repository.get_local_ledger_position(symbol, region)
        position = LocalLedgerPosition(
            position_id=existing.position_id if existing else f"ledger-{region.value}-{symbol.strip().upper()}",
            symbol=symbol, region=region, quantity=quantity, reserved_quantity=reserved_quantity,
            average_price=average_price,
        )
        self.repository.save_local_ledger_position(position)
        self.repository.save_local_ledger_transaction(LocalLedgerTransaction(
            position_id=position.position_id, symbol=position.symbol, region=position.region,
            transaction_type="UPSERT", quantity=quantity, reserved_quantity=reserved_quantity,
        ))
        return position

    def list_positions(self) -> list[LocalLedgerPosition]:
        return self.repository.list_local_ledger_positions()

    def list_transactions(self) -> list[LocalLedgerTransaction]:
        return self.repository.list_local_ledger_transactions()

    def create_snapshot(self) -> LocalLedgerSnapshot:
        positions = self.list_positions()
        snapshot = LocalLedgerSnapshot(
            position_count=len(positions),
            total_quantity=sum(item.quantity for item in positions),
            total_reserved_quantity=sum(item.reserved_quantity for item in positions),
        )
        self.repository.save_local_ledger_snapshot(snapshot)
        return snapshot
