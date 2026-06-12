from stock_risk_mcp.signals import SignalDirection, SignalSeverity, SignalType


def calculate_signal_score(
    direction: SignalDirection,
    severity: SignalSeverity,
    signal_type: SignalType,
) -> int:
    positive = {
        SignalSeverity.LOW: 2,
        SignalSeverity.MEDIUM: 5,
        SignalSeverity.HIGH: 10,
        SignalSeverity.CRITICAL: 10,
    }
    negative = {
        SignalSeverity.LOW: -3,
        SignalSeverity.MEDIUM: -8,
        SignalSeverity.HIGH: -15,
        SignalSeverity.CRITICAL: -100,
    }
    score = positive[severity] if direction == SignalDirection.POSITIVE else negative[severity] if direction == SignalDirection.NEGATIVE else 0
    if signal_type == SignalType.TOSS_PORTFOLIO:
        return max(-10, min(10, score))
    return score
