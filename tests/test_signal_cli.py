import json
from datetime import date, datetime, timedelta

from stock_risk_mcp.cli import main
from stock_risk_mcp.models import PriceBar
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.signals import SignalDirection, SignalSeverity, SignalType, TickerSignal


def test_signal_cli_ingest_list_merge_file_precedence_and_ignore_db(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    news = tmp_path / "news.json"
    repository = RiskRepository(db)
    repository.save_price_bars(_bars())
    repository.save_ticker_signals([_db_signal(5), _future_signal()])
    news.write_text(json.dumps([{
        "ticker": "AAA", "observed_at": "2026-01-01", "title": "Contract",
        "event_type": "CONTRACT", "sentiment": "POSITIVE", "materiality": "HIGH",
    }]), encoding="utf-8")

    merged = _run(capsys, [
        "scan-candidates", "--db", str(db), "--as-of-date", "2026-01-20", "--ticker", "AAA",
        "--news-signal-file", str(news), "--save-signals",
    ])
    db_only = _run(capsys, [
        "scan-candidates", "--db", str(db), "--as-of-date", "2026-01-20", "--ticker", "AAA",
    ])
    file_only = _run(capsys, [
        "scan-candidates", "--db", str(db), "--as-of-date", "2026-01-20", "--ticker", "AAA",
        "--news-signal-file", str(news), "--ignore-db-signals",
    ])
    ignored = _run(capsys, [
        "scan-candidates", "--db", str(db), "--as-of-date", "2026-01-20", "--ticker", "AAA",
        "--ignore-db-signals",
    ])
    listed = _run(capsys, ["signals", "--db", str(db), "--ticker", "AAA", "--as-of-date", "2026-01-20"])
    ingested = _run(capsys, [
        "ingest-signals", "--db", str(db), "--as-of-date", "2026-01-20", "--news-signal-file", str(news),
    ])

    assert merged["db_signal_count"] == 1
    assert merged["file_signal_count"] == 1
    assert merged["merged_signal_count"] == 2
    assert merged["deduped_signal_count"] == 1
    assert merged["top_candidates"][0]["metadata"]["signal_enrichment"]["total_score_delta"] == 10
    assert "deduped_signal_count=1" in merged["notes"]
    assert merged["saved_signal_count"] == 0
    assert merged["skipped_duplicate_count"] == 1
    assert db_only["db_signal_count"] == 1
    assert db_only["top_candidates"][0]["metadata"]["signal_enrichment"]["total_score_delta"] == 5
    assert file_only["db_signal_count"] == 0
    assert file_only["file_signal_count"] == 1
    assert file_only["top_candidates"][0]["metadata"]["signal_enrichment"]["total_score_delta"] == 10
    assert ignored["db_signal_count"] == 0
    assert ignored["deduped_signal_count"] == 0
    assert len(listed["signals"]) == 1
    assert ingested["saved_signal_count"] == 0
    assert ingested["skipped_duplicate_count"] == 1


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def _db_signal(delta):
    return TickerSignal(
        ticker="AAA", signal_type=SignalType.NEWS, as_of_date=date(2026, 1, 20),
        observed_at=datetime(2026, 1, 1), direction=SignalDirection.POSITIVE,
        severity=SignalSeverity.MEDIUM, score_delta=delta, source_name="news_signal_file",
        title="Contract", raw_event_type="CONTRACT",
    )


def _future_signal():
    return _db_signal(10).model_copy(update={"observed_at": datetime(2026, 1, 21), "title": "Future"})


def _bars():
    start = date(2025, 9, 1)
    return [
        PriceBar(ticker="AAA", date=start + timedelta(days=i), open=10+i*.1, high=11+i*.1, low=9.5+i*.1, close=10.5+i*.1, volume=5_000_000+i*100_000)
        for i in range(140)
    ]
