from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stock_risk_mcp.policy_analysis import (
    SCORE_BUCKETS,
    aggregate_hard_block_performance,
    aggregate_performance,
    generate_recommendations,
    score_bucket,
)
from stock_risk_mcp.repository import RiskRepository


class ReportService:
    def __init__(self, repository: RiskRepository | None = None, db_path: str | Path | None = None) -> None:
        if repository is None and db_path is None:
            raise ValueError("Either repository or db_path must be provided.")
        self.repository = repository or RiskRepository(db_path or "")

    def decision_performance(self) -> dict[str, Any]:
        rows = self._report_rows()
        grouped = {decision: [] for decision in ("ALLOW", "REVIEW", "BLOCK")}
        for row in rows:
            grouped.setdefault(str(row["decision"]), []).append(row)
        return {
            decision: aggregate_performance(decision_rows, include_extremes=True)
            for decision, decision_rows in grouped.items()
            if decision_rows
        }

    def score_bucket_performance(self) -> dict[str, Any]:
        rows = self._report_rows()
        grouped = {name: [] for name, _, _ in SCORE_BUCKETS}
        for row in rows:
            grouped[score_bucket(int(row["score"]))].append(row)
        return {bucket: aggregate_performance(bucket_rows) for bucket, bucket_rows in grouped.items() if bucket_rows}

    def hard_block_performance(self) -> dict[str, Any]:
        return aggregate_hard_block_performance(self._report_rows())

    def generate_policy_recommendations(self) -> list[str]:
        return generate_recommendations(
            decision_performance=self.decision_performance(),
            score_bucket_performance=self.score_bucket_performance(),
            hard_block_performance=self.hard_block_performance(),
        )

    def full_report(self) -> dict[str, Any]:
        decision = self.decision_performance()
        score_buckets = self.score_bucket_performance()
        hard_blocks = self.hard_block_performance()
        return {
            "decision_performance": decision,
            "score_bucket_performance": score_buckets,
            "hard_block_performance": hard_blocks,
            "policy_recommendations": generate_recommendations(decision, score_buckets, hard_blocks),
        }

    def _report_rows(self) -> list[dict[str, Any]]:
        with self.repository._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    br.risk_evaluation_id,
                    br.ticker,
                    br.decision,
                    br.score,
                    br.return_pct,
                    br.max_drawdown_pct,
                    br.max_gain_pct,
                    br.outcome,
                    re.result_json,
                    re.market_snapshot_id,
                    re.company_risk_id,
                    GROUP_CONCAT(er.reason_code, '||') AS normalized_hard_block_codes,
                    ms.market_cap_usd,
                    ms.avg_dollar_volume_20d,
                    cr.dilution_risk,
                    cr.nasdaq_noncompliant
                FROM backtest_results br
                JOIN risk_evaluations re ON re.id = br.risk_evaluation_id
                LEFT JOIN market_snapshots ms ON ms.id = re.market_snapshot_id
                LEFT JOIN company_risks cr ON cr.id = re.company_risk_id
                LEFT JOIN evaluation_reasons er
                    ON er.risk_evaluation_id = re.id
                    AND er.reason_type = 'HARD_BLOCK'
                GROUP BY br.id
                ORDER BY br.id ASC
                """
            ).fetchall()
        return [_row_to_report_dict(row) for row in rows]


def _row_to_report_dict(row: Any) -> dict[str, Any]:
    result_payload = json.loads(row["result_json"])
    normalized_codes = str(row["normalized_hard_block_codes"]).split("||") if row["normalized_hard_block_codes"] else []
    return {
        "risk_evaluation_id": int(row["risk_evaluation_id"]),
        "ticker": str(row["ticker"]),
        "decision": str(row["decision"]),
        "score": int(row["score"]),
        "return_pct": _float_or_none(row["return_pct"]),
        "max_drawdown_pct": _float_or_none(row["max_drawdown_pct"]),
        "max_gain_pct": _float_or_none(row["max_gain_pct"]),
        "outcome": str(row["outcome"]),
        "hard_block_reasons": normalized_codes or list(result_payload.get("hard_blocks", [])),
    }


def _float_or_none(value: Any) -> float | None:
    return float(value) if value is not None else None
