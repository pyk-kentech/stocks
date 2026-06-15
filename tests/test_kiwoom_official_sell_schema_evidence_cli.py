import json

from stock_risk_mcp.cli import main
from tests.test_kiwoom_official_sell_schema_evidence import _payload, _write


def _run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_evidence_validate_import_list_show_and_review_cli(tmp_path, capsys):
    db = tmp_path / "risk.sqlite3"
    path = _write(tmp_path / "evidence.json", _payload())

    validated = _run(capsys, [
        "kiwoom-official-sell-schema-evidence-validate", "--evidence-file", str(path),
    ])
    imported = _run(capsys, [
        "kiwoom-official-sell-schema-evidence-import", "--db", str(db), "--evidence-file", str(path),
    ])
    listed = _run(capsys, ["kiwoom-official-sell-schema-evidence-list", "--db", str(db)])
    shown = _run(capsys, [
        "kiwoom-official-sell-schema-evidence-show", "--db", str(db), "--evidence-id", "official-sell-1",
    ])
    reviewed = _run(capsys, [
        "kiwoom-official-sell-schema-evidence-review", "--db", str(db),
        "--evidence-id", "official-sell-1", "--status", "VALIDATED", "--reviewed-by", "operator",
    ])
    payload = json.dumps([validated, imported, listed, shown, reviewed]).lower()

    assert validated["valid"] is True
    assert imported["status"] == "IMPORTED"
    assert listed["evidence"]
    assert shown["evidence_id"] == "official-sell-1"
    assert reviewed["status"] == "VALIDATED"
    assert all(item not in payload for item in ("bearer ", "account_number", "secretkey"))


def test_missing_evidence_file_cli_returns_json_safe_error(tmp_path, capsys):
    result = _run(capsys, [
        "kiwoom-official-sell-schema-evidence-validate",
        "--evidence-file", str(tmp_path / "missing.json"),
    ])
    assert result["errors"] == ["EVIDENCE_FILE_NOT_FOUND"]
