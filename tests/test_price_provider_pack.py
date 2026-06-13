from datetime import date

from stock_risk_mcp.price_provider_pack import run_price_provider_pack
from stock_risk_mcp.provider_pack_config import ProviderPackConfig
from stock_risk_mcp.provider_packs import ProviderPackRunStatus
from stock_risk_mcp.repository import RiskRepository


def test_price_provider_pack_uses_provider_normalizer_and_columns(tmp_path) -> None:
    raw = tmp_path / "prices.csv"
    raw.write_text("Symbol,Date,Close,Volume\nAAA,2026-06-12,10,100\n", encoding="utf-8")
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    config = ProviderPackConfig.model_validate({"price": {"providers": [{
        "provider_name": "prices", "local_file": str(raw), "data_kind": "PRICE_HISTORY",
        "output_format": "CSV", "allowed_hosts": [], "enabled": True,
        "normalizer": "generic-price-csv",
        "columns": {"ticker": "Symbol", "date": "Date", "close": "Close", "volume": "Volume"},
    }]}})

    run = run_price_provider_pack(repository, config, tmp_path / "out", date(2026, 6, 13))

    assert run.status == ProviderPackRunStatus.COMPLETED
    assert repository.get_all_price_history("AAA")
    assert run.normalize_run_id
    assert run.import_run_id


def test_price_provider_pack_records_missing_normalizer_failure(tmp_path) -> None:
    raw = tmp_path / "prices.csv"
    raw.write_text("Symbol,Date,Close,Volume\nAAA,2026-06-12,10,100\n", encoding="utf-8")
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    config = ProviderPackConfig.model_validate({
        "price": {"providers": [{
            "provider_name": "prices", "local_file": str(raw), "data_kind": "PRICE_HISTORY",
            "output_format": "CSV", "allowed_hosts": [], "enabled": True,
            "columns": {"ticker": "Symbol", "date": "Date", "close": "Close", "volume": "Volume"},
        }]},
    })

    run = run_price_provider_pack(repository, config, tmp_path / "out", date(2026, 6, 13))

    assert run.status == ProviderPackRunStatus.FAILED
    assert any("normalizer" in error.lower() for error in run.errors)
