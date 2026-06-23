import json

import stock_risk_mcp.cli as cli_mod

from stock_risk_mcp.cli import main
from stock_risk_mcp.kiwoom_mock_market_data_execution_engine import (
    execute_kiwoom_mock_market_data,
)
from stock_risk_mcp.kiwoom_mock_market_data_execution_fixture import (
    load_kiwoom_mock_market_data_execution_fixture,
)
from tests.test_kiwoom_mock_market_data_execution_models import (
    kiwoom_mock_market_data_execution_fixture_payload,
)


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def install_mock_execution(monkeypatch):
    def fake_run(fixture_file, *, execute, acknowledge_mock_market_data_execution, mock_domain):
        fixture = load_kiwoom_mock_market_data_execution_fixture(fixture_file)
        return execute_kiwoom_mock_market_data(
            fixture,
            execute=execute,
            acknowledge_mock_market_data_execution=acknowledge_mock_market_data_execution,
            mock_domain=mock_domain,
            access_token="in-memory-token",
            transport=lambda request: {"symbol": "005930", "last_price": 70000, "condition_match": True},
        )

    monkeypatch.setattr(cli_mod, "_run_kiwoom_mock_market_data_execution", fake_run)


def test_cli_commands_require_explicit_execution_acknowledgement(tmp_path, capsys):
    fixture_file = write(tmp_path / "market.json", kiwoom_mock_market_data_execution_fixture_payload())
    result = run(capsys, ["kiwoom-mock-market-data-request-execute", "--fixture-file", str(fixture_file)])
    assert result["status"] == "FAILED"
    assert "explicit opt-in" in result["errors"][0].lower()


def test_request_execute_cli_uses_redacted_output(tmp_path, capsys, monkeypatch):
    install_mock_execution(monkeypatch)
    fixture_file = write(tmp_path / "market.json", kiwoom_mock_market_data_execution_fixture_payload())
    result = run(
        capsys,
        [
            "kiwoom-mock-market-data-request-execute",
            "--fixture-file",
            str(fixture_file),
            "--mock-domain",
            "--execute",
            "--acknowledge-mock-market-data-execution",
        ],
    )
    dumped = json.dumps(result)
    assert result["response"]["sanitized"] is True
    assert "in-memory-token" not in dumped
    assert "authorization" not in dumped.lower()


def test_cli_report_commands_output_redacted_json(tmp_path, capsys):
    fixture_file = write(tmp_path / "market.json", kiwoom_mock_market_data_execution_fixture_payload())
    response = run(capsys, ["kiwoom-mock-market-data-response-report", "--fixture-file", str(fixture_file)])
    safety = run(capsys, ["kiwoom-mock-market-data-safety-report", "--fixture-file", str(fixture_file)])
    gap = run(capsys, ["kiwoom-mock-market-data-gap-report", "--fixture-file", str(fixture_file)])
    audit = run(capsys, ["kiwoom-mock-market-data-audit-report", "--fixture-file", str(fixture_file)])
    assert response["sanitized"] is True
    assert "ACCOUNT_PATH_BLOCKED" in safety["blocked_capabilities"]
    assert "REAL_MARKET_DATA_STAGE_NOT_IMPLEMENTED" in gap["gap_categories"]
    assert audit["redaction_applied"] is True


def test_cli_blocks_production_domain(tmp_path, capsys):
    payload = kiwoom_mock_market_data_execution_fixture_payload(
        documented_mock_domain="https://api.kiwoom.com"
    )
    fixture_file = write(tmp_path / "market.json", payload)
    result = run(capsys, ["kiwoom-mock-market-data-safety-report", "--fixture-file", str(fixture_file)])
    assert result["status"] == "FAILED"
    assert "production domain" in result["errors"][0].lower()


def test_cli_rejects_remote_or_parquet_fixture_paths(capsys):
    remote = run(capsys, ["kiwoom-mock-market-data-gap-report", "--fixture-file", "https://mockapi.kiwoom.com/market.json"])
    parquet = run(capsys, ["kiwoom-mock-market-data-gap-report", "--fixture-file", "market.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
