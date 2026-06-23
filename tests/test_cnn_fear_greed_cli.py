import json

from stock_risk_mcp.cli import main
from tests.test_cnn_fear_greed_models import cnn_fear_greed_fixture_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture_file = write(tmp_path / "cnn_fear_greed_fixture.json", cnn_fear_greed_fixture_payload())
    collect = run(capsys, ["cnn-fear-greed-collect", "--fixture-file", str(fixture_file)])
    snapshot = run(capsys, ["cnn-fear-greed-snapshot-report", "--fixture-file", str(fixture_file)])
    history = run(capsys, ["cnn-fear-greed-history-report", "--fixture-file", str(fixture_file)])
    feature = run(capsys, ["cnn-fear-greed-feature-integration-report", "--fixture-file", str(fixture_file)])
    health = run(capsys, ["cnn-fear-greed-source-health-report", "--fixture-file", str(fixture_file)])
    audit = run(capsys, ["cnn-fear-greed-audit-report", "--fixture-file", str(fixture_file)])
    assert collect["report_only"] is True
    assert collect["non_executable"] is True
    assert snapshot["snapshot"]["score"] == 22
    assert history["history_points"][-1]["score"] == 22
    assert feature["cnn_fear_greed_category"] == "EXTREME_FEAR"
    assert health["status"] == "HEALTHY"
    assert audit["redaction_applied"] is True


def test_cli_real_collection_requires_execute_and_ack(tmp_path, capsys):
    fixture_file = write(
        tmp_path / "cnn_fear_greed_fixture.json",
        cnn_fear_greed_fixture_payload(enabled=True, allow_real_network=True),
    )
    missing_execute = run(capsys, ["cnn-fear-greed-collect", "--fixture-file", str(fixture_file), "--acknowledge-cnn-fear-greed-collection"])
    missing_ack = run(capsys, ["cnn-fear-greed-collect", "--fixture-file", str(fixture_file), "--execute"])
    assert missing_execute["status"] == "FAILED"
    assert missing_ack["status"] == "FAILED"


def test_cli_rejects_remote_or_parquet_paths(capsys):
    remote = run(capsys, ["cnn-fear-greed-snapshot-report", "--fixture-file", "https://example.com/cnn.json"])
    parquet = run(capsys, ["cnn-fear-greed-snapshot-report", "--fixture-file", "cnn.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
