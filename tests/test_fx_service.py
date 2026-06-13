from datetime import date

from stock_risk_mcp.fx_service import FXService
from stock_risk_mcp.repository import RiskRepository


def test_fx_service_uses_manual_then_latest_asof_and_inverse(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_fx_rates([
        {"base_currency": "USD", "quote_currency": "KRW", "date": date(2026, 6, 1), "rate": 1300, "source_name": "old"},
        {"base_currency": "USD", "quote_currency": "KRW", "date": date(2026, 6, 12), "rate": 1380, "source_name": "latest"},
        {"base_currency": "USD", "quote_currency": "KRW", "date": date(2026, 6, 15), "rate": 1500, "source_name": "future"},
    ])
    service = FXService(repository)

    manual = service.get_latest_fx_rate("USD", "KRW", date(2026, 6, 13), manual_rate=1400)
    direct = service.get_latest_fx_rate("USD", "KRW", date(2026, 6, 13))
    inverse = service.get_latest_fx_rate("KRW", "USD", date(2026, 6, 13))

    assert manual.rate == 1400
    assert manual.source_name == "manual"
    assert direct.rate == 1380
    assert round(inverse.rate, 8) == round(1 / 1380, 8)


def test_fx_service_marks_stale_and_returns_warning_when_missing(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    repository.save_fx_rates([
        {"base_currency": "USD", "quote_currency": "KRW", "date": date(2026, 6, 1), "rate": 1300, "source_name": "old"},
    ])
    service = FXService(repository)

    stale = service.get_latest_fx_rate("USD", "KRW", date(2026, 6, 13), max_staleness_days=7)
    missing = service.get_latest_fx_rate("EUR", "USD", date(2026, 6, 13))

    assert stale.stale
    assert any("stale" in item.lower() for item in stale.warnings)
    assert missing.rate is None
    assert missing.warnings
