import json
from datetime import date

from stock_risk_mcp.cli import main
from stock_risk_mcp.candidate_universe import CandidateDecision, CandidateScanResult
from stock_risk_mcp.data_import import import_signal_file
from stock_risk_mcp.dilution_provider_pack import run_dilution_provider_pack
from stock_risk_mcp.import_run import ImportSourceType
from stock_risk_mcp.provider_pack_config import ProviderPackConfig
from stock_risk_mcp.provider_packs import ProviderPackRunStatus
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.signal_enrichment import SignalEnricher
from stock_risk_mcp.signals import SignalDirection, SignalSeverity, SignalType


def test_local_dilution_provider_pack_maps_risk_and_preserves_raw_payload(tmp_path) -> None:
    raw = _raw_file(tmp_path)
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    config = ProviderPackConfig.model_validate({"dilution": {"providers": [_provider(raw)]}})

    run = run_dilution_provider_pack(repository, config, tmp_path / "out", date(2026, 6, 13))
    signals = {
        signal.ticker: signal
        for signal in repository.list_ticker_signals(as_of_date=date(2026, 6, 13))
    }

    assert run.status == ProviderPackRunStatus.COMPLETED
    assert (signals["HIGH"].severity, signals["HIGH"].score_delta) == (SignalSeverity.HIGH, -7)
    assert (signals["CRIT"].severity, signals["CRIT"].score_delta) == (SignalSeverity.CRITICAL, -10)
    assert (signals["UNKN"].severity, signals["UNKN"].score_delta) == (SignalSeverity.HIGH, -7)
    assert signals["UNKN"].metadata["raw_payload_json"]["Risk"] == "UNKNOWN"
    assert signals["NONE"].direction == SignalDirection.NEUTRAL
    assert signals["NONE"].score_delta == 0
    assert repository.count_rows("company_risks") == 0


def test_imported_dilution_keeps_existing_high_and_critical_enrichment_rules(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    run_dilution_provider_pack(
        repository,
        ProviderPackConfig.model_validate({"dilution": {"providers": [_provider(_raw_file(tmp_path))]}}),
        tmp_path / "out",
        date(2026, 6, 13),
    )
    candidates = [
        CandidateScanResult(
            scan_run_id="run", ticker=ticker, as_of_date=date(2026, 6, 13),
            decision=CandidateDecision.INCLUDE, score=80,
        )
        for ticker in ("HIGH", "CRIT")
    ]

    result = SignalEnricher().enrich_scan_results(
        candidates, date(2026, 6, 13),
        repository.list_ticker_signals(as_of_date=date(2026, 6, 13)),
    )

    assert result[0].decision == CandidateDecision.WATCH
    assert result[1].decision == CandidateDecision.EXCLUDE


def test_legacy_dilution_import_still_uses_common_signal_scoring(tmp_path) -> None:
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps([{
        "ticker": "AAA", "observed_at": "2026-06-12", "event_type": "OFFERING",
        "severity": "HIGH", "details": "Filed",
    }]), encoding="utf-8")
    repository = RiskRepository(tmp_path / "risk.sqlite3")

    import_signal_file(repository, path, ImportSourceType.DILUTION_SIGNAL, date(2026, 6, 13))
    signal = repository.list_ticker_signals("AAA", date(2026, 6, 13))[0]

    assert signal.signal_type == SignalType.DILUTION
    assert signal.score_delta == -15
    assert signal.source_name == "dilution_signal_file"


def test_dilution_http_provider_is_disabled_without_network(tmp_path) -> None:
    provider = _provider("unused.csv")
    provider.update(local_file=None, url="https://example.com/dilution.csv", allowed_hosts=["example.com"])
    config = ProviderPackConfig.model_validate({"dilution": {"providers": [provider]}})

    run = run_dilution_provider_pack(
        RiskRepository(tmp_path / "risk.sqlite3"), config, tmp_path / "out", date(2026, 6, 13)
    )

    assert run.status == ProviderPackRunStatus.DISABLED


def test_dilution_provider_pack_records_missing_normalizer_failure(tmp_path) -> None:
    provider = _provider(_raw_file(tmp_path))
    provider["normalizer"] = None

    run = run_dilution_provider_pack(
        RiskRepository(tmp_path / "risk.sqlite3"),
        ProviderPackConfig.model_validate({"dilution": {"providers": [provider]}}),
        tmp_path / "out", date(2026, 6, 13),
    )

    assert run.status == ProviderPackRunStatus.FAILED
    assert any("normalizer" in error.lower() for error in run.errors)


def test_fake_http_dilution_provider_flows_to_dilution_signal(tmp_path) -> None:
    provider = _provider("unused.csv")
    provider.update(local_file=None, url="https://example.com/dilution.csv", allowed_hosts=["example.com"])
    repository = RiskRepository(tmp_path / "risk.sqlite3")

    run = run_dilution_provider_pack(
        repository, ProviderPackConfig.model_validate({"dilution": {"providers": [provider]}}),
        tmp_path / "out", date(2026, 6, 13), enable_network=True, client=FakeDilutionClient(),
    )

    assert run.status == ProviderPackRunStatus.COMPLETED
    assert repository.list_ticker_signals("HIGH", date(2026, 6, 13))[0].score_delta == -7


def test_run_dilution_provider_pack_cli(tmp_path, capsys) -> None:
    config_file = tmp_path / "pack.json"
    config_file.write_text(json.dumps({
        "dilution": {"providers": [_provider(_raw_file(tmp_path))]}
    }), encoding="utf-8")

    main([
        "run-dilution-provider-pack", "--db", str(tmp_path / "risk.sqlite3"),
        "--as-of-date", "2026-06-13", "--provider-pack-config", str(config_file),
        "--output-dir", str(tmp_path / "out"),
    ])
    result = json.loads(capsys.readouterr().out)
    main(["provider-pack-runs", "--db", str(tmp_path / "risk.sqlite3")])
    listed = json.loads(capsys.readouterr().out)
    main([
        "provider-pack-show", "--db", str(tmp_path / "risk.sqlite3"),
        "--provider-pack-run-id", result["provider_pack_run_id"],
    ])
    shown = json.loads(capsys.readouterr().out)

    assert result["provider_pack_type"] == "DILUTION"
    assert result["status"] == "COMPLETED"
    assert listed["provider_pack_runs"][0]["provider_pack_type"] == "DILUTION"
    assert shown["provider_pack_run_id"] == result["provider_pack_run_id"]


def _raw_file(tmp_path):
    path = tmp_path / "dilution.csv"
    path.write_text(
        "Symbol,ObservedAt,Event,Risk,Source,Details\n"
        "HIGH,2026-06-12,OFFERING,HIGH,filings,Potential offering\n"
        "CRIT,2026-06-12,SHELF,CRITICAL,filings,Shelf active\n"
        "UNKN,2026-06-12,UNKNOWN,UNKNOWN,filings,Needs review\n"
        "NONE,2026-06-12,NONE,NONE,filings,No known risk\n",
        encoding="utf-8",
    )
    return path


def _provider(path):
    return {
        "provider_name": "dilution", "local_file": str(path), "data_kind": "DILUTION",
        "output_format": "CSV", "allowed_hosts": [], "enabled": True,
        "normalizer": "generic-dilution-csv",
        "columns": {
            "ticker": "Symbol", "observed_at": "ObservedAt", "event_type": "Event",
            "dilution_risk": "Risk", "source_name": "Source", "details": "Details",
        },
    }


class FakeDilutionClient:
    def get(self, *args, **kwargs):
        return {
            "status_code": 200,
            "headers": {"Content-Type": "text/csv"},
            "body": (
                b"Symbol,ObservedAt,Event,Risk,Source,Details\n"
                b"HIGH,2026-06-12,OFFERING,HIGH,filings,Potential offering\n"
            ),
        }
