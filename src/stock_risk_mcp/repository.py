from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from stock_risk_mcp.compliance import ComplianceRecord
from stock_risk_mcp.database import connect_db, create_schema
from stock_risk_mcp.models import (
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
            "data_sources",
            "ingestion_runs",
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


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


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
