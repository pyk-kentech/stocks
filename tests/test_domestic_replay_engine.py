from stock_risk_mcp.domestic_replay_engine import (
    build_domestic_replay_metrics,
    build_domestic_replay_promotion_readiness_report,
    build_domestic_replay_report,
)
from stock_risk_mcp.domestic_replay_fixture import load_domestic_replay_fixture
from stock_risk_mcp.domestic_replay_models import ReplayPromotionReadinessStatus
from tests.test_domestic_candidate_evaluation_fixture import (
    domestic_candidate_evaluation_fixture_payload,
    profitability_context_payload,
    technical_evidence_payload,
)
from tests.test_domestic_realtime_fixture import event_payload, write
from tests.test_domestic_replay_fixture import domestic_replay_fixture_payload


def _load(tmp_path, payload):
    return load_domestic_replay_fixture(write(tmp_path, "domestic_replay_fixture.json", payload))


def test_domestic_replay_builds_ordered_event_level_trace(tmp_path):
    candidate = domestic_candidate_evaluation_fixture_payload()
    candidate["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"] = [
        event_payload(
            provider_timestamp="2026-06-17T09:00:05+09:00",
            received_timestamp="2026-06-17T09:00:06+09:00",
            extra={"source_fixture_id": "fixture-event-2"},
        ),
        event_payload(
            provider_timestamp="2026-06-17T09:00:01+09:00",
            received_timestamp="2026-06-17T09:00:03+09:00",
            extra={"source_fixture_id": "fixture-event-1"},
        ),
    ]
    fixture = _load(tmp_path, domestic_replay_fixture_payload(candidate_fixture=candidate))
    report = build_domestic_replay_report(fixture)
    assert [step.source_event_id for step in report.step_results] == ["FIXTURE-EVENT-1", "FIXTURE-EVENT-2"]
    assert report.metrics.total_events_processed == 2


def test_domestic_replay_marks_stale_event_fail_closed_by_default(tmp_path):
    candidate = domestic_candidate_evaluation_fixture_payload()
    candidate["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"] = [
        event_payload(
            provider_timestamp="2026-06-17T08:58:00+09:00",
            received_timestamp="2026-06-17T09:00:10+09:00",
        )
    ]
    fixture = _load(tmp_path, domestic_replay_fixture_payload(candidate_fixture=candidate))
    report = build_domestic_replay_report(fixture)
    assert report.step_results[0].scanner_candidate_trace.scanner_state.value == "BLOCKED_QUALITY"
    assert report.metrics.quality_failure_count == 1


def test_domestic_replay_allows_explicit_report_only_stale_mode(tmp_path):
    candidate = domestic_candidate_evaluation_fixture_payload()
    candidate["domestic_scanner_fixture"]["scanner_config"]["report_only_mode"] = True
    candidate["domestic_scanner_fixture"]["domestic_realtime_fixture"]["report_only_mode"] = True
    candidate["domestic_scanner_fixture"]["domestic_realtime_fixture"]["staleness_policy"]["allow_report_only_downgrade"] = True
    candidate["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"] = [
        event_payload(
            provider_timestamp="2026-06-17T08:58:00+09:00",
            received_timestamp="2026-06-17T09:00:10+09:00",
        )
    ]
    fixture = _load(
        tmp_path,
        domestic_replay_fixture_payload(
            replay_config={
                **domestic_replay_fixture_payload()["replay_config"],
                **{"report_only_mode": True, "stale_event_policy": "REPORT_ONLY", "report_only_event_policy": "ALLOW_EXPLICIT_REPORT_ONLY"},
            },
            candidate_fixture=candidate,
        ),
    )
    report = build_domestic_replay_report(fixture)
    assert report.step_results[0].scanner_candidate_trace.evaluation_state.value == "REPORT_ONLY"
    assert report.metrics.report_only_candidate_count == 1


def test_domestic_replay_preserves_scanner_and_evaluation_states(tmp_path):
    fixture = _load(tmp_path, domestic_replay_fixture_payload())
    report = build_domestic_replay_report(fixture)
    trace = report.step_results[0].scanner_candidate_trace
    assert trace.scanner_state.value in {"SCANNER_READY", "WATCHLIST_ADD", "WATCHLIST_REMOVE", "INSUFFICIENT_DATA"}
    assert trace.evaluation_state.value in {"EVALUATION_READY", "WATCH_ONLY", "REPORT_ONLY", "BLOCKED_RISK"}


def test_domestic_replay_blocks_profitability_and_technical_evidence(tmp_path):
    candidate = domestic_candidate_evaluation_fixture_payload(
        profitability_context=profitability_context_payload(status="REPORT_ONLY", expected_net_profit=-10.0, expected_net_return_pct=-0.01),
        technical_evidence=technical_evidence_payload(setup_grade="D", missing_flags=["RSI"]),
    )
    fixture = _load(tmp_path, domestic_replay_fixture_payload(candidate_fixture=candidate))
    report = build_domestic_replay_report(fixture)
    assert report.metrics.profitability_blocked_count == 1
    assert report.metrics.technical_evidence_blocked_count == 0


def test_domestic_replay_rejects_unsafe_trigger(tmp_path):
    candidate = domestic_candidate_evaluation_fixture_payload()
    candidate["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"] = [
        event_payload(extra={"data_quality_flags": ["ORDER_TRIGGER_ATTEMPT"]})
    ]
    fixture = _load(tmp_path, domestic_replay_fixture_payload(candidate_fixture=candidate))
    report = build_domestic_replay_report(fixture)
    assert report.metrics.unsafe_trigger_rejection_count == 1


def test_domestic_replay_window_summary_is_derived_from_steps(tmp_path):
    candidate = domestic_candidate_evaluation_fixture_payload()
    candidate["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"] = [
        event_payload(extra={"source_fixture_id": "fixture-event-1"}),
        event_payload(
            provider_timestamp="2026-06-17T09:00:05+09:00",
            received_timestamp="2026-06-17T09:00:06+09:00",
            extra={"source_fixture_id": "fixture-event-2"},
        ),
    ]
    fixture = _load(tmp_path, domestic_replay_fixture_payload(candidate_fixture=candidate))
    report = build_domestic_replay_report(fixture)
    assert report.windows[0].aggregated_summary_metrics["events_processed"] == len(report.windows[0].included_event_ids)


def test_domestic_replay_builds_promotion_readiness_report(tmp_path):
    fixture = _load(tmp_path, domestic_replay_fixture_payload())
    report = build_domestic_replay_promotion_readiness_report(fixture)
    assert report.readiness_status in set(ReplayPromotionReadinessStatus)
    assert report.safety_boundary.advisory_only is True
