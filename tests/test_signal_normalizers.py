import json
from datetime import date

from stock_risk_mcp.signal_normalizers import (
    GenericDilutionCSVNormalizer,
    GenericFlowCSVNormalizer,
    GenericNewsCSVNormalizer,
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


def _csv(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path
