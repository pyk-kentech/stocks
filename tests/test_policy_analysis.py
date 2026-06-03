from __future__ import annotations

from stock_risk_mcp.policy_analysis import (
    aggregate_hard_block_performance,
    aggregate_performance,
    generate_recommendations,
    normalize_hard_block_reason,
    score_bucket,
)


def test_score_bucket_classification() -> None:
    assert score_bucket(0) == "0_39"
    assert score_bucket(59) == "40_59"
    assert score_bucket(60) == "60_79"
    assert score_bucket(100) == "80_100"


def test_aggregate_performance_calculates_average_median_and_rates() -> None:
    rows = [
        {"return_pct": 10, "max_drawdown_pct": -2, "max_gain_pct": 12, "outcome": "WIN"},
        {"return_pct": -4, "max_drawdown_pct": -8, "max_gain_pct": 3, "outcome": "LOSS"},
        {"return_pct": 1, "max_drawdown_pct": -3, "max_gain_pct": 5, "outcome": "FLAT"},
    ]

    result = aggregate_performance(rows, include_extremes=True)

    assert result["count"] == 3
    assert result["avg_return_pct"] == 2.3333
    assert result["median_return_pct"] == 1.0
    assert result["win_rate"] == 0.3333
    assert result["loss_rate"] == 0.3333
    assert result["best_return_pct"] == 10.0
    assert result["worst_return_pct"] == -4.0


def test_hard_block_reason_normalization_and_aggregation() -> None:
    rows = [
        {
            "hard_block_reasons": ["dilution risk HIGH"],
            "return_pct": -10,
            "max_drawdown_pct": -20,
            "max_gain_pct": 2,
            "outcome": "LOSS",
        },
        {
            "hard_block_reasons": ["dilution risk HIGH"],
            "return_pct": 5,
            "max_drawdown_pct": -4,
            "max_gain_pct": 8,
            "outcome": "WIN",
        },
    ]

    result = aggregate_hard_block_performance(rows)

    assert normalize_hard_block_reason("Nasdaq noncompliant") == "NASDAQ_NONCOMPLIANT"
    assert result["DILUTION_RISK_HIGH"]["count"] == 2
    assert result["DILUTION_RISK_HIGH"]["avg_return_pct"] == -2.5
    assert result["DILUTION_RISK_HIGH"]["win_rate"] == 0.5
    assert result["DILUTION_RISK_HIGH"]["worst_return_pct"] == -10.0


def test_recommendations_follow_policy_rules() -> None:
    recommendations = generate_recommendations(
        decision_performance={
            "ALLOW": {"avg_return_pct": 1, "win_rate": 0.4, "avg_max_drawdown_pct": -4},
            "REVIEW": {"avg_return_pct": 3, "win_rate": 0.5, "avg_max_drawdown_pct": -5},
            "BLOCK": {"avg_return_pct": 4, "win_rate": 0.6, "avg_max_drawdown_pct": -16},
        },
        score_bucket_performance={
            "60_79": {"avg_return_pct": 6, "avg_max_drawdown_pct": -4},
            "80_100": {"avg_return_pct": 2, "avg_max_drawdown_pct": -3},
        },
        hard_block_performance={
            "dilution_risk_high": {"count": 5, "avg_return_pct": -8, "win_rate": 0.2},
            "5d_return_too_high": {"count": 5, "avg_return_pct": 5, "win_rate": 0.6},
        },
    )

    assert "dilution_risk_high 차단 규칙은 유효해 보입니다." in recommendations
    assert "5d_return_too_high 차단 규칙은 너무 보수적일 수 있습니다." in recommendations
    assert any("ALLOW 판정 기준" in item for item in recommendations)
    assert any("과도하게 보수적" in item for item in recommendations)
    assert any("소프트 점수" in item for item in recommendations)
    assert any("BLOCK 구간은 손실 변동성이 큽니다" in item for item in recommendations)
