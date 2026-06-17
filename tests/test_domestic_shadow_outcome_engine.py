from stock_risk_mcp.domestic_shadow_outcome_engine import (
    build_domestic_shadow_outcome_validation_report,
    build_paper_shadow_outcome_labels,
    build_paper_shadow_outcome_review_report,
    build_paper_shadow_outcome_safety_report,
)
from stock_risk_mcp.domestic_shadow_outcome_fixture import load_domestic_shadow_outcome_fixture
from tests.test_domestic_realtime_fixture import write
from tests.test_domestic_shadow_outcome_fixture import (
    blocked_profitability_journal_payload,
    report_only_journal_payload,
    shadow_outcome_fixture_payload,
)


def _load(tmp_path, payload):
    return load_domestic_shadow_outcome_fixture(
        write(tmp_path, "domestic_shadow_outcome_fixture.json", payload)
    )


def test_domestic_shadow_outcome_builds_validation_report(tmp_path):
    fixture = _load(tmp_path, shadow_outcome_fixture_payload(tmp_path))
    report = build_domestic_shadow_outcome_validation_report(fixture)
    assert report.config_id == fixture.shadow_outcome_config.config_id


def test_domestic_shadow_outcome_labels_favorable_watch(tmp_path):
    fixture = _load(tmp_path, shadow_outcome_fixture_payload(tmp_path))
    labels = build_paper_shadow_outcome_labels(fixture)
    assert labels[0].outcome_label.value == "OUTCOME_FAVORABLE"


def test_domestic_shadow_outcome_labels_adverse_watch(tmp_path):
    payload = shadow_outcome_fixture_payload(
        tmp_path,
        future_points=[
            {"timestamp": "2026-06-17T11:05:00+09:00", "price": 97.0, "volume": 1000.0},
            {"timestamp": "2026-06-17T11:10:00+09:00", "price": 98.0, "volume": 1200.0},
        ],
    )
    fixture = _load(tmp_path, payload)
    labels = build_paper_shadow_outcome_labels(fixture)
    assert labels[0].outcome_label.value == "OUTCOME_ADVERSE"


def test_domestic_shadow_outcome_labels_neutral_watch(tmp_path):
    payload = shadow_outcome_fixture_payload(
        tmp_path,
        future_points=[
            {"timestamp": "2026-06-17T11:05:00+09:00", "price": 100.5, "volume": 1000.0},
            {"timestamp": "2026-06-17T11:10:00+09:00", "price": 100.2, "volume": 1200.0},
        ],
    )
    fixture = _load(tmp_path, payload)
    labels = build_paper_shadow_outcome_labels(fixture)
    assert labels[0].outcome_label.value == "OUTCOME_NEUTRAL"


def test_domestic_shadow_outcome_labels_inconclusive_watch(tmp_path):
    payload = shadow_outcome_fixture_payload(
        tmp_path,
        future_points=[
            {"timestamp": "2026-06-17T11:05:00+09:00", "price": 103.5, "volume": 1000.0},
            {"timestamp": "2026-06-17T11:10:00+09:00", "price": 97.5, "volume": 1200.0},
        ],
    )
    fixture = _load(tmp_path, payload)
    labels = build_paper_shadow_outcome_labels(fixture)
    assert labels[0].outcome_label.value == "OUTCOME_INCONCLUSIVE"


def test_domestic_shadow_outcome_labels_report_only(tmp_path):
    payload = shadow_outcome_fixture_payload(tmp_path, journal_payload=report_only_journal_payload(tmp_path))
    fixture = _load(tmp_path, payload)
    labels = build_paper_shadow_outcome_labels(fixture)
    assert labels[0].outcome_label.value == "OUTCOME_REPORT_ONLY"


def test_domestic_shadow_outcome_labels_blocked_confirmed(tmp_path):
    blocked_payload = shadow_outcome_fixture_payload(
        tmp_path,
        journal_payload=blocked_profitability_journal_payload(tmp_path),
    )
    blocked_fixture = _load(tmp_path, blocked_payload)
    labels = build_paper_shadow_outcome_labels(blocked_fixture)
    assert labels[0].outcome_label.value == "OUTCOME_BLOCKED_CONFIRMED"


def test_domestic_shadow_outcome_labels_insufficient_data(tmp_path):
    payload = shadow_outcome_fixture_payload(
        tmp_path,
        future_points=[
            {"timestamp": "2026-06-17T11:05:00+09:00", "price": None, "volume": 1000.0},
        ],
    )
    fixture = _load(tmp_path, payload)
    labels = build_paper_shadow_outcome_labels(fixture)
    assert labels[0].outcome_label.value == "OUTCOME_INSUFFICIENT_DATA"


def test_domestic_shadow_outcome_generates_observation_metrics(tmp_path):
    fixture = _load(tmp_path, shadow_outcome_fixture_payload(tmp_path))
    label = build_paper_shadow_outcome_labels(fixture)[0]
    assert label.maximum_favorable_observation_move > 0
    assert label.maximum_adverse_observation_move >= 0
    assert label.final_observation_move > 0
    assert label.threshold_touched is True


def test_domestic_shadow_outcome_review_report_is_derived_from_candidate_labels(tmp_path):
    payload = shadow_outcome_fixture_payload(tmp_path)
    second = dict(payload["outcome_fixtures"][0])
    second["fixture_id"] = "outcome-fixture-2"
    second["source_paper_shadow_decision_id"] = payload["shadow_outcome_input_set"]["paper_shadow_journal"]["entries"][0]["journal_entry_id"]
    second["candidate_id"] = payload["shadow_outcome_input_set"]["paper_shadow_journal"]["entries"][0]["candidate_id"]
    payload["shadow_outcome_input_set"]["paper_shadow_journal"]["entries"].append(
        dict(payload["shadow_outcome_input_set"]["paper_shadow_journal"]["entries"][0], journal_entry_id="domestic-paper-shadow-run-1-entry-2", candidate_id="candidate-2")
    )
    second["source_paper_shadow_decision_id"] = "domestic-paper-shadow-run-1-entry-2"
    second["candidate_id"] = "candidate-2"
    second["symbol"] = "000660"
    second["scenario_family"] = "BREAKOUT"
    second["replay_window_id"] = "REPLAY_WINDOW_B"
    payload["outcome_fixtures"].append(second)
    fixture = _load(tmp_path, payload)
    labels = build_paper_shadow_outcome_labels(fixture)
    review = build_paper_shadow_outcome_review_report(fixture)
    assert review.total_outcome_labels == len(labels)
    assert sum(review.outcome_label_counts.values()) == len(labels)
    assert review.scenario_family_coverage_count == 2


def test_domestic_shadow_outcome_safety_report_is_non_executable(tmp_path):
    fixture = _load(tmp_path, shadow_outcome_fixture_payload(tmp_path))
    report = build_paper_shadow_outcome_safety_report(fixture)
    assert report.safety_boundary.order_creation_allowed is False


def test_domestic_shadow_outcome_uses_no_trade_execution_labels(tmp_path):
    fixture = _load(tmp_path, shadow_outcome_fixture_payload(tmp_path))
    labels = build_paper_shadow_outcome_labels(fixture)
    forbidden = {
        "PROFIT_TRADE",
        "LOSS_TRADE",
        "BUY_SUCCESS",
        "SELL_SUCCESS",
        "ENTRY_SUCCESS",
        "EXECUTION_RESULT",
        "TRADE_RESULT",
        "ORDER_RESULT",
    }
    assert labels[0].outcome_label.value not in forbidden
