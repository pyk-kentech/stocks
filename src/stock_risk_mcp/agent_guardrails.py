from urllib.parse import urlparse


FORBIDDEN_ACTIONS = [
    "place_order", "execute_trade", "send_order", "activate_policy", "approve_policy",
    "modify_hard_risk_rule", "disable_stop_loss", "change_broker_settings",
    "scrape_private_account", "bypass_terms_of_service",
]

READ_ONLY_SYSTEM_INSTRUCTIONS = """You are a read-only trading research assistant.
This is paper trading and research support only.
Do not claim guaranteed profit.
Do not tell the user to buy immediately.
Explain risks, assumptions, stale data, and missing data.
Never execute orders.
Never modify risk policy.
Never activate policies.
Prefer risk-capped interpretation."""


def is_local_endpoint(endpoint_url: str | None) -> bool:
    if not endpoint_url:
        return False
    return urlparse(endpoint_url).hostname in {"localhost", "127.0.0.1", "::1"}
