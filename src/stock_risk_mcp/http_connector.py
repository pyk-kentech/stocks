from __future__ import annotations

from datetime import date, datetime

from stock_risk_mcp.connector_run import (
    ConnectorMode, ConnectorOutput, ConnectorOutputFormat, ConnectorResult,
    ConnectorRun, ConnectorRunStatus, ConnectorType,
)
from stock_risk_mcp.http_download import HTTPDownloadStatus, download_public_http
from stock_risk_mcp.network_safety import sanitize_url_for_logging
from stock_risk_mcp.provider_config import ProviderDataKind


KIND_TO_CONNECTOR = {
    ProviderDataKind.PRICE_HISTORY: ConnectorType.MARKET_DATA,
    ProviderDataKind.NEWS: ConnectorType.NEWS,
    ProviderDataKind.NEWS_SIGNAL: ConnectorType.NEWS,
    ProviderDataKind.DILUTION: ConnectorType.DILUTION,
    ProviderDataKind.DILUTION_SIGNAL: ConnectorType.DILUTION,
    ProviderDataKind.FOREIGN_INSTITUTION_FLOW: ConnectorType.FLOW,
    ProviderDataKind.TOSS_SIGNAL: ConnectorType.TOSS_PORTFOLIO,
    ProviderDataKind.FLOW_SIGNAL: ConnectorType.FLOW,
    ProviderDataKind.COMPLIANCE: ConnectorType.COMPLIANCE,
    ProviderDataKind.FX_RATE: ConnectorType.FX,
    ProviderDataKind.UNKNOWN: ConnectorType.UNKNOWN,
}


class PublicHTTPConnector:
    mode = ConnectorMode.PUBLIC_HTTP

    def __init__(self, config, enable_network=False, runtime_allowed_hosts=None, client=None):
        self.config = config
        self.name = config.provider_name
        self.connector_type = KIND_TO_CONNECTOR[config.data_kind]
        self.enable_network = enable_network
        self.runtime_allowed_hosts = runtime_allowed_hosts
        self.client = client

    def fetch(self, as_of_date: date, output_dir: str, **kwargs) -> ConnectorResult:
        download = download_public_http(
            self.config, output_dir, self.enable_network, self.client, self.runtime_allowed_hosts
        )
        status = {
            HTTPDownloadStatus.COMPLETED: ConnectorRunStatus.COMPLETED,
            HTTPDownloadStatus.DISABLED: ConnectorRunStatus.DISABLED,
            HTTPDownloadStatus.BLOCKED: ConnectorRunStatus.FAILED,
            HTTPDownloadStatus.FAILED: ConnectorRunStatus.FAILED,
        }[download.status]
        metadata = {
            "provider_name": self.config.provider_name, "data_kind": self.config.data_kind.value,
            "sanitized_url": sanitize_url_for_logging(self.config.url),
            "bytes_downloaded": download.bytes_downloaded, "download_status": download.status.value,
        }
        run = ConnectorRun(
            as_of_date=as_of_date, connector_name=self.name, connector_type=self.connector_type,
            mode=self.mode, status=status, output_path=download.output_path, row_count=download.row_count,
            warnings=download.warnings, errors=download.errors, metadata=metadata, completed_at=datetime.now(),
        )
        output = None
        if download.status == HTTPDownloadStatus.COMPLETED:
            output = ConnectorOutput(
                connector_name=self.name, connector_type=self.connector_type,
                output_format=ConnectorOutputFormat(self.config.output_format.value),
                output_path=download.output_path, row_count=download.row_count, metadata=metadata,
            )
        return ConnectorResult(connector_run=run, output=output)
