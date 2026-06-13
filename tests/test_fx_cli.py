import json

from stock_risk_mcp.cli import main


def test_fx_cli_rates_latest_and_convert(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    fx = tmp_path / "fx.csv"
    fx.write_text("base_currency,quote_currency,date,rate,source_name\nUSD,KRW,2026-06-13,1380,fixture\n", encoding="utf-8")
    _run(capsys, ["import-data", "--db", str(db), "--fx-rate-file", str(fx), "--as-of-date", "2026-06-13"])

    rates = _run(capsys, ["fx-rates", "--db", str(db), "--base-currency", "USD", "--quote-currency", "KRW"])
    latest = _run(capsys, ["fx-latest", "--db", str(db), "--base-currency", "USD", "--quote-currency", "KRW", "--as-of-date", "2026-06-13"])
    converted = _run(capsys, ["fx-convert", "--db", str(db), "--amount", "1380", "--from-currency", "KRW", "--to-currency", "USD", "--as-of-date", "2026-06-13"])

    assert rates["fx_rates"]
    assert latest["rate"] == 1380
    assert converted["converted_amount"] == 1


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)
