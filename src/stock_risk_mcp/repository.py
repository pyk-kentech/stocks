from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from stock_risk_mcp.compliance import ComplianceRecord
from stock_risk_mcp.analysis_report import AnalysisReport, ReportSection, ReportType
from stock_risk_mcp.agent_brief import AgentBrief
from stock_risk_mcp.agent_context import AgentContext
from stock_risk_mcp.agent_prompt import AgentPrompt
from stock_risk_mcp.connector_run import ConnectorMode, ConnectorRun, ConnectorRunStatus, ConnectorType
from stock_risk_mcp.dashboard_models import DashboardBuildResult, DashboardBuildStatus, DashboardType
from stock_risk_mcp.candidate_universe import CandidateScanResult, ScanRun
from stock_risk_mcp.basket import (
    BasketAllocation,
    BasketCandidate,
    BasketMode,
    BasketPlan,
    BasketPolicy,
    BasketRiskSummary,
)
from stock_risk_mcp.database import connect_db, create_schema
from stock_risk_mcp.indicators import IndicatorSignal, IndicatorValue
from stock_risk_mcp.import_run import ImportRun, ImportRunStatus, ImportSourceResult, ImportSourceType
from stock_risk_mcp.basket_performance import summarize_basket_performance
from stock_risk_mcp.models import (
    BacktestOutcome,
    BacktestResult,
    CompanyRisk,
    DataSource,
    Decision,
    EvaluationReason,
    Evidence,
    IngestionRun,
    IngestionStatus,
    MarketSnapshot,
    NewsEvent,
    PriceBar,
    ReasonType,
    RiskPolicy,
    RiskResult,
    Severity,
    SourceType,
    TossSignal,
    TradeProposal,
)
from stock_risk_mcp.local_llm import LocalLLMRequest
from stock_risk_mcp.local_llm_response import LocalLLMResponse
from stock_risk_mcp.notification_run import NotificationRun, NotificationRunStatus
from stock_risk_mcp.normalize_run import NormalizeRun, NormalizeRunStatus, NormalizeSourceResult, NormalizerType
from stock_risk_mcp.notifications import NotificationChannelType, NotificationMessage, NotificationSeverity
from stock_risk_mcp.paper_trading import (
    BasketBacktestResult,
    BasketPerformanceSummary,
    ExitReason,
    PaperTrade,
    PaperTradeStatus,
)
from stock_risk_mcp.pipeline_run import PipelineAlert, PipelineRun
from stock_risk_mcp.provider_packs import ProviderPackRun, ProviderPackRunStatus, ProviderPackType
from stock_risk_mcp.realtime_market_data import (
    MarketRegion,
    RealtimeMonitorRun,
    RealtimeMonitorRunStatus,
    WatchlistEntry,
    WatchlistStatus,
)
from stock_risk_mcp.policy_replay_result import (
    PolicyComparisonResult,
    PolicyReplayMode,
    PolicyReplayResult,
    PolicyReplayStatus,
)
from stock_risk_mcp.policy_evaluation_suite import PolicyEvaluationSuiteResult
from stock_risk_mcp.policy_promotion import PolicyPromotionProposal
from stock_risk_mcp.replay_snapshot import (
    ReplayBasketSnapshot,
    ReplayCandidateSnapshot,
    ReplayOutcomeSnapshot,
    ReplayRun,
    ReplayRunStatus,
    ReplaySnapshotMode,
    ReplayTradePlanSnapshot,
)
from stock_risk_mcp.setup import SetupDirection, SetupGrade, TradeDecision, TradePlan
from stock_risk_mcp.signals import SignalDirection, SignalSeverity, SignalType, TickerSignal, signal_dedupe_key
from stock_risk_mcp.strategy_experiments import StrategyEvaluationMode, StrategyExperiment
from stock_risk_mcp.strategy_memory import StrategyMemory
from stock_risk_mcp.strategy_objective import StrategyRecommendation
from stock_risk_mcp.strategy_policy import (
    StrategyPolicy,
    StrategyPolicyCreator,
    StrategyPolicyStatus,
    validate_strategy_policy,
)


@dataclass(frozen=True)
class RiskEvaluationRecord:
    id: int
    ticker: str
    decision: Decision
    score: int
    created_at: str
    market_price: float | None


class RiskRepository:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        with self._connect() as connection:
            create_schema(connection)

    def save_market_snapshot(self, snapshot: MarketSnapshot, source: str = "adapter") -> int:
        payload = snapshot.model_dump(mode="json")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO market_snapshots (
                    ticker, price, market_cap_usd, avg_dollar_volume_20d,
                    return_5d_pct, return_20d_pct, volatility_20d_pct,
                    sector, source, raw_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.ticker,
                    snapshot.price,
                    snapshot.market_cap_usd,
                    snapshot.avg_dollar_volume_20d,
                    snapshot.return_5d_pct,
                    snapshot.return_20d_pct,
                    snapshot.volatility_20d_pct,
                    snapshot.sector,
                    source,
                    _json(payload),
                ),
            )
            return int(cursor.lastrowid)

    def save_company_risk(self, risk: CompanyRisk, source: str = "adapter") -> int:
        payload = risk.model_dump(mode="json")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO company_risks (
                    ticker, nasdaq_noncompliant, dilution_risk,
                    recent_reverse_split_days, recent_offering_days,
                    has_warrants, has_convertibles, has_going_concern_warning,
                    source, raw_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    risk.ticker,
                    int(risk.nasdaq_noncompliant),
                    str(risk.dilution_risk.value),
                    risk.recent_reverse_split_days,
                    risk.recent_offering_days,
                    int(risk.has_warrants),
                    int(risk.has_convertibles),
                    int(risk.has_going_concern_warning),
                    source,
                    _json(payload),
                ),
            )
            return int(cursor.lastrowid)

    def save_toss_signal(self, ticker: str, signal: TossSignal, source: str = "adapter") -> int:
        payload = signal.model_dump(mode="json")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO toss_investor_snapshots (
                    ticker, tracked_investors_holding, new_buy_count_7d,
                    consensus_level, signal_quality, historical_follow_return_30d_pct,
                    source, raw_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticker.upper(),
                    signal.tracked_investors_holding,
                    signal.new_buy_count_7d,
                    str(signal.consensus_level.value),
                    str(signal.signal_quality.value),
                    signal.historical_follow_return_30d_pct,
                    source,
                    _json(payload),
                ),
            )
            return int(cursor.lastrowid)

    def save_news_event(self, event: NewsEvent) -> int:
        payload = event.model_dump(mode="json")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO news_events (
                    ticker, headline, source, published_at, url,
                    sentiment, summary, raw_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.ticker,
                    event.headline,
                    event.source,
                    event.published_at,
                    event.url,
                    event.sentiment,
                    event.summary,
                    _json(payload),
                ),
            )
            return int(cursor.lastrowid)

    def save_risk_evaluation(
        self,
        proposal: TradeProposal,
        policy: RiskPolicy,
        result: RiskResult,
        market_snapshot_id: int | None = None,
        company_risk_id: int | None = None,
        toss_investor_snapshot_id: int | None = None,
    ) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO risk_evaluations (
                    ticker, decision, score, max_order_usd, max_position_pct,
                    market_snapshot_id, company_risk_id, toss_investor_snapshot_id,
                    proposal_json, policy_json, result_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.ticker,
                    str(result.decision.value),
                    result.score,
                    result.max_order_usd,
                    result.max_position_pct,
                    market_snapshot_id,
                    company_risk_id,
                    toss_investor_snapshot_id,
                    _model_json(proposal),
                    _model_json(policy),
                    _model_json(result),
                ),
            )
            return int(cursor.lastrowid)

    def save_price_bars(self, bars: list[PriceBar]) -> list[int]:
        ids: list[int] = []
        with self._connect() as connection:
            for bar in bars:
                connection.execute(
                    """
                    INSERT INTO price_history (
                        ticker, date, open, high, low, close, volume
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(ticker, date) DO UPDATE SET
                        open = excluded.open,
                        high = excluded.high,
                        low = excluded.low,
                        close = excluded.close,
                        volume = excluded.volume
                    """,
                    (
                        bar.ticker,
                        bar.date.isoformat(),
                        bar.open,
                        bar.high,
                        bar.low,
                        bar.close,
                        bar.volume,
                    ),
                )
                row = connection.execute(
                    "SELECT id FROM price_history WHERE ticker = ? AND date = ?",
                    (bar.ticker, bar.date.isoformat()),
                ).fetchone()
                ids.append(int(row["id"]))
        return ids

    def list_price_bar_keys(self) -> set[tuple[str, str]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT ticker, date FROM price_history").fetchall()
        return {(str(row["ticker"]), str(row["date"])) for row in rows}

    def get_price_history(self, ticker: str, start_date: date, end_date: date) -> list[PriceBar]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT ticker, date, open, high, low, close, volume
                FROM price_history
                WHERE ticker = ? AND date >= ? AND date <= ?
                ORDER BY date ASC
                """,
                (ticker.upper(), start_date.isoformat(), end_date.isoformat()),
            ).fetchall()
        return [PriceBar.model_validate(dict(row)) for row in rows]

    def get_all_price_history(self, ticker: str) -> list[PriceBar]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT ticker, date, open, high, low, close, volume
                FROM price_history
                WHERE ticker = ?
                ORDER BY date ASC
                """,
                (ticker.strip().upper(),),
            ).fetchall()
        return [PriceBar.model_validate(dict(row)) for row in rows]

    def list_price_history_tickers(self, as_of_date: date) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT ticker FROM price_history WHERE date <= ? ORDER BY ticker",
                (as_of_date.isoformat(),),
            ).fetchall()
        return [str(row["ticker"]) for row in rows]

    def get_risk_evaluation_for_backtest(self, risk_evaluation_id: int) -> RiskEvaluationRecord:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    re.id,
                    re.ticker,
                    re.decision,
                    re.score,
                    re.created_at,
                    ms.price AS market_price
                FROM risk_evaluations re
                LEFT JOIN market_snapshots ms ON ms.id = re.market_snapshot_id
                WHERE re.id = ?
                """,
                (risk_evaluation_id,),
            ).fetchone()
        if row is None:
            raise LookupError(f"Risk evaluation not found: {risk_evaluation_id}")
        return _risk_evaluation_record_from_row(row)

    def get_pending_risk_evaluations_for_backtest(self) -> list[RiskEvaluationRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    re.id,
                    re.ticker,
                    re.decision,
                    re.score,
                    re.created_at,
                    ms.price AS market_price
                FROM risk_evaluations re
                LEFT JOIN market_snapshots ms ON ms.id = re.market_snapshot_id
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM backtest_results br
                    WHERE br.risk_evaluation_id = re.id
                )
                ORDER BY re.id ASC
                """
            ).fetchall()
        return [_risk_evaluation_record_from_row(row) for row in rows]

    def save_backtest_result(self, result: BacktestResult) -> int:
        evaluation = self.get_risk_evaluation_for_backtest(result.risk_evaluation_id)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO backtest_results (
                    risk_evaluation_id, ticker, evaluation_created_at,
                    decision, score, horizon_days, entry_price, exit_price,
                    return_pct, max_drawdown_pct, max_gain_pct, outcome
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.risk_evaluation_id,
                    result.ticker,
                    evaluation.created_at,
                    str(result.decision.value),
                    result.score,
                    result.horizon_days,
                    result.entry_price,
                    result.exit_price,
                    result.return_pct,
                    result.max_drawdown_pct,
                    result.max_gain_pct,
                    str(result.outcome.value),
                ),
            )
            return int(cursor.lastrowid)

    def save_evaluation_reasons(self, risk_evaluation_id: int, reasons: list[EvaluationReason]) -> list[int]:
        ids: list[int] = []
        with self._connect() as connection:
            for reason in reasons:
                evidence = reason.evidence
                cursor = connection.execute(
                    """
                    INSERT INTO evaluation_reasons (
                        risk_evaluation_id, ticker, reason_type, reason_code,
                        message, severity, source_name, source_type, source_url,
                        observed_at, raw_reference, confidence
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        risk_evaluation_id,
                        reason.ticker,
                        str(reason.reason_type.value),
                        reason.reason_code,
                        reason.message,
                        str(reason.severity.value),
                        evidence.source_name if evidence else None,
                        str(evidence.source_type.value) if evidence else None,
                        evidence.source_url if evidence else None,
                        evidence.observed_at.isoformat() if evidence and evidence.observed_at else None,
                        evidence.raw_reference if evidence else None,
                        evidence.confidence if evidence else None,
                    ),
                )
                ids.append(int(cursor.lastrowid))
        return ids

    def get_evaluation_reasons(self, risk_evaluation_id: int) -> list[EvaluationReason]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM evaluation_reasons
                WHERE risk_evaluation_id = ?
                ORDER BY id ASC
                """,
                (risk_evaluation_id,),
            ).fetchall()
        return [_evaluation_reason_from_row(row) for row in rows]

    def get_reasons_by_code(self, reason_code: str) -> list[EvaluationReason]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM evaluation_reasons
                WHERE reason_code = ?
                ORDER BY id ASC
                """,
                (reason_code.upper(),),
            ).fetchall()
        return [_evaluation_reason_from_row(row) for row in rows]

    def save_compliance_records(self, records: list[ComplianceRecord]) -> list[int]:
        ids: list[int] = []
        with self._connect() as connection:
            for record in records:
                cursor = connection.execute(
                    """
                    INSERT INTO compliance_records (
                        ticker, company_name, issue, deficiency, notice_date,
                        source_name, source_type, source_url, raw_reference, observed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.ticker,
                        record.company_name,
                        record.issue,
                        record.deficiency,
                        record.notice_date.isoformat() if record.notice_date else None,
                        record.source_name,
                        str(record.source_type.value),
                        record.source_url,
                        record.raw_reference,
                        record.observed_at.isoformat(),
                    ),
                )
                ids.append(int(cursor.lastrowid))
        return ids

    def get_compliance_records(self, ticker: str) -> list[ComplianceRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT ticker, company_name, issue, deficiency, notice_date,
                       source_name, source_type, source_url, raw_reference, observed_at
                FROM compliance_records
                WHERE ticker = ?
                ORDER BY id ASC
                """,
                (ticker.strip().upper(),),
            ).fetchall()
        return [_compliance_record_from_row(row) for row in rows]

    def list_compliance_dedupe_keys(self) -> set[tuple[str, str | None, str, str | None, str | None]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT ticker, notice_date, source_name, issue, deficiency FROM compliance_records"
            ).fetchall()
        return {
            (str(row["ticker"]), row["notice_date"], str(row["source_name"]), row["issue"], row["deficiency"])
            for row in rows
        }

    def save_indicator_values(self, values: list[IndicatorValue]) -> list[int]:
        ids: list[int] = []
        with self._connect() as connection:
            for value in values:
                evidence = value.evidence
                cursor = connection.execute(
                    """
                    INSERT INTO indicator_values (
                        ticker, indicator_code, category, value_json, unit, signal,
                        severity, interpretation, beginner_explanation, source_name,
                        source_type, observed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        value.ticker,
                        value.indicator_code,
                        value.category,
                        json.dumps(value.value, ensure_ascii=False),
                        value.unit,
                        value.signal.value,
                        value.severity.value,
                        value.interpretation,
                        value.beginner_explanation,
                        evidence.source_name if evidence else None,
                        evidence.source_type.value if evidence else None,
                        evidence.observed_at.isoformat() if evidence and evidence.observed_at else None,
                    ),
                )
                ids.append(int(cursor.lastrowid))
        return ids

    def get_indicator_values(self, ticker: str, latest_only: bool = True) -> list[IndicatorValue]:
        latest_filter = """
            AND id IN (
                SELECT MAX(id)
                FROM indicator_values
                WHERE ticker = ?
                GROUP BY indicator_code
            )
        """ if latest_only else ""
        parameters = (ticker.strip().upper(), ticker.strip().upper()) if latest_only else (ticker.strip().upper(),)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM indicator_values
                WHERE ticker = ?
                {latest_filter}
                ORDER BY id ASC
                """,
                parameters,
            ).fetchall()
        return [_indicator_value_from_row(row) for row in rows]

    def save_trade_plan(self, plan: TradePlan) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO trade_plans (
                    ticker, direction, setup_grade, setup_score, entry_price,
                    stop_price, target_price, risk_reward_ratio, max_loss_amount,
                    max_loss_currency, position_size, notional_value, decision,
                    reasons_json, warnings_json, beginner_summary, policy_id,
                    policy_version, setup_scoring_mode, fx_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan.ticker,
                    plan.direction.value,
                    plan.setup_grade.value,
                    plan.setup_score,
                    plan.entry_price,
                    plan.stop_price,
                    plan.target_price,
                    plan.risk_reward_ratio,
                    plan.max_loss_amount,
                    plan.max_loss_currency,
                    plan.position_size,
                    plan.notional_value,
                    plan.decision.value,
                    json.dumps(plan.reasons, ensure_ascii=False),
                    json.dumps(plan.warnings, ensure_ascii=False),
                    plan.beginner_summary,
                    plan.policy_id,
                    plan.policy_version,
                    plan.setup_scoring_mode,
                    _fx_json(plan),
                ),
            )
            return int(cursor.lastrowid)

    def get_trade_plan(self, plan_id: int) -> TradePlan:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM trade_plans WHERE id = ?", (plan_id,)).fetchone()
        if row is None:
            raise LookupError(f"Trade plan not found: {plan_id}")
        return _trade_plan_from_row(row)

    def list_trade_plans(self, ticker: str | None = None, limit: int = 50) -> list[TradePlan]:
        with self._connect() as connection:
            if ticker is None:
                rows = connection.execute("SELECT * FROM trade_plans ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM trade_plans WHERE ticker = ? ORDER BY id DESC LIMIT ?",
                    (ticker.strip().upper(), limit),
                ).fetchall()
        return [_trade_plan_from_row(row) for row in rows]

    def save_basket_plan(self, plan: BasketPlan) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO basket_plans (
                    basket_id, basket_name, mode, policy_json, decision,
                    risk_summary_json, beginner_summary, created_at, policy_id,
                    policy_version, basket_scoring_mode
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan.basket_id,
                    plan.basket_name,
                    plan.mode.value,
                    plan.policy.model_dump_json(),
                    plan.decision.value,
                    plan.risk_summary.model_dump_json(),
                    plan.beginner_summary,
                    plan.created_at.isoformat(),
                    plan.policy_id,
                    plan.policy_version,
                    plan.basket_scoring_mode,
                ),
            )
            for allocation in plan.allocations:
                connection.execute(
                    """
                    INSERT INTO basket_allocations (
                        basket_id, ticker, setup_grade, allocated_loss_amount,
                        allocated_notional_value, position_size, entry_price,
                        stop_price, target_price, risk_reward_ratio, allocation_reason
                        , fx_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan.basket_id,
                        allocation.ticker,
                        allocation.setup_grade.value,
                        allocation.allocated_loss_amount,
                        allocation.allocated_notional_value,
                        allocation.position_size,
                        allocation.entry_price,
                        allocation.stop_price,
                        allocation.target_price,
                        allocation.risk_reward_ratio,
                        allocation.allocation_reason,
                        _fx_json(allocation),
                    ),
                )
            for candidate in plan.blocked:
                connection.execute(
                    """
                    INSERT INTO basket_blocked_candidates (
                        basket_id, ticker, setup_grade, decision, score,
                        reasons_json, warnings_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan.basket_id,
                        candidate.ticker,
                        candidate.setup_grade.value,
                        candidate.decision.value,
                        candidate.score,
                        json.dumps(candidate.reasons, ensure_ascii=False),
                        json.dumps(candidate.warnings, ensure_ascii=False),
                    ),
                )
            return int(cursor.lastrowid)

    def get_basket_plan(self, basket_id: str) -> BasketPlan:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM basket_plans WHERE basket_id = ?", (basket_id,)).fetchone()
            blocked_rows = connection.execute(
                "SELECT * FROM basket_blocked_candidates WHERE basket_id = ? ORDER BY id ASC", (basket_id,)
            ).fetchall()
        if row is None:
            raise LookupError(f"Basket plan not found: {basket_id}")
        allocations = self.get_basket_allocations(basket_id)
        blocked = [_blocked_candidate_from_row(item) for item in blocked_rows]
        return _basket_plan_from_row(row, allocations, blocked)

    def list_basket_plans(self, limit: int = 50) -> list[BasketPlan]:
        with self._connect() as connection:
            rows = connection.execute("SELECT basket_id FROM basket_plans ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [self.get_basket_plan(str(row["basket_id"])) for row in rows]

    def get_basket_allocations(self, basket_id: str) -> list[BasketAllocation]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM basket_allocations WHERE basket_id = ? ORDER BY id ASC", (basket_id,)
            ).fetchall()
        return [_basket_allocation_from_row(row) for row in rows]

    def save_paper_trade(self, trade: PaperTrade) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO paper_trades (
                    trade_id, basket_id, ticker, direction, setup_grade,
                    entry_price, stop_price, target_price, position_size,
                    allocated_loss_amount, notional_value, entry_date, exit_date,
                    exit_price, exit_reason, realized_pnl, realized_return_pct,
                    status, created_at, policy_id, policy_version, basket_scoring_mode
                    , fx_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade.trade_id,
                    trade.basket_id,
                    trade.ticker,
                    trade.direction.value,
                    trade.setup_grade.value,
                    trade.entry_price,
                    trade.stop_price,
                    trade.target_price,
                    trade.position_size,
                    trade.allocated_loss_amount,
                    trade.notional_value,
                    trade.entry_date.isoformat(),
                    trade.exit_date.isoformat() if trade.exit_date else None,
                    trade.exit_price,
                    trade.exit_reason.value if trade.exit_reason else None,
                    trade.realized_pnl,
                    trade.realized_return_pct,
                    trade.status.value,
                    trade.created_at.isoformat(),
                    trade.policy_id,
                    trade.policy_version,
                    trade.basket_scoring_mode,
                    _fx_json(trade),
                ),
            )
            return int(cursor.lastrowid)

    def save_paper_trades(self, trades: list[PaperTrade]) -> list[int]:
        return [self.save_paper_trade(trade) for trade in trades]

    def list_paper_trades(self, basket_id: str | None = None, limit: int = 100) -> list[PaperTrade]:
        with self._connect() as connection:
            if basket_id is None:
                rows = connection.execute("SELECT * FROM paper_trades ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM paper_trades WHERE basket_id = ? ORDER BY id ASC LIMIT ?",
                    (basket_id, limit),
                ).fetchall()
        return [_paper_trade_from_row(row) for row in rows]

    def save_basket_backtest_result(self, result: BasketBacktestResult) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO basket_backtest_results (
                    basket_id, horizon_days, entry_date, exit_date,
                    total_notional_value, total_allocated_loss, realized_pnl,
                    realized_return_pct, max_drawdown, max_gain, win_count,
                    loss_count, flat_count, no_data_count, closed_trade_count,
                    outcome, created_at, policy_id, policy_version, basket_scoring_mode
                    , fx_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.basket_id,
                    result.horizon_days,
                    result.entry_date.isoformat(),
                    result.exit_date.isoformat() if result.exit_date else None,
                    result.total_notional_value,
                    result.total_allocated_loss,
                    result.realized_pnl,
                    result.realized_return_pct,
                    result.max_drawdown,
                    result.max_gain,
                    result.win_count,
                    result.loss_count,
                    result.flat_count,
                    result.no_data_count,
                    result.closed_trade_count,
                    result.outcome.value,
                    result.created_at.isoformat(),
                    result.policy_id,
                    result.policy_version,
                    result.basket_scoring_mode,
                    _fx_json(result),
                ),
            )
            return int(cursor.lastrowid)

    def get_basket_backtest_result(self, basket_id: str) -> BasketBacktestResult | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM basket_backtest_results WHERE basket_id = ? ORDER BY id DESC LIMIT 1",
                (basket_id,),
            ).fetchone()
        return _basket_backtest_result_from_row(row) if row else None

    def list_basket_backtest_results(self, limit: int | None = 50) -> list[BasketBacktestResult]:
        with self._connect() as connection:
            if limit is None:
                rows = connection.execute("SELECT * FROM basket_backtest_results ORDER BY id ASC").fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM basket_backtest_results ORDER BY id ASC LIMIT ?", (limit,)
                ).fetchall()
        return [_basket_backtest_result_from_row(row) for row in rows]

    def basket_performance_summary(self) -> BasketPerformanceSummary:
        return summarize_basket_performance(
            self.list_basket_backtest_results(limit=None),
            self.list_paper_trades(limit=1_000_000),
        )

    def save_replay_run(self, run: ReplayRun) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO replay_runs (
                    run_id, status, snapshot_mode, source_type, source_basket_id,
                    as_of_date, policy_id, policy_version, notes_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id, run.status.value, run.snapshot_mode.value, run.source_type,
                    run.source_basket_id, run.as_of_date.isoformat() if run.as_of_date else None,
                    run.policy_id, run.policy_version, _json(run.notes), run.created_at.isoformat(),
                ),
            )

    def save_policy_replay_result(self, result: PolicyReplayResult) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO policy_replay_results (
                    policy_replay_id, source_replay_run_id, replay_mode, policy_id, policy_version,
                    as_of_date, horizon_days, candidate_count, trade_plan_count, basket_id,
                    total_notional_value, total_allocated_loss, realized_pnl, realized_return_pct,
                    win_count, loss_count, no_data_count, outcome, objective_score, status,
                    notes_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.policy_replay_id, result.source_replay_run_id, result.replay_mode.value,
                    result.policy_id, result.policy_version, result.as_of_date.isoformat(), result.horizon_days,
                    result.candidate_count, result.trade_plan_count, result.basket_id, result.total_notional_value,
                    result.total_allocated_loss, result.realized_pnl, result.realized_return_pct, result.win_count,
                    result.loss_count, result.no_data_count, result.outcome, result.objective_score,
                    result.status.value, _json(result.notes), result.created_at.isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def get_policy_replay_result(self, policy_replay_id: str) -> PolicyReplayResult:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM policy_replay_results WHERE policy_replay_id = ?", (policy_replay_id,)
            ).fetchone()
        if row is None:
            raise LookupError(f"Policy replay result not found: {policy_replay_id}")
        return _policy_replay_result_from_row(row)

    def list_policy_replay_results(
        self, source_replay_run_id: str | None = None, limit: int = 50
    ) -> list[PolicyReplayResult]:
        with self._connect() as connection:
            if source_replay_run_id is None:
                rows = connection.execute(
                    "SELECT * FROM policy_replay_results ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM policy_replay_results WHERE source_replay_run_id = ? ORDER BY id DESC LIMIT ?",
                    (source_replay_run_id, limit),
                ).fetchall()
        return [_policy_replay_result_from_row(row) for row in rows]

    def save_policy_comparison_result(self, result: PolicyComparisonResult) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO policy_comparison_results (
                    comparison_id, source_replay_run_id, baseline_policy_id, baseline_policy_version,
                    candidate_policy_id, candidate_policy_version, baseline_replay_id, candidate_replay_id,
                    baseline_return_pct, candidate_return_pct, return_delta_pct, baseline_objective_score,
                    candidate_objective_score, objective_delta, recommendation, notes_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.comparison_id, result.source_replay_run_id, result.baseline_policy_id,
                    result.baseline_policy_version, result.candidate_policy_id, result.candidate_policy_version,
                    result.baseline_replay_id, result.candidate_replay_id, result.baseline_return_pct,
                    result.candidate_return_pct, result.return_delta_pct, result.baseline_objective_score,
                    result.candidate_objective_score, result.objective_delta, result.recommendation.value,
                    _json(result.notes), result.created_at.isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def list_policy_comparison_results(
        self, source_replay_run_id: str | None = None, limit: int = 50
    ) -> list[PolicyComparisonResult]:
        with self._connect() as connection:
            if source_replay_run_id is None:
                rows = connection.execute(
                    "SELECT * FROM policy_comparison_results ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM policy_comparison_results WHERE source_replay_run_id = ? ORDER BY id DESC LIMIT ?",
                    (source_replay_run_id, limit),
                ).fetchall()
        return [_policy_comparison_result_from_row(row) for row in rows]

    def save_policy_evaluation_suite(self, result: PolicyEvaluationSuiteResult) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO policy_evaluation_suites (
                    suite_id, baseline_policy_id, baseline_policy_version, candidate_policy_id,
                    candidate_policy_version, replay_run_count, completed_pair_count,
                    no_data_replay_count, incomplete_pair_count, baseline_avg_return_pct,
                    candidate_avg_return_pct, return_delta_pct, baseline_avg_objective_score,
                    candidate_avg_objective_score, objective_delta, baseline_win_rate,
                    candidate_win_rate, win_rate_delta, baseline_loss_rate, candidate_loss_rate,
                    no_data_rate, recommendation, result_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    result.suite_id, result.baseline_policy_id, result.baseline_policy_version,
                    result.candidate_policy_id, result.candidate_policy_version, result.replay_run_count,
                    result.completed_pair_count, result.no_data_replay_count, result.incomplete_pair_count,
                    result.baseline_avg_return_pct, result.candidate_avg_return_pct, result.return_delta_pct,
                    result.baseline_avg_objective_score, result.candidate_avg_objective_score,
                    result.objective_delta, result.baseline_win_rate, result.candidate_win_rate,
                    result.win_rate_delta, result.baseline_loss_rate, result.candidate_loss_rate,
                    result.no_data_rate, result.recommendation.value, result.model_dump_json(), result.created_at.isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def get_policy_evaluation_suite(self, suite_id: str) -> PolicyEvaluationSuiteResult:
        with self._connect() as connection:
            row = connection.execute("SELECT result_json FROM policy_evaluation_suites WHERE suite_id = ?", (suite_id,)).fetchone()
        if row is None:
            raise LookupError(f"Policy evaluation suite not found: {suite_id}")
        return PolicyEvaluationSuiteResult.model_validate_json(str(row["result_json"]))

    def list_policy_evaluation_suites(self, limit: int = 50) -> list[PolicyEvaluationSuiteResult]:
        with self._connect() as connection:
            rows = connection.execute("SELECT result_json FROM policy_evaluation_suites ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [PolicyEvaluationSuiteResult.model_validate_json(str(row["result_json"])) for row in rows]

    def save_policy_promotion_proposal(self, proposal: PolicyPromotionProposal) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO policy_promotion_proposals (
                    proposal_id, suite_id, candidate_policy_id, candidate_policy_version, from_status,
                    proposed_status, recommendation, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (proposal.proposal_id, proposal.suite_id, proposal.candidate_policy_id, proposal.candidate_policy_version,
                 proposal.from_status, proposal.proposed_status, proposal.recommendation.value, proposal.reason,
                 proposal.created_at.isoformat()),
            )
            return int(cursor.lastrowid)

    def list_policy_promotion_proposals(self, limit: int = 50) -> list[PolicyPromotionProposal]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM policy_promotion_proposals ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [PolicyPromotionProposal(
            proposal_id=str(row["proposal_id"]), suite_id=str(row["suite_id"]),
            candidate_policy_id=str(row["candidate_policy_id"]), candidate_policy_version=str(row["candidate_policy_version"]),
            from_status=str(row["from_status"]), proposed_status=str(row["proposed_status"]),
            recommendation=str(row["recommendation"]), reason=str(row["reason"] or ""),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        ) for row in rows]

    def save_scan_run(self, run: ScanRun) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO scan_runs (
                    scan_run_id, as_of_date, source, policy_id, policy_version,
                    universe_size, included_count, watch_count, excluded_count,
                    status, notes_json, run_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.scan_run_id,
                    run.as_of_date.isoformat(),
                    run.source.value,
                    run.policy_id,
                    run.policy_version,
                    run.universe_size,
                    run.included_count,
                    run.watch_count,
                    run.excluded_count,
                    run.status.value,
                    _json(run.notes),
                    run.model_dump_json(),
                    run.created_at.isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def get_scan_run(self, scan_run_id: str) -> ScanRun:
        with self._connect() as connection:
            row = connection.execute("SELECT run_json FROM scan_runs WHERE scan_run_id = ?", (scan_run_id,)).fetchone()
        if row is None:
            raise LookupError(f"Scan run not found: {scan_run_id}")
        return ScanRun.model_validate_json(str(row["run_json"]))

    def list_scan_runs(self, limit: int = 50) -> list[ScanRun]:
        with self._connect() as connection:
            rows = connection.execute("SELECT run_json FROM scan_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [ScanRun.model_validate_json(str(row["run_json"])) for row in rows]

    def save_candidate_scan_results(self, results: list[CandidateScanResult]) -> list[int]:
        ids = []
        with self._connect() as connection:
            for result in results:
                cursor = connection.execute(
                    """
                    INSERT INTO candidate_scan_results (
                        scan_run_id, ticker, as_of_date, decision, score, setup_grade,
                        setup_score, trade_plan_decision, price, return_1d_pct,
                        return_5d_pct, return_20d_pct, avg_dollar_volume_20d,
                        volume_spike_ratio, dollar_volume_spike_ratio, volatility_20d_pct,
                        risk_reward_ratio, sector, theme, reasons_json, warnings_json,
                        metadata_json, result_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.scan_run_id,
                        result.ticker,
                        result.as_of_date.isoformat(),
                        result.decision.value,
                        result.score,
                        result.setup_grade,
                        result.setup_score,
                        result.trade_plan_decision,
                        result.price,
                        result.return_1d_pct,
                        result.return_5d_pct,
                        result.return_20d_pct,
                        result.avg_dollar_volume_20d,
                        result.volume_spike_ratio,
                        result.dollar_volume_spike_ratio,
                        result.volatility_20d_pct,
                        result.risk_reward_ratio,
                        result.sector,
                        result.theme,
                        _json(result.reasons),
                        _json(result.warnings),
                        _json(result.metadata),
                        result.model_dump_json(),
                    ),
                )
                ids.append(int(cursor.lastrowid))
        return ids

    def list_candidate_scan_results(
        self, scan_run_id: str, decision: str | None = None, limit: int = 200
    ) -> list[CandidateScanResult]:
        with self._connect() as connection:
            if decision is None:
                rows = connection.execute(
                    "SELECT result_json FROM candidate_scan_results WHERE scan_run_id = ? ORDER BY id LIMIT ?",
                    (scan_run_id, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT result_json FROM candidate_scan_results WHERE scan_run_id = ? AND decision = ? ORDER BY id LIMIT ?",
                    (scan_run_id, decision, limit),
                ).fetchall()
        return [CandidateScanResult.model_validate_json(str(row["result_json"])) for row in rows]

    def save_ticker_signals(self, signals: list[TickerSignal]) -> list[int]:
        ids: list[int] = []
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM ticker_signals").fetchall()
            existing = {signal_dedupe_key(_ticker_signal_from_row(row)) for row in rows}
            for signal in signals:
                key = signal_dedupe_key(signal)
                if key in existing:
                    continue
                cursor = connection.execute(
                    """
                    INSERT INTO ticker_signals (
                        ticker, signal_type, as_of_date, observed_at, direction,
                        severity, score_delta, source_name, title, summary,
                        raw_event_type, metadata_json, reasons_json, warnings_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        signal.ticker, signal.signal_type.value, signal.as_of_date.isoformat(),
                        signal.observed_at.isoformat(), signal.direction.value, signal.severity.value,
                        signal.score_delta, signal.source_name, signal.title, signal.summary,
                        signal.raw_event_type, _json(signal.metadata), _json(signal.reasons), _json(signal.warnings),
                    ),
                )
                ids.append(int(cursor.lastrowid))
                existing.add(key)
        return ids

    def save_import_run(self, run: ImportRun) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO import_runs (
                    import_run_id, as_of_date, status, total_row_count, total_saved_count,
                    total_skipped_duplicate_count, total_error_count, notes_json, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run.import_run_id, run.as_of_date.isoformat() if run.as_of_date else None, run.status.value,
                    run.total_row_count, run.total_saved_count, run.total_skipped_duplicate_count,
                    run.total_error_count, _json(run.notes), run.created_at.isoformat(),
                    run.completed_at.isoformat() if run.completed_at else None,
                ),
            )
            for result in run.source_results:
                connection.execute(
                    """INSERT INTO import_source_results (
                        import_run_id, source_type, file_path, row_count, saved_count,
                        skipped_duplicate_count, error_count, warnings_json, errors_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run.import_run_id, result.source_type.value, result.file_path, result.row_count,
                        result.saved_count, result.skipped_duplicate_count, result.error_count,
                        _json(result.warnings), _json(result.errors),
                    ),
                )
            return int(cursor.lastrowid)

    def get_import_run(self, import_run_id: str) -> ImportRun:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM import_runs WHERE import_run_id = ?", (import_run_id,)).fetchone()
            if row is None:
                raise LookupError(f"Import run not found: {import_run_id}")
            results = connection.execute(
                "SELECT * FROM import_source_results WHERE import_run_id = ? ORDER BY id", (import_run_id,)
            ).fetchall()
        return _import_run_from_rows(row, results)

    def list_import_runs(self, limit: int = 50) -> list[ImportRun]:
        with self._connect() as connection:
            rows = connection.execute("SELECT import_run_id FROM import_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [self.get_import_run(str(row["import_run_id"])) for row in rows]

    def save_normalize_run(self, run: NormalizeRun) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO normalize_runs (
                    normalize_run_id, as_of_date, status, total_row_count, total_normalized_count,
                    total_skipped_count, total_error_count, output_paths_json, notes_json, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run.normalize_run_id, run.as_of_date.isoformat() if run.as_of_date else None, run.status.value,
                    run.total_row_count, run.total_normalized_count, run.total_skipped_count, run.total_error_count,
                    _json(run.output_paths), _json(run.notes), run.created_at.isoformat(),
                    run.completed_at.isoformat() if run.completed_at else None,
                ),
            )
            for item in run.source_results:
                connection.execute(
                    """INSERT INTO normalize_source_results (
                        normalize_run_id, normalizer_name, normalizer_type, input_path, output_path,
                        row_count, normalized_count, skipped_count, error_count, warnings_json, errors_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run.normalize_run_id, item.normalizer_name, item.normalizer_type.value,
                        item.input_path, item.output_path, item.row_count, item.normalized_count,
                        item.skipped_count, item.error_count, _json(item.warnings), _json(item.errors),
                    ),
                )
            return int(cursor.lastrowid)

    def get_normalize_run(self, normalize_run_id: str) -> NormalizeRun:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM normalize_runs WHERE normalize_run_id = ?", (normalize_run_id,)
            ).fetchone()
            if row is None:
                raise LookupError(f"Normalize run not found: {normalize_run_id}")
            results = connection.execute(
                "SELECT * FROM normalize_source_results WHERE normalize_run_id = ? ORDER BY id", (normalize_run_id,)
            ).fetchall()
        return _normalize_run_from_rows(row, results)

    def list_normalize_runs(self, limit: int = 50) -> list[NormalizeRun]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT normalize_run_id FROM normalize_runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self.get_normalize_run(str(row["normalize_run_id"])) for row in rows]

    def save_fx_rates(self, rates: list[dict[str, Any]]) -> list[int]:
        ids = []
        with self._connect() as connection:
            for item in rates:
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO fx_rates (
                        base_currency, quote_currency, date, rate, source_name
                    ) VALUES (?, ?, ?, ?, ?)""",
                    (
                        str(item["base_currency"]).upper(), str(item["quote_currency"]).upper(),
                        item["date"].isoformat() if isinstance(item["date"], date) else str(item["date"]),
                        float(item["rate"]), item.get("source_name"),
                    ),
                )
                if cursor.rowcount:
                    ids.append(int(cursor.lastrowid))
        return ids

    def list_fx_rates(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM fx_rates ORDER BY date DESC, id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def get_latest_fx_rate(self, base_currency: str, quote_currency: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM fx_rates WHERE base_currency=? AND quote_currency=?
                ORDER BY date DESC, id DESC LIMIT 1""",
                (base_currency.upper(), quote_currency.upper()),
            ).fetchone()
        if row is None:
            raise LookupError(f"FX rate not found: {base_currency}/{quote_currency}")
        return dict(row)

    def get_latest_fx_rate_asof(self, base_currency: str, quote_currency: str, as_of_date: date) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM fx_rates WHERE base_currency=? AND quote_currency=? AND date<=?
                ORDER BY date DESC, id DESC LIMIT 1""",
                (base_currency.upper(), quote_currency.upper(), as_of_date.isoformat()),
            ).fetchone()
        return dict(row) if row else None

    def save_connector_run(self, run: ConnectorRun) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO connector_runs (
                    connector_run_id, as_of_date, connector_name, connector_type, mode, status,
                    output_path, row_count, warnings_json, errors_json, metadata_json, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run.connector_run_id, run.as_of_date.isoformat(), run.connector_name, run.connector_type.value,
                    run.mode.value, run.status.value, run.output_path, run.row_count, _json(run.warnings),
                    _json(run.errors), _json(run.metadata), run.created_at.isoformat(),
                    run.completed_at.isoformat() if run.completed_at else None,
                ),
            )
            return int(cursor.lastrowid)

    def save_provider_pack_run(self, run: ProviderPackRun) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO provider_pack_runs (
                    provider_pack_run_id, provider_pack_type, as_of_date, status,
                    connector_run_ids_json, normalize_run_id, import_run_id, output_paths_json,
                    warnings_json, errors_json, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run.provider_pack_run_id, run.provider_pack_type.value, run.as_of_date.isoformat(),
                    run.status.value, _json(run.connector_run_ids), run.normalize_run_id, run.import_run_id,
                    _json(run.output_paths), _json(run.warnings), _json(run.errors), run.created_at.isoformat(),
                    run.completed_at.isoformat() if run.completed_at else None,
                ),
            )
            return int(cursor.lastrowid)

    def get_provider_pack_run(self, provider_pack_run_id: str) -> ProviderPackRun:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM provider_pack_runs WHERE provider_pack_run_id = ?", (provider_pack_run_id,)
            ).fetchone()
        if row is None:
            raise LookupError(f"Provider pack run not found: {provider_pack_run_id}")
        return _provider_pack_run_from_row(row)

    def list_provider_pack_runs(self, limit: int = 50) -> list[ProviderPackRun]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM provider_pack_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [_provider_pack_run_from_row(row) for row in rows]

    def get_connector_run(self, connector_run_id: str) -> ConnectorRun:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM connector_runs WHERE connector_run_id = ?", (connector_run_id,)).fetchone()
        if row is None:
            raise LookupError(f"Connector run not found: {connector_run_id}")
        return _connector_run_from_row(row)

    def list_connector_runs(self, limit: int = 50) -> list[ConnectorRun]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM connector_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [_connector_run_from_row(row) for row in rows]

    def save_analysis_report(self, report: AnalysisReport) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO analysis_reports (
                    report_id, report_type, source_id, generated_at, title, summary,
                    sections_json, key_metrics_json, warnings_json, disclaimer, context_json, markdown
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    report.report_id, report.report_type.value, report.source_id, report.generated_at.isoformat(),
                    report.title, report.summary, _json([item.model_dump(mode="json") for item in report.sections]),
                    _json(report.key_metrics), _json(report.warnings), report.disclaimer,
                    _json(report.context_json), report.markdown,
                ),
            )
            return int(cursor.lastrowid)

    def get_analysis_report(self, report_id: str) -> AnalysisReport:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM analysis_reports WHERE report_id = ?", (report_id,)).fetchone()
        if row is None:
            raise LookupError(f"Analysis report not found: {report_id}")
        return _analysis_report_from_row(row)

    def list_analysis_reports(self, limit: int = 50) -> list[AnalysisReport]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM analysis_reports ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [_analysis_report_from_row(row) for row in rows]

    def save_agent_context(self, item: AgentContext) -> int:
        return self._save_json_record("agent_contexts", "context_id", item.context_id, "context_json", item.model_dump_json())

    def get_agent_context(self, context_id: str) -> AgentContext:
        return AgentContext.model_validate_json(self._get_json_record("agent_contexts", "context_id", context_id, "context_json"))

    def list_agent_contexts(self, limit: int = 50) -> list[AgentContext]:
        return [AgentContext.model_validate_json(value) for value in self._list_json_records("agent_contexts", "context_json", limit)]

    def save_agent_prompt(self, item: AgentPrompt) -> int:
        return self._save_json_record("agent_prompts", "prompt_id", item.prompt_id, "prompt_json", item.model_dump_json())

    def get_agent_prompt(self, prompt_id: str) -> AgentPrompt:
        return AgentPrompt.model_validate_json(self._get_json_record("agent_prompts", "prompt_id", prompt_id, "prompt_json"))

    def list_agent_prompts(self, limit: int = 50) -> list[AgentPrompt]:
        return [AgentPrompt.model_validate_json(value) for value in self._list_json_records("agent_prompts", "prompt_json", limit)]

    def save_agent_brief(self, item: AgentBrief) -> int:
        return self._save_json_record("agent_briefs", "brief_id", item.brief_id, "brief_json", item.model_dump_json())

    def get_agent_brief(self, brief_id: str) -> AgentBrief:
        return AgentBrief.model_validate_json(self._get_json_record("agent_briefs", "brief_id", brief_id, "brief_json"))

    def list_agent_briefs(self, limit: int = 50) -> list[AgentBrief]:
        return [AgentBrief.model_validate_json(value) for value in self._list_json_records("agent_briefs", "brief_json", limit)]

    def save_local_llm_request(self, item: LocalLLMRequest) -> int:
        return self._save_json_record("local_llm_requests", "request_id", item.request_id, "request_json", item.model_dump_json())

    def save_local_llm_response(self, item: LocalLLMResponse) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO local_llm_responses (response_id, request_id, response_json) VALUES (?, ?, ?)",
                (item.response_id, item.request_id, item.model_dump_json()),
            )
            return int(cursor.lastrowid)

    def list_local_llm_responses(self, limit: int = 50) -> list[LocalLLMResponse]:
        return [LocalLLMResponse.model_validate_json(value) for value in self._list_json_records("local_llm_responses", "response_json", limit)]

    def get_local_llm_response(self, response_id: str) -> LocalLLMResponse:
        return LocalLLMResponse.model_validate_json(
            self._get_json_record("local_llm_responses", "response_id", response_id, "response_json")
        )

    def list_local_llm_responses_by_date(self, as_of_date: date) -> list[LocalLLMResponse]:
        return [item for item in self.list_local_llm_responses(1000) if item.created_at.date() == as_of_date]

    def save_notification_run(self, run: NotificationRun) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO notification_runs (
                    notification_run_id, source_type, source_id, channel_type, status,
                    message_count, delivered_count, skipped_duplicate_count, failed_count,
                    output_path, warnings_json, errors_json, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run.notification_run_id, run.source_type, run.source_id, run.channel_type.value, run.status.value,
                    run.message_count, run.delivered_count, run.skipped_duplicate_count, run.failed_count,
                    run.output_path, _json(run.warnings), _json(run.errors), run.created_at.isoformat(),
                    run.completed_at.isoformat() if run.completed_at else None,
                ),
            )
            return int(cursor.lastrowid)

    def get_notification_run(self, notification_run_id: str) -> NotificationRun:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM notification_runs WHERE notification_run_id=?", (notification_run_id,)
            ).fetchone()
        if row is None:
            raise LookupError(f"Notification run not found: {notification_run_id}")
        return _notification_run_from_row(row)

    def list_notification_runs(self, limit: int = 50) -> list[NotificationRun]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM notification_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [_notification_run_from_row(row) for row in rows]

    def save_notification_messages(self, messages: list[NotificationMessage]) -> list[int]:
        ids: list[int] = []
        with self._connect() as connection:
            for item in messages:
                cursor = connection.execute(
                    """INSERT INTO notification_messages (
                        notification_id, source_type, source_id, channel_type, severity, title,
                        message, metadata_json, dedupe_key, created_at, delivered_at, delivery_status, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item.notification_id, item.source_type, item.source_id, item.channel_type.value,
                        item.severity.value, item.title, item.message, _json(item.metadata), item.dedupe_key,
                        item.created_at.isoformat(), item.delivered_at.isoformat() if item.delivered_at else None,
                        item.delivery_status, item.error,
                    ),
                )
                ids.append(int(cursor.lastrowid))
        return ids

    def list_notification_messages(self, source_id: str | None = None, limit: int = 100) -> list[NotificationMessage]:
        with self._connect() as connection:
            if source_id:
                rows = connection.execute(
                    "SELECT * FROM notification_messages WHERE source_id=? ORDER BY id LIMIT ?", (source_id, limit)
                ).fetchall()
            else:
                rows = connection.execute("SELECT * FROM notification_messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [_notification_message_from_row(row) for row in rows]

    def has_notification_dedupe_key(self, dedupe_key: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM notification_messages WHERE dedupe_key=? LIMIT 1", (dedupe_key,)
            ).fetchone()
        return row is not None

    def save_dashboard_build(self, result: DashboardBuildResult) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO dashboard_builds (
                    dashboard_id, dashboard_type, as_of_date, source_id, status, output_path,
                    section_count, warnings_json, errors_json, generated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    result.dashboard_id, result.dashboard_type.value,
                    result.as_of_date.isoformat() if result.as_of_date else None, result.source_id,
                    result.status.value, result.output_path, result.section_count, _json(result.warnings),
                    _json(result.errors), result.generated_at.isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def get_dashboard_build(self, dashboard_id: str) -> DashboardBuildResult:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM dashboard_builds WHERE dashboard_id=?", (dashboard_id,)).fetchone()
        if row is None:
            raise LookupError(f"Dashboard build not found: {dashboard_id}")
        return _dashboard_build_from_row(row)

    def list_dashboard_builds(self, limit: int = 50) -> list[DashboardBuildResult]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM dashboard_builds ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [_dashboard_build_from_row(row) for row in rows]

    def _save_json_record(self, table: str, id_column: str, id_value: str, json_column: str, payload: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                f"INSERT INTO {table} ({id_column}, {json_column}) VALUES (?, ?)", (id_value, payload)
            )
            return int(cursor.lastrowid)

    def _get_json_record(self, table: str, id_column: str, id_value: str, json_column: str) -> str:
        with self._connect() as connection:
            row = connection.execute(f"SELECT {json_column} FROM {table} WHERE {id_column} = ?", (id_value,)).fetchone()
        if row is None:
            raise LookupError(f"{table} record not found: {id_value}")
        return str(row[json_column])

    def _list_json_records(self, table: str, json_column: str, limit: int) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(f"SELECT {json_column} FROM {table} ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [str(row[json_column]) for row in rows]

    def list_ticker_signals(
        self, ticker: str | None = None, as_of_date: date | None = None, limit: int = 200
    ) -> list[TickerSignal]:
        clauses: list[str] = []
        values: list[Any] = []
        if ticker is not None:
            clauses.append("ticker = ?")
            values.append(ticker.strip().upper())
        if as_of_date is not None:
            clauses.append("date(observed_at) <= ?")
            values.append(as_of_date.isoformat())
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        values.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM ticker_signals{where} ORDER BY id LIMIT ?", values
            ).fetchall()
        return [_ticker_signal_from_row(row) for row in rows]

    def get_signals_for_ticker_asof(self, ticker: str, as_of_date: date) -> list[TickerSignal]:
        return self.list_ticker_signals(ticker=ticker, as_of_date=as_of_date)

    def save_pipeline_run(self, run: PipelineRun) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO pipeline_runs (
                    pipeline_run_id, mode, as_of_date, policy_id, policy_version,
                    scan_run_id, basket_id, replay_run_id, policy_replay_id,
                    evaluation_suite_id, status, candidate_count, included_count,
                    watch_count, basket_allocation_count, alert_count, notes_json,
                    error, run_json, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                _pipeline_run_values(run),
            )
            return int(cursor.lastrowid)

    def update_pipeline_run(self, run: PipelineRun) -> None:
        with self._connect() as connection:
            connection.execute(
                """UPDATE pipeline_runs SET
                    mode=?, as_of_date=?, policy_id=?, policy_version=?, scan_run_id=?,
                    basket_id=?, replay_run_id=?, policy_replay_id=?, evaluation_suite_id=?,
                    status=?, candidate_count=?, included_count=?, watch_count=?,
                    basket_allocation_count=?, alert_count=?, notes_json=?, error=?,
                    run_json=?, created_at=?, completed_at=?
                WHERE pipeline_run_id=?""",
                (*_pipeline_run_values(run)[1:], run.pipeline_run_id),
            )

    def get_pipeline_run(self, pipeline_run_id: str) -> PipelineRun:
        with self._connect() as connection:
            row = connection.execute("SELECT run_json FROM pipeline_runs WHERE pipeline_run_id=?", (pipeline_run_id,)).fetchone()
        if row is None:
            raise LookupError(f"Pipeline run not found: {pipeline_run_id}")
        return PipelineRun.model_validate_json(str(row["run_json"]))

    def list_pipeline_runs(self, limit: int = 50) -> list[PipelineRun]:
        with self._connect() as connection:
            rows = connection.execute("SELECT run_json FROM pipeline_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [PipelineRun.model_validate_json(str(row["run_json"])) for row in rows]

    def save_pipeline_alerts(self, alerts: list[PipelineAlert]) -> list[int]:
        ids = []
        with self._connect() as connection:
            for alert in alerts:
                cursor = connection.execute(
                    """INSERT INTO pipeline_alerts (
                        alert_id, pipeline_run_id, alert_type, severity, ticker,
                        title, message, metadata_json, alert_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        alert.alert_id, alert.pipeline_run_id, alert.alert_type.value, alert.severity.value,
                        alert.ticker, alert.title, alert.message, _json(alert.metadata),
                        alert.model_dump_json(), alert.created_at.isoformat(),
                    ),
                )
                ids.append(int(cursor.lastrowid))
        return ids

    def list_pipeline_alerts(self, pipeline_run_id: str | None = None, limit: int = 100) -> list[PipelineAlert]:
        with self._connect() as connection:
            if pipeline_run_id:
                rows = connection.execute("SELECT alert_json FROM pipeline_alerts WHERE pipeline_run_id=? ORDER BY id LIMIT ?", (pipeline_run_id, limit)).fetchall()
            else:
                rows = connection.execute("SELECT alert_json FROM pipeline_alerts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [PipelineAlert.model_validate_json(str(row["alert_json"])) for row in rows]

    def save_realtime_monitor_run(self, run: RealtimeMonitorRun) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO realtime_monitor_runs (
                    realtime_monitor_run_id, as_of, status, provider_name, universe_count,
                    processed_event_count, candidate_count, hot_watchlist_count, warnings_json,
                    errors_json, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run.realtime_monitor_run_id, run.as_of.isoformat(), run.status.value, run.provider_name,
                    run.universe_count, run.processed_event_count, run.candidate_count,
                    run.hot_watchlist_count, _json(run.warnings), _json(run.errors),
                    run.created_at.isoformat(), run.completed_at.isoformat() if run.completed_at else None,
                ),
            )
            return int(cursor.lastrowid)

    def get_realtime_monitor_run(self, realtime_monitor_run_id: str) -> RealtimeMonitorRun:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM realtime_monitor_runs WHERE realtime_monitor_run_id=?",
                (realtime_monitor_run_id,),
            ).fetchone()
        if row is None:
            raise LookupError(f"Realtime monitor run not found: {realtime_monitor_run_id}")
        return _realtime_monitor_run_from_row(row)

    def list_realtime_monitor_runs(self, limit: int = 50) -> list[RealtimeMonitorRun]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM realtime_monitor_runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_realtime_monitor_run_from_row(row) for row in rows]

    def upsert_watchlist_entry(self, entry: WatchlistEntry) -> int:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO watchlist_entries (
                    symbol, region, status, first_seen_at, last_seen_at, promotion_reason,
                    score, metrics_json, warnings_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, region) DO UPDATE SET
                    status=excluded.status, first_seen_at=excluded.first_seen_at,
                    last_seen_at=excluded.last_seen_at, promotion_reason=excluded.promotion_reason,
                    score=excluded.score, metrics_json=excluded.metrics_json,
                    warnings_json=excluded.warnings_json""",
                (
                    entry.symbol, entry.region.value, entry.status.value, entry.first_seen_at.isoformat(),
                    entry.last_seen_at.isoformat(), entry.promotion_reason, entry.score,
                    entry.metrics_json, _json(entry.warnings),
                ),
            )
            row = connection.execute(
                "SELECT id FROM watchlist_entries WHERE symbol=? AND region=?",
                (entry.symbol, entry.region.value),
            ).fetchone()
            return int(row["id"])

    def get_watchlist_entry(self, symbol: str, region: MarketRegion) -> WatchlistEntry:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM watchlist_entries WHERE symbol=? AND region=?",
                (symbol.strip().upper(), region.value),
            ).fetchone()
        if row is None:
            raise LookupError(f"Watchlist entry not found: {symbol} {region.value}")
        return _watchlist_entry_from_row(row)

    def list_watchlist_entries(
        self, status: WatchlistStatus | None = None, limit: int = 200
    ) -> list[WatchlistEntry]:
        with self._connect() as connection:
            if status is None:
                rows = connection.execute(
                    "SELECT * FROM watchlist_entries ORDER BY score DESC, symbol LIMIT ?", (limit,)
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM watchlist_entries WHERE status=? ORDER BY score DESC, symbol LIMIT ?",
                    (status.value, limit),
                ).fetchall()
        return [_watchlist_entry_from_row(row) for row in rows]

    def get_replay_run(self, run_id: str) -> ReplayRun:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM replay_runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise LookupError(f"Replay run not found: {run_id}")
        return _replay_run_from_row(row)

    def list_replay_runs(self, limit: int = 50) -> list[ReplayRun]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM replay_runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [_replay_run_from_row(row) for row in rows]

    def save_replay_candidate_snapshot(self, snapshot: ReplayCandidateSnapshot) -> int:
        return self._save_replay_snapshot(
            "replay_candidate_snapshots", ("run_id", "ticker", "source", "snapshot_json"),
            (snapshot.run_id, snapshot.ticker, snapshot.source, _json(snapshot.snapshot_json)),
        )

    def list_replay_candidate_snapshots(self, run_id: str) -> list[ReplayCandidateSnapshot]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM replay_candidate_snapshots WHERE run_id = ? ORDER BY id", (run_id,)
            ).fetchall()
        return [
            ReplayCandidateSnapshot(
                run_id=str(row["run_id"]), ticker=str(row["ticker"]), source=str(row["source"]),
                snapshot_json=json.loads(str(row["snapshot_json"])),
            )
            for row in rows
        ]

    def save_replay_trade_plan_snapshot(self, snapshot: ReplayTradePlanSnapshot) -> int:
        return self._save_replay_snapshot(
            "replay_trade_plan_snapshots",
            ("run_id", "ticker", "trade_plan_id", "decision", "snapshot_json"),
            (snapshot.run_id, snapshot.ticker, snapshot.trade_plan_id, snapshot.decision, _json(snapshot.snapshot_json)),
        )

    def list_replay_trade_plan_snapshots(self, run_id: str) -> list[ReplayTradePlanSnapshot]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM replay_trade_plan_snapshots WHERE run_id = ? ORDER BY id", (run_id,)
            ).fetchall()
        return [
            ReplayTradePlanSnapshot(
                run_id=str(row["run_id"]), ticker=str(row["ticker"]), trade_plan_id=row["trade_plan_id"],
                decision=str(row["decision"]), snapshot_json=json.loads(str(row["snapshot_json"])),
            )
            for row in rows
        ]

    def save_replay_basket_snapshot(self, snapshot: ReplayBasketSnapshot) -> int:
        return self._save_replay_snapshot(
            "replay_basket_snapshots",
            ("run_id", "basket_id", "decision", "policy_id", "policy_version", "scoring_mode", "snapshot_json"),
            (
                snapshot.run_id, snapshot.basket_id, snapshot.decision, snapshot.policy_id,
                snapshot.policy_version, snapshot.scoring_mode, _json(snapshot.snapshot_json),
            ),
        )

    def get_replay_basket_snapshot(self, run_id: str) -> ReplayBasketSnapshot | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM replay_basket_snapshots WHERE run_id = ?", (run_id,)).fetchone()
        return _replay_basket_snapshot_from_row(row) if row else None

    def get_replay_basket_snapshot_by_basket_id(self, basket_id: str) -> ReplayBasketSnapshot | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM replay_basket_snapshots WHERE basket_id = ? ORDER BY id DESC LIMIT 1", (basket_id,)
            ).fetchone()
        return _replay_basket_snapshot_from_row(row) if row else None

    def save_replay_outcome_snapshot(self, snapshot: ReplayOutcomeSnapshot) -> int:
        return self._save_replay_snapshot(
            "replay_outcome_snapshots",
            ("run_id", "basket_id", "outcome", "realized_return_pct", "snapshot_json"),
            (snapshot.run_id, snapshot.basket_id, snapshot.outcome, snapshot.realized_return_pct, _json(snapshot.snapshot_json)),
        )

    def get_replay_outcome_snapshot(self, run_id: str) -> ReplayOutcomeSnapshot | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM replay_outcome_snapshots WHERE run_id = ?", (run_id,)).fetchone()
        return _replay_outcome_snapshot_from_row(row) if row else None

    def _save_replay_snapshot(self, table: str, columns: tuple[str, ...], values: tuple[Any, ...]) -> int:
        placeholders = ", ".join("?" for _ in columns)
        with self._connect() as connection:
            cursor = connection.execute(
                f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", values
            )
            return int(cursor.lastrowid)

    def save_strategy_policy(self, policy: StrategyPolicy) -> int:
        validate_strategy_policy(policy)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO strategy_policies (
                    policy_id, version, status, weights_json, setup_thresholds_json,
                    basket_rules_json, risk_overrides_json, created_by, reason,
                    parent_policy_id, parent_version, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    policy.policy_id,
                    policy.version,
                    policy.status.value,
                    _json(policy.weights),
                    _json(policy.setup_thresholds),
                    _json(policy.basket_rules),
                    _json(policy.risk_overrides),
                    policy.created_by.value,
                    policy.reason,
                    policy.parent_policy_id,
                    policy.parent_version,
                    policy.created_at.isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def get_strategy_policy(self, policy_id: str, version: str) -> StrategyPolicy:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM strategy_policies WHERE policy_id = ? AND version = ?",
                (policy_id, version),
            ).fetchone()
        if row is None:
            raise LookupError(f"Strategy policy not found: {policy_id}/{version}")
        return _strategy_policy_from_row(row)

    def get_active_strategy_policy(self) -> StrategyPolicy | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM strategy_policies WHERE status = ? ORDER BY id DESC LIMIT 1",
                (StrategyPolicyStatus.ACTIVE.value,),
            ).fetchone()
        return _strategy_policy_from_row(row) if row else None

    def update_strategy_policy_status(self, policy_id: str, version: str, status: str) -> None:
        normalized_status = StrategyPolicyStatus(status).value
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE strategy_policies SET status = ? WHERE policy_id = ? AND version = ?",
                (normalized_status, policy_id, version),
            )
        if cursor.rowcount == 0:
            raise LookupError(f"Strategy policy not found: {policy_id}/{version}")

    def list_strategy_policies(self, limit: int = 50) -> list[StrategyPolicy]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM strategy_policies ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [_strategy_policy_from_row(row) for row in rows]

    def save_strategy_experiment(self, experiment: StrategyExperiment) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO strategy_experiments (
                    experiment_id, baseline_policy_id, baseline_version,
                    candidate_policy_id, candidate_version, evaluation_mode,
                    horizon_days, sample_count, avg_return_pct, median_return_pct,
                    win_rate, loss_rate, profit_factor, avg_max_drawdown,
                    avg_realized_pnl, objective_score, recommendation, notes_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    experiment.experiment_id,
                    experiment.baseline_policy_id,
                    experiment.baseline_version,
                    experiment.candidate_policy_id,
                    experiment.candidate_version,
                    experiment.evaluation_mode.value,
                    experiment.horizon_days,
                    experiment.sample_count,
                    experiment.avg_return_pct,
                    experiment.median_return_pct,
                    experiment.win_rate,
                    experiment.loss_rate,
                    experiment.profit_factor,
                    experiment.avg_max_drawdown,
                    experiment.avg_realized_pnl,
                    experiment.objective_score,
                    experiment.recommendation.value,
                    json.dumps(experiment.notes, ensure_ascii=False),
                    experiment.created_at.isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def list_strategy_experiments(self, limit: int = 50) -> list[StrategyExperiment]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM strategy_experiments ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_strategy_experiment_from_row(row) for row in rows]

    def save_strategy_memory(self, memory: StrategyMemory) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO strategy_memories (
                    memory_id, basket_id, ticker, setup_grade, decision,
                    features_json, outcome, realized_return_pct, realized_pnl,
                    max_drawdown, policy_id, policy_version, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory.memory_id,
                    memory.basket_id,
                    memory.ticker,
                    memory.setup_grade,
                    memory.decision,
                    _json(memory.features_json),
                    memory.outcome,
                    memory.realized_return_pct,
                    memory.realized_pnl,
                    memory.max_drawdown,
                    memory.policy_id,
                    memory.policy_version,
                    memory.created_at.isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def list_strategy_memories(self, limit: int = 100) -> list[StrategyMemory]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM strategy_memories ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [_strategy_memory_from_row(row) for row in rows]

    def upsert_data_source(self, source: DataSource) -> int:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO data_sources (name, source_type, description, base_url, enabled)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    source_type = excluded.source_type,
                    description = excluded.description,
                    base_url = excluded.base_url,
                    enabled = excluded.enabled
                """,
                (
                    source.name,
                    str(source.source_type.value),
                    source.description,
                    source.base_url,
                    int(source.enabled),
                ),
            )
            row = connection.execute("SELECT id FROM data_sources WHERE name = ?", (source.name,)).fetchone()
            return int(row["id"])

    def get_data_sources(self) -> list[DataSource]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT name, source_type, description, base_url, enabled
                FROM data_sources
                ORDER BY name ASC
                """
            ).fetchall()
        return [
            DataSource(
                name=str(row["name"]),
                source_type=SourceType(str(row["source_type"])),
                description=row["description"],
                base_url=row["base_url"],
                enabled=bool(row["enabled"]),
            )
            for row in rows
        ]

    def start_ingestion_run(
        self,
        source_name: str,
        source_type: str,
        metadata: dict | None = None,
    ) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO ingestion_runs (
                    source_name, source_type, status, metadata_json
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    source_name,
                    SourceType(source_type).value,
                    IngestionStatus.STARTED.value,
                    json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True),
                ),
            )
            return int(cursor.lastrowid)

    def finish_ingestion_run(
        self,
        run_id: int,
        status: str,
        records_seen: int,
        records_saved: int,
        error_message: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE ingestion_runs
                SET finished_at = CURRENT_TIMESTAMP,
                    status = ?,
                    records_seen = ?,
                    records_saved = ?,
                    error_message = ?
                WHERE id = ?
                """,
                (
                    IngestionStatus(status).value,
                    records_seen,
                    records_saved,
                    error_message,
                    run_id,
                ),
            )

    def get_ingestion_runs(self, limit: int = 50) -> list[IngestionRun]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT source_name, source_type, started_at, finished_at, status,
                       records_seen, records_saved, error_message, metadata_json
                FROM ingestion_runs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_ingestion_run_from_row(row) for row in rows]

    def get_backtest_summary(self) -> dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    decision,
                    COUNT(*) AS count,
                    AVG(return_pct) AS avg_return_pct,
                    AVG(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0.0 END) AS win_rate,
                    AVG(max_drawdown_pct) AS avg_max_drawdown_pct
                FROM backtest_results
                GROUP BY decision
                ORDER BY decision
                """
            ).fetchall()
            total_row = connection.execute("SELECT COUNT(*) AS count FROM backtest_results").fetchone()
            horizon_row = connection.execute(
                "SELECT horizon_days FROM backtest_results ORDER BY created_at DESC, id DESC LIMIT 1"
            ).fetchone()

        return {
            "horizon_days": int(horizon_row["horizon_days"]) if horizon_row else None,
            "total": int(total_row["count"]),
            "by_decision": {
                str(row["decision"]): {
                    "count": int(row["count"]),
                    "avg_return_pct": _round_optional(row["avg_return_pct"]),
                    "win_rate": _round_optional(row["win_rate"]),
                    "avg_max_drawdown_pct": _round_optional(row["avg_max_drawdown_pct"]),
                }
                for row in rows
            },
        }

    def count_rows(self, table_name: str) -> int:
        allowed_tables = {
            "market_snapshots",
            "company_risks",
            "toss_investor_snapshots",
            "news_events",
            "risk_evaluations",
            "price_history",
            "backtest_results",
            "evaluation_reasons",
            "compliance_records",
            "indicator_values",
            "trade_plans",
            "basket_plans",
            "basket_allocations",
            "basket_blocked_candidates",
            "paper_trades",
            "basket_backtest_results",
            "strategy_policies",
            "strategy_experiments",
            "strategy_memories",
            "replay_runs",
            "replay_candidate_snapshots",
            "replay_trade_plan_snapshots",
            "replay_basket_snapshots",
            "replay_outcome_snapshots",
            "policy_replay_results",
            "policy_comparison_results",
            "policy_evaluation_suites",
            "policy_promotion_proposals",
            "scan_runs",
            "candidate_scan_results",
            "ticker_signals",
            "pipeline_runs",
            "pipeline_alerts",
            "data_sources",
            "ingestion_runs",
            "import_runs",
            "import_source_results",
            "connector_runs",
            "normalize_runs",
            "normalize_source_results",
            "fx_rates",
            "analysis_reports",
            "agent_contexts",
            "agent_prompts",
            "agent_briefs",
            "local_llm_requests",
            "local_llm_responses",
            "notification_runs",
            "notification_messages",
            "dashboard_builds",
        }
        if table_name not in allowed_tables:
            raise ValueError(f"Unsupported table name: {table_name}")
        with self._connect() as connection:
            row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
            return int(row["count"])

    def _connect(self) -> sqlite3.Connection:
        return connect_db(self.db_path)


def _model_json(model: BaseModel) -> str:
    return _json(model.model_dump(mode="json"))


def _fx_json(model: BaseModel) -> str:
    return _json({
        key: value for key, value in model.model_dump(mode="json").items()
        if key in {
            "account_currency", "trading_currency", "fx_rate", "fx_date", "fx_source_name", "fx_stale",
            "max_loss_account", "max_loss_trading", "notional_account", "notional_trading",
            "estimated_loss_account", "estimated_loss_trading", "allocated_loss_account",
            "allocated_loss_trading", "realized_pnl_account", "realized_pnl_trading",
            "return_account_pct", "return_trading_pct", "fx_warnings_json",
        }
    })


def _fx_payload(row: sqlite3.Row) -> dict:
    return json.loads(row["fx_json"]) if "fx_json" in row.keys() and row["fx_json"] else {}


def _import_run_from_rows(row: sqlite3.Row, results: list[sqlite3.Row]) -> ImportRun:
    return ImportRun(
        import_run_id=str(row["import_run_id"]),
        as_of_date=date.fromisoformat(str(row["as_of_date"])) if row["as_of_date"] else None,
        status=ImportRunStatus(str(row["status"])),
        source_results=[
            ImportSourceResult(
                source_type=ImportSourceType(str(item["source_type"])),
                file_path=str(item["file_path"]),
                row_count=int(item["row_count"]),
                saved_count=int(item["saved_count"]),
                skipped_duplicate_count=int(item["skipped_duplicate_count"]),
                error_count=int(item["error_count"]),
                warnings=json.loads(item["warnings_json"]) if item["warnings_json"] else [],
                errors=json.loads(item["errors_json"]) if item["errors_json"] else [],
            )
            for item in results
        ],
        notes=json.loads(row["notes_json"]) if row["notes_json"] else [],
        created_at=datetime.fromisoformat(str(row["created_at"])),
        completed_at=datetime.fromisoformat(str(row["completed_at"])) if row["completed_at"] else None,
    )


def _connector_run_from_row(row: sqlite3.Row) -> ConnectorRun:
    return ConnectorRun(
        connector_run_id=str(row["connector_run_id"]), as_of_date=date.fromisoformat(str(row["as_of_date"])),
        connector_name=str(row["connector_name"]), connector_type=ConnectorType(str(row["connector_type"])),
        mode=ConnectorMode(str(row["mode"])), status=ConnectorRunStatus(str(row["status"])),
        output_path=row["output_path"], row_count=int(row["row_count"]),
        warnings=json.loads(row["warnings_json"]) if row["warnings_json"] else [],
        errors=json.loads(row["errors_json"]) if row["errors_json"] else [],
        metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
        created_at=datetime.fromisoformat(str(row["created_at"])),
        completed_at=datetime.fromisoformat(str(row["completed_at"])) if row["completed_at"] else None,
    )


def _normalize_run_from_rows(row: sqlite3.Row, results: list[sqlite3.Row]) -> NormalizeRun:
    return NormalizeRun(
        normalize_run_id=str(row["normalize_run_id"]),
        as_of_date=date.fromisoformat(str(row["as_of_date"])) if row["as_of_date"] else None,
        status=NormalizeRunStatus(str(row["status"])),
        source_results=[
            NormalizeSourceResult(
                normalizer_name=str(item["normalizer_name"]),
                normalizer_type=NormalizerType(str(item["normalizer_type"])),
                input_path=str(item["input_path"]), output_path=item["output_path"],
                row_count=int(item["row_count"]), normalized_count=int(item["normalized_count"]),
                skipped_count=int(item["skipped_count"]), error_count=int(item["error_count"]),
                warnings=json.loads(item["warnings_json"]) if item["warnings_json"] else [],
                errors=json.loads(item["errors_json"]) if item["errors_json"] else [],
            )
            for item in results
        ],
        notes=json.loads(row["notes_json"]) if row["notes_json"] else [],
        created_at=datetime.fromisoformat(str(row["created_at"])),
        completed_at=datetime.fromisoformat(str(row["completed_at"])) if row["completed_at"] else None,
    )


def _analysis_report_from_row(row: sqlite3.Row) -> AnalysisReport:
    return AnalysisReport(
        report_id=str(row["report_id"]), report_type=ReportType(str(row["report_type"])),
        source_id=str(row["source_id"]), generated_at=datetime.fromisoformat(str(row["generated_at"])),
        title=str(row["title"]), summary=str(row["summary"]),
        sections=[ReportSection.model_validate(item) for item in json.loads(str(row["sections_json"]))],
        key_metrics=json.loads(row["key_metrics_json"]) if row["key_metrics_json"] else {},
        warnings=json.loads(row["warnings_json"]) if row["warnings_json"] else [],
        disclaimer=str(row["disclaimer"] or ""), context_json=json.loads(row["context_json"]) if row["context_json"] else {},
        markdown=row["markdown"],
    )


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _ticker_signal_from_row(row: sqlite3.Row) -> TickerSignal:
    observed_text = str(row["observed_at"])
    observed_at = datetime.fromisoformat(observed_text) if "T" in observed_text else date.fromisoformat(observed_text)
    return TickerSignal(
        ticker=str(row["ticker"]),
        signal_type=SignalType(str(row["signal_type"])),
        as_of_date=date.fromisoformat(str(row["as_of_date"])),
        observed_at=observed_at,
        direction=SignalDirection(str(row["direction"])),
        severity=SignalSeverity(str(row["severity"])),
        score_delta=int(row["score_delta"]),
        source_name=str(row["source_name"]),
        title=row["title"],
        summary=row["summary"],
        raw_event_type=row["raw_event_type"],
        metadata=json.loads(str(row["metadata_json"])) if row["metadata_json"] else {},
        reasons=json.loads(str(row["reasons_json"])) if row["reasons_json"] else [],
        warnings=json.loads(str(row["warnings_json"])) if row["warnings_json"] else [],
    )


def _pipeline_run_values(run: PipelineRun) -> tuple[Any, ...]:
    return (
        run.pipeline_run_id, run.mode.value, run.as_of_date.isoformat(), run.policy_id, run.policy_version,
        run.scan_run_id, run.basket_id, run.replay_run_id, run.policy_replay_id, run.evaluation_suite_id,
        run.status.value, run.candidate_count, run.included_count, run.watch_count,
        run.basket_allocation_count, run.alert_count, _json(run.notes), run.error,
        run.model_dump_json(), run.created_at.isoformat(), run.completed_at.isoformat() if run.completed_at else None,
    )


def _risk_evaluation_record_from_row(row: sqlite3.Row) -> RiskEvaluationRecord:
    return RiskEvaluationRecord(
        id=int(row["id"]),
        ticker=str(row["ticker"]),
        decision=Decision(str(row["decision"])),
        score=int(row["score"]),
        created_at=str(row["created_at"]),
        market_price=float(row["market_price"]) if row["market_price"] is not None else None,
    )


def _round_optional(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def _evaluation_reason_from_row(row: sqlite3.Row) -> EvaluationReason:
    evidence = None
    if row["source_name"] and row["source_type"]:
        evidence = Evidence(
            source_name=str(row["source_name"]),
            source_type=SourceType(str(row["source_type"])),
            source_url=row["source_url"],
            observed_at=datetime.fromisoformat(row["observed_at"]) if row["observed_at"] else None,
            raw_reference=row["raw_reference"],
            confidence=float(row["confidence"]) if row["confidence"] is not None else None,
        )
    return EvaluationReason(
        risk_evaluation_id=int(row["risk_evaluation_id"]),
        ticker=str(row["ticker"]),
        reason_type=ReasonType(str(row["reason_type"])),
        reason_code=str(row["reason_code"]),
        message=str(row["message"]),
        severity=Severity(str(row["severity"])),
        evidence=evidence,
    )


def _ingestion_run_from_row(row: sqlite3.Row) -> IngestionRun:
    metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else None
    return IngestionRun(
        source_name=str(row["source_name"]),
        source_type=SourceType(str(row["source_type"])),
        started_at=datetime.fromisoformat(str(row["started_at"])),
        finished_at=datetime.fromisoformat(str(row["finished_at"])) if row["finished_at"] else None,
        status=IngestionStatus(str(row["status"])),
        records_seen=int(row["records_seen"]),
        records_saved=int(row["records_saved"]),
        error_message=row["error_message"],
        metadata_json=metadata,
    )


def _compliance_record_from_row(row: sqlite3.Row) -> ComplianceRecord:
    return ComplianceRecord(
        ticker=str(row["ticker"]),
        company_name=row["company_name"],
        issue=row["issue"],
        deficiency=row["deficiency"],
        notice_date=date.fromisoformat(str(row["notice_date"])) if row["notice_date"] else None,
        source_name=str(row["source_name"]),
        source_type=SourceType(str(row["source_type"])),
        source_url=row["source_url"],
        raw_reference=row["raw_reference"],
        observed_at=datetime.fromisoformat(str(row["observed_at"])),
    )


def _indicator_value_from_row(row: sqlite3.Row) -> IndicatorValue:
    evidence = None
    if row["source_name"] and row["source_type"]:
        evidence = Evidence(
            source_name=str(row["source_name"]),
            source_type=SourceType(str(row["source_type"])),
            observed_at=datetime.fromisoformat(str(row["observed_at"])) if row["observed_at"] else None,
        )
    return IndicatorValue(
        ticker=str(row["ticker"]),
        indicator_code=str(row["indicator_code"]),
        category=str(row["category"]),
        value=json.loads(row["value_json"]) if row["value_json"] is not None else None,
        unit=row["unit"],
        signal=IndicatorSignal(str(row["signal"])),
        severity=Severity(str(row["severity"])),
        interpretation=str(row["interpretation"] or ""),
        beginner_explanation=str(row["beginner_explanation"] or ""),
        evidence=evidence,
    )


def _trade_plan_from_row(row: sqlite3.Row) -> TradePlan:
    return TradePlan(
        ticker=str(row["ticker"]),
        direction=SetupDirection(str(row["direction"])),
        setup_grade=SetupGrade(str(row["setup_grade"])),
        setup_score=int(row["setup_score"]),
        entry_price=float(row["entry_price"]) if row["entry_price"] is not None else None,
        stop_price=float(row["stop_price"]) if row["stop_price"] is not None else None,
        target_price=float(row["target_price"]) if row["target_price"] is not None else None,
        risk_reward_ratio=float(row["risk_reward_ratio"]) if row["risk_reward_ratio"] is not None else None,
        max_loss_amount=float(row["max_loss_amount"]) if row["max_loss_amount"] is not None else None,
        max_loss_currency=str(row["max_loss_currency"] or "USD"),
        position_size=float(row["position_size"]) if row["position_size"] is not None else None,
        notional_value=float(row["notional_value"]) if row["notional_value"] is not None else None,
        decision=TradeDecision(str(row["decision"])),
        reasons=json.loads(row["reasons_json"]) if row["reasons_json"] else [],
        warnings=json.loads(row["warnings_json"]) if row["warnings_json"] else [],
        beginner_summary=str(row["beginner_summary"] or ""),
        policy_id=row["policy_id"],
        policy_version=row["policy_version"],
        setup_scoring_mode=row["setup_scoring_mode"],
        **_fx_payload(row),
    )


def _basket_allocation_from_row(row: sqlite3.Row) -> BasketAllocation:
    return BasketAllocation(
        ticker=str(row["ticker"]),
        setup_grade=SetupGrade(str(row["setup_grade"])),
        allocated_loss_amount=float(row["allocated_loss_amount"]),
        allocated_notional_value=float(row["allocated_notional_value"]),
        position_size=float(row["position_size"]),
        entry_price=float(row["entry_price"]),
        stop_price=float(row["stop_price"]),
        target_price=float(row["target_price"]) if row["target_price"] is not None else None,
        risk_reward_ratio=float(row["risk_reward_ratio"]) if row["risk_reward_ratio"] is not None else None,
        allocation_reason=str(row["allocation_reason"] or ""),
        **_fx_payload(row),
    )


def _blocked_candidate_from_row(row: sqlite3.Row) -> BasketCandidate:
    return BasketCandidate(
        ticker=str(row["ticker"]),
        setup_grade=SetupGrade(str(row["setup_grade"])),
        setup_score=0,
        decision=TradeDecision(str(row["decision"])),
        score=int(row["score"]),
        reasons=json.loads(row["reasons_json"]) if row["reasons_json"] else [],
        warnings=json.loads(row["warnings_json"]) if row["warnings_json"] else [],
    )


def _basket_plan_from_row(
    row: sqlite3.Row,
    allocations: list[BasketAllocation],
    blocked: list[BasketCandidate],
) -> BasketPlan:
    risk_summary = BasketRiskSummary.model_validate_json(str(row["risk_summary_json"]))
    allocation_candidates = [
        BasketCandidate(
            ticker=item.ticker,
            setup_grade=item.setup_grade,
            setup_score=0,
            decision=TradeDecision.PROPOSE,
            entry_price=item.entry_price,
            stop_price=item.stop_price,
            target_price=item.target_price,
            risk_reward_ratio=item.risk_reward_ratio,
            max_loss_amount=item.allocated_loss_amount,
            position_size=item.position_size,
            notional_value=item.allocated_notional_value,
            score=0,
            reasons=[],
            warnings=[],
        )
        for item in allocations
    ]
    return BasketPlan(
        basket_id=str(row["basket_id"]),
        basket_name=str(row["basket_name"]),
        mode=BasketMode(str(row["mode"])),
        policy=BasketPolicy.model_validate_json(str(row["policy_json"])),
        candidates=[*allocation_candidates, *blocked],
        allocations=allocations,
        blocked=blocked,
        risk_summary=risk_summary,
        decision=TradeDecision(str(row["decision"])),
        beginner_summary=str(row["beginner_summary"] or ""),
        created_at=datetime.fromisoformat(str(row["created_at"])),
        policy_id=row["policy_id"],
        policy_version=row["policy_version"],
        basket_scoring_mode=str(row["basket_scoring_mode"] or "FIXED_RULES"),
        account_currency=risk_summary.account_currency, trading_currency=risk_summary.trading_currency,
        fx_rate=risk_summary.fx_rate, fx_date=risk_summary.fx_date,
        total_notional_account=risk_summary.total_notional_account,
        total_notional_trading=risk_summary.total_notional_trading,
        total_max_loss_account=risk_summary.total_max_loss_account,
        total_max_loss_trading=risk_summary.total_max_loss_trading,
        fx_warnings_json=risk_summary.fx_warnings_json,
    )


def _paper_trade_from_row(row: sqlite3.Row) -> PaperTrade:
    return PaperTrade(
        trade_id=str(row["trade_id"]),
        basket_id=str(row["basket_id"]),
        ticker=str(row["ticker"]),
        direction=SetupDirection(str(row["direction"])),
        setup_grade=SetupGrade(str(row["setup_grade"])),
        entry_price=float(row["entry_price"]),
        stop_price=float(row["stop_price"]),
        target_price=float(row["target_price"]) if row["target_price"] is not None else None,
        position_size=float(row["position_size"]),
        allocated_loss_amount=float(row["allocated_loss_amount"]),
        notional_value=float(row["notional_value"]),
        entry_date=date.fromisoformat(str(row["entry_date"])),
        exit_date=date.fromisoformat(str(row["exit_date"])) if row["exit_date"] else None,
        exit_price=float(row["exit_price"]) if row["exit_price"] is not None else None,
        exit_reason=ExitReason(str(row["exit_reason"])) if row["exit_reason"] else None,
        realized_pnl=float(row["realized_pnl"]) if row["realized_pnl"] is not None else None,
        realized_return_pct=float(row["realized_return_pct"]) if row["realized_return_pct"] is not None else None,
        status=PaperTradeStatus(str(row["status"])),
        created_at=datetime.fromisoformat(str(row["created_at"])),
        policy_id=row["policy_id"],
        policy_version=row["policy_version"],
        basket_scoring_mode=row["basket_scoring_mode"],
        **_fx_payload(row),
    )


def _basket_backtest_result_from_row(row: sqlite3.Row) -> BasketBacktestResult:
    return BasketBacktestResult(
        basket_id=str(row["basket_id"]),
        horizon_days=int(row["horizon_days"]),
        entry_date=date.fromisoformat(str(row["entry_date"])),
        exit_date=date.fromisoformat(str(row["exit_date"])) if row["exit_date"] else None,
        total_notional_value=float(row["total_notional_value"]),
        total_allocated_loss=float(row["total_allocated_loss"]),
        realized_pnl=float(row["realized_pnl"]),
        realized_return_pct=float(row["realized_return_pct"]),
        max_drawdown=float(row["max_drawdown"]) if row["max_drawdown"] is not None else None,
        max_gain=float(row["max_gain"]) if row["max_gain"] is not None else None,
        win_count=int(row["win_count"]),
        loss_count=int(row["loss_count"]),
        flat_count=int(row["flat_count"]),
        no_data_count=int(row["no_data_count"]),
        closed_trade_count=int(row["closed_trade_count"]),
        outcome=BacktestOutcome(str(row["outcome"])),
        created_at=datetime.fromisoformat(str(row["created_at"])),
        policy_id=row["policy_id"],
        policy_version=row["policy_version"],
        basket_scoring_mode=row["basket_scoring_mode"],
        **_fx_payload(row),
    )


def _strategy_policy_from_row(row: sqlite3.Row) -> StrategyPolicy:
    return StrategyPolicy(
        policy_id=str(row["policy_id"]),
        version=str(row["version"]),
        status=StrategyPolicyStatus(str(row["status"])),
        weights=json.loads(str(row["weights_json"])),
        setup_thresholds=json.loads(str(row["setup_thresholds_json"])),
        basket_rules=json.loads(str(row["basket_rules_json"])),
        risk_overrides=json.loads(str(row["risk_overrides_json"])),
        created_by=StrategyPolicyCreator(str(row["created_by"])),
        reason=str(row["reason"] or ""),
        parent_policy_id=row["parent_policy_id"],
        parent_version=row["parent_version"],
        created_at=datetime.fromisoformat(str(row["created_at"])),
    )


def _strategy_experiment_from_row(row: sqlite3.Row) -> StrategyExperiment:
    return StrategyExperiment(
        experiment_id=str(row["experiment_id"]),
        baseline_policy_id=str(row["baseline_policy_id"]),
        baseline_version=str(row["baseline_version"]),
        candidate_policy_id=str(row["candidate_policy_id"]),
        candidate_version=str(row["candidate_version"]),
        evaluation_mode=StrategyEvaluationMode(str(row["evaluation_mode"])),
        horizon_days=int(row["horizon_days"]),
        sample_count=int(row["sample_count"]),
        avg_return_pct=float(row["avg_return_pct"]) if row["avg_return_pct"] is not None else None,
        median_return_pct=float(row["median_return_pct"]) if row["median_return_pct"] is not None else None,
        win_rate=float(row["win_rate"]) if row["win_rate"] is not None else None,
        loss_rate=float(row["loss_rate"]) if row["loss_rate"] is not None else None,
        profit_factor=float(row["profit_factor"]) if row["profit_factor"] is not None else None,
        avg_max_drawdown=float(row["avg_max_drawdown"]) if row["avg_max_drawdown"] is not None else None,
        avg_realized_pnl=float(row["avg_realized_pnl"]) if row["avg_realized_pnl"] is not None else None,
        objective_score=float(row["objective_score"]),
        recommendation=StrategyRecommendation(str(row["recommendation"])),
        notes=json.loads(row["notes_json"]) if row["notes_json"] else [],
        created_at=datetime.fromisoformat(str(row["created_at"])),
    )


def _strategy_memory_from_row(row: sqlite3.Row) -> StrategyMemory:
    return StrategyMemory(
        memory_id=str(row["memory_id"]),
        basket_id=row["basket_id"],
        ticker=row["ticker"],
        setup_grade=row["setup_grade"],
        decision=str(row["decision"]),
        features_json=json.loads(str(row["features_json"])),
        outcome=row["outcome"],
        realized_return_pct=float(row["realized_return_pct"]) if row["realized_return_pct"] is not None else None,
        realized_pnl=float(row["realized_pnl"]) if row["realized_pnl"] is not None else None,
        max_drawdown=float(row["max_drawdown"]) if row["max_drawdown"] is not None else None,
        policy_id=row["policy_id"],
        policy_version=row["policy_version"],
        created_at=datetime.fromisoformat(str(row["created_at"])),
    )


def _replay_run_from_row(row: sqlite3.Row) -> ReplayRun:
    return ReplayRun(
        run_id=str(row["run_id"]),
        status=ReplayRunStatus(str(row["status"])),
        snapshot_mode=ReplaySnapshotMode(str(row["snapshot_mode"])),
        source_type=str(row["source_type"]),
        source_basket_id=row["source_basket_id"],
        as_of_date=date.fromisoformat(str(row["as_of_date"])) if row["as_of_date"] else None,
        policy_id=row["policy_id"],
        policy_version=row["policy_version"],
        notes=json.loads(str(row["notes_json"])),
        created_at=datetime.fromisoformat(str(row["created_at"])),
    )


def _replay_basket_snapshot_from_row(row: sqlite3.Row) -> ReplayBasketSnapshot:
    return ReplayBasketSnapshot(
        run_id=str(row["run_id"]), basket_id=str(row["basket_id"]), decision=str(row["decision"]),
        policy_id=row["policy_id"], policy_version=row["policy_version"], scoring_mode=str(row["scoring_mode"]),
        snapshot_json=json.loads(str(row["snapshot_json"])),
    )


def _replay_outcome_snapshot_from_row(row: sqlite3.Row) -> ReplayOutcomeSnapshot:
    return ReplayOutcomeSnapshot(
        run_id=str(row["run_id"]), basket_id=str(row["basket_id"]), outcome=str(row["outcome"]),
        realized_return_pct=float(row["realized_return_pct"]),
        snapshot_json=json.loads(str(row["snapshot_json"])),
    )


def _policy_replay_result_from_row(row: sqlite3.Row) -> PolicyReplayResult:
    return PolicyReplayResult(
        policy_replay_id=str(row["policy_replay_id"]), source_replay_run_id=str(row["source_replay_run_id"]),
        replay_mode=PolicyReplayMode(str(row["replay_mode"])), policy_id=str(row["policy_id"]),
        policy_version=str(row["policy_version"]), as_of_date=date.fromisoformat(str(row["as_of_date"])),
        horizon_days=int(row["horizon_days"]), candidate_count=int(row["candidate_count"]),
        trade_plan_count=int(row["trade_plan_count"]), basket_id=row["basket_id"],
        total_notional_value=float(row["total_notional_value"]) if row["total_notional_value"] is not None else None,
        total_allocated_loss=float(row["total_allocated_loss"]) if row["total_allocated_loss"] is not None else None,
        realized_pnl=float(row["realized_pnl"]) if row["realized_pnl"] is not None else None,
        realized_return_pct=float(row["realized_return_pct"]) if row["realized_return_pct"] is not None else None,
        win_count=int(row["win_count"]) if row["win_count"] is not None else None,
        loss_count=int(row["loss_count"]) if row["loss_count"] is not None else None,
        no_data_count=int(row["no_data_count"]) if row["no_data_count"] is not None else None,
        outcome=row["outcome"], objective_score=float(row["objective_score"]) if row["objective_score"] is not None else None,
        status=PolicyReplayStatus(str(row["status"])), notes=json.loads(row["notes_json"]) if row["notes_json"] else [],
        created_at=datetime.fromisoformat(str(row["created_at"])),
    )


def _policy_comparison_result_from_row(row: sqlite3.Row) -> PolicyComparisonResult:
    return PolicyComparisonResult(
        comparison_id=str(row["comparison_id"]), source_replay_run_id=str(row["source_replay_run_id"]),
        baseline_policy_id=str(row["baseline_policy_id"]), baseline_policy_version=str(row["baseline_policy_version"]),
        candidate_policy_id=str(row["candidate_policy_id"]), candidate_policy_version=str(row["candidate_policy_version"]),
        baseline_replay_id=row["baseline_replay_id"], candidate_replay_id=row["candidate_replay_id"],
        baseline_return_pct=float(row["baseline_return_pct"]) if row["baseline_return_pct"] is not None else None,
        candidate_return_pct=float(row["candidate_return_pct"]) if row["candidate_return_pct"] is not None else None,
        return_delta_pct=float(row["return_delta_pct"]) if row["return_delta_pct"] is not None else None,
        baseline_objective_score=float(row["baseline_objective_score"]) if row["baseline_objective_score"] is not None else None,
        candidate_objective_score=float(row["candidate_objective_score"]) if row["candidate_objective_score"] is not None else None,
        objective_delta=float(row["objective_delta"]) if row["objective_delta"] is not None else None,
        recommendation=StrategyRecommendation(str(row["recommendation"])),
        notes=json.loads(row["notes_json"]) if row["notes_json"] else [],
        created_at=datetime.fromisoformat(str(row["created_at"])),
    )


def _notification_run_from_row(row: sqlite3.Row) -> NotificationRun:
    return NotificationRun(
        notification_run_id=str(row["notification_run_id"]), source_type=str(row["source_type"]),
        source_id=str(row["source_id"]), channel_type=NotificationChannelType(str(row["channel_type"])),
        status=NotificationRunStatus(str(row["status"])), message_count=int(row["message_count"]),
        delivered_count=int(row["delivered_count"]), skipped_duplicate_count=int(row["skipped_duplicate_count"]),
        failed_count=int(row["failed_count"]), output_path=row["output_path"],
        warnings=json.loads(row["warnings_json"]) if row["warnings_json"] else [],
        errors=json.loads(row["errors_json"]) if row["errors_json"] else [],
        created_at=datetime.fromisoformat(str(row["created_at"])),
        completed_at=datetime.fromisoformat(str(row["completed_at"])) if row["completed_at"] else None,
    )


def _notification_message_from_row(row: sqlite3.Row) -> NotificationMessage:
    return NotificationMessage(
        notification_id=str(row["notification_id"]), source_type=str(row["source_type"]),
        source_id=str(row["source_id"]), channel_type=NotificationChannelType(str(row["channel_type"])),
        severity=NotificationSeverity(str(row["severity"])), title=str(row["title"]), message=str(row["message"]),
        metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {}, dedupe_key=str(row["dedupe_key"]),
        created_at=datetime.fromisoformat(str(row["created_at"])),
        delivered_at=datetime.fromisoformat(str(row["delivered_at"])) if row["delivered_at"] else None,
        delivery_status=str(row["delivery_status"]), error=row["error"],
    )


def _dashboard_build_from_row(row: sqlite3.Row) -> DashboardBuildResult:
    return DashboardBuildResult(
        dashboard_id=str(row["dashboard_id"]), dashboard_type=DashboardType(str(row["dashboard_type"])),
        as_of_date=date.fromisoformat(str(row["as_of_date"])) if row["as_of_date"] else None,
        source_id=row["source_id"], status=DashboardBuildStatus(str(row["status"])),
        output_path=row["output_path"], section_count=int(row["section_count"]),
        warnings=json.loads(row["warnings_json"]) if row["warnings_json"] else [],
        errors=json.loads(row["errors_json"]) if row["errors_json"] else [],
        generated_at=datetime.fromisoformat(str(row["generated_at"])),
    )


def _provider_pack_run_from_row(row: sqlite3.Row) -> ProviderPackRun:
    return ProviderPackRun(
        provider_pack_run_id=str(row["provider_pack_run_id"]),
        provider_pack_type=ProviderPackType(str(row["provider_pack_type"])),
        as_of_date=date.fromisoformat(str(row["as_of_date"])),
        status=ProviderPackRunStatus(str(row["status"])),
        connector_run_ids=json.loads(row["connector_run_ids_json"]) if row["connector_run_ids_json"] else [],
        normalize_run_id=row["normalize_run_id"],
        import_run_id=row["import_run_id"],
        output_paths=json.loads(row["output_paths_json"]) if row["output_paths_json"] else [],
        warnings=json.loads(row["warnings_json"]) if row["warnings_json"] else [],
        errors=json.loads(row["errors_json"]) if row["errors_json"] else [],
        created_at=datetime.fromisoformat(str(row["created_at"])),
        completed_at=datetime.fromisoformat(str(row["completed_at"])) if row["completed_at"] else None,
    )


def _realtime_monitor_run_from_row(row: sqlite3.Row) -> RealtimeMonitorRun:
    return RealtimeMonitorRun(
        realtime_monitor_run_id=str(row["realtime_monitor_run_id"]),
        as_of=datetime.fromisoformat(str(row["as_of"])),
        status=RealtimeMonitorRunStatus(str(row["status"])),
        provider_name=str(row["provider_name"]),
        universe_count=int(row["universe_count"]),
        processed_event_count=int(row["processed_event_count"]),
        candidate_count=int(row["candidate_count"]),
        hot_watchlist_count=int(row["hot_watchlist_count"]),
        warnings=json.loads(row["warnings_json"]) if row["warnings_json"] else [],
        errors=json.loads(row["errors_json"]) if row["errors_json"] else [],
        created_at=datetime.fromisoformat(str(row["created_at"])),
        completed_at=datetime.fromisoformat(str(row["completed_at"])) if row["completed_at"] else None,
    )


def _watchlist_entry_from_row(row: sqlite3.Row) -> WatchlistEntry:
    return WatchlistEntry(
        symbol=str(row["symbol"]),
        region=MarketRegion(str(row["region"])),
        status=WatchlistStatus(str(row["status"])),
        first_seen_at=datetime.fromisoformat(str(row["first_seen_at"])),
        last_seen_at=datetime.fromisoformat(str(row["last_seen_at"])),
        promotion_reason=str(row["promotion_reason"]),
        score=float(row["score"]),
        metrics_json=str(row["metrics_json"] or "{}"),
        warnings=json.loads(row["warnings_json"]) if row["warnings_json"] else [],
    )
