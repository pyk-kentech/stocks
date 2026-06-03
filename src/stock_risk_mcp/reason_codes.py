from __future__ import annotations

from enum import StrEnum

from stock_risk_mcp.models import ReasonType, Severity


class HardBlockCode(StrEnum):
    READ_ONLY_MODE = "READ_ONLY_MODE"
    SIDE_NOT_ALLOWED = "SIDE_NOT_ALLOWED"
    NASDAQ_NONCOMPLIANT = "NASDAQ_NONCOMPLIANT"
    DILUTION_RISK_HIGH = "DILUTION_RISK_HIGH"
    DILUTION_RISK_UNKNOWN = "DILUTION_RISK_UNKNOWN"
    RECENT_REVERSE_SPLIT = "RECENT_REVERSE_SPLIT"
    RECENT_OFFERING = "RECENT_OFFERING"
    WARRANT_OVERHANG = "WARRANT_OVERHANG"
    CONVERTIBLE_OVERHANG = "CONVERTIBLE_OVERHANG"
    MISSING_MARKET_CAP = "MISSING_MARKET_CAP"
    MISSING_DOLLAR_VOLUME = "MISSING_DOLLAR_VOLUME"
    MARKET_CAP_TOO_SMALL = "MARKET_CAP_TOO_SMALL"
    DOLLAR_VOLUME_TOO_LOW = "DOLLAR_VOLUME_TOO_LOW"
    RETURN_5D_TOO_HIGH = "RETURN_5D_TOO_HIGH"
    POSITION_LIMIT_EXCEEDED = "POSITION_LIMIT_EXCEEDED"
    SECTOR_EXPOSURE_EXCEEDED = "SECTOR_EXPOSURE_EXCEEDED"
    DAILY_LOSS_LIMIT_EXCEEDED = "DAILY_LOSS_LIMIT_EXCEEDED"
    CASH_BELOW_MINIMUM = "CASH_BELOW_MINIMUM"
    TOO_MANY_OPEN_ORDERS = "TOO_MANY_OPEN_ORDERS"


class WarningCode(StrEnum):
    VOLATILITY_HIGH = "VOLATILITY_HIGH"
    SHORT_TERM_OVERHEATED = "SHORT_TERM_OVERHEATED"
    DILUTION_RISK_MEDIUM = "DILUTION_RISK_MEDIUM"
    TOSS_SIGNAL_LOW_QUALITY = "TOSS_SIGNAL_LOW_QUALITY"
    HISTORICAL_FOLLOW_RETURN_NEGATIVE = "HISTORICAL_FOLLOW_RETURN_NEGATIVE"
    DATA_PARTIAL = "DATA_PARTIAL"


class PositiveCode(StrEnum):
    DOLLAR_VOLUME_STRONG = "DOLLAR_VOLUME_STRONG"
    VOLATILITY_LOW = "VOLATILITY_LOW"
    SHORT_TERM_NOT_OVERHEATED = "SHORT_TERM_NOT_OVERHEATED"
    DILUTION_RISK_LOW = "DILUTION_RISK_LOW"
    TOSS_CONSENSUS_HIGH = "TOSS_CONSENSUS_HIGH"
    TOSS_CONSENSUS_MEDIUM = "TOSS_CONSENSUS_MEDIUM"
    TOSS_SIGNAL_QUALITY_HIGH = "TOSS_SIGNAL_QUALITY_HIGH"
    TOSS_SIGNAL_QUALITY_MEDIUM = "TOSS_SIGNAL_QUALITY_MEDIUM"
    HISTORICAL_FOLLOW_RETURN_POSITIVE = "HISTORICAL_FOLLOW_RETURN_POSITIVE"


NEGATIVE_CODE_BY_FACTOR = {
    "DOLLAR_VOLUME_TOO_LOW": WarningCode.DATA_PARTIAL,
    "VOLATILITY_HIGH": WarningCode.VOLATILITY_HIGH,
    "RETURN_5D_TOO_HIGH": WarningCode.SHORT_TERM_OVERHEATED,
    "DILUTION_RISK_MEDIUM": WarningCode.DILUTION_RISK_MEDIUM,
    "TOSS_SIGNAL_LOW_QUALITY": WarningCode.TOSS_SIGNAL_LOW_QUALITY,
    "HISTORICAL_FOLLOW_RETURN_NEGATIVE": WarningCode.HISTORICAL_FOLLOW_RETURN_NEGATIVE,
}


DEFAULT_SEVERITY_BY_TYPE = {
    ReasonType.HARD_BLOCK: Severity.CRITICAL,
    ReasonType.WARNING: Severity.MEDIUM,
    ReasonType.POSITIVE: Severity.LOW,
    ReasonType.NEGATIVE: Severity.MEDIUM,
}


def normalize_legacy_hard_block_reason(message: str) -> str:
    lowered = message.lower()
    if "read_only" in lowered:
        return HardBlockCode.READ_ONLY_MODE.value
    if "buy" in lowered:
        return HardBlockCode.SIDE_NOT_ALLOWED.value
    if "nasdaq" in lowered:
        return HardBlockCode.NASDAQ_NONCOMPLIANT.value
    if "high" in lowered and ("dilution" in lowered or "희석" in message):
        return HardBlockCode.DILUTION_RISK_HIGH.value
    if "unknown" in lowered and ("dilution" in lowered or "희석" in message):
        return HardBlockCode.DILUTION_RISK_UNKNOWN.value
    if "reverse" in lowered or "역분할" in message:
        return HardBlockCode.RECENT_REVERSE_SPLIT.value
    if "offering" in lowered or "오퍼링" in message or "유상증자" in message:
        return HardBlockCode.RECENT_OFFERING.value
    if "warrant" in lowered or "워런트" in message:
        return HardBlockCode.WARRANT_OVERHANG.value
    if "convert" in lowered or "전환" in message:
        return HardBlockCode.CONVERTIBLE_OVERHANG.value
    if "market cap" in lowered or "시가총액" in message:
        if "missing" in lowered or "누락" in message:
            return HardBlockCode.MISSING_MARKET_CAP.value
        return HardBlockCode.MARKET_CAP_TOO_SMALL.value
    if "dollar volume" in lowered or "거래대금" in message:
        if "missing" in lowered or "누락" in message:
            return HardBlockCode.MISSING_DOLLAR_VOLUME.value
        return HardBlockCode.DOLLAR_VOLUME_TOO_LOW.value
    if "5d" in lowered or "5일" in message:
        return HardBlockCode.RETURN_5D_TOO_HIGH.value
    if "position" in lowered or "포지션" in message:
        return HardBlockCode.POSITION_LIMIT_EXCEEDED.value
    if "sector" in lowered or "섹터" in message:
        return HardBlockCode.SECTOR_EXPOSURE_EXCEEDED.value
    if "daily loss" in lowered or "일일 손실" in message:
        return HardBlockCode.DAILY_LOSS_LIMIT_EXCEEDED.value
    if "cash" in lowered or "현금" in message:
        return HardBlockCode.CASH_BELOW_MINIMUM.value
    if "open order" in lowered or "열린 주문" in message:
        return HardBlockCode.TOO_MANY_OPEN_ORDERS.value
    if "누락" in message:
        return HardBlockCode.MISSING_MARKET_CAP.value
    return _slugify(message).upper()


def _slugify(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "_" for char in value)
    return "_".join(part for part in cleaned.split("_") if part) or "UNKNOWN_REASON"
