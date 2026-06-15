from statistics import mean, median

from stock_risk_mcp.llm_feature_models import (
    LLMAggregateMetric,
    LLMFeatureStoreResult,
    LLMHorizon,
    LLMRiskWarningMetric,
    LLMSignalDirection,
    LLMSignalEvaluation,
    LLMSignalEvaluationReport,
    LLMSpilloverEvaluation,
    LLMVersionMetric,
)


HORIZONS = [LLMHorizon.ONE_DAY, LLMHorizon.THREE_DAY, LLMHorizon.FIVE_DAY]


def build_feature_store_result(fixture, checksum):
    return LLMFeatureStoreResult(
        fixture_checksum=checksum, run_id=fixture.run_id,
        prompt_version=fixture.prompt_version, model_version=fixture.model_version,
        signals=fixture.signals, signal_count=len(fixture.signals),
    )


def _confidence(value):
    return "HIGH" if value >= .75 else "MEDIUM" if value >= .5 else "LOW"


def _directional(direction, value):
    if direction in {LLMSignalDirection.NEUTRAL, LLMSignalDirection.UNCERTAIN}:
        return "NOT_APPLICABLE"
    return "HIT" if (direction == LLMSignalDirection.POSITIVE and value > 0) or (direction == LLMSignalDirection.NEGATIVE and value < 0) else "MISS"


def _metric(items, missing=0, neutral=0):
    returns = [item.return_pct for item in items if item.return_pct is not None]
    draws = [item.max_drawdown_pct for item in items if item.max_drawdown_pct is not None]
    directional = [item.directional_outcome for item in items if item.directional_outcome in {"HIT", "MISS"}]
    total = len(returns) + missing
    return LLMAggregateMetric(
        sample_status="SUFFICIENT_SAMPLE" if len(returns) >= 5 else "INSUFFICIENT_SAMPLE",
        available_count=len(returns), missing_count=missing,
        missing_data_rate=missing / total if total else 0,
        mean_return_pct=mean(returns) if returns else None,
        median_return_pct=median(returns) if returns else None,
        hit_rate=directional.count("HIT") / len(directional) * 100 if directional else None,
        mean_drawdown_pct=mean(draws) if draws else None,
        median_drawdown_pct=median(draws) if draws else None,
        neutral_uncertain_count=neutral,
    )


def evaluate_llm_signals(signals, outcomes, signal_checksum, outcome_checksum):
    outcome_map = {(item.ticker, item.as_of_time): item for item in outcomes.snapshots}
    evaluations, spillovers = [], []
    for signal in signals.signals:
        confidence = 1 - signal.uncertainty_score
        snapshot = outcome_map.get((signal.ticker, signal.as_of_time))
        horizon_map = {item.horizon: item for item in snapshot.horizons} if snapshot else {}
        for horizon in HORIZONS:
            outcome = horizon_map.get(horizon)
            evaluations.append(LLMSignalEvaluation(
                ticker=signal.ticker, as_of_time=signal.as_of_time, event_type=signal.event_type,
                prompt_version_id=signals.prompt_version.prompt_version_id,
                model_version_id=signals.model_version.model_version_id,
                horizon=horizon, direction=signal.direction,
                status="EVALUATED" if outcome else "NEEDS_MORE_DATA",
                confidence=confidence, confidence_bucket=_confidence(confidence),
                risk_warning_bucket="HIGH_RISK_WARNING" if signal.risk_language_score >= .7 else "LOW_RISK_WARNING",
                directional_outcome=_directional(signal.direction, outcome.return_pct) if outcome else "NEEDS_MORE_DATA",
                return_pct=outcome.return_pct if outcome else None,
                max_drawdown_pct=outcome.max_drawdown_pct if outcome else None,
            ))
            for related in signal.related_tickers:
                related_snapshot = outcome_map.get((related, signal.as_of_time))
                related_map = {item.horizon: item for item in related_snapshot.horizons} if related_snapshot else {}
                related_outcome = related_map.get(horizon)
                spillovers.append(LLMSpilloverEvaluation(
                    source_ticker=signal.ticker, related_ticker=related, horizon=horizon,
                    status="EVALUATED" if related_outcome else "NEEDS_MORE_DATA",
                    directional_outcome=_directional(signal.direction, related_outcome.return_pct) if related_outcome else "NEEDS_MORE_DATA",
                    return_pct=related_outcome.return_pct if related_outcome else None,
                    max_drawdown_pct=related_outcome.max_drawdown_pct if related_outcome else None,
                ))
    horizon_metrics, confidence_metrics, risk_metrics, spillover_metrics, version_metrics = {}, {}, {}, {}, {}
    for horizon in HORIZONS:
        horizon_items = [item for item in evaluations if item.horizon == horizon]
        available = [item for item in horizon_items if item.status == "EVALUATED"]
        metric = _metric(
            available, len(horizon_items) - len(available),
            sum(item.direction in {LLMSignalDirection.NEUTRAL, LLMSignalDirection.UNCERTAIN} for item in available),
        )
        baseline = []
        for snapshot in outcomes.snapshots:
            baseline.extend(item.return_pct for item in snapshot.horizons if item.horizon == horizon)
        positive = [item.return_pct for item in available if item.direction == LLMSignalDirection.POSITIVE]
        metric.baseline_mean_return_pct = mean(baseline) if baseline else None
        metric.positive_mean_return_pct = mean(positive) if positive else None
        if metric.baseline_mean_return_pct is not None and metric.positive_mean_return_pct is not None:
            metric.positive_minus_baseline_pct = metric.positive_mean_return_pct - metric.baseline_mean_return_pct
        horizon_metrics[horizon.value] = metric
        confidence_metrics[horizon.value] = {
            bucket: _metric(
                [item for item in available if item.confidence_bucket == bucket],
                sum(item.status == "NEEDS_MORE_DATA" and item.confidence_bucket == bucket for item in horizon_items),
            )
            for bucket in ("HIGH", "MEDIUM", "LOW")
        }
        high = [item.max_drawdown_pct for item in available if item.risk_warning_bucket == "HIGH_RISK_WARNING"]
        low = [item.max_drawdown_pct for item in available if item.risk_warning_bucket == "LOW_RISK_WARNING"]
        risk_metrics[horizon.value] = LLMRiskWarningMetric(
            high_risk_mean_drawdown_pct=mean(high) if high else None,
            low_risk_mean_drawdown_pct=mean(low) if low else None,
        )
        spill = [item for item in spillovers if item.horizon == horizon]
        spill_available = [item for item in spill if item.status == "EVALUATED"]
        spillover_metrics[horizon.value] = _metric(spill_available, len(spill) - len(spill_available))
        version_metrics[horizon.value] = LLMVersionMetric(
            **_metric(available, len(horizon_items) - len(available)).model_dump(),
            prompt_version_id=signals.prompt_version.prompt_version_id,
            model_version_id=signals.model_version.model_version_id,
        )
    return LLMSignalEvaluationReport(
        signal_fixture_checksum=signal_checksum, outcome_fixture_checksum=outcome_checksum,
        evaluations=evaluations, spillover_evaluations=spillovers,
        horizon_metrics=horizon_metrics, confidence_metrics=confidence_metrics,
        risk_warning_metrics=risk_metrics, spillover_metrics=spillover_metrics,
        version_metrics=version_metrics,
    )
