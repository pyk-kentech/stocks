from __future__ import annotations

from stock_risk_mcp.paper_evaluation_models import (
    PaperEvaluationFill,
    PaperEvaluationFillStatus,
    PaperEvaluationIntent,
    PaperEvaluationLedgerEntry,
    PaperEvaluationPipelineInput,
    PaperEvaluationPosition,
    PaperEvaluationSide,
    PaperEvaluationTrade,
)


def build_paper_evaluation_ledger(
    pipeline_input: PaperEvaluationPipelineInput,
    intents: list[PaperEvaluationIntent],
    fills: list[PaperEvaluationFill],
) -> tuple[list[PaperEvaluationLedgerEntry], list[PaperEvaluationPosition], list[PaperEvaluationTrade]]:
    cash = pipeline_input.config.starting_cash
    positions: dict[str, PaperEvaluationPosition] = {}
    trades: dict[str, PaperEvaluationTrade] = {}
    ledger_entries: list[PaperEvaluationLedgerEntry] = []
    intents_by_id = {intent.intent_id: intent for intent in intents}
    training_by_row = {row.row_id: row for row in pipeline_input.training_rows}

    for fill in sorted(fills, key=lambda item: (item.fill_available_at or item.fill_observed_at or pipeline_input.feature_rows[0].feature_asof, item.fill_id)):
        intent = intents_by_id[fill.intent_id]
        training_row = training_by_row.get(intent.row_id)
        split_id = training_row.split_id if training_row else f"{pipeline_input.dataset_id}-UNKNOWN"
        cash_before = cash
        event_type = "NO_FILL"
        realized_pnl = 0.0

        if fill.fill_status != PaperEvaluationFillStatus.FILLED or fill.fill_price is None:
            ledger_entries.append(
                PaperEvaluationLedgerEntry(
                    ledger_entry_id=f"{fill.fill_id}-LEDGER",
                    dataset_id=pipeline_input.dataset_id,
                    split_id=split_id,
                    instrument_id=fill.instrument_id,
                    event_time=fill.fill_available_at or fill.fill_observed_at or intent.feature_asof,
                    event_type=event_type,
                    side=fill.side,
                    cash_before=cash_before,
                    cash_after=cash,
                )
            )
            continue

        position = positions.get(fill.instrument_id)
        total_cost = fill.gross_notional + fill.commission_cost + fill.tax_cost + fill.slippage_cost + fill.spread_penalty_cost + fill.fx_cost
        if fill.side == PaperEvaluationSide.BUY:
            if position and pipeline_input.config.duplicate_position_policy.value == "BLOCK":
                event_type = "DUPLICATE_BLOCK"
            elif cash < total_cost:
                event_type = "INSUFFICIENT_CASH_BLOCK"
            else:
                cash -= total_cost
                event_type = "OPEN"
                positions[fill.instrument_id] = PaperEvaluationPosition(
                    position_id=f"{fill.instrument_id}-{split_id}-POSITION",
                    dataset_id=pipeline_input.dataset_id,
                    split_id=split_id,
                    instrument_id=fill.instrument_id,
                    open_quantity=fill.fill_quantity,
                    average_entry_price=fill.fill_price,
                    market_price=fill.fill_price,
                    market_value=fill.fill_price * fill.fill_quantity,
                    unrealized_pnl=0.0,
                    closed=False,
                )
                trades[fill.instrument_id] = PaperEvaluationTrade(
                    trade_id=f"{fill.instrument_id}-{split_id}-TRADE",
                    dataset_id=pipeline_input.dataset_id,
                    split_id=split_id,
                    instrument_id=fill.instrument_id,
                    side=fill.side,
                    entry_time=fill.fill_available_at or fill.fill_observed_at or intent.feature_asof,
                    entry_price=fill.fill_price,
                    quantity=fill.fill_quantity,
                    split_role=training_row.split_role.value if training_row and hasattr(training_row.split_role, "value") else str(training_row.split_role) if training_row else "UNKNOWN",
                )
        elif fill.side == PaperEvaluationSide.SELL and position:
            proceeds = fill.gross_notional - fill.commission_cost - fill.tax_cost - fill.slippage_cost - fill.spread_penalty_cost - fill.fx_cost
            cash += proceeds
            event_type = "CLOSE"
            realized_pnl = proceeds - (position.average_entry_price * fill.fill_quantity)
            trade = trades[fill.instrument_id]
            trades[fill.instrument_id] = trade.model_copy(
                update={
                    "exit_time": fill.fill_available_at or fill.fill_observed_at or intent.feature_asof,
                    "exit_price": fill.fill_price,
                    "gross_pnl": proceeds - (position.average_entry_price * fill.fill_quantity),
                    "net_pnl": realized_pnl,
                    "holding_bars": 1,
                }
            )
            positions[fill.instrument_id] = position.model_copy(
                update={
                    "open_quantity": 0.0,
                    "market_price": fill.fill_price,
                    "market_value": 0.0,
                    "unrealized_pnl": 0.0,
                    "closed": True,
                }
            )

        ledger_entries.append(
            PaperEvaluationLedgerEntry(
                ledger_entry_id=f"{fill.fill_id}-LEDGER",
                dataset_id=pipeline_input.dataset_id,
                split_id=split_id,
                instrument_id=fill.instrument_id,
                event_time=fill.fill_available_at or fill.fill_observed_at or intent.feature_asof,
                event_type=event_type,
                side=fill.side,
                cash_before=cash_before,
                cash_after=cash,
                realized_pnl_delta=realized_pnl,
                fees_delta=fill.commission_cost,
                taxes_delta=fill.tax_cost,
                slippage_delta=fill.slippage_cost + fill.spread_penalty_cost + fill.fx_cost,
            )
        )

    return ledger_entries, list(positions.values()), list(trades.values())
