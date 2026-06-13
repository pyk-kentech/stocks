from __future__ import annotations

import shutil
from datetime import date, datetime
from pathlib import Path

from stock_risk_mcp.connector_outputs import count_output_rows
from stock_risk_mcp.connector_run import (
    ConnectorMode, ConnectorOutput, ConnectorOutputFormat, ConnectorResult,
    ConnectorRun, ConnectorRunStatus, ConnectorType,
)


class LocalFileConnector:
    mode = ConnectorMode.LOCAL_FILE

    def __init__(self, name: str, connector_type: ConnectorType, source_path: str | Path, copy: bool = False) -> None:
        self.name = name
        self.connector_type = connector_type
        self.source_path = Path(source_path)
        self.copy = copy

    def fetch(self, as_of_date: date, output_dir: str, **kwargs) -> ConnectorResult:
        if not self.source_path.exists():
            raise FileNotFoundError(f"Local connector file not found: {self.source_path}")
        row_count = count_output_rows(self.source_path)
        path = self.source_path
        if self.copy:
            path = Path(output_dir) / self.source_path.name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.source_path, path)
        output_format = ConnectorOutputFormat.CSV if path.suffix.lower() == ".csv" else ConnectorOutputFormat.JSON
        metadata = {"source_type": "local_file", "source_path": str(self.source_path), "copied": self.copy}
        completed_at = datetime.now()
        return ConnectorResult(
            connector_run=ConnectorRun(
                as_of_date=as_of_date, connector_name=self.name, connector_type=self.connector_type,
                mode=self.mode, status=ConnectorRunStatus.COMPLETED, output_path=str(path),
                row_count=row_count, metadata=metadata, completed_at=completed_at,
            ),
            output=ConnectorOutput(
                connector_name=self.name, connector_type=self.connector_type, output_format=output_format,
                output_path=str(path), row_count=row_count, metadata=metadata,
            ),
        )
