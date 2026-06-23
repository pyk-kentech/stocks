import json

from stock_risk_mcp.cli import main
from tests.test_risk_adjusted_paper_eval_models import risk_adjusted_paper_eval_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "risk_adjusted_paper_eval_fixture.json", risk_adjusted_paper_eval_payload())
    check = run(capsys, ["risk-adjusted-paper-eval-check", "--fixture-file", str(fixture_file)])
    summary = run(capsys, ["paper-evaluation-summary-report", "--fixture-file", str(fixture_file)])
    portfolio = run(capsys, ["virtual-portfolio-report", "--fixture-file", str(fixture_file)])
    ledger = run(capsys, ["virtual-trade-ledger-report", "--fixture-file", str(fixture_file)])
    costs = run(capsys, ["paper-cost-slippage-report", "--fixture-file", str(fixture_file)])
    perf = run(capsys, ["paper-risk-adjusted-performance-report", "--fixture-file", str(fixture_file)])
    drawdown = run(capsys, ["paper-drawdown-exposure-report", "--fixture-file", str(fixture_file)])
    bucket = run(capsys, ["paper-regime-fear-bucket-report", "--fixture-file", str(fixture_file)])
    readiness = run(capsys, ["paper-pass-readiness-report", "--fixture-file", str(fixture_file)])
    assert check["decision"] in {"PAPER_EVALUATED", "PAPER_PASS", "GAP", "BLOCKED", "RESEARCH_ONLY"}
    assert summary["report_only"] is True
    assert portfolio["report_only"] is True
    assert ledger["report_only"] is True
    assert costs["report_only"] is True
    assert perf["report_only"] is True
    assert drawdown["report_only"] is True
    assert bucket["report_only"] is True
    assert readiness["report_only"] is True


def test_cli_missing_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["risk-adjusted-paper-eval-check", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_cli_rejects_remote_or_parquet_paths(capsys):
    remote = run(capsys, ["paper-evaluation-summary-report", "--fixture-file", "https://example.com/eval.json"])
    parquet = run(capsys, ["paper-evaluation-summary-report", "--fixture-file", "eval.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
