from datetime import date

from stock_risk_mcp.fx_normalizers import GenericFXCSVNormalizer
from stock_risk_mcp.repository import RiskRepository


def test_fx_normalizer_and_repository_storage(tmp_path) -> None:
    raw = tmp_path / "fx.csv"
    raw.write_text("base,quote,day,value,provider\nUSD,KRW,2026-06-12,1350.5,fixture\n", encoding="utf-8")
    result = GenericFXCSVNormalizer().normalize(
        raw, tmp_path / "out", date(2026, 6, 13),
        columns={"base_currency": "base", "quote_currency": "quote", "date": "day",
                 "rate": "value", "source_name": "provider"},
    )
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_fx_rates([{
        "base_currency": "USD", "quote_currency": "KRW", "date": date(2026, 6, 12),
        "rate": 1350.5, "source_name": "fixture",
    }])

    assert result.normalized_count == 1
    assert repository.get_latest_fx_rate("USD", "KRW")["rate"] == 1350.5
    assert repository.list_fx_rates()
