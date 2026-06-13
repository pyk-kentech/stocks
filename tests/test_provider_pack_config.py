import json

from stock_risk_mcp.provider_pack_config import load_provider_pack_config, validate_provider_pack_config_file


def test_provider_pack_config_is_single_connector_and_normalizer_source(tmp_path) -> None:
    config_file = tmp_path / "pack.json"
    config_file.write_text(json.dumps(_payload()), encoding="utf-8")

    config = load_provider_pack_config(config_file)

    assert config.price.providers[0].normalizer == "generic-price-csv"
    assert config.price.providers[0].columns["ticker"] == "Symbol"
    assert config.fx.providers[0].normalizer == "generic-fx-csv"


def test_provider_pack_config_reports_missing_required_columns(tmp_path) -> None:
    payload = _payload()
    del payload["price"]["providers"][0]["columns"]["close"]
    config_file = tmp_path / "pack.json"
    config_file.write_text(json.dumps(payload), encoding="utf-8")

    result = validate_provider_pack_config_file(config_file)

    assert result["status"] == "BLOCKED"
    assert any("close" in error for error in result["errors"])


def test_news_provider_config_requires_headline_not_title(tmp_path) -> None:
    payload = _payload()
    payload["news"] = {"providers": [{
        "provider_name": "news", "local_file": "news.csv", "data_kind": "NEWS",
        "output_format": "CSV", "allowed_hosts": [], "enabled": True,
        "normalizer": "generic-news-csv",
        "columns": {
            "ticker": "Symbol", "observed_at": "PublishedAt",
            "headline": "Headline", "source_name": "Source",
        },
    }]}
    config_file = tmp_path / "pack.json"
    config_file.write_text(json.dumps(payload), encoding="utf-8")

    config = load_provider_pack_config(config_file)

    assert config.news.providers[0].columns["headline"] == "Headline"
    assert "title" not in config.news.providers[0].columns


def test_news_provider_config_reports_missing_headline(tmp_path) -> None:
    payload = _payload()
    payload["news"] = {"providers": [{
        "provider_name": "news", "local_file": "news.csv", "data_kind": "NEWS",
        "output_format": "CSV", "allowed_hosts": [], "enabled": True,
        "normalizer": "generic-news-csv",
        "columns": {"ticker": "Symbol", "observed_at": "PublishedAt", "source_name": "Source"},
    }]}
    config_file = tmp_path / "pack.json"
    config_file.write_text(json.dumps(payload), encoding="utf-8")

    result = validate_provider_pack_config_file(config_file)

    assert result["status"] == "BLOCKED"
    assert any("headline" in error for error in result["errors"])


def test_dilution_provider_config_requires_dilution_risk(tmp_path) -> None:
    payload = {"dilution": {"providers": [{
        "provider_name": "dilution", "local_file": "dilution.csv", "data_kind": "DILUTION",
        "output_format": "CSV", "allowed_hosts": [], "enabled": True,
        "normalizer": "generic-dilution-csv",
        "columns": {
            "ticker": "Symbol", "observed_at": "ObservedAt",
            "event_type": "Event", "source_name": "Source",
        },
    }]}}
    config_file = tmp_path / "pack.json"
    config_file.write_text(json.dumps(payload), encoding="utf-8")

    result = validate_provider_pack_config_file(config_file)

    assert result["status"] == "BLOCKED"
    assert any("dilution_risk" in error for error in result["errors"])


def test_flow_provider_config_requires_a_flow_value_mapping(tmp_path) -> None:
    payload = {"flow": {"providers": [{
        "provider_name": "flow", "local_file": "flow.csv",
        "data_kind": "FOREIGN_INSTITUTION_FLOW", "output_format": "CSV",
        "allowed_hosts": [], "enabled": True, "normalizer": "generic-flow-csv",
        "columns": {"ticker": "Symbol", "observed_at": "ObservedAt", "source_name": "Source"},
    }]}}
    config_file = tmp_path / "pack.json"
    config_file.write_text(json.dumps(payload), encoding="utf-8")

    result = validate_provider_pack_config_file(config_file)

    assert result["status"] == "BLOCKED"
    assert any("flow value" in error.lower() for error in result["errors"])


def _payload():
    return {
        "price": {"providers": [{
            "provider_name": "prices", "local_file": "prices.csv",
            "data_kind": "PRICE_HISTORY", "output_format": "CSV", "allowed_hosts": [],
            "enabled": True, "normalizer": "generic-price-csv",
            "columns": {"ticker": "Symbol", "date": "Date", "close": "Close", "volume": "Volume"},
        }]},
        "fx": {"providers": [{
            "provider_name": "fx", "local_file": "fx.csv",
            "data_kind": "FX_RATE", "output_format": "CSV", "allowed_hosts": [],
            "enabled": True, "normalizer": "generic-fx-csv",
            "columns": {"base_currency": "Base", "quote_currency": "Quote", "date": "Date", "rate": "Rate"},
        }]},
    }
