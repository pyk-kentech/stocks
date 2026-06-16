from __future__ import annotations

from collections import defaultdict

from stock_risk_mcp.walk_forward_policy_models import WalkForwardPolicyFixture, WalkForwardWindow


def build_walk_forward_windows(fixture: WalkForwardPolicyFixture) -> list[WalkForwardWindow]:
    rows_by_date = defaultdict(list)
    for row in sorted(fixture.replay_rows, key=lambda item: item.timestamp):
        rows_by_date[row.timestamp.date().isoformat()].append(row)
    ordered_dates = sorted(rows_by_date)
    train_count = fixture.window_config.train_window_count
    eval_count = fixture.window_config.eval_window_count
    stride = fixture.window_config.window_stride
    total = train_count + eval_count
    windows: list[WalkForwardWindow] = []
    start = 0
    while start + total <= len(ordered_dates):
        train_dates = ordered_dates[start : start + train_count]
        eval_dates = ordered_dates[start + train_count : start + total]
        train_rows = [row for date in train_dates for row in rows_by_date[date]]
        eval_rows = [row for date in eval_dates for row in rows_by_date[date]]
        windows.append(
            WalkForwardWindow(
                train_window_dates=train_dates,
                eval_window_dates=eval_dates,
                train_rows=train_rows,
                eval_rows=eval_rows,
            )
        )
        start += stride
    return windows
