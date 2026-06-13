import json

from stock_risk_mcp.cli import main


def test_demo_smoke_and_release_cli_commands(tmp_path, capsys) -> None:
    demo = _run(capsys, [
        "run-local-demo", "--db", str(tmp_path / "demo.sqlite3"), "--as-of-date", "2026-06-13",
        "--output-dir", str(tmp_path / "demo_outputs"),
    ])
    smoke = _run(capsys, [
        "system-smoke", "--db", str(tmp_path / "smoke.sqlite3"), "--output-dir", str(tmp_path / "smoke_outputs"),
    ])
    release = _run(capsys, ["release-check"])

    assert demo["demo_run_id"]
    assert demo["pipeline_run_id"]
    assert smoke["checks"]["external_network_calls"] is False
    assert release["commands"]["pytest"] == "pytest -q"


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)
