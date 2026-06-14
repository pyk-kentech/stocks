import json

from stock_risk_mcp.cli import main


def test_kiwoom_official_manifest_cli_list_validate_and_show(capsys) -> None:
    main(["kiwoom-official-endpoints-list", "--class", "ORDER", "--limit", "10"])
    listed = json.loads(capsys.readouterr().out)
    main(["kiwoom-official-endpoints-validate"])
    validated = json.loads(capsys.readouterr().out)
    main(["kiwoom-official-endpoint-show", "--api-id", "ka10008", "--path", "/api/dostk/frgnistt"])
    shown = json.loads(capsys.readouterr().out)

    assert len(listed["endpoints"]) == 2
    assert all(item["read_write_class"] == "ORDER" for item in listed["endpoints"])
    assert validated["valid"] is True
    assert shown["api_id"] == "ka10008"


def test_kiwoom_official_manifest_cli_runtime_allowed_filter_is_empty(capsys) -> None:
    main(["kiwoom-official-endpoints-list", "--runtime-allowed", "--limit", "20"])
    result = json.loads(capsys.readouterr().out)
    assert result["endpoints"] == []
