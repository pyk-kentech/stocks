from __future__ import annotations

from statistics import fmean

from stock_risk_mcp.paper_fill_engine import evaluate_long_exit, should_fill_long_entry
from stock_risk_mcp.walk_forward_policy_models import (
    CandidatePolicyComparison,
    PolicyWindowMetrics,
    ReplayPolicyConfig,
    WalkForwardPolicyFixture,
    WalkForwardPolicyReport,
    WindowPolicyComparison,
    WindowReplayResult,
)
from stock_risk_mcp.walk_forward_promotion_gate import decide_promotion
from stock_risk_mcp.walk_forward_window_split import build_walk_forward_windows


def build_walk_forward_policy_report(fixture: WalkForwardPolicyFixture, fixture_checksum: str) -> WalkForwardPolicyReport:
    windows = build_walk_forward_windows(fixture)
    price_paths = {path.price_path_id: path for path in fixture.price_paths}
    window_results: list[WindowReplayResult] = []
    baseline_by_window: list[PolicyWindowMetrics] = []
    candidates_by_id: dict[str, list[PolicyWindowMetrics]] = {policy.policy_id: [] for policy in fixture.candidate_policies}
    for window in windows:
        baseline_metrics = evaluate_policy_window(fixture.baseline_policy, window.eval_rows, price_paths, window.train_window_dates, window.eval_window_dates)
        baseline_by_window.append(baseline_metrics)
        candidate_metrics = []
        for candidate in fixture.candidate_policies:
            metrics = evaluate_policy_window(candidate, window.eval_rows, price_paths, window.train_window_dates, window.eval_window_dates)
            candidate_metrics.append(metrics)
            candidates_by_id[candidate.policy_id].append(metrics)
        window_results.append(
            WindowReplayResult(
                train_window_dates=window.train_window_dates,
                eval_window_dates=window.eval_window_dates,
                baseline=baseline_metrics,
                candidate_results=candidate_metrics,
            )
        )

    candidate_comparisons = [
        build_candidate_comparison(fixture, policy, baseline_by_window, candidates_by_id[policy.policy_id])
        for policy in fixture.candidate_policies
    ]
    return WalkForwardPolicyReport(
        fixture_checksum=fixture_checksum,
        run_id=fixture.run_id,
        created_at=fixture.created_at,
        baseline_policy=fixture.baseline_policy,
        candidate_policies=fixture.candidate_policies,
        window_results=window_results,
        candidate_comparisons=candidate_comparisons,
    )


def evaluate_policy_window(policy: ReplayPolicyConfig, eval_rows, price_paths, train_window_dates, eval_window_dates) -> PolicyWindowMetrics:
    replay_row_count = len(eval_rows)
    total_return_pct = 0.0
    pnl_values: list[float] = []
    win_count = 0
    blocked_count = 0
    missing_data_count = 0
    exposure_bars = 0
    total_bars = 0
    safety_violation = is_unsafe_policy(policy)
    drawdowns: list[float] = []
    for row in eval_rows:
        path = price_paths.get(row.price_path_id)
        if path is None:
            missing_data_count += 1
            continue
        total_bars += len(path.bars)
        if safety_violation:
            blocked_count += 1
            continue
        if row.setup_grade not in policy.allowed_setup_grades:
            blocked_count += 1
            continue
        score = (
            row.technical_score * policy.score_weights.technical
            + row.discovery_score * policy.score_weights.discovery
            + row.llm_score * policy.score_weights.llm
        )
        risk_reward = (row.target_reference - row.entry_reference) / abs(row.entry_reference - row.stop_reference)
        if score < policy.minimum_score_threshold or risk_reward < policy.minimum_risk_reward:
            blocked_count += 1
            continue
        entry_bar = next((bar for bar in path.bars if bar.timestamp >= row.timestamp and should_fill_long_entry(row.entry_reference, bar)), None)
        if entry_bar is None:
            blocked_count += 1
            continue
        quantity = 1 + int(max(score - policy.minimum_score_threshold, 0) // 5)
        exposure_bars += 1
        for bar in [bar for bar in path.bars if bar.timestamp >= entry_bar.timestamp]:
            exposure_bars += 1
            decision = evaluate_long_exit(
                type("Position", (), {
                    "stop_price": row.stop_reference,
                    "target_price": row.target_reference,
                })(),
                bar,
            )
            if decision is None:
                continue
            exit_reason, exit_price = decision
            pnl = (exit_price - row.entry_reference) * quantity
            pnl_values.append(pnl)
            total_return_pct += pnl
            if pnl > 0:
                win_count += 1
            if exit_reason == "STOP_HIT":
                drawdowns.append(abs(pnl))
            break
        else:
            final_close = path.bars[-1].close
            pnl = (final_close - row.entry_reference) * quantity
            pnl_values.append(pnl)
            total_return_pct += pnl
            if pnl > 0:
                win_count += 1
    trade_count = len(pnl_values)
    losses = [value for value in pnl_values if value < 0]
    profits = [value for value in pnl_values if value > 0]
    return PolicyWindowMetrics(
        policy_id=policy.policy_id,
        train_window_dates=train_window_dates,
        eval_window_dates=eval_window_dates,
        replay_row_count=replay_row_count,
        total_return_pct=total_return_pct,
        max_drawdown_pct=max(drawdowns, default=0.0),
        win_rate=(win_count / trade_count * 100) if trade_count else None,
        profit_factor=(sum(profits) / abs(sum(losses))) if losses else None,
        expectancy_amount=fmean(pnl_values) if pnl_values else None,
        exposure_time_pct=(exposure_bars / total_bars * 100) if total_bars else 0.0,
        trade_count=trade_count,
        missing_data_rate=(missing_data_count / replay_row_count) if replay_row_count else 0.0,
        blocked_rate=(blocked_count / replay_row_count) if replay_row_count else 0.0,
        missing_data_count=missing_data_count,
        blocked_count=blocked_count,
        safety_violation=safety_violation,
    )


def build_candidate_comparison(fixture, policy, baseline_metrics, candidate_metrics):
    window_comparisons = []
    deltas = []
    for baseline, candidate in zip(baseline_metrics, candidate_metrics):
        delta = candidate.total_return_pct - baseline.total_return_pct
        deltas.append(delta)
        window_comparisons.append(
            WindowPolicyComparison(
                policy_id=policy.policy_id,
                eval_window_dates=candidate.eval_window_dates,
                baseline_total_return_pct=baseline.total_return_pct,
                candidate_total_return_pct=candidate.total_return_pct,
                return_delta_pct=delta,
                baseline_trade_count=baseline.trade_count,
                candidate_trade_count=candidate.trade_count,
            )
        )
    comparison = CandidatePolicyComparison(
        policy_id=policy.policy_id,
        window_comparisons=window_comparisons,
        aggregate_baseline_metrics=aggregate_metrics(fixture.baseline_policy.policy_id, baseline_metrics),
        aggregate_candidate_metrics=aggregate_metrics(policy.policy_id, candidate_metrics),
        aggregate_return_delta_pct=sum(deltas),
        stability_score=stability_score(deltas),
        promotion_decision="KEEP_BASELINE_POLICY",
    )
    return decide_promotion(comparison, fixture.promotion_gates)


def aggregate_metrics(policy_id: str, metrics: list[PolicyWindowMetrics]) -> PolicyWindowMetrics:
    total_rows = sum(item.replay_row_count for item in metrics)
    trade_count = sum(item.trade_count for item in metrics)
    return PolicyWindowMetrics(
        policy_id=policy_id,
        train_window_dates=[],
        eval_window_dates=[],
        replay_row_count=total_rows,
        total_return_pct=sum(item.total_return_pct for item in metrics),
        max_drawdown_pct=max((item.max_drawdown_pct for item in metrics), default=0.0),
        win_rate=(sum((item.win_rate or 0) * item.trade_count for item in metrics) / trade_count) if trade_count else None,
        profit_factor=None if any(item.profit_factor is None for item in metrics) else fmean(item.profit_factor for item in metrics if item.profit_factor is not None),
        expectancy_amount=(sum((item.expectancy_amount or 0) * item.trade_count for item in metrics) / trade_count) if trade_count else None,
        exposure_time_pct=fmean(item.exposure_time_pct for item in metrics) if metrics else 0.0,
        trade_count=trade_count,
        missing_data_rate=(sum(item.missing_data_count for item in metrics) / total_rows) if total_rows else 0.0,
        blocked_rate=(sum(item.blocked_count for item in metrics) / total_rows) if total_rows else 0.0,
        missing_data_count=sum(item.missing_data_count for item in metrics),
        blocked_count=sum(item.blocked_count for item in metrics),
        safety_violation=any(item.safety_violation for item in metrics),
    )


def stability_score(deltas: list[float]) -> float:
    if not deltas:
        return 0.0
    if len(deltas) == 1:
        return 1.0
    non_zero = [1 if delta > 0 else -1 if delta < 0 else 0 for delta in deltas]
    consistent = sum(non_zero[index] == non_zero[index - 1] for index in range(1, len(non_zero)))
    return consistent / (len(non_zero) - 1)


def is_unsafe_policy(policy: ReplayPolicyConfig) -> bool:
    return (
        policy.allow_short
        or policy.allow_margin
        or policy.allow_leverage
        or policy.allow_market_orders
        or policy.score_weights.llm > policy.llm_weight_cap
    )
