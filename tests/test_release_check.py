from stock_risk_mcp.release_check import build_release_check


def test_release_check_lists_commands_docs_and_cli(tmp_path) -> None:
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    (tmp_path / "WORK_SUMMARY.md").write_text("summary", encoding="utf-8")

    result = build_release_check(tmp_path)

    assert result["commands"]["pytest"] == "pytest -q"
    assert result["commands"]["compileall"] == "python -m compileall -q src"
    assert result["documents"]["README.md"] is True
    assert "run-local-demo" in result["major_cli_commands"]
    assert result["recommended_tag"].startswith("v")
    assert result["tag_created"] is False
