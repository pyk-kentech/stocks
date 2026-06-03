from __future__ import annotations

from stock_risk_mcp.models import DataSource, Evidence, SourceType


MOCK_DATA_SOURCES = (
    DataSource(name="mock_market_data", source_type=SourceType.MOCK, description="Deterministic MVP market data"),
    DataSource(name="mock_company_risk", source_type=SourceType.MOCK, description="Deterministic MVP company risk"),
    DataSource(name="mock_portfolio", source_type=SourceType.MOCK, description="Deterministic MVP portfolio state"),
    DataSource(name="mock_toss_signal", source_type=SourceType.MOCK, description="Deterministic MVP Toss signal"),
)


def evidence_for_source(source_name: str, confidence: float = 1.0) -> Evidence:
    return Evidence(source_name=source_name, source_type=SourceType.MOCK, confidence=confidence)


def evidence_for_reason_code(reason_code: str) -> Evidence:
    if reason_code in {
        "NASDAQ_NONCOMPLIANT",
        "DILUTION_RISK_HIGH",
        "DILUTION_RISK_UNKNOWN",
        "RECENT_REVERSE_SPLIT",
        "RECENT_OFFERING",
        "WARRANT_OVERHANG",
        "CONVERTIBLE_OVERHANG",
    }:
        return evidence_for_source("mock_company_risk")
    if reason_code in {
        "MISSING_MARKET_CAP",
        "MISSING_DOLLAR_VOLUME",
        "MARKET_CAP_TOO_SMALL",
        "DOLLAR_VOLUME_TOO_LOW",
        "RETURN_5D_TOO_HIGH",
        "DOLLAR_VOLUME_STRONG",
        "VOLATILITY_LOW",
        "VOLATILITY_HIGH",
        "SHORT_TERM_NOT_OVERHEATED",
        "SHORT_TERM_OVERHEATED",
    }:
        return evidence_for_source("mock_market_data")
    if reason_code in {
        "POSITION_LIMIT_EXCEEDED",
        "SECTOR_EXPOSURE_EXCEEDED",
        "DAILY_LOSS_LIMIT_EXCEEDED",
        "CASH_BELOW_MINIMUM",
        "TOO_MANY_OPEN_ORDERS",
    }:
        return evidence_for_source("mock_portfolio")
    if reason_code.startswith("TOSS_") or reason_code.startswith("HISTORICAL_FOLLOW"):
        return evidence_for_source("mock_toss_signal")
    return Evidence(source_name="risk_engine", source_type=SourceType.SYSTEM, confidence=1.0)
