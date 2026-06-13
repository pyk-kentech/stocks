from stock_risk_mcp.http_download import HTTPDownloadStatus, download_public_http
from stock_risk_mcp.provider_config import HTTPProviderConfig, ProviderDataKind


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, headers, timeout_seconds, max_bytes):
        self.calls.append(url)
        return self.responses.pop(0)


def test_download_follows_only_allowed_redirect_and_writes_csv(tmp_path) -> None:
    client = FakeClient([
        {"status_code": 302, "headers": {"Location": "https://example.com/final.csv"}, "body": b""},
        {"status_code": 200, "headers": {"Content-Type": "text/csv"}, "body": b"ticker,date,close\nAAA,2026-01-01,1\n"},
    ])

    result = download_public_http(_config(), tmp_path, True, client)

    assert result.status == HTTPDownloadStatus.COMPLETED
    assert result.row_count == 1
    assert result.bytes_downloaded > 0
    assert result.output_path
    assert len(client.calls) == 2


def test_download_blocks_redirect_outside_allowlist_and_max_bytes(tmp_path) -> None:
    redirect = FakeClient([{"status_code": 302, "headers": {"Location": "https://evil.example/a.csv"}, "body": b""}])
    large = FakeClient([{"status_code": 200, "headers": {"Content-Type": "text/csv"}, "body": b"x" * 20}])

    blocked = download_public_http(_config(), tmp_path, True, redirect)
    exceeded = download_public_http(_config(max_bytes=10), tmp_path, True, large)

    assert blocked.status == HTTPDownloadStatus.BLOCKED
    assert exceeded.status == HTTPDownloadStatus.FAILED


def _config(max_bytes=10_000):
    return HTTPProviderConfig(
        provider_name="prices", url="https://example.com/start.csv", data_kind=ProviderDataKind.PRICE_HISTORY,
        output_format="CSV", allowed_hosts=["example.com"], max_bytes=max_bytes, enabled=True,
    )
