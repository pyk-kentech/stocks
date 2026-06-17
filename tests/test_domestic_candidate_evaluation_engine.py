from stock_risk_mcp.domestic_candidate_evaluation_engine import (
    build_candidate_evaluation_gap_report,
    build_candidate_evaluation_report,
    build_candidate_evaluation_safety_report,
)
from stock_risk_mcp.domestic_candidate_evaluation_fixture import load_domestic_candidate_evaluation_fixture
from stock_risk_mcp.domestic_candidate_evaluation_models import (
    CandidateEvaluationCompatibility,
    CandidateEvaluationState,
)
from tests.test_domestic_candidate_evaluation_fixture import (
    domestic_candidate_evaluation_fixture_payload,
    profitability_context_payload,
    technical_evidence_payload,
)
from tests.test_domestic_realtime_fixture import event_payload, write


def _load(tmp_path, payload):
    return load_domestic_candidate_evaluation_fixture(
        write(tmp_path, "domestic_candidate_evaluation_fixture.json", payload)
    )


def test_domestic_candidate_evaluation_builds_scanner_ready_report(tmp_path):
    fixture = _load(tmp_path, domestic_candidate_evaluation_fixture_payload())
    report = build_candidate_evaluation_report(fixture)
    assert report.decisions[0].scanner_state.value in {"SCANNER_READY", "WATCHLIST_ADD"}
    assert report.decisions[0].evaluation_state == CandidateEvaluationState.EVALUATION_READY


def test_domestic_candidate_evaluation_builds_watch_only_report(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload(
        profitability_context=profitability_context_payload(
            status="ACTIONABLE",
            expected_net_profit=5000.0,
            expected_net_return_pct=0.01,
        ),
        technical_evidence=technical_evidence_payload(setup_grade="B"),
    )
    report = build_candidate_evaluation_report(_load(tmp_path, payload))
    assert report.decisions[0].evaluation_state == CandidateEvaluationState.WATCH_ONLY


def test_domestic_candidate_evaluation_builds_report_only_stale_report(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload()
    payload["domestic_scanner_fixture"]["scanner_config"]["report_only_mode"] = True
    payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["report_only_mode"] = True
    payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["staleness_policy"]["allow_report_only_downgrade"] = True
    payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"] = [
        event_payload(
            provider_timestamp="2026-06-17T08:58:00+09:00",
            received_timestamp="2026-06-17T09:00:10+09:00",
        )
    ]
    report = build_candidate_evaluation_report(_load(tmp_path, payload))
    assert report.decisions[0].evaluation_state == CandidateEvaluationState.REPORT_ONLY


def test_domestic_candidate_evaluation_blocks_scanner_quality(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload()
    payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"] = [
        event_payload(
            provider_timestamp="2026-06-17T08:58:00+09:00",
            received_timestamp="2026-06-17T09:00:10+09:00",
        )
    ]
    report = build_candidate_evaluation_report(_load(tmp_path, payload))
    assert report.decisions[0].evaluation_state == CandidateEvaluationState.BLOCKED_SCANNER_QUALITY


def test_domestic_candidate_evaluation_blocks_profitability(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload(
        profitability_context=profitability_context_payload(
            status="NON_ACTIONABLE",
            expected_net_profit=-1000.0,
            expected_net_return_pct=-0.01,
        )
    )
    report = build_candidate_evaluation_report(_load(tmp_path, payload))
    assert report.decisions[0].evaluation_state == CandidateEvaluationState.BLOCKED_PROFITABILITY


def test_domestic_candidate_evaluation_blocks_technical_evidence(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload(
        technical_evidence=technical_evidence_payload(
            setup_grade="C",
            evidence_freshness="STALE_FIXTURE",
            missing_flags=["MACD", "RSI"],
        )
    )
    report = build_candidate_evaluation_report(_load(tmp_path, payload))
    assert report.decisions[0].evaluation_state == CandidateEvaluationState.BLOCKED_TECHNICAL_EVIDENCE


def test_domestic_candidate_evaluation_blocks_risk(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload()
    payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"] = [
        event_payload(
            extra={
                "best_bid": 69990.0,
                "best_ask": 72000.0,
                "bid_size": 10.0,
                "ask_size": 10.0,
                "volume": 10.0,
                "baseline_volume": 1000.0,
            }
        )
    ]
    report = build_candidate_evaluation_report(_load(tmp_path, payload))
    assert report.decisions[0].evaluation_state == CandidateEvaluationState.BLOCKED_RISK


def test_domestic_candidate_evaluation_rejects_unsafe_order_trigger_attempt(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload()
    payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"] = [
        event_payload(extra={"data_quality_flags": ["ORDER_TRIGGER_ATTEMPT"]})
    ]
    report = build_candidate_evaluation_report(_load(tmp_path, payload))
    assert report.decisions[0].evaluation_state == CandidateEvaluationState.REJECTED_UNSAFE_TRIGGER


def test_domestic_candidate_evaluation_preserves_scanner_fields(tmp_path):
    report = build_candidate_evaluation_report(_load(tmp_path, domestic_candidate_evaluation_fixture_payload()))
    assert report.decisions[0].scanner_state.value
    assert report.decisions[0].scanner_compatibility_status.value


def test_domestic_candidate_evaluation_maps_evaluation_compatibility(tmp_path):
    report = build_candidate_evaluation_report(_load(tmp_path, domestic_candidate_evaluation_fixture_payload()))
    assert report.decisions[0].evaluation_compatibility_status in {
        CandidateEvaluationCompatibility.DISCOVER,
        CandidateEvaluationCompatibility.WATCH,
        CandidateEvaluationCompatibility.EXCLUDE,
    }


def test_domestic_candidate_evaluation_gap_report_detects_missing_evidence(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload(
        technical_evidence=technical_evidence_payload(missing_flags=["MACD"])
    )
    gap = build_candidate_evaluation_gap_report(_load(tmp_path, payload))
    assert gap.missing_technical_evidence_count == 1


def test_domestic_candidate_evaluation_safety_report_is_non_actionable(tmp_path):
    report = build_candidate_evaluation_safety_report(
        _load(tmp_path, domestic_candidate_evaluation_fixture_payload())
    )
    assert report.safety_boundary.advisory_only is True
