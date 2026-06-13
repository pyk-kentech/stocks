from stock_risk_mcp.network_safety import (
    is_allowed_host,
    is_localhost,
    sanitize_url_for_logging,
    validate_no_credentials,
    validate_public_http_url,
)


def test_network_safety_blocks_unsafe_urls_and_credentials() -> None:
    assert is_localhost("localhost")
    assert is_localhost("127.0.0.1")
    assert is_localhost("::1")
    assert is_allowed_host("https://example.com/data.csv", ["example.com"])
    assert not is_allowed_host("https://sub.example.com/data.csv", ["example.com"])
    assert validate_public_http_url("file:///tmp/a.csv", ["example.com"])
    assert validate_public_http_url("ftp://example.com/a.csv", ["example.com"])
    assert validate_public_http_url("https://user:pass@example.com/a.csv", ["example.com"])
    assert validate_public_http_url("https://evil.example/a.csv", ["example.com"])
    assert validate_no_credentials({"Authorization": "secret", "Cookie": "x", "X-API-Key": "k"})
    assert sanitize_url_for_logging("https://example.com/a.csv?token=secret#fragment") == "https://example.com/a.csv"
