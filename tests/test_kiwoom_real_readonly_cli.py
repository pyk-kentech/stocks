import json

from stock_risk_mcp.cli import main
from stock_risk_mcp.repository import RiskRepository


def test_real_readonly_health_defaults_disabled_and_json_safe(tmp_path, capsys):
    db = tmp_path / "risk.sqlite3"
    main(["kiwoom-real-readonly-health", "--db", str(db)])
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "DISABLED"
    assert result["credentials_loaded"] is False
    assert result["external_network_call_made"] is False
    assert RiskRepository(db).list_kiwoom_real_readonly_runs()


def test_real_readonly_request_without_opt_in_is_blocked_json(tmp_path, capsys):
    db = tmp_path / "risk.sqlite3"
    main(["kiwoom-real-readonly-stock-info", "--db", str(db), "--ticker", "005930"])
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "BLOCKED"
    assert "disabled" in result["error"]
