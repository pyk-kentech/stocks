import json

from stock_risk_mcp.cli import main
from tests.test_breadth_leadership_routing_models import breadth_leadership_routing_payload


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(capsys, args):
    main(args)
    return json.loads(capsys.readouterr().out)


def test_breadth_leadership_routing_cli_commands_output_expected_reports(tmp_path, capsys):
    fixture = write(tmp_path / "breadth_routing_fixture.json", breadth_leadership_routing_payload())
    check = run(capsys, ["breadth-leadership-routing-check", "--fixture-file", str(fixture)])
    summary = run(capsys, ["breadth-routing-summary-report", "--fixture-file", str(fixture)])
    snapshot = run(capsys, ["breadth-input-snapshot-report", "--fixture-file", str(fixture)])
    ad = run(capsys, ["advance-decline-report", "--fixture-file", str(fixture)])
    nhl = run(capsys, ["new-high-low-report", "--fixture-file", str(fixture)])
    volume = run(capsys, ["up-down-volume-participation-report", "--fixture-file", str(fixture)])
    sector = run(capsys, ["sector-leadership-report", "--fixture-file", str(fixture)])
    concentration = run(capsys, ["leadership-concentration-report", "--fixture-file", str(fixture)])
    distortion = run(capsys, ["index-distortion-report", "--fixture-file", str(fixture)])
    divergence = run(capsys, ["equal-weight-divergence-report", "--fixture-file", str(fixture)])
    outlier = run(capsys, ["outlier-momentum-candidate-report", "--fixture-file", str(fixture)])
    sleeve = run(capsys, ["outlier-sleeve-risk-report", "--fixture-file", str(fixture)])
    downstream = run(capsys, ["breadth-routing-downstream-constraint-report", "--fixture-file", str(fixture)])
    readiness = run(capsys, ["breadth-routing-provider-readiness-report", "--fixture-file", str(fixture)])
    leakage = run(capsys, ["breadth-routing-leakage-report", "--fixture-file", str(fixture)])
    gap = run(capsys, ["breadth-routing-gap-report", "--fixture-file", str(fixture)])

    assert check["primary_decision"] in {
        "BROAD_MARKET_OK",
        "LEADERSHIP_ONLY",
        "SECTOR_ONLY",
        "LARGE_CAP_ONLY",
        "WATCH_NON_LEADERS",
        "OUTLIER_MOMENTUM_ALLOWED",
        "OUTLIER_MOMENTUM_RESTRICTED",
        "REDUCE_SIZE",
        "BLOCK_CHASING",
        "DATA_GAP",
        "BLOCKED",
        "REJECTED",
    }
    for report in (
        summary,
        snapshot,
        ad,
        nhl,
        volume,
        sector,
        concentration,
        distortion,
        divergence,
        outlier,
        sleeve,
        downstream,
        readiness,
        leakage,
        gap,
    ):
        assert report["report_only"] is True


def test_breadth_leadership_cli_missing_fixture_is_json_safe(tmp_path, capsys):
    result = run(capsys, ["breadth-leadership-routing-check", "--fixture-file", str(tmp_path / "missing.json")])
    assert result["status"] == "FAILED"
    assert result["errors"]


def test_breadth_leadership_cli_rejects_remote_or_parquet_paths(capsys):
    remote = run(capsys, ["breadth-routing-summary-report", "--fixture-file", "https://example.com/breadth_routing.json"])
    parquet = run(capsys, ["breadth-routing-summary-report", "--fixture-file", "breadth_routing.parquet"])
    assert remote["status"] == "FAILED"
    assert parquet["status"] == "FAILED"
