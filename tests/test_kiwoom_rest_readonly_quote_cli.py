import json

from stock_risk_mcp.cli import main
from tests.test_kiwoom_rest_readonly_quote_models import kiwoom_rest_readonly_quote_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_kiwoom_rest_quote_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "kiwoom_rest_quote_fixture.json", kiwoom_rest_readonly_quote_payload())
    check = run(capsys, ["kiwoom-rest-quote-adapter-check", "--fixture-file", str(fixture_file)])
    request = run(capsys, ["kiwoom-rest-quote-request-report", "--fixture-file", str(fixture_file)])
    mocked = run(capsys, ["kiwoom-rest-quote-mocked-response-report", "--fixture-file", str(fixture_file)])
    canonical_quote = run(capsys, ["kiwoom-rest-canonical-quote-report", "--fixture-file", str(fixture_file)])
    canonical_orderbook = run(capsys, ["kiwoom-rest-canonical-orderbook-report", "--fixture-file", str(fixture_file)])
    liquidity = run(capsys, ["kiwoom-rest-liquidity-hint-report", "--fixture-file", str(fixture_file)])
    basic_info = run(capsys, ["kiwoom-rest-basic-info-report", "--fixture-file", str(fixture_file)])
    continuation = run(capsys, ["kiwoom-rest-quote-continuation-report", "--fixture-file", str(fixture_file)])
    safety = run(capsys, ["kiwoom-rest-quote-readonly-safety-report", "--fixture-file", str(fixture_file)])
    integration = run(capsys, ["kiwoom-rest-quote-v7-integration-report", "--fixture-file", str(fixture_file)])
    gap = run(capsys, ["kiwoom-rest-quote-gap-report", "--fixture-file", str(fixture_file)])

    assert check["readiness"] in {"MOCKED_TRANSPORT_READY", "CANONICAL_QUOTE_READY", "CANONICAL_ORDERBOOK_READY", "LIQUIDITY_HINT_READY", "READONLY_ADAPTER_READY", "DATA_GAP", "SCHEMA_GAP", "BLOCKED", "REJECTED"}
    for report in (request, mocked, canonical_quote, canonical_orderbook, liquidity, basic_info, continuation, safety, integration, gap):
        assert report["report_only"] is True


def test_kiwoom_rest_quote_cli_rejects_remote_or_parquet_or_missing(capsys, tmp_path):
    missing = run(capsys, ["kiwoom-rest-quote-adapter-check", "--fixture-file", str(tmp_path / "missing.json")])
    remote = run(capsys, ["kiwoom-rest-quote-request-report", "--fixture-file", "https://example.com/quote.json"])
    parquet = run(capsys, ["kiwoom-rest-quote-request-report", "--fixture-file", "quote.parquet"])
    assert missing["status"] == "FAILED"
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
