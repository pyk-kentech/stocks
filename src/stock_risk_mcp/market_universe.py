from __future__ import annotations

from dataclasses import dataclass, field

from stock_risk_mcp.realtime_market_data import MarketRegion


@dataclass
class MarketUniverseResult:
    symbols: list[str] = field(default_factory=list)
    blocked_symbols: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class MarketUniverseRegistry:
    def __init__(self, max_symbols: int = 500) -> None:
        self.max_symbols = max_symbols

    def register(self, symbols: list[str], region: MarketRegion) -> MarketUniverseResult:
        normalized = list(dict.fromkeys(symbol.strip().upper() for symbol in symbols if symbol.strip()))
        if region == MarketRegion.UNKNOWN:
            return MarketUniverseResult(
                blocked_symbols=normalized,
                warnings=["unknown region blocked"],
            )
        warnings: list[str] = []
        if len(normalized) > self.max_symbols:
            warnings.append(f"max_symbols limit applied: {self.max_symbols}")
        return MarketUniverseResult(
            symbols=normalized[: self.max_symbols],
            blocked_symbols=normalized[self.max_symbols :],
            warnings=warnings,
        )
