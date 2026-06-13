from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from stock_risk_mcp.connector_outputs import write_csv_output
from stock_risk_mcp.connector_run import (
    ConnectorMode, ConnectorOutput, ConnectorOutputFormat, ConnectorResult,
    ConnectorRun, ConnectorRunStatus, ConnectorType,
)


class _MockCsvConnector:
    mode = ConnectorMode.MOCK
    connector_type = ConnectorType.UNKNOWN
    name = "mock"

    def fetch(self, as_of_date: date, output_dir: str, **kwargs) -> ConnectorResult:
        records = self.records(as_of_date, kwargs.get("tickers") or ["MOCK"])
        path = write_csv_output(Path(output_dir) / f"{self.name}_{as_of_date:%Y%m%d}.csv", records)
        completed_at = datetime.now()
        output = ConnectorOutput(
            connector_name=self.name, connector_type=self.connector_type,
            output_format=ConnectorOutputFormat.CSV, output_path=str(path), row_count=len(records),
            metadata={"network_access": False},
        )
        run = ConnectorRun(
            as_of_date=as_of_date, connector_name=self.name, connector_type=self.connector_type,
            mode=self.mode, status=ConnectorRunStatus.COMPLETED, output_path=str(path),
            row_count=len(records), metadata={"network_access": False}, completed_at=completed_at,
        )
        return ConnectorResult(connector_run=run, output=output)

    def records(self, as_of_date: date, tickers: list[str]) -> list[dict]:  # pragma: no cover - interface guard
        raise NotImplementedError


class MockMarketDataConnector(_MockCsvConnector):
    name = "mock_market_data"
    connector_type = ConnectorType.MARKET_DATA

    def records(self, as_of_date: date, tickers: list[str]) -> list[dict]:
        records = []
        for ticker_index, ticker in enumerate(tickers):
            for offset in range(119, -1, -1):
                day = as_of_date - timedelta(days=offset)
                close = round(10 + ticker_index + (119 - offset) * 0.05, 4)
                records.append({
                    "ticker": ticker.upper(), "date": day.isoformat(), "open": close - 0.1,
                    "high": close + 0.2, "low": close - 0.2, "close": close,
                    "volume": 1_000_000 + (119 - offset) * 1000,
                })
        return records


class MockNewsSignalConnector(_MockCsvConnector):
    name = "mock_news_signal"
    connector_type = ConnectorType.NEWS

    def records(self, as_of_date: date, tickers: list[str]) -> list[dict]:
        return [{
            "ticker": ticker.upper(), "observed_at": as_of_date.isoformat(), "title": "Mock contract update",
            "summary": "Deterministic local mock news", "event_type": "CONTRACT",
            "sentiment": "POSITIVE", "materiality": "MEDIUM",
        } for ticker in tickers]


class MockDilutionSignalConnector(_MockCsvConnector):
    name = "mock_dilution_signal"
    connector_type = ConnectorType.DILUTION

    def records(self, as_of_date: date, tickers: list[str]) -> list[dict]:
        return [{"ticker": ticker.upper(), "observed_at": as_of_date.isoformat(), "event_type": "OFFERING_CLOSED", "severity": "MEDIUM", "details": "Deterministic local mock"} for ticker in tickers]


class MockTossSignalConnector(_MockCsvConnector):
    name = "mock_toss_signal"
    connector_type = ConnectorType.TOSS_PORTFOLIO

    def records(self, as_of_date: date, tickers: list[str]) -> list[dict]:
        return [{"ticker": ticker.upper(), "observed_at": as_of_date.isoformat(), "investor_id": "mock_1", "investor_rank_group": "TOP", "holding_weight": 1.0, "change_type": "HOLD", "change_pct": 0} for ticker in tickers]


class MockFlowSignalConnector(_MockCsvConnector):
    name = "mock_flow_signal"
    connector_type = ConnectorType.FLOW

    def records(self, as_of_date: date, tickers: list[str]) -> list[dict]:
        return [{"ticker": ticker.upper(), "observed_at": as_of_date.isoformat(), "foreign_net_buy": 100, "institution_net_buy": 100, "foreign_ownership_change": 0.1, "flow_window_days": 5} for ticker in tickers]
