from stock_risk_mcp.watch_loop import run_watch_loop


def test_watch_loop_runs_exact_max_iterations_without_extra_sleep() -> None:
    calls = []
    sleeps = []

    results = run_watch_loop(lambda: calls.append(len(calls)) or len(calls), 5, max_iterations=2, sleep_fn=sleeps.append)

    assert results == [1, 2]
    assert calls == [0, 1]
    assert sleeps == [5]
