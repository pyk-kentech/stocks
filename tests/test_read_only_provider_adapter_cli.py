import json

from stock_risk_mcp.cli import main
from tests.test_read_only_provider_adapter_models import read_only_provider_adapter_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_read_only_provider_adapter_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "read_only_provider_adapter_fixture.json", read_only_provider_adapter_payload())
    check = run(capsys, ["read-only-provider-adapter-boundary-check", "--fixture-file", str(fixture_file)])
    evidence = run(capsys, ["kiwoom-rest-evidence-map-report", "--fixture-file", str(fixture_file)])
    ls_report = run(capsys, ["ls-future-compatibility-report", "--fixture-file", str(fixture_file)])
    contract = run(capsys, ["canonical-readonly-contract-report", "--fixture-file", str(fixture_file)])
    capability = run(capsys, ["provider-capability-matrix-report", "--fixture-file", str(fixture_file)])
    blocked = run(capsys, ["blocked-account-order-api-report", "--fixture-file", str(fixture_file)])
    migration = run(capsys, ["provider-migration-readiness-report", "--fixture-file", str(fixture_file)])
    gap = run(capsys, ["read-only-provider-gap-report", "--fixture-file", str(fixture_file)])

    assert check["readiness"] in {"BOUNDARY_READY", "KIWOOM_READONLY_EVIDENCE_READY", "LS_FUTURE_PLACEHOLDER", "CANONICAL_CONTRACT_READY", "DATA_GAP", "BLOCKED", "REJECTED"}
    for report in (evidence, ls_report, contract, capability, blocked, migration, gap):
        assert report["report_only"] is True


def test_read_only_provider_cli_rejects_remote_or_parquet_or_missing(capsys, tmp_path):
    missing = run(capsys, ["read-only-provider-adapter-boundary-check", "--fixture-file", str(tmp_path / "missing.json")])
    remote = run(capsys, ["kiwoom-rest-evidence-map-report", "--fixture-file", "https://example.com/provider.json"])
    parquet = run(capsys, ["kiwoom-rest-evidence-map-report", "--fixture-file", "provider.parquet"])
    assert missing["status"] == "FAILED"
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
