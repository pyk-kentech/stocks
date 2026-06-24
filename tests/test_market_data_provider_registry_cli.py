import json

from stock_risk_mcp.cli import main
from tests.test_market_data_provider_registry_models import market_data_provider_registry_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_registry_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture = write(tmp_path / "provider_registry_fixture.json", market_data_provider_registry_payload())
    check = run(capsys, ["market-data-provider-registry-check", "--fixture-file", str(fixture)])
    registry = run(capsys, ["global-provider-registry-report", "--fixture-file", str(fixture)])
    requirement = run(capsys, ["module-data-requirement-report", "--fixture-file", str(fixture)])
    readiness = run(capsys, ["provider-readiness-matrix-report", "--fixture-file", str(fixture)])
    contract = run(capsys, ["canonical-data-contract-report", "--fixture-file", str(fixture)])
    mapping = run(capsys, ["symbol-mapping-report", "--fixture-file", str(fixture)])
    selection = run(capsys, ["provider-selection-report", "--fixture-file", str(fixture)])
    gap = run(capsys, ["market-data-provider-gap-report", "--fixture-file", str(fixture)])
    assert check["decision"] in {"PAPER_READY", "TRAINING_READY", "BACKTEST_READY", "GAP", "REJECTED"}
    assert registry["report_only"] is True
    assert requirement["report_only"] is True
    assert readiness["report_only"] is True
    assert contract["report_only"] is True
    assert mapping["report_only"] is True
    assert selection["report_only"] is True
    assert gap["report_only"] is True


def test_registry_cli_missing_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["market-data-provider-registry-check", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_registry_cli_rejects_remote_or_parquet_paths(capsys):
    remote = run(capsys, ["global-provider-registry-report", "--fixture-file", "https://example.com/provider_registry.json"])
    parquet = run(capsys, ["global-provider-registry-report", "--fixture-file", "provider_registry.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
