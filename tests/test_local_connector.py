from datetime import date

from stock_risk_mcp.connector_outputs import count_output_rows
from stock_risk_mcp.connector_run import ConnectorType
from stock_risk_mcp.local_connector import LocalFileConnector


def test_local_connector_registers_or_copies_without_modifying_content(tmp_path) -> None:
    source = tmp_path / "news.csv"
    source.write_text("ticker,observed_at\nAAA,2026-01-01\n", encoding="utf-8")
    direct = LocalFileConnector("manual_news", ConnectorType.NEWS, source, copy=False).fetch(date(2026, 6, 13), tmp_path / "out")
    copied = LocalFileConnector("copied_news", ConnectorType.NEWS, source, copy=True).fetch(date(2026, 6, 13), tmp_path / "out")

    assert direct.output.output_path == str(source)
    assert copied.output.output_path != str(source)
    assert count_output_rows(copied.output.output_path) == 1
    assert open(copied.output.output_path, encoding="utf-8").read() == source.read_text(encoding="utf-8")
