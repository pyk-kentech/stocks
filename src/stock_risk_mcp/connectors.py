from datetime import date
from typing import Protocol

from stock_risk_mcp.connector_run import ConnectorMode, ConnectorResult, ConnectorType


class BaseConnector(Protocol):
    name: str
    connector_type: ConnectorType
    mode: ConnectorMode

    def fetch(self, as_of_date: date, output_dir: str, **kwargs) -> ConnectorResult: ...
