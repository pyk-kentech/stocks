from __future__ import annotations

from typing import Any

from stock_risk_mcp.models import PolicyMode, RiskPolicy, TradeProposal


def make_policy(**overrides: Any) -> RiskPolicy:
    data: dict[str, Any] = {
        "mode": PolicyMode.PROPOSE_ONLY,
        "min_market_cap_usd": 300_000_000,
        "min_avg_dollar_volume_usd": 10_000_000,
        "max_5d_return_pct": 80,
        "max_single_position_pct": 5,
        "max_sector_exposure_pct": 25,
        "max_daily_loss_pct": -3,
        "max_order_pct": 2,
        "min_cash_pct": 5,
        "block_unknown_dilution": True,
        "block_missing_core_data": True,
        "block_nasdaq_noncompliant": True,
        "block_dilution_high": True,
        "block_reverse_split_within_days": 180,
        "block_offering_within_days": 90,
        "block_warrants": True,
        "block_convertibles": True,
        "allow_market_order": False,
        "allow_margin": False,
        "allow_options": False,
        "require_human_approval": True,
    }
    data.update(overrides)
    return RiskPolicy.model_validate(data)


def make_proposal(ticker: str, side: str = "BUY") -> TradeProposal:
    return TradeProposal(
        ticker=ticker,
        side=side,
        reason="토스 상위 투자자들이 공통 보유",
        llm_confidence=0.7,
        intended_holding_days=30,
    )
