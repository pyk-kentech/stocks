from stock_risk_mcp.llm_feature_models import LLMSignalDirection
from stock_risk_mcp.llm_signal_evaluation import build_feature_store_result, evaluate_llm_signals
from tests.test_llm_feature_fixture import outcome_payload, signal_payload


def signal(ticker, direction, uncertainty, risk, related=None):
    value = dict(signal_payload()["signals"][0])
    value.update(
        ticker=ticker, direction=direction, uncertainty_score=uncertainty,
        risk_language_score=risk, related_tickers=related or [],
    )
    return value


def snapshot(ticker, returns=(5, 3, -1), drawdown=2):
    return {
        "ticker": ticker, "as_of_time": "2026-01-01T15:30:00+00:00", "reference_price": 100,
        "horizons": [
            {
                "horizon": horizon, "outcome_time": f"2026-01-0{day}T16:00:00+00:00",
                "future_price": 100 + value, "return_pct": value, "max_drawdown_pct": drawdown,
            }
            for horizon, day, value in zip(("1D", "3D", "5D"), (2, 4, 6), returns)
        ],
    }


def fixtures():
    from stock_risk_mcp.llm_feature_models import LLMOutcomeFixture, LLMSignalFixture
    signals = [
        signal("AAA", "POSITIVE", .1, .2, ["REL"]),
        signal("BBB", "NEGATIVE", .3, .8),
        signal("CCC", "NEUTRAL", .6, .1),
    ]
    outcomes = [snapshot("AAA"), snapshot("BBB", (-2, -1, 2), 8), snapshot("CCC", (1, 1, 1)), snapshot("REL", (4, 2, 1))]
    return LLMSignalFixture.model_validate(signal_payload(signals)), LLMOutcomeFixture.model_validate(outcome_payload(outcomes))


def test_feature_store_is_advisory_and_local_only():
    signals, _ = fixtures()
    result = build_feature_store_result(signals, "checksum")
    assert result.signal_count == 3
    assert result.metadata_json["advisory_only"] is True
    assert result.metadata_json["llm_called"] is False


def test_evaluates_horizons_buckets_neutral_and_spillover():
    signals, outcomes = fixtures()
    report = evaluate_llm_signals(signals, outcomes, "signals", "outcomes")
    first = report.evaluations[0]
    assert len(report.evaluations) == 9
    assert first.confidence == .9 and first.confidence_bucket == "HIGH"
    assert first.directional_outcome == "HIT"
    assert sum(item.direction == LLMSignalDirection.NEUTRAL for item in report.evaluations) == 3
    assert report.horizon_metrics["1D"].neutral_uncertain_count == 1
    assert report.spillover_metrics["1D"].available_count == 1
    assert report.version_metrics["1D"].prompt_version_id == "prompt-v1"
    assert report.version_metrics["1D"].sample_status == "INSUFFICIENT_SAMPLE"
    assert report.metadata_json["strategy_weight_changed"] is False


def test_missing_horizons_are_needs_more_data():
    from stock_risk_mcp.llm_feature_models import LLMOutcomeFixture, LLMSignalFixture
    signals = LLMSignalFixture.model_validate(signal_payload())
    outcomes = LLMOutcomeFixture.model_validate(outcome_payload())
    report = evaluate_llm_signals(signals, outcomes, "signals", "outcomes")
    assert [item.status for item in report.evaluations] == ["EVALUATED", "NEEDS_MORE_DATA", "NEEDS_MORE_DATA"]
    assert report.horizon_metrics["3D"].missing_count == 1


def test_risk_warning_metrics_are_accuracy_not_causal():
    signals, outcomes = fixtures()
    report = evaluate_llm_signals(signals, outcomes, "signals", "outcomes")
    metric = report.risk_warning_metrics["1D"]
    assert metric.high_risk_mean_drawdown_pct == 8
    assert metric.low_risk_mean_drawdown_pct == 2
    assert metric.causal_claim is False


def test_positive_baseline_confidence_and_version_metrics_are_deterministic():
    signals, outcomes = fixtures()
    first = evaluate_llm_signals(signals, outcomes, "signals", "outcomes")
    second = evaluate_llm_signals(signals, outcomes, "signals", "outcomes")
    metric = first.horizon_metrics["1D"]

    assert first == second
    assert metric.positive_mean_return_pct == 5
    assert metric.baseline_mean_return_pct == 2
    assert metric.positive_minus_baseline_pct == 3
    assert first.confidence_metrics["1D"]["HIGH"].available_count == 1
    assert first.confidence_metrics["1D"]["MEDIUM"].available_count == 1
    assert first.confidence_metrics["1D"]["LOW"].available_count == 1
