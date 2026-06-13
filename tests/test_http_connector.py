from datetime import date

from stock_risk_mcp.connector_run import ConnectorRunStatus
from stock_risk_mcp.http_connector import PublicHTTPConnector
from stock_risk_mcp.provider_config import HTTPProviderConfig, ProviderDataKind


class ExplodingClient:
    def get(self, *args, **kwargs):
        raise AssertionError("network client must not be called")


class FakeClient:
    def get(self, *args, **kwargs):
        return {"status_code": 200, "headers": {"Content-Type": "application/json"}, "body": b'[{"ticker":"AAA"}]'}


def test_http_connector_is_disabled_without_explicit_network_enablement(tmp_path) -> None:
    connector = PublicHTTPConnector(_config(), enable_network=False, client=ExplodingClient())

    result = connector.fetch(date(2026, 6, 13), str(tmp_path))

    assert result.connector_run.status == ConnectorRunStatus.DISABLED
    assert result.output is None


def test_http_connector_is_disabled_when_provider_config_is_disabled(tmp_path) -> None:
    config = _config()
    config.enabled = False
    connector = PublicHTTPConnector(config, enable_network=True, client=ExplodingClient())

    result = connector.fetch(date(2026, 6, 13), str(tmp_path))

    assert result.connector_run.status == ConnectorRunStatus.DISABLED
    assert result.output is None


def test_http_connector_downloads_with_fake_client_and_records_metadata(tmp_path) -> None:
    connector = PublicHTTPConnector(_config(output_format="JSON"), enable_network=True, client=FakeClient())

    result = connector.fetch(date(2026, 6, 13), str(tmp_path))

    assert result.connector_run.status == ConnectorRunStatus.COMPLETED
    assert result.connector_run.row_count == 1
    assert result.connector_run.metadata["download_status"] == "COMPLETED"
    assert "?" not in result.connector_run.metadata["sanitized_url"]


def _config(output_format="CSV"):
    return HTTPProviderConfig(
        provider_name="prices", url="https://example.com/data?token=secret",
        data_kind=ProviderDataKind.PRICE_HISTORY, output_format=output_format,
        allowed_hosts=["example.com"], enabled=True,
    )
