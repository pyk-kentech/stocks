from stock_risk_mcp.walk_forward_policy_fixture import load_walk_forward_policy_fixture
from stock_risk_mcp.walk_forward_window_split import build_walk_forward_windows
from tests.test_walk_forward_policy_fixture import fixture_payload, write


def test_window_split_is_timestamp_ordered_and_walk_forward(tmp_path):
    fixture = load_walk_forward_policy_fixture(write(tmp_path, "policy_replay_fixture.json", fixture_payload()))
    windows = build_walk_forward_windows(fixture)
    assert len(windows) == 1
    assert windows[0].train_window_dates == ["2026-01-10", "2026-01-11"]
    assert windows[0].eval_window_dates == ["2026-01-12"]
    assert all(row.timestamp.date().isoformat() in windows[0].eval_window_dates for row in windows[0].eval_rows)
