from stock_risk_mcp.domestic_calibration_engine import (
    build_calibration_run_result,
    build_policy_comparison_report,
    build_promotion_gate_report,
)
from stock_risk_mcp.domestic_calibration_fixture import load_domestic_calibration_fixture
from stock_risk_mcp.domestic_calibration_models import PromotionGateStatus
from stock_risk_mcp.domestic_replay_engine import build_domestic_replay_report
from stock_risk_mcp.domestic_replay_fixture import load_domestic_replay_fixture
from tests.test_domestic_calibration_fixture import (
    calibration_fixture_payload,
    calibration_run_config_payload,
)
from tests.test_domestic_realtime_fixture import event_payload, write
from tests.test_domestic_replay_fixture import domestic_replay_fixture_payload


def _load(tmp_path, payload):
    return load_domestic_calibration_fixture(write(tmp_path, "domestic_calibration_fixture.json", payload))


def _replay_report(tmp_path, replay_payload):
    replay_fixture = load_domestic_replay_fixture(
        write(tmp_path, "domestic_replay_fixture.json", replay_payload)
    )
    return build_domestic_replay_report(replay_fixture).model_dump(mode="json")


def test_domestic_calibration_builds_valid_single_run_comparisons(tmp_path):
    fixture = _load(tmp_path, calibration_fixture_payload(tmp_path))
    result = build_calibration_run_result(fixture)
    assert len(result.single_run_results) == 2
    assert all(item.promotion_eligible is False for item in result.single_run_results)


def test_domestic_calibration_pack_preserves_underlying_report_references(tmp_path):
    fixture = _load(tmp_path, calibration_fixture_payload(tmp_path))
    result = build_calibration_run_result(fixture)
    assert result.calibration_pack.included_replay_report_ids
    assert result.calibration_pack.included_single_run_comparison_ids


def test_domestic_calibration_generates_policy_comparison_report(tmp_path):
    fixture = _load(tmp_path, calibration_fixture_payload(tmp_path))
    report = build_policy_comparison_report(fixture)
    assert report.candidate_policy_ids == ["STRICTER_POLICY", "LOOSER_POLICY"]
    assert report.pack_level_summaries["run_count"] == 2


def test_domestic_calibration_stricter_and_looser_candidates_have_different_deltas(tmp_path):
    fixture = _load(tmp_path, calibration_fixture_payload(tmp_path))
    report = build_policy_comparison_report(fixture)
    deltas = {item["candidate_policy_id"]: item["coverage_score"] for item in report.single_run_summaries}
    assert deltas["STRICTER_POLICY"] != deltas["LOOSER_POLICY"]


def test_domestic_calibration_report_only_policy_behavior_is_preserved(tmp_path):
    replay_payload = domestic_replay_fixture_payload()
    replay_payload["domestic_candidate_evaluation_fixture"]["domestic_scanner_fixture"]["scanner_config"]["report_only_mode"] = True
    replay_payload["domestic_candidate_evaluation_fixture"]["domestic_scanner_fixture"]["domestic_realtime_fixture"]["report_only_mode"] = True
    replay_payload["domestic_candidate_evaluation_fixture"]["domestic_scanner_fixture"]["domestic_realtime_fixture"]["staleness_policy"]["allow_report_only_downgrade"] = True
    replay_payload["domestic_candidate_evaluation_fixture"]["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"] = [
        event_payload(provider_timestamp="2026-06-17T08:58:00+09:00", received_timestamp="2026-06-17T09:00:10+09:00")
    ]
    fixture = _load(
        tmp_path,
        calibration_fixture_payload(
            tmp_path,
            replay_reports=[_replay_report(tmp_path, replay_payload), _replay_report(tmp_path, replay_payload)],
        ),
    )
    result = build_calibration_run_result(fixture)
    assert result.calibration_pack.pack_metrics.report_only_count >= 2


def test_domestic_calibration_fails_closed_on_safety_regression(tmp_path):
    replay_payload = domestic_replay_fixture_payload()
    replay_payload["domestic_candidate_evaluation_fixture"]["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"] = [
        event_payload(extra={"data_quality_flags": ["ORDER_TRIGGER_ATTEMPT"]})
    ]
    fixture = _load(
        tmp_path,
        calibration_fixture_payload(
            tmp_path,
            replay_reports=[_replay_report(tmp_path, replay_payload), _replay_report(tmp_path, replay_payload)],
        ),
    )
    gate = build_promotion_gate_report(fixture)
    assert gate.gate_status == PromotionGateStatus.PROMOTION_BLOCKED_SAFETY


def test_domestic_calibration_fails_closed_on_insufficient_coverage(tmp_path):
    payload = calibration_fixture_payload(tmp_path)
    payload["calibration_input_set"]["replay_reports"] = payload["calibration_input_set"]["replay_reports"][:1]
    fixture = _load(tmp_path, payload)
    gate = build_promotion_gate_report(fixture)
    assert gate.gate_status == PromotionGateStatus.PROMOTION_BLOCKED_COVERAGE


def test_domestic_calibration_fails_closed_when_required_scenario_missing(tmp_path):
    payload = calibration_fixture_payload(
        tmp_path,
        run_config=calibration_run_config_payload(required_scenario_families=["BASELINE", "UNSAFE_TRIGGER"]),
    )
    fixture = _load(tmp_path, payload)
    gate = build_promotion_gate_report(fixture)
    assert gate.gate_status == PromotionGateStatus.PROMOTION_BLOCKED_COVERAGE


def test_domestic_calibration_single_run_only_promotion_gate_fails_closed(tmp_path):
    payload = calibration_fixture_payload(tmp_path)
    payload["calibration_input_set"]["replay_reports"] = payload["calibration_input_set"]["replay_reports"][:1]
    fixture = _load(tmp_path, payload)
    gate = build_promotion_gate_report(fixture)
    assert "SINGLE_RUN_ONLY_EVIDENCE" in gate.block_reasons


def test_domestic_calibration_promotion_gate_status_mapping(tmp_path):
    fixture = _load(tmp_path, calibration_fixture_payload(tmp_path))
    gate = build_promotion_gate_report(fixture)
    assert gate.gate_status in set(PromotionGateStatus)
