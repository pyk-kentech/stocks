from stock_risk_mcp.agent_guardrails import FORBIDDEN_ACTIONS, is_local_endpoint


def test_local_endpoint_allows_only_loopback_hosts() -> None:
    assert is_local_endpoint("http://localhost:11434")
    assert is_local_endpoint("http://127.0.0.1:8000/v1")
    assert is_local_endpoint("http://[::1]:8080/v1")
    assert not is_local_endpoint("https://api.openai.com/v1")
    assert not is_local_endpoint("http://8.8.8.8:8000")
    assert not is_local_endpoint("http://example.com")
    assert "place_order" in FORBIDDEN_ACTIONS
    assert "activate_policy" in FORBIDDEN_ACTIONS
