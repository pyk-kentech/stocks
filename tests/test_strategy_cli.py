import json

from stock_risk_mcp.cli import main


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def write_fixture(path):
    path.write_text(json.dumps({
        "schema_version": "3.0", "config": {},
        "snapshots": [{"snapshot_id": "s1", "ticker": "ABC", "region": "US", "observed_at": "2026-06-15T00:00:00", "features": {"signal_score": 0.8, "risk_score": 0.2, "hard_block": False}}],
        "candidates": [{"candidate_id": "c1", "snapshot_id": "s1", "side": "BUY", "order_type": "LIMIT", "quantity": 1, "limit_price": 10, "rationale": "fixture"}],
    }), encoding="utf-8")


def test_strategy_cli_run_list_show_draft_and_health(tmp_path, capsys) -> None:
    db = tmp_path / "risk.sqlite3"
    fixture = tmp_path / "fixture.json"
    write_fixture(fixture)
    result = run(capsys, ["strategy-run", "--db", str(db), "--fixture-file", str(fixture)])
    decision_id = result["decisions"][0]["decision_id"]

    decisions = run(capsys, ["strategy-decisions", "--db", str(db)])
    shown = run(capsys, ["strategy-decision-show", "--db", str(db), "--decision-id", decision_id])
    candidates = run(capsys, ["strategy-candidates", "--db", str(db)])
    candidate = run(capsys, ["strategy-candidate-show", "--db", str(db), "--candidate-id", "c1"])
    draft = run(capsys, ["strategy-create-order-intent-draft", "--db", str(db), "--decision-id", decision_id])
    health = run(capsys, ["local-llm-health"])

    assert result["run"]["status"] == "COMPLETED"
    assert decisions["decisions"] and shown["decision_id"] == decision_id
    assert candidates["candidates"] and candidate["candidate_id"] == "c1"
    assert draft["order_intent"]["status"] == "CREATED"
    assert health["status"] == "DISABLED"
    assert "secret" not in json.dumps([result, decisions, shown, candidates, candidate, draft, health]).lower()


def test_strategy_run_invalid_fixture_is_json_safe(tmp_path, capsys) -> None:
    result = run(capsys, [
        "strategy-run", "--db", str(tmp_path / "risk.sqlite3"),
        "--fixture-file", str(tmp_path / "missing.json"),
    ])
    assert result["status"] == "FAILED"
    assert result["errors"]
