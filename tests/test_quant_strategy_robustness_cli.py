import json

from stock_risk_mcp.cli import main
from tests.test_quant_strategy_robustness_models import quant_strategy_robustness_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_quant_robustness_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "quant_strategy_robustness_fixture.json", quant_strategy_robustness_payload())
    check = run(capsys, ["quant-robustness-check", "--fixture-file", str(fixture_file)])
    survivorship = run(capsys, ["quant-survivorship-bias-report", "--fixture-file", str(fixture_file)])
    pit = run(capsys, ["quant-point-in-time-leakage-report", "--fixture-file", str(fixture_file)])
    walk = run(capsys, ["quant-walk-forward-policy-report", "--fixture-file", str(fixture_file)])
    snooping = run(capsys, ["quant-data-snooping-report", "--fixture-file", str(fixture_file)])
    diversification = run(capsys, ["quant-strategy-diversification-report", "--fixture-file", str(fixture_file)])
    regime = run(capsys, ["quant-regime-readiness-report", "--fixture-file", str(fixture_file)])
    assert check["decision"] == "TRAINING_READY"
    assert survivorship["report_only"] is True
    assert pit["report_only"] is True
    assert walk["report_only"] is True
    assert snooping["report_only"] is True
    assert diversification["report_only"] is True
    assert regime["report_only"] is True


def test_quant_robustness_cli_missing_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["quant-robustness-check", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_quant_robustness_cli_rejects_remote_or_parquet_paths(capsys):
    remote = run(capsys, ["quant-point-in-time-leakage-report", "--fixture-file", "https://example.com/test.json"])
    parquet = run(capsys, ["quant-point-in-time-leakage-report", "--fixture-file", "test.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
