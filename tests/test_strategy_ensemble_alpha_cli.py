import json

from stock_risk_mcp.cli import main
from tests.test_strategy_ensemble_alpha_models import strategy_ensemble_alpha_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_strategy_ensemble_alpha_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "strategy_ensemble_alpha_fixture.json", strategy_ensemble_alpha_payload())
    check = run(capsys, ["strategy-ensemble-check", "--fixture-file", str(fixture_file)])
    candidate = run(capsys, ["alpha-candidate-report", "--fixture-file", str(fixture_file)])
    family = run(capsys, ["strategy-family-diversification-report", "--fixture-file", str(fixture_file)])
    correlation = run(capsys, ["alpha-correlation-risk-report", "--fixture-file", str(fixture_file)])
    drawdown = run(capsys, ["drawdown-co-movement-report", "--fixture-file", str(fixture_file)])
    regime = run(capsys, ["regime-overlap-report", "--fixture-file", str(fixture_file)])
    concentration = run(capsys, ["alpha-portfolio-concentration-report", "--fixture-file", str(fixture_file)])
    promotion = run(capsys, ["ensemble-promotion-readiness-report", "--fixture-file", str(fixture_file)])
    assert check["decision"] in {"ENSEMBLE_READY", "PAPER_CANDIDATE", "GAP"}
    assert candidate["report_only"] is True
    assert family["report_only"] is True
    assert correlation["report_only"] is True
    assert drawdown["report_only"] is True
    assert regime["report_only"] is True
    assert concentration["report_only"] is True
    assert promotion["report_only"] is True


def test_strategy_ensemble_alpha_cli_missing_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["strategy-ensemble-check", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_strategy_ensemble_alpha_cli_rejects_remote_or_parquet_paths(capsys):
    remote = run(capsys, ["alpha-candidate-report", "--fixture-file", "https://example.com/ensemble.json"])
    parquet = run(capsys, ["alpha-candidate-report", "--fixture-file", "ensemble.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
