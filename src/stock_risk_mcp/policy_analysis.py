from __future__ import annotations

from statistics import median
from typing import Any

from stock_risk_mcp.reason_codes import normalize_legacy_hard_block_reason


SCORE_BUCKETS: tuple[tuple[str, int, int], ...] = (
    ("0_39", 0, 39),
    ("40_59", 40, 59),
    ("60_79", 60, 79),
    ("80_100", 80, 100),
)


def score_bucket(score: int) -> str:
    for name, lower, upper in SCORE_BUCKETS:
        if lower <= score <= upper:
            return name
    raise ValueError(f"Score must be between 0 and 100: {score}")


def aggregate_performance(rows: list[dict[str, Any]], include_extremes: bool = False) -> dict[str, Any]:
    if not rows:
        base: dict[str, Any] = {
            "count": 0,
            "avg_return_pct": None,
            "median_return_pct": None,
            "win_rate": None,
            "loss_rate": None,
            "avg_max_drawdown_pct": None,
            "avg_max_gain_pct": None,
        }
        if include_extremes:
            base["best_return_pct"] = None
            base["worst_return_pct"] = None
        return base

    returns = _not_none(row.get("return_pct") for row in rows)
    drawdowns = _not_none(row.get("max_drawdown_pct") for row in rows)
    gains = _not_none(row.get("max_gain_pct") for row in rows)

    result = {
        "count": len(rows),
        "avg_return_pct": _avg(returns),
        "median_return_pct": _round(median(returns)) if returns else None,
        "win_rate": _rate(rows, "WIN"),
        "loss_rate": _rate(rows, "LOSS"),
        "avg_max_drawdown_pct": _avg(drawdowns),
        "avg_max_gain_pct": _avg(gains),
    }
    if include_extremes:
        result["best_return_pct"] = _round(max(returns)) if returns else None
        result["worst_return_pct"] = _round(min(returns)) if returns else None
    return result


def aggregate_hard_block_performance(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        for reason in row.get("hard_block_reasons", []):
            grouped.setdefault(normalize_hard_block_reason(str(reason)), []).append(row)
    return {
        reason: {
            "count": stats["count"],
            "avg_return_pct": stats["avg_return_pct"],
            "win_rate": stats["win_rate"],
            "avg_max_drawdown_pct": stats["avg_max_drawdown_pct"],
            "worst_return_pct": stats["worst_return_pct"],
        }
        for reason, stats in (
            (reason, aggregate_performance(reason_rows, include_extremes=True))
            for reason, reason_rows in sorted(grouped.items())
        )
    }


def normalize_hard_block_reason(reason: str) -> str:
    if reason.isupper() and "_" in reason:
        return reason
    return normalize_legacy_hard_block_reason(reason)


def generate_recommendations(
    decision_performance: dict[str, Any],
    score_bucket_performance: dict[str, Any],
    hard_block_performance: dict[str, Any],
) -> list[str]:
    recommendations: list[str] = []

    for reason, stats in hard_block_performance.items():
        if stats["count"] >= 5 and stats["avg_return_pct"] is not None and stats["avg_return_pct"] <= -5:
            recommendations.append(f"{reason} 차단 규칙은 유효해 보입니다.")
        if (
            stats["count"] >= 5
            and stats["avg_return_pct"] is not None
            and stats["avg_return_pct"] >= 3
            and stats["win_rate"] is not None
            and stats["win_rate"] >= 0.55
        ):
            recommendations.append(f"{reason} 차단 규칙은 너무 보수적일 수 있습니다.")

    allow = decision_performance.get("ALLOW")
    review = decision_performance.get("REVIEW")
    block = decision_performance.get("BLOCK")
    if _metric(allow, "avg_return_pct") is not None and _metric(review, "avg_return_pct") is not None:
        if _metric(allow, "avg_return_pct") < _metric(review, "avg_return_pct"):
            recommendations.append("ALLOW 판정 기준이 약할 수 있습니다. score threshold를 높이는 것을 검토하십시오.")
    if _metric(block, "avg_return_pct") is not None and _metric(block, "avg_return_pct") > 0:
        if _metric(block, "win_rate") is not None and _metric(block, "win_rate") >= 0.5:
            recommendations.append("차단 규칙이 과도하게 보수적일 수 있습니다.")

    high_bucket = score_bucket_performance.get("80_100")
    mid_bucket = score_bucket_performance.get("60_79")
    if _metric(high_bucket, "avg_return_pct") is not None and _metric(mid_bucket, "avg_return_pct") is not None:
        if _metric(high_bucket, "avg_return_pct") < _metric(mid_bucket, "avg_return_pct"):
            recommendations.append("소프트 점수 가중치가 실제 성과와 잘 맞지 않을 수 있습니다.")

    for label, stats in {**decision_performance, **score_bucket_performance}.items():
        drawdown = _metric(stats, "avg_max_drawdown_pct")
        if drawdown is not None and drawdown <= -15:
            recommendations.append(f"{label} 구간은 손실 변동성이 큽니다. 포지션 크기를 줄이는 것을 검토하십시오.")

    return recommendations


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return _round(sum(values) / len(values))


def _rate(rows: list[dict[str, Any]], outcome: str) -> float:
    if not rows:
        return 0.0
    return _round(sum(1 for row in rows if row.get("outcome") == outcome) / len(rows))


def _not_none(values: Any) -> list[float]:
    return [float(value) for value in values if value is not None]


def _round(value: float) -> float:
    return round(float(value), 4)


def _metric(stats: dict[str, Any] | None, key: str) -> float | None:
    if not stats:
        return None
    value = stats.get(key)
    return float(value) if value is not None else None
