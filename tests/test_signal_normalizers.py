import json
from datetime import date

from stock_risk_mcp.signal_normalizers import (
    GenericDilutionCSVNormalizer,
    GenericFlowCSVNormalizer,
    GenericNewsCSVNormalizer,
    _news_provider_score,
    _dilution_provider_mapping,
)


def test_news_normalizer_maps_columns_and_skips_future(tmp_path) -> None:
    raw = _csv(tmp_path, "news.csv", "symbol,published,headline,body,sentiment\n"
               "aaa,2026-06-12,Deal,Details,mystery\nBBB,2026-06-14,Future,Later,positive\n")
    result = GenericNewsCSVNormalizer().normalize(
        raw, tmp_path / "out", date(2026, 6, 13), output_name="news.json",
        columns={"ticker": "symbol", "observed_at": "published", "title": "headline",
                 "summary": "body", "sentiment": "sentiment"},
    )
    rows = json.loads(open(result.output_path, encoding="utf-8").read())
    assert rows[0]["ticker"] == "AAA"
    assert rows[0]["sentiment"] == "NEUTRAL"
    assert result.skipped_count == 1


def test_news_normalizer_maps_headline_defaults_info_and_preserves_raw_payload(tmp_path) -> None:
    raw = _csv(
        tmp_path, "provider-news.csv",
        "Symbol,PublishedAt,Headline,Source,Sentiment,Severity,Url\n"
        "AAA,2026-06-12,Deal signed,wire,positive,INFO,https://example.com/a\n"
        "BBB,2026-06-12,Investigation,wire,negative,CRITICAL,https://example.com/b\n",
    )

    result = GenericNewsCSVNormalizer().normalize(
        raw, tmp_path / "out", date(2026, 6, 13), output_name="news.json",
        columns={
            "ticker": "Symbol", "observed_at": "PublishedAt", "headline": "Headline",
            "source_name": "Source", "sentiment": "Sentiment", "severity": "Severity", "url": "Url",
        },
    )
    rows = json.loads(open(result.output_path, encoding="utf-8").read())

    assert rows[0]["title"] == "Deal signed"
    assert rows[0]["severity"] == "LOW"
    assert rows[0]["score_delta"] == 1
    assert rows[0]["raw_payload_json"]["Severity"] == "INFO"
    assert rows[1]["score_delta"] == -10


def test_news_provider_score_policy_is_conservative_and_isolated() -> None:
    assert [_news_provider_score("POSITIVE", item) for item in ("LOW", "MEDIUM", "HIGH", "CRITICAL")] == [1, 2, 3, 3]
    assert [_news_provider_score("NEGATIVE", item) for item in ("LOW", "MEDIUM", "HIGH", "CRITICAL")] == [-1, -3, -5, -10]
    assert _news_provider_score("NEUTRAL", "HIGH") == 0


def test_dilution_and_flow_normalizers_create_internal_schemas(tmp_path) -> None:
    dilution = _csv(tmp_path, "dilution.csv", "symbol,when,event,risk,details\nAAA,2026-06-12,OFFERING,HIGH,Filed\n")
    flow = _csv(tmp_path, "flow.csv", "symbol,when,foreign,inst,ownership,days\nAAA,2026-06-12,10,20,0.1,5\n")

    dilution_result = GenericDilutionCSVNormalizer().normalize(
        dilution, tmp_path / "out", date(2026, 6, 13),
        columns={"ticker": "symbol", "observed_at": "when", "event_type": "event",
                 "severity": "risk", "details": "details"},
    )
    flow_result = GenericFlowCSVNormalizer().normalize(
        flow, tmp_path / "out", date(2026, 6, 13),
        columns={"ticker": "symbol", "observed_at": "when", "foreign_net_buy": "foreign",
                 "institution_net_buy": "inst", "foreign_ownership_change": "ownership",
                 "flow_window_days": "days"},
    )

    assert dilution_result.normalized_count == 1
    assert flow_result.normalized_count == 1


def test_dilution_provider_mapping_is_non_positive_and_preserves_unknown(tmp_path) -> None:
    raw = _csv(
        tmp_path, "provider-dilution.csv",
        "Symbol,ObservedAt,Event,Risk,Source\n"
        "AAA,2026-06-12,OFFERING,HIGH,filings\n"
        "BBB,2026-06-12,UNKNOWN,UNKNOWN,filings\n",
    )

    result = GenericDilutionCSVNormalizer().normalize(
        raw, tmp_path / "out", date(2026, 6, 13), output_name="dilution.json",
        columns={
            "ticker": "Symbol", "observed_at": "ObservedAt", "event_type": "Event",
            "dilution_risk": "Risk", "source_name": "Source",
        },
    )
    rows = json.loads(open(result.output_path, encoding="utf-8").read())

    assert (rows[0]["severity"], rows[0]["score_delta"]) == ("HIGH", -7)
    assert (rows[1]["severity"], rows[1]["score_delta"]) == ("HIGH", -7)
    assert rows[1]["raw_payload_json"]["Risk"] == "UNKNOWN"
    assert [_dilution_provider_mapping(item)[1] for item in (
        "NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"
    )] == [0, -1, -3, -7, -10, -7]


def _csv(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path
