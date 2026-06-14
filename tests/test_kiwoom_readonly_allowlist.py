import pytest

from stock_risk_mcp.kiwoom_readonly_allowlist import KiwoomReadOnlyAllowlist
from stock_risk_mcp.kiwoom_readonly_models import KiwoomEndpointCategory, KiwoomReadOnlyEndpoint


def test_allowlist_accepts_exact_internal_endpoint_and_rejects_unknown_or_mismatch() -> None:
    allowlist = KiwoomReadOnlyAllowlist()
    assert allowlist.require("RO_QUOTE", "/readonly/quote").api_id == "RO_QUOTE"
    with pytest.raises(ValueError):
        allowlist.require("UNKNOWN", "/readonly/quote")
    with pytest.raises(ValueError):
        allowlist.require("RO_QUOTE", "/readonly/chart")


@pytest.mark.parametrize("term", ["order", "buy", "sell", "cancel", "account", "balance", "position", "holding", "fill", "execution", "cash", "margin", "credit"])
def test_allowlist_rejects_forbidden_terms(term) -> None:
    endpoint = KiwoomReadOnlyEndpoint(
        api_id=f"RO_{term.upper()}", path=f"/readonly/{term}",
        category=KiwoomEndpointCategory.QUOTE, description="test", read_only=True, enabled=True,
    )
    with pytest.raises(ValueError):
        KiwoomReadOnlyAllowlist([endpoint])
