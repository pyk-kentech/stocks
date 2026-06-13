from datetime import date

from stock_risk_mcp.fx import CurrencyCode, FXConversion, convert_with_rate


def test_currency_conversion_supports_same_currency_and_missing_rate() -> None:
    same = convert_with_rate(100, CurrencyCode.USD, CurrencyCode.USD, None)
    missing = convert_with_rate(100, CurrencyCode.KRW, CurrencyCode.USD, None)

    assert same == 100
    assert missing is None


def test_fx_conversion_converts_base_to_quote() -> None:
    fx = FXConversion(base_currency="USD", quote_currency="KRW", date=date(2026, 6, 13), rate=1380)

    assert fx.convert(10, "USD", "KRW") == 13800
    assert round(fx.convert(13800, "KRW", "USD"), 2) == 10
