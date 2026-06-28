from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from stock_risk_mcp.historical_market_data_guard import validate_safe_local_root


_PROFILE_DEFAULTS: dict[str, dict[str, float | int]] = {
    "CONSERVATIVE": {
        "max_tr_per_second": 4,
        "max_tr_per_minute": 90,
        "max_tr_per_hour": 900,
        "min_request_interval_seconds": 4.0,
    },
    "OFFICIAL_CEILING": {
        "max_tr_per_second": 5,
        "max_tr_per_minute": 100,
        "max_tr_per_hour": 1000,
        "min_request_interval_seconds": 3.6,
    },
    "TEST_FAST": {
        "max_tr_per_second": 50,
        "max_tr_per_minute": 1000,
        "max_tr_per_hour": 10000,
        "min_request_interval_seconds": 0.0,
    },
}


def _utc_iso(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone().isoformat()


@dataclass(frozen=True)
class KiwoomTrRateLimitConfig:
    profile_name: str
    max_tr_per_second: int
    max_tr_per_minute: int
    max_tr_per_hour: int
    min_request_interval_seconds: float
    ledger_path: str


@dataclass(frozen=True)
class KiwoomTrRateLimiterDecision:
    request_count_last_minute: int
    request_count_last_hour: int
    estimated_next_safe_request_at: str | None
    limiter_expected_safe: bool
    sleep_seconds: float


def resolve_kiwoom_tr_rate_limit_config(
    *,
    profile_name: str | None,
    ledger_path: str | None,
    max_tr_per_second: int | None = None,
    max_tr_per_minute: int | None = None,
    max_tr_per_hour: int | None = None,
    min_request_interval_seconds: float | None = None,
) -> KiwoomTrRateLimitConfig:
    normalized_profile = str(profile_name or "CONSERVATIVE").strip().upper()
    defaults = _PROFILE_DEFAULTS.get(normalized_profile, _PROFILE_DEFAULTS["CONSERVATIVE"])
    resolved_ledger_path = ledger_path or "local_data/kiwoom_rate_limit/ka10081_tr_rate_ledger.json"
    return KiwoomTrRateLimitConfig(
        profile_name=normalized_profile,
        max_tr_per_second=int(max_tr_per_second if max_tr_per_second is not None else defaults["max_tr_per_second"]),
        max_tr_per_minute=int(max_tr_per_minute if max_tr_per_minute is not None else defaults["max_tr_per_minute"]),
        max_tr_per_hour=int(max_tr_per_hour if max_tr_per_hour is not None else defaults["max_tr_per_hour"]),
        min_request_interval_seconds=float(
            min_request_interval_seconds
            if min_request_interval_seconds is not None
            else defaults["min_request_interval_seconds"]
        ),
        ledger_path=str(validate_safe_local_root(resolved_ledger_path)),
    )


class KiwoomTrRateLimiter:
    def __init__(
        self,
        config: KiwoomTrRateLimitConfig,
        *,
        now_fn: Callable[[], float] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self.config = config
        self._now_fn = now_fn or time.time
        self._sleep_fn = sleep_fn or time.sleep
        self._session_request_count = 0
        self._session_sleep_count = 0
        self._session_sleep_seconds = 0.0
        self._last_decision = KiwoomTrRateLimiterDecision(
            request_count_last_minute=0,
            request_count_last_hour=0,
            estimated_next_safe_request_at=None,
            limiter_expected_safe=True,
            sleep_seconds=0.0,
        )

    def _ledger_path(self) -> Path:
        path = Path(self.config.ledger_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _load_ledger(self) -> dict[str, object]:
        path = self._ledger_path()
        if not path.exists():
            return {
                "api_id": "KA10081",
                "profile_name": self.config.profile_name,
                "max_tr_per_second": self.config.max_tr_per_second,
                "max_tr_per_minute": self.config.max_tr_per_minute,
                "max_tr_per_hour": self.config.max_tr_per_hour,
                "min_request_interval_seconds": self.config.min_request_interval_seconds,
                "request_timestamps": [],
                "updated_at": None,
            }
        payload = json.loads(path.read_text(encoding="utf-8"))
        timestamps = payload.get("request_timestamps", [])
        if not isinstance(timestamps, list):
            timestamps = []
        return {
            "api_id": "KA10081",
            "profile_name": self.config.profile_name,
            "max_tr_per_second": self.config.max_tr_per_second,
            "max_tr_per_minute": self.config.max_tr_per_minute,
            "max_tr_per_hour": self.config.max_tr_per_hour,
            "min_request_interval_seconds": self.config.min_request_interval_seconds,
            "request_timestamps": [float(item) for item in timestamps if isinstance(item, (int, float))],
            "updated_at": payload.get("updated_at"),
        }

    def _persist_ledger(self, timestamps: list[float]) -> None:
        payload = {
            "api_id": "KA10081",
            "profile_name": self.config.profile_name,
            "max_tr_per_second": self.config.max_tr_per_second,
            "max_tr_per_minute": self.config.max_tr_per_minute,
            "max_tr_per_hour": self.config.max_tr_per_hour,
            "min_request_interval_seconds": self.config.min_request_interval_seconds,
            "request_timestamps": timestamps,
            "request_count_last_minute": self._count_since(timestamps, self._now_fn(), 60.0),
            "request_count_last_hour": self._count_since(timestamps, self._now_fn(), 3600.0),
            "updated_at": _utc_iso(self._now_fn()),
        }
        self._ledger_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _count_since(timestamps: list[float], now: float, seconds: float) -> int:
        boundary = now - seconds
        return sum(1 for item in timestamps if item > boundary)

    @staticmethod
    def _prune_timestamps(timestamps: list[float], now: float) -> list[float]:
        floor = now - 3600.0
        return [item for item in timestamps if item > floor]

    def _compute_required_sleep(self, timestamps: list[float], now: float) -> float:
        waits: list[float] = []
        second_hits = [item for item in timestamps if item > now - 1.0]
        minute_hits = [item for item in timestamps if item > now - 60.0]
        hour_hits = [item for item in timestamps if item > now - 3600.0]
        if len(second_hits) >= self.config.max_tr_per_second:
            waits.append(second_hits[-self.config.max_tr_per_second] + 1.0 - now)
        if len(minute_hits) >= self.config.max_tr_per_minute:
            waits.append(minute_hits[-self.config.max_tr_per_minute] + 60.0 - now)
        if len(hour_hits) >= self.config.max_tr_per_hour:
            waits.append(hour_hits[-self.config.max_tr_per_hour] + 3600.0 - now)
        if timestamps and self.config.min_request_interval_seconds > 0:
            waits.append(timestamps[-1] + self.config.min_request_interval_seconds - now)
        return max([0.0, *waits])

    def await_request_slot(self) -> KiwoomTrRateLimiterDecision:
        total_sleep = 0.0
        while True:
            ledger = self._load_ledger()
            now = self._now_fn()
            timestamps = self._prune_timestamps(list(ledger.get("request_timestamps", [])), now)
            delay = self._compute_required_sleep(timestamps, now)
            if delay <= 0:
                decision = KiwoomTrRateLimiterDecision(
                    request_count_last_minute=self._count_since(timestamps, now, 60.0),
                    request_count_last_hour=self._count_since(timestamps, now, 3600.0),
                    estimated_next_safe_request_at=_utc_iso(
                        max(
                            now + self.config.min_request_interval_seconds,
                            timestamps[-1] + self.config.min_request_interval_seconds if timestamps else now,
                        )
                    ),
                    limiter_expected_safe=True,
                    sleep_seconds=total_sleep,
                )
                self._last_decision = decision
                return decision
            self._sleep_fn(delay)
            total_sleep += delay
            self._session_sleep_count += 1
            self._session_sleep_seconds += delay

    def record_request(self) -> None:
        ledger = self._load_ledger()
        now = self._now_fn()
        timestamps = self._prune_timestamps(list(ledger.get("request_timestamps", [])), now)
        timestamps.append(now)
        self._persist_ledger(timestamps)
        self._session_request_count += 1

    def build_summary(self) -> dict[str, object]:
        ledger = self._load_ledger()
        now = self._now_fn()
        timestamps = self._prune_timestamps(list(ledger.get("request_timestamps", [])), now)
        estimated_next_safe_request_at = None
        if timestamps:
            estimated_next_safe_request_at = _utc_iso(
                max(
                    timestamps[-1] + self.config.min_request_interval_seconds,
                    now,
                )
            )
        return {
            "tr_rate_limit_profile": self.config.profile_name,
            "max_tr_per_second": self.config.max_tr_per_second,
            "max_tr_per_minute": self.config.max_tr_per_minute,
            "max_tr_per_hour": self.config.max_tr_per_hour,
            "min_request_interval_seconds": self.config.min_request_interval_seconds,
            "tr_rate_ledger_path": self.config.ledger_path,
            "tr_request_count": self._session_request_count,
            "tr_rate_limiter_sleep_count": self._session_sleep_count,
            "tr_rate_limiter_total_sleep_seconds": round(self._session_sleep_seconds, 6),
            "estimated_next_safe_request_at": estimated_next_safe_request_at,
            "tr_request_count_last_minute": self._count_since(timestamps, now, 60.0),
            "tr_request_count_last_hour": self._count_since(timestamps, now, 3600.0),
            "limiter_expected_safe": self._last_decision.limiter_expected_safe,
        }
