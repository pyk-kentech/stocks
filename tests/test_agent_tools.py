from stock_risk_mcp.agent_tools import read_only_tool_manifest


def test_agent_tool_manifest_contains_only_read_only_tools() -> None:
    names = [item["name"] for item in read_only_tool_manifest()]

    assert "get_pipeline_run" in names
    assert "get_analysis_report" in names
    assert "place_order" not in names
    assert "activate_policy" not in names
    assert "delete_data" not in names
