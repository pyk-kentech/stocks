import json

from stock_risk_mcp.cli import main


def test_kiwoom_readonly_cli_commands_use_fake_transport(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    commands = [
        ["kiwoom-readonly-health", "--db", str(db), "--environment", "MOCK"],
        ["kiwoom-readonly-endpoints", "--db", str(db)],
        ["kiwoom-readonly-stock-info", "--db", str(db), "--ticker", "005930"],
        ["kiwoom-readonly-quote", "--db", str(db), "--ticker", "005930"],
        ["kiwoom-readonly-rankings", "--db", str(db), "--rank-type", "volume", "--market", "KOSPI"],
        ["kiwoom-readonly-flow", "--db", str(db), "--ticker", "005930"],
        ["kiwoom-readonly-chart", "--db", str(db), "--ticker", "005930", "--interval", "1m", "--count", "1"],
        ["kiwoom-readonly-condition-list", "--db", str(db)],
        ["kiwoom-readonly-condition-run", "--db", str(db), "--condition-id", "C1"],
    ]
    results = []
    for command in commands:
        main(command)
        results.append(json.loads(capsys.readouterr().out))

    assert results[0]["status"] == "CONNECTED"
    assert len(results[1]["endpoints"]) == 7
    assert all("authorization" not in str(item).lower() for item in results)
    assert all("fake-local-token" not in str(item) for item in results)


def test_kiwoom_prod_disabled_cli_returns_json(tmp_path, capsys) -> None:
    main([
        "kiwoom-readonly-quote", "--db", str(tmp_path / "risk.sqlite3"),
        "--ticker", "005930", "--environment", "PROD_DISABLED",
    ])
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "DISABLED"
