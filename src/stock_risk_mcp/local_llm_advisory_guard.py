from __future__ import annotations


UNSAFE_PATTERNS = {
    "BUY_SELL_INSTRUCTION": ("buy now", "sell now", "go long", "go short"),
    "ORDER_CREATION_INTENT": ("place an order", "submit order", "create order", "draft order"),
    "EXECUTION_APPROVAL": ("execution approved", "approve execution"),
    "GATE_BYPASS": ("bypass riskgate", "bypass executiongate", "ignore risk gate"),
    "BROKER_ACCOUNT_ACCESS": ("broker login", "account balance", "fetch holdings", "connect kiwoom"),
    "CREDENTIAL_REQUEST": ("api key", "token", "password", "credential"),
    "POSITION_SIZING_AUTHORITY": ("position size should be", "buy 100 shares", "allocate 10%"),
}


def detect_unsafe_output(text: str | None) -> str | None:
    if not text:
        return None
    lowered = text.lower()
    for reason, patterns in UNSAFE_PATTERNS.items():
        if any(pattern in lowered for pattern in patterns):
            return reason
    return None
