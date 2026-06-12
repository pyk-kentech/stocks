from stock_risk_mcp.signal_scoring import calculate_signal_score
from stock_risk_mcp.signals import SignalDirection, SignalSeverity, SignalType


def test_signal_scoring_and_toss_absolute_clamp() -> None:
    assert calculate_signal_score(SignalDirection.POSITIVE, SignalSeverity.HIGH, SignalType.NEWS) == 10
    assert calculate_signal_score(SignalDirection.NEGATIVE, SignalSeverity.CRITICAL, SignalType.DILUTION) == -100
    assert calculate_signal_score(SignalDirection.POSITIVE, SignalSeverity.CRITICAL, SignalType.TOSS_PORTFOLIO) == 10
    assert calculate_signal_score(SignalDirection.NEGATIVE, SignalSeverity.CRITICAL, SignalType.TOSS_PORTFOLIO) == -10
