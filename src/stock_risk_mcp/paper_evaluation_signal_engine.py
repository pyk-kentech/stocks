from __future__ import annotations

from stock_risk_mcp.paper_evaluation_guard import ensure_signal_does_not_use_labels
from stock_risk_mcp.paper_evaluation_models import (
    PaperEvaluationConfidenceBucket,
    PaperEvaluationIntent,
    PaperEvaluationPipelineInput,
    PaperEvaluationRiskBucket,
    PaperEvaluationSide,
    PaperEvaluationSignal,
    PaperEvaluationSignalStatus,
)


def _score(feature_values: dict[str, object]) -> float:
    for key in ("signal_score", "alpha_score", "context_score", "macro_score"):
        raw = feature_values.get(key)
        if isinstance(raw, (int, float)):
            return max(0.0, min(1.0, float(raw)))
    close_price = feature_values.get("close_price")
    if isinstance(close_price, (int, float)):
        return 0.7 if float(close_price) > 0 else 0.0
    return 0.5


def build_paper_evaluation_signals(
    pipeline_input: PaperEvaluationPipelineInput,
) -> tuple[list[PaperEvaluationSignal], list[PaperEvaluationIntent]]:
    training_rows_by_id = {row.row_id: row for row in pipeline_input.training_rows}
    split_role_by_id = {
        row.row_id: (row.split_id, row.split_role.value if hasattr(row.split_role, "value") else str(row.split_role))
        for row in pipeline_input.training_rows
    }
    override = pipeline_input.rule_override
    allow_symbolic_sell = pipeline_input.config.allow_symbolic_sell or bool(override and override.allow_symbolic_sell)
    buy_threshold = override.buy_score_threshold if override else 0.65
    watch_threshold = override.watch_score_threshold if override else 0.5
    liquidity_threshold = override.liquidity_min_threshold if override else 0.3
    macro_block_threshold = override.macro_block_threshold if override else 0.8

    signals: list[PaperEvaluationSignal] = []
    intents: list[PaperEvaluationIntent] = []

    for feature_row in pipeline_input.feature_rows:
        ensure_signal_does_not_use_labels(feature_row.feature_values)
        training_row = training_rows_by_id.get(feature_row.row_id)
        split_id, split_role = split_role_by_id.get(feature_row.row_id, (f"{pipeline_input.dataset_id}-UNASSIGNED", "UNASSIGNED"))
        score = _score(feature_row.feature_values)
        reasons: list[str] = []
        status = PaperEvaluationSignalStatus.SIGNAL_READY
        side = PaperEvaluationSide.BUY if score >= buy_threshold else PaperEvaluationSide.HOLD

        if training_row and training_row.blocked_from_training:
            status = PaperEvaluationSignalStatus.BLOCKED_LEAKAGE
            side = PaperEvaluationSide.NO_TRADE
            reasons.append("BLOCKED_LEAKAGE")
        elif feature_row.feature_values.get("event_block") is True or feature_row.feature_values.get("event_window_active") is True:
            status = PaperEvaluationSignalStatus.BLOCKED_EVENT_RISK
            side = PaperEvaluationSide.WATCH
            reasons.append("EVENT_RISK")
        elif isinstance(feature_row.feature_values.get("macro_block_score"), (int, float)) and float(feature_row.feature_values["macro_block_score"]) >= macro_block_threshold:
            status = PaperEvaluationSignalStatus.BLOCKED_MACRO_RISK
            side = PaperEvaluationSide.NO_TRADE
            reasons.append("MACRO_RISK")
        elif isinstance(feature_row.feature_values.get("volume_ratio"), (int, float)) and float(feature_row.feature_values["volume_ratio"]) < liquidity_threshold:
            status = PaperEvaluationSignalStatus.BLOCKED_LIQUIDITY
            side = PaperEvaluationSide.WATCH
            reasons.append("LIQUIDITY")
        elif score < watch_threshold:
            status = PaperEvaluationSignalStatus.NO_TRADE
            side = PaperEvaluationSide.NO_TRADE
            reasons.append("LOW_SCORE")
        elif score < buy_threshold:
            status = PaperEvaluationSignalStatus.WATCH_ONLY
            side = PaperEvaluationSide.WATCH
            reasons.append("WATCH_THRESHOLD")
        elif allow_symbolic_sell and feature_row.feature_values.get("symbolic_sell") is True:
            side = PaperEvaluationSide.SELL
            reasons.append("SYMBOLIC_SELL")
        else:
            reasons.append("BUY_THRESHOLD")

        signal = PaperEvaluationSignal(
            signal_id=f"{feature_row.row_id}-SIGNAL",
            dataset_id=pipeline_input.dataset_id,
            row_id=feature_row.row_id,
            instrument_id=feature_row.instrument_id,
            split_id=split_id,
            split_role=split_role,
            feature_asof=feature_row.feature_asof,
            signal_status=status,
            side=side,
            signal_score=score,
            reason_codes=reasons,
            used_feature_keys=sorted(feature_row.feature_values.keys()),
            signal_metadata={"training_row_labeled": bool(training_row.labeled) if training_row else False},
        )
        signals.append(signal)
        intents.append(
            PaperEvaluationIntent(
                intent_id=f"{feature_row.row_id}-INTENT",
                signal_id=signal.signal_id,
                dataset_id=pipeline_input.dataset_id,
                row_id=feature_row.row_id,
                instrument_id=feature_row.instrument_id,
                feature_asof=feature_row.feature_asof,
                side=signal.side,
                intent_source="BUILTIN_REPLAY" if override is None else "HYBRID_REPLAY",
                confidence_bucket=PaperEvaluationConfidenceBucket.HIGH if score >= buy_threshold else PaperEvaluationConfidenceBucket.MEDIUM if score >= watch_threshold else PaperEvaluationConfidenceBucket.LOW,
                risk_bucket=PaperEvaluationRiskBucket.BLOCKED if status in {PaperEvaluationSignalStatus.BLOCKED_EVENT_RISK, PaperEvaluationSignalStatus.BLOCKED_MACRO_RISK, PaperEvaluationSignalStatus.BLOCKED_LIQUIDITY, PaperEvaluationSignalStatus.BLOCKED_LEAKAGE} else PaperEvaluationRiskBucket.LOW if score >= buy_threshold else PaperEvaluationRiskBucket.MEDIUM,
                sizing_hint=1.0 if signal.side == PaperEvaluationSide.BUY else 0.0,
                reason_codes=signal.reason_codes,
            )
        )

    return signals, intents
