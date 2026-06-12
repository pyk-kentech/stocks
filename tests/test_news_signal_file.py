import json
from datetime import date

from stock_risk_mcp.news_signal_file import load_news_signals
from stock_risk_mcp.signals import SignalDirection


def test_news_file_uses_only_asof_events_and_classifies_material_news(tmp_path) -> None:
    path = tmp_path / "news.json"
    path.write_text(json.dumps([
        {"ticker": "AAA", "observed_at": "2026-01-01", "title": "Contract awarded", "summary": "x", "event_type": "contract", "sentiment": "POSITIVE", "materiality": "HIGH"},
        {"ticker": "AAA", "observed_at": "2026-01-03", "title": "Future", "event_type": "lawsuit", "sentiment": "NEGATIVE", "materiality": "HIGH"},
    ]), encoding="utf-8")

    signals = load_news_signals(path, date(2026, 1, 2))

    assert len(signals) == 1
    assert signals[0].direction == SignalDirection.POSITIVE
    assert signals[0].score_delta == 10
