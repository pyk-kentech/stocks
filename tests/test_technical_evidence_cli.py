import json
from stock_risk_mcp.cli import main
from tests.test_technical_evidence_fixture import payload

def run(capsys,args):
    main(args);return json.loads(capsys.readouterr().out)

def test_technical_evidence_run_output_and_show(tmp_path,capsys):
    fixture=tmp_path/"fixture.json";fixture.write_text(json.dumps(payload(20)),encoding="utf-8")
    output=tmp_path/"result.json"
    summary=run(capsys,["technical-evidence-run","--fixture-file",str(fixture),"--output-file",str(output)])
    shown=run(capsys,["technical-evidence-show","--output-file",str(output)])
    stdout=run(capsys,["technical-evidence-run","--fixture-file",str(fixture)])
    assert summary["status"]=="COMPLETED" and output.exists()
    assert shown["metadata_json"]["advisory_only"] is True
    assert stdout["evidence"][0]["grade"]=="NO_TRADE"

def test_technical_evidence_invalid_fixture_is_json_safe(tmp_path,capsys):
    result=run(capsys,["technical-evidence-run","--fixture-file",str(tmp_path/"missing.json")])
    assert result["status"]=="FAILED" and result["errors"]
