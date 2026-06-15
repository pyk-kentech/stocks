from stock_risk_mcp.system_smoke import run_system_smoke


def test_system_smoke_validates_local_workflow(tmp_path) -> None:
    result = run_system_smoke(tmp_path / "smoke.sqlite3", tmp_path / "outputs")

    assert result["status"] in {"COMPLETED", "PARTIAL"}
    assert result["checks"]["db_migration"] is True
    assert result["checks"]["mock_connector_output"] is True
    assert result["checks"]["import"] is True
    assert result["checks"]["pipeline_run"] is True
    assert result["checks"]["dashboard_html"] is True
    assert result["checks"]["external_network_calls"] is False
    assert result["checks"]["strategy_fixture_run"] is True
