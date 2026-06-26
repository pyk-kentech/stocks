from __future__ import annotations

from collections import defaultdict

from stock_risk_mcp.paper_evaluation_models import (
    PaperEvaluationFill,
    PaperEvaluationFillPolicy,
    PaperEvaluationFillStatus,
    PaperEvaluationIntent,
    PaperEvaluationPipelineInput,
    PaperEvaluationSide,
)


def _next_bar(feature_asof, bars):
    future = [bar for bar in bars if bar.observed_at > feature_asof]
    return future[0] if future else None


def build_paper_evaluation_fills(
    pipeline_input: PaperEvaluationPipelineInput,
    intents: list[PaperEvaluationIntent],
) -> list[PaperEvaluationFill]:
    price_bars: dict[str, list] = defaultdict(list)
    for bar in pipeline_input.price_history_rows:
        price_bars[bar.instrument_id].append(bar)
    for bars in price_bars.values():
        bars.sort(key=lambda item: item.observed_at)

    fills: list[PaperEvaluationFill] = []
    for intent in intents:
        if intent.side in {PaperEvaluationSide.HOLD, PaperEvaluationSide.WATCH, PaperEvaluationSide.NO_TRADE}:
            fills.append(
                PaperEvaluationFill(
                    fill_id=f"{intent.intent_id}-NO-FILL",
                    intent_id=intent.intent_id,
                    dataset_id=pipeline_input.dataset_id,
                    instrument_id=intent.instrument_id,
                    side=intent.side,
                    fill_policy=PaperEvaluationFillPolicy.NO_FILL,
                    fill_status=PaperEvaluationFillStatus.NO_FILL,
                    assumption_notes=["non-trading intent"],
                )
            )
            continue

        candidate_bars = price_bars.get(intent.instrument_id, [])
        same_bar_unsafe = any(
            bar.observed_at <= intent.feature_asof and bar.available_at > intent.feature_asof
            for bar in candidate_bars
        )
        if same_bar_unsafe:
            fills.append(
                PaperEvaluationFill(
                    fill_id=f"{intent.intent_id}-LEAKAGE-BLOCKED",
                    intent_id=intent.intent_id,
                    dataset_id=pipeline_input.dataset_id,
                    instrument_id=intent.instrument_id,
                    side=intent.side,
                    fill_policy=pipeline_input.config.fill_policy,
                    fill_status=PaperEvaluationFillStatus.LEAKAGE_BLOCKED,
                    assumption_notes=["same-bar post-decision price blocked"],
                )
            )
            continue

        bar = _next_bar(intent.feature_asof, candidate_bars)
        if bar is None:
            fills.append(
                PaperEvaluationFill(
                    fill_id=f"{intent.intent_id}-FILL-GAP",
                    intent_id=intent.intent_id,
                    dataset_id=pipeline_input.dataset_id,
                    instrument_id=intent.instrument_id,
                    side=intent.side,
                    fill_policy=pipeline_input.config.fill_policy,
                    fill_status=PaperEvaluationFillStatus.FILL_GAP,
                    assumption_notes=["future bar missing"],
                )
            )
            continue

        if pipeline_input.config.fill_policy == PaperEvaluationFillPolicy.NEXT_BAR_CLOSE:
            base_price = bar.close_price
        else:
            base_price = bar.open_price or bar.close_price
        quantity = max(intent.sizing_hint, 1.0)
        gross_notional = float(base_price) * quantity
        commission = gross_notional * (pipeline_input.config.commission_bps / 10_000.0)
        tax = gross_notional * (pipeline_input.config.tax_bps / 10_000.0)
        slippage = gross_notional * (pipeline_input.config.slippage_bps / 10_000.0)
        spread = gross_notional * (pipeline_input.config.spread_penalty_bps / 10_000.0)
        fx_cost = gross_notional * (pipeline_input.config.fx_cost_bps / 10_000.0)
        fills.append(
            PaperEvaluationFill(
                fill_id=f"{intent.intent_id}-FILL",
                intent_id=intent.intent_id,
                dataset_id=pipeline_input.dataset_id,
                instrument_id=intent.instrument_id,
                side=intent.side,
                fill_policy=pipeline_input.config.fill_policy,
                fill_status=PaperEvaluationFillStatus.FILLED,
                fill_price=float(base_price),
                fill_quantity=quantity,
                fill_observed_at=bar.observed_at,
                fill_available_at=bar.available_at,
                gross_notional=gross_notional,
                commission_cost=commission,
                tax_cost=tax,
                slippage_cost=slippage,
                spread_penalty_cost=spread,
                fx_cost=fx_cost,
                assumption_notes=["local future bar", "recorded cost model"],
            )
        )
    return fills
