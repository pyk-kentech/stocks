from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from stock_risk_mcp.historical_market_data_models import (
    HistoricalChartCaptureDecision,
    HistoricalChartCaptureTask,
    HistoricalMarketDataCaptureProfile,
    HistoricalMarketDataMode,
    HistoricalMarketDataOptIn,
)


_BLOCKED_TEXT = re.compile(r"authorization|bearer|token|secret|appkey|account|acct|order|주문|계좌", re.IGNORECASE)


def is_pytest_runtime() -> bool:
    return "PYTEST_CURRENT_TEST" in os.environ or "pytest" in Path(sys.argv[0]).name.lower()


def validate_safe_local_root(path: str, *, allow_tmp: bool = True) -> Path:
    lowered = path.strip().lower()
    if "://" in lowered or lowered.startswith("//"):
        raise ValueError("path must be local only")
    candidate = Path(path).expanduser()
    resolved = candidate.resolve()
    text = str(resolved)
    if "/tmp/" in text or text.startswith("/tmp"):
        return resolved
    if allow_tmp and "/var/tmp/" in text:
        return resolved
    if "local_data" in resolved.parts:
        return resolved
    raise ValueError("path must remain under local_data or tmp roots")


def validate_no_sensitive_markers(value: object, *, context: str) -> None:
    text = str(value)
    if _BLOCKED_TEXT.search(text):
        raise ValueError(f"{context} contains blocked credential/account/order marker")


def validate_real_capture_opt_in(mode: HistoricalMarketDataMode, opt_in: HistoricalMarketDataOptIn) -> list[str]:
    reasons: list[str] = []
    if mode != HistoricalMarketDataMode.REAL_OPT_IN_BOUNDARY:
        reasons.append("MODE_NOT_REAL_BOUNDARY")
    if not opt_in.allow_real_chart_capture:
        reasons.append("ALLOW_REAL_CHART_CAPTURE_MISSING")
    if not opt_in.acknowledge_readonly_only:
        reasons.append("ACKNOWLEDGE_READONLY_ONLY_MISSING")
    if not opt_in.acknowledge_no_orders:
        reasons.append("ACKNOWLEDGE_NO_ORDERS_MISSING")
    if not opt_in.acknowledge_user_initiated:
        reasons.append("ACKNOWLEDGE_USER_INITIATED_MISSING")
    if not opt_in.acknowledge_rate_limit_and_capacity:
        reasons.append("ACKNOWLEDGE_RATE_LIMIT_AND_CAPACITY_MISSING")
    if is_pytest_runtime():
        reasons.append("PYTEST_REAL_CAPTURE_BLOCKED")
    return reasons


def validate_profile_guard(profile: HistoricalMarketDataCaptureProfile, *, in_test: bool | None = None) -> list[str]:
    test_runtime = is_pytest_runtime() if in_test is None else in_test
    reasons: list[str] = []
    if profile == HistoricalMarketDataCaptureProfile.FULL_INTRADAY_PROFILE:
        reasons.append("FULL_INTRADAY_PROFILE_DISABLED_BY_DEFAULT")
        if test_runtime:
            reasons.append("FULL_INTRADAY_PROFILE_BLOCKED_IN_TESTS")
    return reasons


def decide_capture_task(task: HistoricalChartCaptureTask, *, mode: HistoricalMarketDataMode, opt_in: HistoricalMarketDataOptIn) -> HistoricalChartCaptureTask:
    reasons = list(task.blocking_reasons)
    reasons.extend(validate_profile_guard(task.request_spec.interval and HistoricalMarketDataCaptureProfile.SMOKE_PROFILE, in_test=is_pytest_runtime()))
    if task.capability.real_capture_boundary_supported and mode == HistoricalMarketDataMode.REAL_OPT_IN_BOUNDARY:
        reasons.extend(validate_real_capture_opt_in(mode, opt_in))
    elif mode == HistoricalMarketDataMode.REAL_OPT_IN_BOUNDARY:
        reasons.append("REAL_CAPTURE_NOT_SUPPORTED_FOR_API")
    decision = HistoricalChartCaptureDecision.ALLOWED if not reasons else HistoricalChartCaptureDecision.BLOCKED
    return task.model_copy(update={"execution_decision": decision, "blocking_reasons": sorted(set(reasons))})
