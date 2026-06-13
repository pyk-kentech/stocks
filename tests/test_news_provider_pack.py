import json
from datetime import date

from stock_risk_mcp.cli import main
from stock_risk_mcp.candidate_universe import CandidateDecision, CandidateScanResult
from stock_risk_mcp.news_provider_pack import run_news_provider_pack
from stock_risk_mcp.provider_pack_config import ProviderPackConfig
from stock_risk_mcp.provider_packs import ProviderPackRunStatus
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.signal_enrichment import SignalEnricher
from stock_risk_mcp.signals import SignalDirection, SignalSeverity, SignalType


def test_local_news_provider_pack_normalizes_imports_and_preserves_metadata(tmp_path) -> None:
    raw = tmp_path / "news.csv"
    raw.write_text(
        "Symbol,PublishedAt,Headline,Source,Sentiment,Severity,Url\n"
        "AAA,2026-06-12,Investigation,wire,negative,HIGH,https://example.com/news\n",
        encoding="utf-8",
    )
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    config = ProviderPackConfig.model_validate({"news": {"providers": [_provider(raw)]}})

    run = run_news_provider_pack(repository, config, tmp_path / "out", date(2026, 6, 13))
    signal = repository.list_ticker_signals("AAA", date(2026, 6, 13))[0]

    assert run.status == ProviderPackRunStatus.COMPLETED
    assert signal.signal_type == SignalType.NEWS
    assert signal.title == "Investigation"
    assert signal.source_name == "wire"
    assert signal.direction == SignalDirection.NEGATIVE
    assert signal.severity == SignalSeverity.HIGH
    assert signal.score_delta == -5
    assert signal.metadata["url"] == "https://example.com/news"
    assert signal.metadata["raw_payload_json"]["Severity"] == "HIGH"


def test_news_provider_pack_records_missing_normalizer_failure(tmp_path) -> None:
    raw = tmp_path / "news.csv"
    raw.write_text("Symbol,PublishedAt,Headline,Source\nAAA,2026-06-12,Deal,wire\n", encoding="utf-8")
    config = ProviderPackConfig.model_validate({"news": {"providers": [{
        **_provider(raw), "normalizer": None,
    }]}})

    run = run_news_provider_pack(
        RiskRepository(tmp_path / "risk.sqlite3"), config, tmp_path / "out", date(2026, 6, 13)
    )

    assert run.status == ProviderPackRunStatus.FAILED
    assert any("normalizer" in error.lower() for error in run.errors)


def test_news_http_provider_is_disabled_without_network(tmp_path) -> None:
    config = ProviderPackConfig.model_validate({"news": {"providers": [{
        **_provider("unused.csv"), "local_file": None, "url": "https://example.com/news.csv",
        "allowed_hosts": ["example.com"],
    }]}})

    run = run_news_provider_pack(
        RiskRepository(tmp_path / "risk.sqlite3"), config, tmp_path / "out", date(2026, 6, 13)
    )

    assert run.status == ProviderPackRunStatus.DISABLED


def test_fake_http_news_provider_flows_to_news_signal(tmp_path) -> None:
    config = ProviderPackConfig.model_validate({"news": {"providers": [{
        **_provider("unused.csv"), "local_file": None, "url": "https://example.com/news.csv",
        "allowed_hosts": ["example.com"],
    }]}})
    repository = RiskRepository(tmp_path / "risk.sqlite3")

    run = run_news_provider_pack(
        repository, config, tmp_path / "out", date(2026, 6, 13),
        enable_network=True, client=FakeNewsClient(),
    )

    assert run.status == ProviderPackRunStatus.COMPLETED
    assert repository.list_ticker_signals("AAA", date(2026, 6, 13))[0].score_delta == -10


def test_imported_news_keeps_existing_critical_and_high_enrichment_rules(tmp_path) -> None:
    raw = tmp_path / "news.csv"
    raw.write_text(
        "Symbol,PublishedAt,Headline,Source,Sentiment,Severity\n"
        "CRIT,2026-06-12,Critical,wire,negative,CRITICAL\n"
        "HIGH,2026-06-12,High,wire,negative,HIGH\n",
        encoding="utf-8",
    )
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    run_news_provider_pack(
        repository, ProviderPackConfig.model_validate({"news": {"providers": [_provider(raw)]}}),
        tmp_path / "out", date(2026, 6, 13),
    )
    candidates = [
        CandidateScanResult(scan_run_id="run", ticker=ticker, as_of_date=date(2026, 6, 13), decision=CandidateDecision.INCLUDE, score=80)
        for ticker in ("CRIT", "HIGH")
    ]

    result = SignalEnricher().enrich_scan_results(
        candidates, date(2026, 6, 13), repository.list_ticker_signals(as_of_date=date(2026, 6, 13))
    )

    assert result[0].decision == CandidateDecision.EXCLUDE
    assert result[1].decision == CandidateDecision.WATCH


def test_run_news_provider_pack_cli(tmp_path, capsys) -> None:
    raw = tmp_path / "news.csv"
    raw.write_text("Symbol,PublishedAt,Headline,Source\nAAA,2026-06-12,Deal,wire\n", encoding="utf-8")
    config_file = tmp_path / "pack.json"
    config_file.write_text(json.dumps({"news": {"providers": [_provider(raw)]}}), encoding="utf-8")

    result = _run(capsys, [
        "run-news-provider-pack", "--db", str(tmp_path / "risk.sqlite3"),
        "--as-of-date", "2026-06-13", "--provider-pack-config", str(config_file),
        "--output-dir", str(tmp_path / "out"),
    ])
    listed = _run(capsys, ["provider-pack-runs", "--db", str(tmp_path / "risk.sqlite3")])
    shown = _run(capsys, [
        "provider-pack-show", "--db", str(tmp_path / "risk.sqlite3"),
        "--provider-pack-run-id", result["provider_pack_run_id"],
    ])

    assert result["provider_pack_type"] == "NEWS"
    assert result["status"] == "COMPLETED"
    assert listed["provider_pack_runs"][0]["provider_pack_type"] == "NEWS"
    assert shown["provider_pack_run_id"] == result["provider_pack_run_id"]


def _provider(path):
    return {
        "provider_name": "news", "local_file": str(path), "data_kind": "NEWS",
        "output_format": "CSV", "allowed_hosts": [], "enabled": True,
        "normalizer": "generic-news-csv",
        "columns": {
            "ticker": "Symbol", "observed_at": "PublishedAt",
            "headline": "Headline", "source_name": "Source",
            "sentiment": "Sentiment", "severity": "Severity", "url": "Url",
        },
    }


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


class FakeNewsClient:
    def get(self, *args, **kwargs):
        body = (
            b"Symbol,PublishedAt,Headline,Source,Sentiment,Severity,Url\n"
            b"AAA,2026-06-12,Investigation,wire,negative,CRITICAL,https://example.com/news\n"
        )
        return {"status_code": 200, "headers": {"Content-Type": "text/csv"}, "body": body}
