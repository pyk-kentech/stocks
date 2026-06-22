from __future__ import annotations

from stock_risk_mcp.historical_paper_trading_guard import validate_historical_paper_trading_metadata_safety
from stock_risk_mcp.historical_paper_trading_models import (
    HistoricalPaperSide,
    HistoricalPaperTradingGapCategory,
    HistoricalPaperTradingInput,
)


def run_historical_paper_trading(
    paper_input: HistoricalPaperTradingInput,
) -> HistoricalPaperTradingInput:
    gap_entries: list[dict[str, str]] = []
    runtime = paper_input.paper_runtime_context or {}

    signal_candidate = runtime.get("signal_candidate") or {}
    price_bars = runtime.get("price_bars") or []
    metadata = runtime.get("metadata") or {}

    try:
        validate_historical_paper_trading_metadata_safety(metadata, context="historical paper trading")
    except ValueError as exc:
        gap_entries.append(_unsafe_gap(str(exc)))

    slippage_bps = paper_input.paper_trading_config.slippage_bps
    fee_bps = paper_input.paper_trading_config.fee_bps
    if slippage_bps < 0:
        gap_entries.append(_gap("invalid-slippage", HistoricalPaperTradingGapCategory.PAPER_TRADING_INVALID_SLIPPAGE, "BLOCKING", "invalid slippage"))
    if fee_bps < 0:
        gap_entries.append(_gap("invalid-fee", HistoricalPaperTradingGapCategory.PAPER_TRADING_INVALID_FEE, "BLOCKING", "invalid fee"))

    if not signal_candidate or not signal_candidate.get("candidate_id"):
        gap_entries.append(_gap("missing-signal-candidate", HistoricalPaperTradingGapCategory.PAPER_TRADING_MISSING_SIGNAL_CANDIDATE_REF, "BLOCKING", "missing signal candidate ref"))
    if not price_bars:
        gap_entries.append(_gap("missing-price-bar", HistoricalPaperTradingGapCategory.PAPER_TRADING_MISSING_PRICE_BAR, "BLOCKING", "missing price bar"))

    if paper_input.paper_ledger is None:
        gap_entries.append(_gap("missing-ledger-state", HistoricalPaperTradingGapCategory.PAPER_TRADING_MISSING_LEDGER_STATE, "BLOCKING", "missing ledger state"))
    if paper_input.paper_risk_limit is None:
        gap_entries.append(_gap("missing-risk-limit", HistoricalPaperTradingGapCategory.PAPER_TRADING_MISSING_RISK_LIMIT, "BLOCKING", "missing risk limit"))

    if paper_input.paper_trading_config.initial_cash <= 0:
        gap_entries.append(_gap("invalid-initial-cash", HistoricalPaperTradingGapCategory.PAPER_TRADING_INVALID_INITIAL_CASH, "BLOCKING", "invalid initial cash"))
    if paper_input.paper_order_intent.quantity <= 0:
        gap_entries.append(_gap("invalid-position-size", HistoricalPaperTradingGapCategory.PAPER_TRADING_INVALID_POSITION_SIZE, "BLOCKING", "invalid position size"))

    if paper_input.paper_policy.max_exposure <= 0 or paper_input.paper_policy.max_per_symbol_exposure <= 0:
        gap_entries.append(_gap("invalid-exposure-limit", HistoricalPaperTradingGapCategory.PAPER_TRADING_INVALID_EXPOSURE_LIMIT, "BLOCKING", "invalid exposure limit"))

    decision_side = _evaluate_policy(paper_input, runtime, gap_entries)
    decision = paper_input.paper_decision.model_copy(update={"paper_side": decision_side})
    order_intent = paper_input.paper_order_intent.model_copy(update={"paper_side": decision_side})

    fill = paper_input.paper_fill
    ledger = paper_input.paper_ledger
    position = paper_input.paper_position
    trade = paper_input.paper_trade
    performance = paper_input.paper_performance_report

    if decision_side in {HistoricalPaperSide.PAPER_BUY, HistoricalPaperSide.PAPER_SELL, HistoricalPaperSide.PAPER_CLOSE} and not _has_blocking_gaps(gap_entries):
        next_bar = price_bars[0] if price_bars else {}
        if next_bar.get("open") is None:
            gap_entries.append(_gap("missing-fill-price", HistoricalPaperTradingGapCategory.PAPER_TRADING_MISSING_FILL_PRICE, "BLOCKING", "missing fill price"))
        else:
            fill_price = float(next_bar["open"])
            quantity = order_intent.quantity
            gross_notional = fill_price * quantity
            slippage_cost = round(gross_notional * (slippage_bps / 1000.0), 6)
            fee_cost = round(gross_notional * (fee_bps / 1000.0), 6)
            total_cost = gross_notional + slippage_cost + fee_cost

            if ledger.cash_balance < total_cost and decision_side == HistoricalPaperSide.PAPER_BUY:
                gap_entries.append(_gap("insufficient-simulated-cash", HistoricalPaperTradingGapCategory.PAPER_TRADING_INVALID_POSITION_SIZE, "BLOCKING", "insufficient simulated cash"))
            else:
                fill = fill.model_copy(
                    update={
                        "paper_side": decision_side,
                        "fill_price": fill_price,
                        "fill_quantity": quantity,
                        "slippage_cost": slippage_cost,
                        "fee_cost": fee_cost,
                    }
                )
                ledger, position, trade, performance = _apply_fill(
                    paper_input=paper_input,
                    decision_side=decision_side,
                    fill=fill,
                    ledger=ledger,
                    position=position,
                    trade=trade,
                    performance=performance,
                    runtime=runtime,
                )

    gap_entries.extend(
        [
            _gap("plan-generated", HistoricalPaperTradingGapCategory.PAPER_TRADING_PLAN_GENERATED, "REPORT_ONLY", "paper trading plan generated"),
            _gap("local-only", HistoricalPaperTradingGapCategory.PAPER_TRADING_LOCAL_ONLY, "REPORT_ONLY", "paper trading remains local-only"),
            _gap("offline-only", HistoricalPaperTradingGapCategory.PAPER_TRADING_OFFLINE_ONLY, "REPORT_ONLY", "paper trading remains offline-only"),
            _gap("paper-only", HistoricalPaperTradingGapCategory.PAPER_TRADING_PAPER_ONLY, "REPORT_ONLY", "paper trading remains paper-only"),
            _gap("simulated-only", HistoricalPaperTradingGapCategory.PAPER_TRADING_SIMULATED_ONLY, "REPORT_ONLY", "paper trading remains simulated-only"),
            _gap("non-executable", HistoricalPaperTradingGapCategory.PAPER_TRADING_NON_EXECUTABLE, "REPORT_ONLY", "paper trading remains non-executable"),
        ]
    )

    gap_report = paper_input.gap_report.model_copy(
        update={
            "gap_status": _gap_status(gap_entries),
            "gap_categories": [item["gap_category"] for item in gap_entries],
            "blocking_gap_count": len([item for item in gap_entries if item["severity"] == "BLOCKING"]),
            "report_only_gap_count": len([item for item in gap_entries if item["severity"] != "BLOCKING"]),
            "gaps": gap_entries,
        }
    )
    safety_report = paper_input.safety_report

    return paper_input.model_copy(
        update={
            "paper_decision": decision,
            "paper_order_intent": order_intent,
            "paper_fill": fill,
            "paper_ledger": ledger,
            "paper_position": position,
            "paper_trade": trade,
            "paper_performance_report": performance,
            "safety_report": safety_report,
            "gap_report": gap_report,
            "audit_records": paper_input.audit_records,
        }
    )


def _evaluate_policy(
    paper_input: HistoricalPaperTradingInput,
    runtime: dict[str, object],
    gap_entries: list[dict[str, str]],
) -> HistoricalPaperSide:
    candidate = runtime.get("signal_candidate") or {}
    score = float(candidate.get("score", 0.0) or 0.0)
    confidence = str(candidate.get("confidence_bucket", "UNKNOWN")).upper()
    risk_blocked = bool(candidate.get("risk_review_blocked", False))
    promotion_blocked = bool(candidate.get("promotion_blocked", True))

    existing_position_count = int(runtime.get("existing_position_count", 0) or 0)
    existing_symbol_exposure = float(runtime.get("existing_symbol_exposure", 0.0) or 0.0)
    existing_total_exposure = float(runtime.get("existing_total_exposure", 0.0) or 0.0)
    daily_loss = float(runtime.get("daily_loss", 0.0) or 0.0)
    drawdown = float(runtime.get("drawdown", 0.0) or 0.0)

    if existing_position_count >= paper_input.paper_policy.max_positions:
        return HistoricalPaperSide.PAPER_SKIP
    if existing_symbol_exposure > paper_input.paper_policy.max_per_symbol_exposure:
        gap_entries.append(_gap("symbol-exposure-limit", HistoricalPaperTradingGapCategory.PAPER_TRADING_INVALID_EXPOSURE_LIMIT, "BLOCKING", "max per-symbol exposure exceeded"))
        return HistoricalPaperSide.PAPER_SKIP
    if existing_total_exposure > paper_input.paper_policy.max_exposure:
        gap_entries.append(_gap("total-exposure-limit", HistoricalPaperTradingGapCategory.PAPER_TRADING_INVALID_EXPOSURE_LIMIT, "BLOCKING", "max total exposure exceeded"))
        return HistoricalPaperSide.PAPER_SKIP
    if daily_loss > paper_input.paper_policy.max_daily_loss:
        gap_entries.append(_gap("daily-loss-limit", HistoricalPaperTradingGapCategory.PAPER_TRADING_INVALID_POSITION_SIZE, "BLOCKING", "max daily loss exceeded"))
        return HistoricalPaperSide.PAPER_SKIP
    if drawdown > paper_input.paper_policy.max_drawdown:
        gap_entries.append(_gap("drawdown-limit", HistoricalPaperTradingGapCategory.PAPER_TRADING_INVALID_EXPOSURE_LIMIT, "BLOCKING", "max drawdown exceeded"))
        return HistoricalPaperSide.PAPER_SKIP
    if promotion_blocked and risk_blocked:
        return HistoricalPaperSide.PAPER_SKIP
    if paper_input.paper_decision.paper_side == HistoricalPaperSide.PAPER_CLOSE:
        return HistoricalPaperSide.PAPER_CLOSE
    if score >= 0.7 and confidence == "HIGH":
        return HistoricalPaperSide.PAPER_BUY
    if score < 0.3:
        return HistoricalPaperSide.PAPER_HOLD
    return paper_input.paper_decision.paper_side


def _apply_fill(
    *,
    paper_input: HistoricalPaperTradingInput,
    decision_side: HistoricalPaperSide,
    fill,
    ledger,
    position,
    trade,
    performance,
    runtime: dict[str, object],
):
    quantity = fill.fill_quantity
    fill_price = fill.fill_price
    gross_notional = fill_price * quantity
    total_cost = gross_notional + fill.slippage_cost + fill.fee_cost
    mark_price = float(runtime.get("current_mark_price", fill_price) or fill_price)

    if decision_side == HistoricalPaperSide.PAPER_CLOSE:
        entry_price = trade.entry_price if trade.entry_price > 0 else position.average_entry_price
        realized_pnl = (fill_price - entry_price) * quantity - fill.slippage_cost - fill.fee_cost
        ledger = ledger.model_copy(
            update={
                "cash_balance": round(ledger.cash_balance + gross_notional - fill.slippage_cost - fill.fee_cost, 6),
                "realized_pnl": round(ledger.realized_pnl + realized_pnl, 6),
                "fees_paid": round(ledger.fees_paid + fill.fee_cost, 6),
                "slippage_paid": round(ledger.slippage_paid + fill.slippage_cost, 6),
                "unrealized_pnl": 0.0,
            }
        )
        position = position.model_copy(
            update={
                "open_quantity": 0,
                "market_value": 0.0,
                "unrealized_pnl": 0.0,
            }
        )
        trade = trade.model_copy(
            update={
                "entry_side": decision_side,
                "entry_quantity": quantity,
                "status": "CLOSED",
            }
        )
        performance = performance.model_copy(
            update={
                "realized_pnl": round(ledger.realized_pnl, 6),
                "unrealized_pnl": 0.0,
                "win_rate": 1.0 if realized_pnl > 0 else 0.0,
                "profit_factor": abs(realized_pnl) if realized_pnl != 0 else 0.0,
                "average_win": realized_pnl if realized_pnl > 0 else 0.0,
                "average_loss": abs(realized_pnl) if realized_pnl < 0 else 0.0,
                "turnover": round(gross_notional, 6),
                "number_of_trades": 1,
                "fees": round(ledger.fees_paid, 6),
                "slippage_cost": round(ledger.slippage_paid, 6),
                "max_drawdown": float(runtime.get("drawdown", 0.0) or 0.0),
            }
        )
        return ledger, position, trade, performance

    cash_balance = round(ledger.cash_balance - total_cost, 6)
    unrealized_pnl = round((mark_price - fill_price) * quantity, 6)
    market_value = round(mark_price * quantity, 6)

    ledger = ledger.model_copy(
        update={
            "cash_balance": cash_balance,
            "fees_paid": round(ledger.fees_paid + fill.fee_cost, 6),
            "slippage_paid": round(ledger.slippage_paid + fill.slippage_cost, 6),
            "unrealized_pnl": unrealized_pnl,
        }
    )
    position = position.model_copy(
        update={
            "symbol": fill.symbol,
            "open_quantity": quantity,
            "average_entry_price": fill_price,
            "market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
        }
    )
    trade = trade.model_copy(
        update={
            "symbol": fill.symbol,
            "entry_fill_id": fill.paper_fill_id,
            "entry_side": decision_side,
            "entry_price": fill_price,
            "entry_quantity": quantity,
            "status": "OPEN",
        }
    )
    performance = performance.model_copy(
        update={
            "total_return": round((ledger.cash_balance + market_value - ledger.starting_cash) / ledger.starting_cash, 8) if ledger.starting_cash else 0.0,
            "realized_pnl": round(ledger.realized_pnl, 6),
            "unrealized_pnl": unrealized_pnl,
            "turnover": round(gross_notional, 6),
            "fees": round(ledger.fees_paid, 6),
            "slippage_cost": round(ledger.slippage_paid, 6),
            "number_of_trades": 1,
            "profit_factor": 0.0,
            "win_rate": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "exposure_time": float(paper_input.paper_policy.default_holding_period_sessions),
            "max_drawdown": float(runtime.get("drawdown", 0.0) or 0.0),
        }
    )
    return ledger, position, trade, performance


def _gap(gap_id: str, category: HistoricalPaperTradingGapCategory, severity: str, message: str) -> dict[str, str]:
    return {
        "gap_id": gap_id.upper(),
        "gap_category": category.value,
        "severity": severity,
        "message": message,
    }


def _gap_status(gap_entries: list[dict[str, str]]) -> str:
    if any(entry["severity"] == "BLOCKING" for entry in gap_entries):
        return "BLOCKING_GAPS"
    if gap_entries:
        return "REPORT_ONLY_GAPS"
    return "NO_GAPS"


def _has_blocking_gaps(gap_entries: list[dict[str, str]]) -> bool:
    return any(entry["severity"] == "BLOCKING" for entry in gap_entries)


def _unsafe_gap(reason: str) -> dict[str, str]:
    lowered = reason.lower()
    mapping = (
        ("real_action", HistoricalPaperTradingGapCategory.PAPER_TRADING_REAL_ACTION_NOT_ALLOWED, "real action not allowed"),
        ("order", HistoricalPaperTradingGapCategory.PAPER_TRADING_REAL_ORDER_INTENT_NOT_ALLOWED, "real order intent not allowed"),
        ("broker", HistoricalPaperTradingGapCategory.PAPER_TRADING_BROKER_PATH_NOT_ALLOWED, "broker path not allowed"),
        ("account", HistoricalPaperTradingGapCategory.PAPER_TRADING_ACCOUNT_API_NOT_ALLOWED, "account api not allowed"),
        ("kiwoom", HistoricalPaperTradingGapCategory.PAPER_TRADING_KIWOOM_API_NOT_ALLOWED, "kiwoom api not allowed"),
        ("ls", HistoricalPaperTradingGapCategory.PAPER_TRADING_LS_API_NOT_ALLOWED, "ls api not allowed"),
        ("provider", HistoricalPaperTradingGapCategory.PAPER_TRADING_PROVIDER_API_NOT_ALLOWED, "provider api not allowed"),
        ("api", HistoricalPaperTradingGapCategory.PAPER_TRADING_ORDER_API_NOT_ALLOWED, "order api not allowed"),
        ("network", HistoricalPaperTradingGapCategory.PAPER_TRADING_NETWORK_NOT_ALLOWED, "network not allowed"),
        ("live_trading", HistoricalPaperTradingGapCategory.PAPER_TRADING_LIVE_TRADING_NOT_ALLOWED, "live trading not allowed"),
        ("live_prod", HistoricalPaperTradingGapCategory.PAPER_TRADING_LIVE_PROD_NOT_ALLOWED, "live/prod not allowed"),
        ("cloud_llm", HistoricalPaperTradingGapCategory.PAPER_TRADING_CLOUD_LLM_NOT_ALLOWED, "cloud llm not allowed"),
        ("local_llm", HistoricalPaperTradingGapCategory.PAPER_TRADING_LOCAL_LLM_RUNTIME_NOT_ALLOWED, "local llm runtime not allowed"),
        ("credential", HistoricalPaperTradingGapCategory.PAPER_TRADING_CREDENTIALS_NOT_ALLOWED, "credentials not allowed"),
        ("parquet", HistoricalPaperTradingGapCategory.PAPER_TRADING_PARQUET_NOT_ALLOWED, "parquet not allowed"),
    )
    for needle, category, message in mapping:
        if needle in lowered:
            return _gap(f"unsafe-{needle}", category, "BLOCKING", message)
    return _gap("unsafe-paper-trading", HistoricalPaperTradingGapCategory.PAPER_TRADING_REAL_ORDER_INTENT_NOT_ALLOWED, "BLOCKING", "unsafe paper trading metadata detected")
