from __future__ import annotations

import time


def run_watch_loop(run_once, interval_seconds: float, max_iterations: int | None = None, sleep_fn=time.sleep):
    results = []
    iteration = 0
    try:
        while max_iterations is None or iteration < max_iterations:
            results.append(run_once())
            iteration += 1
            if max_iterations is None or iteration < max_iterations:
                sleep_fn(interval_seconds)
    except KeyboardInterrupt:
        pass
    return results
