from __future__ import annotations

from stock_risk_mcp.macro_regime_provider_models import FredSeriesRequest, MacroRegimeRuntimeContext


_BLOCKED_MARKERS = (
    "authorization",
    "bearer ",
    "api_key=",
    "secret",
    "token",
    "password",
    "account",
    "order",
    "buy",
    "sell",
    "broker",
)


def validate_macro_regime_metadata_safety(metadata: dict[str, object], context: str) -> None:
    for key, value in metadata.items():
        lowered_key = str(key).lower()
        lowered_value = str(value).lower()
        if any(marker in lowered_key for marker in _BLOCKED_MARKERS):
            raise ValueError(f"{context} contains blocked metadata field: {key}")
        if any(marker in lowered_value for marker in _BLOCKED_MARKERS):
            raise ValueError(f"{context} contains blocked metadata value")


def validate_fred_real_http_request(
    request: FredSeriesRequest,
    *,
    runtime_context: MacroRegimeRuntimeContext,
    api_key: str | None,
) -> None:
    if not request.allow_real_http:
        raise ValueError("real FRED HTTP is disabled by default")
    if not request.explicit_opt_in:
        raise ValueError("real FRED HTTP requires explicit opt-in")
    if runtime_context == MacroRegimeRuntimeContext.PYTEST:
        raise ValueError("real FRED HTTP must never run in pytest")
    if not request.api_key_ref:
        raise ValueError("real FRED HTTP requires api_key_ref policy")
    if not api_key or not str(api_key).strip():
        raise ValueError("real FRED HTTP requires an explicit API key value")
