from datetime import date

from stock_risk_mcp.fx_provider_pack import run_fx_provider_pack
from stock_risk_mcp.provider_pack_config import ProviderPackConfig
from stock_risk_mcp.provider_packs import ProviderPackRunStatus
from stock_risk_mcp.repository import RiskRepository


def test_fx_provider_pack_uses_provider_normalizer_and_columns(tmp_path) -> None:
    raw = tmp_path / "fx.csv"
    raw.write_text("Base,Quote,Date,Rate\nUSD,KRW,2026-06-12,1380\n", encoding="utf-8")
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    config = ProviderPackConfig.model_validate({"fx": {"providers": [{
        "provider_name": "fx", "local_file": str(raw), "data_kind": "FX_RATE",
        "output_format": "CSV", "allowed_hosts": [], "enabled": True,
        "normalizer": "generic-fx-csv",
        "columns": {"base_currency": "Base", "quote_currency": "Quote", "date": "Date", "rate": "Rate"},
    }]}})

    run = run_fx_provider_pack(repository, config, tmp_path / "out", date(2026, 6, 13))

    assert run.status == ProviderPackRunStatus.COMPLETED
    assert repository.get_latest_fx_rate("USD", "KRW")["rate"] == 1380
