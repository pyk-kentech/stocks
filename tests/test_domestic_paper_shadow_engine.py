from stock_risk_mcp.domestic_calibration_engine import build_promotion_gate_report
from stock_risk_mcp.domestic_calibration_fixture import load_domestic_calibration_fixture
from stock_risk_mcp.domestic_calibration_models import PromotionGateStatus
from stock_risk_mcp.domestic_candidate_evaluation_engine import build_candidate_evaluation_report
from stock_risk_mcp.domestic_candidate_evaluation_fixture import load_domestic_candidate_evaluation_fixture
from stock_risk_mcp.domestic_paper_shadow_engine import (
    build_paper_shadow_gap_report,
    build_paper_shadow_journal,
    build_paper_shadow_review_report,
    build_paper_shadow_safety_report,
)
from stock_risk_mcp.domestic_paper_shadow_fixture import load_domestic_paper_shadow_fixture
from tests.test_domestic_calibration_fixture import calibration_fixture_payload
from tests.test_domestic_candidate_evaluation_fixture import (
    domestic_candidate_evaluation_fixture_payload,
    profitability_context_payload,
    technical_evidence_payload,
)
from tests.test_domestic_paper_shadow_fixture import paper_shadow_fixture_payload
from tests.test_domestic_realtime_fixture import event_payload, write


def _gate_payload(tmp_path, calibration_payload=None):
    fixture = load_domestic_calibration_fixture(
        write(tmp_path, "domestic_calibration_fixture.json", calibration_payload or calibration_fixture_payload(tmp_path))
    )
    return build_promotion_gate_report(fixture).model_dump(mode="json")


def _eval_payload(tmp_path, evaluation_payload=None):
    fixture = load_domestic_candidate_evaluation_fixture(
        write(tmp_path, "domestic_candidate_evaluation_fixture.json", evaluation_payload or domestic_candidate_evaluation_fixture_payload())
    )
    return build_candidate_evaluation_report(fixture).model_dump(mode="json")


def _load(tmp_path, payload):
    return load_domestic_paper_shadow_fixture(
        write(tmp_path, "domestic_paper_shadow_fixture.json", payload)
    )


def test_domestic_paper_shadow_generates_candidate_level_entries(tmp_path):
    fixture = _load(tmp_path, paper_shadow_fixture_payload(tmp_path))
    journal = build_paper_shadow_journal(fixture)
    assert len(journal.entries) == journal.entry_count == 1
    assert journal.entries[0].candidate_id


def test_domestic_paper_shadow_builds_one_entry_per_candidate_evaluation_result(tmp_path):
    payload = paper_shadow_fixture_payload(
        tmp_path,
        candidate_evaluation_reports=[_eval_payload(tmp_path), _eval_payload(tmp_path)],
    )
    fixture = _load(tmp_path, payload)
    journal = build_paper_shadow_journal(fixture)
    assert journal.entry_count == 2


def test_domestic_paper_shadow_review_summary_is_derived_from_entries(tmp_path):
    payload = paper_shadow_fixture_payload(
        tmp_path,
        candidate_evaluation_reports=[_eval_payload(tmp_path), _eval_payload(tmp_path)],
    )
    fixture = _load(tmp_path, payload)
    journal = build_paper_shadow_journal(fixture)
    review = build_paper_shadow_review_report(fixture)
    assert review.total_journal_entries == journal.entry_count
    assert sum(review.decision_type_counts.values()) == journal.entry_count


def test_domestic_paper_shadow_maps_shadow_watch_from_evaluation_ready(tmp_path):
    fixture = _load(tmp_path, paper_shadow_fixture_payload(tmp_path))
    journal = build_paper_shadow_journal(fixture)
    assert journal.entries[0].decision_type.value == "SHADOW_WATCH"


def test_domestic_paper_shadow_maps_report_only(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload()
    payload["domestic_scanner_fixture"]["scanner_config"]["report_only_mode"] = True
    payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["report_only_mode"] = True
    payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["staleness_policy"]["allow_report_only_downgrade"] = True
    payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"] = [
        event_payload(provider_timestamp="2026-06-17T08:58:00+09:00", received_timestamp="2026-06-17T09:00:10+09:00")
    ]
    fixture = _load(
        tmp_path,
        paper_shadow_fixture_payload(tmp_path, candidate_evaluation_reports=[_eval_payload(tmp_path, payload)]),
    )
    journal = build_paper_shadow_journal(fixture)
    assert journal.entries[0].decision_type.value == "SHADOW_REPORT_ONLY"


def test_domestic_paper_shadow_maps_blocked_profitability(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload(
        profitability_context=profitability_context_payload(status="REPORT_ONLY", expected_net_profit=-10.0, expected_net_return_pct=-0.01),
    )
    fixture = _load(
        tmp_path,
        paper_shadow_fixture_payload(tmp_path, candidate_evaluation_reports=[_eval_payload(tmp_path, payload)]),
    )
    journal = build_paper_shadow_journal(fixture)
    assert journal.entries[0].decision_type.value == "SHADOW_BLOCKED_PROFITABILITY"


def test_domestic_paper_shadow_maps_blocked_technical_evidence(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload(
        technical_evidence=technical_evidence_payload(setup_grade="D", missing_flags=["RSI"]),
    )
    fixture = _load(
        tmp_path,
        paper_shadow_fixture_payload(tmp_path, candidate_evaluation_reports=[_eval_payload(tmp_path, payload)]),
    )
    journal = build_paper_shadow_journal(fixture)
    assert journal.entries[0].decision_type.value == "SHADOW_BLOCKED_TECHNICAL_EVIDENCE"


def test_domestic_paper_shadow_maps_blocked_risk(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload()
    payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"] = [
        event_payload(extra={"best_bid": 69990.0, "best_ask": 72000.0, "bid_size": 10.0, "ask_size": 10.0, "volume": 10.0, "baseline_volume": 1000.0})
    ]
    fixture = _load(
        tmp_path,
        paper_shadow_fixture_payload(tmp_path, candidate_evaluation_reports=[_eval_payload(tmp_path, payload)]),
    )
    journal = build_paper_shadow_journal(fixture)
    assert journal.entries[0].decision_type.value == "SHADOW_BLOCKED_RISK"


def test_domestic_paper_shadow_maps_blocked_safety(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload()
    payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"] = [
        event_payload(extra={"data_quality_flags": ["ORDER_TRIGGER_ATTEMPT"]})
    ]
    fixture = _load(
        tmp_path,
        paper_shadow_fixture_payload(tmp_path, candidate_evaluation_reports=[_eval_payload(tmp_path, payload)]),
    )
    journal = build_paper_shadow_journal(fixture)
    assert journal.entries[0].decision_type.value == "SHADOW_BLOCKED_SAFETY"


def test_domestic_paper_shadow_maps_insufficient_context(tmp_path):
    payload = domestic_candidate_evaluation_fixture_payload()
    payload["domestic_scanner_fixture"]["domestic_realtime_fixture"]["events"] = [
        event_payload(extra={"price": None})
    ]
    fixture = _load(
        tmp_path,
        paper_shadow_fixture_payload(tmp_path, candidate_evaluation_reports=[_eval_payload(tmp_path, payload)]),
    )
    journal = build_paper_shadow_journal(fixture)
    assert journal.entries[0].decision_type.value == "SHADOW_INSUFFICIENT_CONTEXT"


def test_domestic_paper_shadow_blocked_promotion_gate_fails_closed(tmp_path):
    calibration_payload = calibration_fixture_payload(tmp_path)
    calibration_payload["calibration_input_set"]["replay_reports"] = calibration_payload["calibration_input_set"]["replay_reports"][:1]
    fixture = _load(
        tmp_path,
        paper_shadow_fixture_payload(tmp_path, promotion_gate_report=_gate_payload(tmp_path, calibration_payload)),
    )
    gap = build_paper_shadow_gap_report(fixture)
    assert gap.blocked_promotion_gate_count == 1


def test_domestic_paper_shadow_single_run_only_evidence_fails_closed(tmp_path):
    calibration_payload = calibration_fixture_payload(tmp_path)
    calibration_payload["calibration_input_set"]["replay_reports"] = calibration_payload["calibration_input_set"]["replay_reports"][:1]
    fixture = _load(
        tmp_path,
        paper_shadow_fixture_payload(tmp_path, promotion_gate_report=_gate_payload(tmp_path, calibration_payload)),
    )
    safety = build_paper_shadow_safety_report(fixture)
    assert "SINGLE_RUN_ONLY_EVIDENCE" in safety.block_reasons


def test_domestic_paper_shadow_uses_no_executable_labels(tmp_path):
    fixture = _load(tmp_path, paper_shadow_fixture_payload(tmp_path))
    journal = build_paper_shadow_journal(fixture)
    forbidden = {"BUY", "SELL", "ORDER", "EXECUTE", "ENTRY_APPROVED", "TRADE_APPROVED", "POSITION_OPEN", "POSITION_CLOSE"}
    assert journal.entries[0].decision_type.value not in forbidden
