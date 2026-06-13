import json
from datetime import date

from stock_risk_mcp.candidate_universe import CandidateDecision, CandidateScanResult
from stock_risk_mcp.cli import main
from stock_risk_mcp.data_import import import_signal_file
from stock_risk_mcp.flow_provider_pack import run_flow_provider_pack
from stock_risk_mcp.import_run import ImportSourceType
from stock_risk_mcp.provider_pack_config import ProviderPackConfig
from stock_risk_mcp.provider_packs import ProviderPackRunStatus
from stock_risk_mcp.repository import RiskRepository
from stock_risk_mcp.signal_enrichment import SignalEnricher
from stock_risk_mcp.signals import SignalDirection, SignalSeverity, SignalType


def test_local_flow_provider_pack_maps_signs_and_preserves_raw_payload(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    config = ProviderPackConfig.model_validate({"flow": {"providers": [_provider(_raw_file(tmp_path))]}})

    run = run_flow_provider_pack(repository, config, tmp_path / "out", date(2026, 6, 13))
    signals = {
        signal.ticker: signal
        for signal in repository.list_ticker_signals(as_of_date=date(2026, 6, 13))
    }

    assert run.status == ProviderPackRunStatus.COMPLETED
    assert _result(signals["BOTHBUY"]) == (SignalDirection.POSITIVE, SignalSeverity.LOW, 2)
    assert _result(signals["ONEBUY"]) == (SignalDirection.POSITIVE, SignalSeverity.LOW, 1)
    assert _result(signals["BOTHSELL"]) == (SignalDirection.NEGATIVE, SignalSeverity.MEDIUM, -3)
    assert _result(signals["ONESELL"]) == (SignalDirection.NEGATIVE, SignalSeverity.LOW, -1)
    assert _result(signals["MIXED"]) == (SignalDirection.NEUTRAL, SignalSeverity.LOW, 0)
    assert _result(signals["ZERO"]) == (SignalDirection.NEUTRAL, SignalSeverity.LOW, 0)
    assert signals["BOTHBUY"].metadata["provider_record_mode"] == "RICH_FLOW_PROVIDER"
    assert signals["BOTHBUY"].metadata["raw_payload_json"]["ForeignAmount"] == "10"
    assert all(signal.severity not in {SignalSeverity.HIGH, SignalSeverity.CRITICAL} for signal in signals.values())


def test_amount_mapping_takes_precedence_without_row_fallback(tmp_path) -> None:
    raw = tmp_path / "flow.csv"
    raw.write_text(
        "Symbol,ObservedAt,Source,ForeignAmount,InstitutionAmount,ForeignShares,InstitutionShares\n"
        "AAA,2026-06-12,exchange,,,100,100\n",
        encoding="utf-8",
    )
    repository = RiskRepository(tmp_path / "risk.sqlite3")

    run_flow_provider_pack(
        repository, ProviderPackConfig.model_validate({"flow": {"providers": [_provider(raw)]}}),
        tmp_path / "out", date(2026, 6, 13),
    )
    signal = repository.list_ticker_signals("AAA", date(2026, 6, 13))[0]

    assert _result(signal) == (SignalDirection.NEUTRAL, SignalSeverity.LOW, 0)
    assert signal.metadata["flow_value_basis"] == "AMOUNT"


def test_shares_are_used_when_amount_mappings_are_absent(tmp_path) -> None:
    raw = tmp_path / "flow.csv"
    raw.write_text(
        "Symbol,ObservedAt,Source,ForeignShares,InstitutionShares\n"
        "AAA,2026-06-12,exchange,100,0\n",
        encoding="utf-8",
    )
    provider = _provider(raw)
    del provider["columns"]["foreign_net_buy_amount"]
    del provider["columns"]["institution_net_buy_amount"]
    repository = RiskRepository(tmp_path / "risk.sqlite3")

    run_flow_provider_pack(
        repository, ProviderPackConfig.model_validate({"flow": {"providers": [provider]}}),
        tmp_path / "out", date(2026, 6, 13),
    )
    signal = repository.list_ticker_signals("AAA", date(2026, 6, 13))[0]

    assert _result(signal) == (SignalDirection.POSITIVE, SignalSeverity.LOW, 1)
    assert signal.metadata["flow_value_basis"] == "SHARES"


def test_score_delta_alone_does_not_identify_rich_flow_record(tmp_path) -> None:
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps([{
        "ticker": "AAA", "observed_at": "2026-06-12",
        "foreign_net_buy": 10, "institution_net_buy": 10, "score_delta": 99,
    }]), encoding="utf-8")
    repository = RiskRepository(tmp_path / "risk.sqlite3")

    import_signal_file(repository, path, ImportSourceType.FLOW_SIGNAL, date(2026, 6, 13))
    signal = repository.list_ticker_signals("AAA", date(2026, 6, 13))[0]

    assert signal.score_delta == 5
    assert signal.source_name == "flow_signal_file"


def test_positive_flow_does_not_promote_excluded_candidate(tmp_path) -> None:
    repository = RiskRepository(tmp_path / "risk.sqlite3")
    run_flow_provider_pack(
        repository, ProviderPackConfig.model_validate({"flow": {"providers": [_provider(_raw_file(tmp_path))]}}),
        tmp_path / "out", date(2026, 6, 13),
    )
    candidate = CandidateScanResult(
        scan_run_id="run", ticker="BOTHBUY", as_of_date=date(2026, 6, 13),
        decision=CandidateDecision.EXCLUDE, score=30,
    )

    result = SignalEnricher().enrich_scan_results(
        [candidate], date(2026, 6, 13),
        repository.list_ticker_signals("BOTHBUY", date(2026, 6, 13)),
    )[0]

    assert result.decision == CandidateDecision.EXCLUDE
    assert result.score == 32


def test_flow_http_provider_is_disabled_without_network(tmp_path) -> None:
    provider = _provider("unused.csv")
    provider.update(local_file=None, url="https://example.com/flow.csv", allowed_hosts=["example.com"])

    run = run_flow_provider_pack(
        RiskRepository(tmp_path / "risk.sqlite3"),
        ProviderPackConfig.model_validate({"flow": {"providers": [provider]}}),
        tmp_path / "out", date(2026, 6, 13),
    )

    assert run.status == ProviderPackRunStatus.DISABLED


def test_flow_provider_pack_records_missing_normalizer_failure(tmp_path) -> None:
    provider = _provider(_raw_file(tmp_path))
    provider["normalizer"] = None

    run = run_flow_provider_pack(
        RiskRepository(tmp_path / "risk.sqlite3"),
        ProviderPackConfig.model_validate({"flow": {"providers": [provider]}}),
        tmp_path / "out", date(2026, 6, 13),
    )

    assert run.status == ProviderPackRunStatus.FAILED
    assert any("normalizer" in error.lower() for error in run.errors)


def test_fake_http_flow_provider_flows_to_signal(tmp_path) -> None:
    provider = _provider("unused.csv")
    provider.update(local_file=None, url="https://example.com/flow.csv", allowed_hosts=["example.com"])
    repository = RiskRepository(tmp_path / "risk.sqlite3")

    run = run_flow_provider_pack(
        repository, ProviderPackConfig.model_validate({"flow": {"providers": [provider]}}),
        tmp_path / "out", date(2026, 6, 13), enable_network=True, client=FakeFlowClient(),
    )

    assert run.status == ProviderPackRunStatus.COMPLETED
    assert repository.list_ticker_signals("BOTHBUY", date(2026, 6, 13))[0].signal_type == SignalType.FOREIGN_INSTITUTION_FLOW


def test_run_flow_provider_pack_cli(tmp_path, capsys) -> None:
    config_file = tmp_path / "pack.json"
    config_file.write_text(json.dumps({
        "flow": {"providers": [_provider(_raw_file(tmp_path))]}
    }), encoding="utf-8")

    main([
        "run-flow-provider-pack", "--db", str(tmp_path / "risk.sqlite3"),
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

    assert result["provider_pack_type"] == "FLOW"
    assert result["status"] == "COMPLETED"
    assert listed["provider_pack_runs"][0]["provider_pack_type"] == "FLOW"
    assert shown["provider_pack_run_id"] == result["provider_pack_run_id"]


def _result(signal):
    return signal.direction, signal.severity, signal.score_delta


def _raw_file(tmp_path):
    path = tmp_path / "flow.csv"
    path.write_text(
        "Symbol,ObservedAt,Source,ForeignAmount,InstitutionAmount,ForeignShares,InstitutionShares\n"
        "BOTHBUY,2026-06-12,exchange,10,20,-100,-100\n"
        "ONEBUY,2026-06-12,exchange,10,0,0,0\n"
        "BOTHSELL,2026-06-12,exchange,-10,-20,0,0\n"
        "ONESELL,2026-06-12,exchange,-10,,0,0\n"
        "MIXED,2026-06-12,exchange,10,-20,0,0\n"
        "ZERO,2026-06-12,exchange,,,0,0\n",
        encoding="utf-8",
    )
    return path


def _provider(path):
    return {
        "provider_name": "flow", "local_file": str(path),
        "data_kind": "FOREIGN_INSTITUTION_FLOW", "output_format": "CSV",
        "allowed_hosts": [], "enabled": True, "normalizer": "generic-flow-csv",
        "columns": {
            "ticker": "Symbol", "observed_at": "ObservedAt", "source_name": "Source",
            "foreign_net_buy_amount": "ForeignAmount",
            "institution_net_buy_amount": "InstitutionAmount",
            "foreign_net_buy_shares": "ForeignShares",
            "institution_net_buy_shares": "InstitutionShares",
        },
    }


class FakeFlowClient:
    def get(self, *args, **kwargs):
        return {
            "status_code": 200,
            "headers": {"Content-Type": "text/csv"},
            "body": (
                b"Symbol,ObservedAt,Source,ForeignAmount,InstitutionAmount,ForeignShares,InstitutionShares\n"
                b"BOTHBUY,2026-06-12,exchange,10,20,0,0\n"
            ),
        }
