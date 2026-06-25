from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import urlopen

from stock_risk_mcp.macro_regime_provider_guard import validate_fred_real_http_request
from stock_risk_mcp.macro_regime_provider_models import (
    CanonicalMacroEvent,
    CanonicalMacroSeriesPoint,
    FredSeriesRequest,
    MacroRegimeAssetClass,
    MacroRegimeProvider,
    MacroRegimeProviderStatus,
    MacroRegimeRequestPreview,
    MacroRegimeRuntimeContext,
    MacroRegimeSeriesId,
    MockedProviderPayload,
)


FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

_FRED_SERIES_CODE = {
    MacroRegimeSeriesId.VIX: "VIXCLS",
    MacroRegimeSeriesId.US10Y: "DGS10",
    MacroRegimeSeriesId.USDKRW: "DEXKOUS",
    MacroRegimeSeriesId.DOLLAR_STRENGTH: "DTWEXBGS",
}

_SERIES_ASSET_CLASS = {
    MacroRegimeSeriesId.NQ_CONTINUOUS: MacroRegimeAssetClass.FUTURES,
    MacroRegimeSeriesId.ES_CONTINUOUS: MacroRegimeAssetClass.FUTURES,
    MacroRegimeSeriesId.VIX: MacroRegimeAssetClass.VOLATILITY,
    MacroRegimeSeriesId.DOLLAR_STRENGTH: MacroRegimeAssetClass.INDEX,
    MacroRegimeSeriesId.US10Y: MacroRegimeAssetClass.RATES,
    MacroRegimeSeriesId.USDKRW: MacroRegimeAssetClass.FX,
}


def build_fred_request_preview(request: FredSeriesRequest) -> MacroRegimeRequestPreview:
    query_params = {
        "series_id": request.fred_series_code,
        "api_key": request.api_key_ref or "KEY_REF_REQUIRED",
        "file_type": request.file_type.lower(),
    }
    if request.observation_start:
        query_params["observation_start"] = request.observation_start.isoformat()
    if request.observation_end:
        query_params["observation_end"] = request.observation_end.isoformat()
    status = MacroRegimeProviderStatus.OPT_IN_REQUIRED
    if not request.allow_real_http:
        status = MacroRegimeProviderStatus.MOCKED_ONLY
    return MacroRegimeRequestPreview(
        preview_id=f"{request.request_id}-PREVIEW",
        provider=MacroRegimeProvider.FRED,
        url=FRED_BASE_URL,
        query_params=query_params,
        redacted_fields=["API_KEY"],
        status=status,
        decision_reason=(
            "FRED request preview only; real HTTP disabled by default"
            if not request.allow_real_http
            else "FRED request preview built; explicit opt-in still required for real HTTP"
        ),
    )


def execute_fred_observations_request(
    request: FredSeriesRequest,
    *,
    api_key: str | None,
    runtime_context: MacroRegimeRuntimeContext,
    timeout_seconds: int = 15,
) -> dict[str, object]:
    validate_fred_real_http_request(request, runtime_context=runtime_context, api_key=api_key)
    params = {
        "series_id": request.fred_series_code,
        "api_key": str(api_key).strip(),
        "file_type": request.file_type.lower(),
    }
    if request.observation_start:
        params["observation_start"] = request.observation_start.isoformat()
    if request.observation_end:
        params["observation_end"] = request.observation_end.isoformat()
    url = f"{FRED_BASE_URL}?{urlencode(params)}"
    with urlopen(url, timeout=timeout_seconds) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def parse_fred_observations_payload(
    request: FredSeriesRequest,
    payload: dict[str, object],
    *,
    source_ref: str,
) -> list[CanonicalMacroSeriesPoint]:
    observations = payload.get("observations", [])
    if not isinstance(observations, list):
        raise ValueError("fred observations payload must contain a list")
    points: list[CanonicalMacroSeriesPoint] = []
    provider_symbol = request.fred_series_code
    unit = "INDEX"
    if request.series_id == MacroRegimeSeriesId.US10Y:
        unit = "PERCENT"
    elif request.series_id == MacroRegimeSeriesId.USDKRW:
        unit = "KRW_PER_USD"
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        value = str(observation.get("value", "")).strip()
        if not value or value == ".":
            continue
        observed_date = str(observation.get("date", "")).strip()
        if not observed_date:
            continue
        observed_at = datetime.fromisoformat(f"{observed_date}T00:00:00+00:00")
        points.append(
            CanonicalMacroSeriesPoint(
                series_id=request.series_id,
                asset_class=_SERIES_ASSET_CLASS[request.series_id],
                provider=MacroRegimeProvider.FRED,
                provider_symbol=provider_symbol,
                observed_at=observed_at,
                available_at=observed_at,
                value=float(value),
                unit=unit,
                source_ref=source_ref,
                quality_flags=["FRED_MOCKED_OR_OFFICIAL_SERIES"],
            )
        )
    return points


def parse_mocked_provider_payload(payload: MockedProviderPayload) -> tuple[list[CanonicalMacroSeriesPoint], list[CanonicalMacroEvent]]:
    if payload.provider == MacroRegimeProvider.FRED:
        if payload.series_id is None:
            raise ValueError("FRED mocked payload requires series_id")
        request = FredSeriesRequest(
            request_id=payload.payload_id,
            series_id=payload.series_id,
            fred_series_code=_FRED_SERIES_CODE[payload.series_id],
            api_key_ref="FRED_KEY_REF",
        )
        return parse_fred_observations_payload(request, payload.payload, source_ref=payload.source_ref), []

    if payload.provider in {
        MacroRegimeProvider.DATABENTO,
        MacroRegimeProvider.CME,
        MacroRegimeProvider.LS_OPEN_API_FUTURE,
        MacroRegimeProvider.LOCAL_FIXTURE,
        MacroRegimeProvider.MANUAL_JSON,
        MacroRegimeProvider.MANUAL_CSV,
    }:
        records = payload.payload.get("records", [])
        if not isinstance(records, list):
            raise ValueError("mocked futures payload must contain records")
        points: list[CanonicalMacroSeriesPoint] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            raw_series_id = record.get("series_id") or payload.series_id
            if raw_series_id is None:
                raise ValueError("mocked futures record missing series_id")
            series_id = raw_series_id if isinstance(raw_series_id, MacroRegimeSeriesId) else MacroRegimeSeriesId(str(raw_series_id))
            observed_at = datetime.fromisoformat(str(record["observed_at"]))
            available_at = datetime.fromisoformat(str(record.get("available_at", record["observed_at"])))
            points.append(
                CanonicalMacroSeriesPoint(
                    series_id=series_id,
                    asset_class=_SERIES_ASSET_CLASS[series_id],
                    provider=payload.provider,
                    provider_symbol=str(record.get("provider_symbol", series_id.value)),
                    observed_at=observed_at,
                    available_at=available_at,
                    value=float(record["value"]),
                    pct_change_1d=float(record["pct_change_1d"]) if record.get("pct_change_1d") is not None else None,
                    unit=str(record.get("unit", "INDEX")),
                    source_ref=payload.source_ref,
                    quality_flags=["MANUAL_FUTURES_FIXTURE"],
                    stale_flag=bool(record.get("stale_flag", False)),
                )
            )
        return points, []

    records = payload.payload.get("events", [])
    if not isinstance(records, list):
        raise ValueError("mocked event payload must contain events")
    events: list[CanonicalMacroEvent] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        events.append(
            CanonicalMacroEvent.model_validate(
                {
                    "event_id": record["event_id"],
                    "event_type": record["event_type"],
                    "provider": payload.provider,
                    "country": record.get("country", "US"),
                    "title": record["title"],
                    "event_time": record["event_time"],
                    "timezone": record.get("timezone", "UTC"),
                    "importance": record.get("importance", "HIGH"),
                    "affected_assets": record.get("affected_assets", []),
                    "pre_event_block_window_minutes": record.get("pre_event_block_window_minutes", 0),
                    "pre_event_reduce_window_minutes": record.get("pre_event_reduce_window_minutes", 0),
                    "post_event_cooldown_minutes": record.get("post_event_cooldown_minutes", 0),
                    "event_active_window_minutes": record.get("event_active_window_minutes", 0),
                    "source_ref": payload.source_ref,
                    "available_at": record.get("available_at"),
                }
            )
        )
    return [], events
