import json
from datetime import date

from stock_risk_mcp.cli import main
from stock_risk_mcp.provider_pack_config import ProviderPackConfig
from stock_risk_mcp.provider_pack_pipeline import run_provider_pack
from stock_risk_mcp.provider_packs import ProviderPackRunStatus, ProviderPackType
from stock_risk_mcp.repository import RiskRepository


def test_price_and_fx_pack_is_partial_when_price_succeeds_and_fx_fails(tmp_path) -> None:
    prices = tmp_path / "prices.csv"
    prices.write_text("Symbol,Date,Close,Volume\nAAA,2026-06-12,10,100\n", encoding="utf-8")
    config = ProviderPackConfig.model_validate({
        "price": {"providers": [_provider("prices", prices, "PRICE_HISTORY", "generic-price-csv", {
            "ticker": "Symbol", "date": "Date", "close": "Close", "volume": "Volume",
        })]},
        "fx": {"providers": [_provider("fx", tmp_path / "missing.csv", "FX_RATE", "generic-fx-csv", {
            "base_currency": "Base", "quote_currency": "Quote", "date": "Date", "rate": "Rate",
        })]},
    })

    run = run_provider_pack(
        RiskRepository(tmp_path / "risk.sqlite3"), config, ProviderPackType.PRICE_AND_FX,
        tmp_path / "out", date(2026, 6, 13),
    )

    assert run.status == ProviderPackRunStatus.PARTIAL


def test_price_and_fx_pack_fails_when_price_fails(tmp_path) -> None:
    fx = tmp_path / "fx.csv"
    fx.write_text("Base,Quote,Date,Rate\nUSD,KRW,2026-06-12,1380\n", encoding="utf-8")
    config = ProviderPackConfig.model_validate({
        "price": {"providers": [_provider("prices", tmp_path / "missing.csv", "PRICE_HISTORY", "generic-price-csv", {
            "ticker": "Symbol", "date": "Date", "close": "Close", "volume": "Volume",
        })]},
        "fx": {"providers": [_provider("fx", fx, "FX_RATE", "generic-fx-csv", {
            "base_currency": "Base", "quote_currency": "Quote", "date": "Date", "rate": "Rate",
        })]},
    })

    run = run_provider_pack(
        RiskRepository(tmp_path / "risk.sqlite3"), config, ProviderPackType.PRICE_AND_FX,
        tmp_path / "out", date(2026, 6, 13),
    )

    assert run.status == ProviderPackRunStatus.FAILED


def test_http_provider_is_disabled_when_network_is_off(tmp_path) -> None:
    config = ProviderPackConfig.model_validate({"price": {"providers": [{
        "provider_name": "prices", "url": "https://example.com/prices.csv", "data_kind": "PRICE_HISTORY",
        "output_format": "CSV", "allowed_hosts": ["example.com"], "enabled": True,
        "normalizer": "generic-price-csv",
        "columns": {"ticker": "ticker", "date": "date", "close": "close", "volume": "volume"},
    }]}})

    run = run_provider_pack(
        RiskRepository(tmp_path / "risk.sqlite3"), config, ProviderPackType.PRICE,
        tmp_path / "out", date(2026, 6, 13), enable_network=False,
    )

    assert run.status == ProviderPackRunStatus.DISABLED


def test_fake_http_price_and_fx_outputs_flow_through_normalize_and_import(tmp_path) -> None:
    config = ProviderPackConfig.model_validate({
        "price": {"providers": [{
            "provider_name": "prices", "url": "https://example.com/prices.csv",
            "data_kind": "PRICE_HISTORY", "output_format": "CSV", "allowed_hosts": ["example.com"],
            "enabled": True, "normalizer": "generic-price-csv",
            "columns": {"ticker": "Symbol", "date": "Date", "close": "Close", "volume": "Volume"},
        }]},
        "fx": {"providers": [{
            "provider_name": "fx", "url": "https://example.com/fx.csv",
            "data_kind": "FX_RATE", "output_format": "CSV", "allowed_hosts": ["example.com"],
            "enabled": True, "normalizer": "generic-fx-csv",
            "columns": {"base_currency": "Base", "quote_currency": "Quote", "date": "Date", "rate": "Rate"},
        }]},
    })
    repository = RiskRepository(tmp_path / "risk.sqlite3")

    run = run_provider_pack(
        repository, config, ProviderPackType.PRICE_AND_FX, tmp_path / "out", date(2026, 6, 13),
        enable_network=True, client=FakeProviderClient(),
    )

    assert run.status == ProviderPackRunStatus.COMPLETED
    assert repository.get_all_price_history("AAA")
    assert repository.get_latest_fx_rate("USD", "KRW")["rate"] == 1380


def test_provider_pack_cli_runs_lists_and_shows_without_normalizer_config(tmp_path, capsys) -> None:
    raw = tmp_path / "prices.csv"
    raw.write_text("Symbol,Date,Close,Volume\nAAA,2026-06-12,10,100\n", encoding="utf-8")
    fx = tmp_path / "fx.csv"
    fx.write_text("Base,Quote,Date,Rate\nUSD,KRW,2026-06-12,1380\n", encoding="utf-8")
    config_file = tmp_path / "pack.json"
    config_file.write_text(json.dumps({
        "price": {"providers": [_provider("prices", raw, "PRICE_HISTORY", "generic-price-csv", {
            "ticker": "Symbol", "date": "Date", "close": "Close", "volume": "Volume",
        })]},
        "fx": {"providers": [_provider("fx", fx, "FX_RATE", "generic-fx-csv", {
            "base_currency": "Base", "quote_currency": "Quote", "date": "Date", "rate": "Rate",
        })]},
    }), encoding="utf-8")
    db = tmp_path / "risk.sqlite3"

    price_result = _run(capsys, [
        "run-price-provider-pack", "--db", str(db), "--as-of-date", "2026-06-13",
        "--provider-pack-config", str(config_file), "--output-dir", str(tmp_path / "price-out"),
    ])
    fx_result = _run(capsys, [
        "run-fx-provider-pack", "--db", str(db), "--as-of-date", "2026-06-13",
        "--provider-pack-config", str(config_file), "--output-dir", str(tmp_path / "fx-out"),
    ])
    combined_result = _run(capsys, [
        "run-price-fx-provider-pack", "--db", str(db), "--as-of-date", "2026-06-13",
        "--provider-pack-config", str(config_file), "--output-dir", str(tmp_path / "combined-out"),
    ])
    listed = _run(capsys, ["provider-pack-runs", "--db", str(db)])
    shown = _run(capsys, [
        "provider-pack-show", "--db", str(db), "--provider-pack-run-id", combined_result["provider_pack_run_id"],
    ])

    assert price_result["status"] == "COMPLETED"
    assert fx_result["status"] == "COMPLETED"
    assert combined_result["status"] == "COMPLETED"
    assert listed["provider_pack_runs"]
    assert shown["provider_pack_run_id"] == combined_result["provider_pack_run_id"]


def _provider(name, path, data_kind, normalizer, columns):
    return {
        "provider_name": name, "local_file": str(path), "data_kind": data_kind,
        "output_format": "CSV", "allowed_hosts": [], "enabled": True,
        "normalizer": normalizer, "columns": columns,
    }


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


class FakeProviderClient:
    def get(self, url, *args, **kwargs):
        if "prices" in url:
            body = b"Symbol,Date,Close,Volume\nAAA,2026-06-12,10,100\n"
        else:
            body = b"Base,Quote,Date,Rate\nUSD,KRW,2026-06-12,1380\n"
        return {"status_code": 200, "headers": {"Content-Type": "text/csv"}, "body": body}
