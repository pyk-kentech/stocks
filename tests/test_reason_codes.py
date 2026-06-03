from __future__ import annotations

from stock_risk_mcp.models import ReasonType, Severity
from stock_risk_mcp.reason_codes import HardBlockCode, normalize_legacy_hard_block_reason


def test_reason_code_constants_are_stable() -> None:
    assert HardBlockCode.NASDAQ_NONCOMPLIANT.value == "NASDAQ_NONCOMPLIANT"
    assert HardBlockCode.DILUTION_RISK_HIGH.value == "DILUTION_RISK_HIGH"
    assert HardBlockCode.RETURN_5D_TOO_HIGH.value == "RETURN_5D_TOO_HIGH"


def test_legacy_hard_block_reason_normalization() -> None:
    assert normalize_legacy_hard_block_reason("Nasdaq noncompliant") == "NASDAQ_NONCOMPLIANT"
    assert normalize_legacy_hard_block_reason("dilution risk HIGH") == "DILUTION_RISK_HIGH"
    assert normalize_legacy_hard_block_reason("5d return too high") == "RETURN_5D_TOO_HIGH"
    assert ReasonType.HARD_BLOCK.value == "HARD_BLOCK"
    assert Severity.CRITICAL.value == "CRITICAL"
