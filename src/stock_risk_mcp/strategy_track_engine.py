from __future__ import annotations

from datetime import datetime, timezone

from stock_risk_mcp.strategy_track_models import (
    StrategyTrackComparisonReport,
    StrategyTrackFixture,
    StrategyTrackRequest,
    StrategyTrackValidationReport,
)


def _as_fixture(value) -> StrategyTrackFixture:
    if isinstance(value, StrategyTrackFixture):
        return value
    return StrategyTrackFixture.model_validate(value)


def validate_strategy_track_fixture(value) -> StrategyTrackValidationReport:
    fixture = _as_fixture(value)
    requests = [
        {
            "request_id": item.request_id,
            "strategy_track": item.strategy_track.value,
            "market_id": item.market_profile.market_id,
            "base_currency": item.market_profile.base_currency,
            "provider_id": item.provider_capability.provider_id,
            "provider_status": item.provider_capability.status.value,
        }
        for item in fixture.strategy_requests
    ]
    track_counts: dict[str, int] = {}
    for item in requests:
        track_counts[item["strategy_track"]] = track_counts.get(item["strategy_track"], 0) + 1
    return StrategyTrackValidationReport(
        run_id=fixture.run_id,
        created_at=fixture.created_at,
        requests=requests,
        summary={"request_count": len(requests), "track_counts": track_counts},
    )


def compare_strategy_track_requests(value) -> StrategyTrackComparisonReport:
    fixture = _as_fixture(value) if not isinstance(value, list) else None
    requests = fixture.strategy_requests if fixture is not None else [StrategyTrackRequest.model_validate(item) for item in value]
    comparisons = []
    for left, right in zip(requests, requests[1:]):
        changed_fields = []
        field_pairs = {
            "market_id": (left.market_profile.market_id, right.market_profile.market_id),
            "country": (left.market_profile.country, right.market_profile.country),
            "base_currency": (left.market_profile.base_currency, right.market_profile.base_currency),
            "exchange_session_profile": (
                left.market_profile.exchange_session_profile,
                right.market_profile.exchange_session_profile,
            ),
            "trading_hours": (left.market_profile.trading_hours, right.market_profile.trading_hours),
            "settlement_cash_availability": (
                left.market_profile.settlement_cash_availability,
                right.market_profile.settlement_cash_availability,
            ),
            "fee_tax_profile_reference": (
                left.market_profile.fee_tax_profile_reference,
                right.market_profile.fee_tax_profile_reference,
            ),
            "realtime_data_profile_reference": (
                left.market_profile.realtime_data_profile_reference,
                right.market_profile.realtime_data_profile_reference,
            ),
            "provider_capability_reference": (
                left.market_profile.provider_capability_reference,
                right.market_profile.provider_capability_reference,
            ),
            "fx_reference": (left.market_profile.fx_reference, right.market_profile.fx_reference),
            "provider_status": (left.provider_capability.status.value, right.provider_capability.status.value),
            "provider_id": (left.provider_capability.provider_id, right.provider_capability.provider_id),
        }
        for field_name, pair in field_pairs.items():
            if pair[0] != pair[1]:
                changed_fields.append(field_name)
        comparisons.append(
            {
                "left_request_id": left.request_id,
                "right_request_id": right.request_id,
                "left_track": left.strategy_track.value,
                "right_track": right.strategy_track.value,
                "changed_fields": changed_fields,
            }
        )
    return StrategyTrackComparisonReport(
        run_id=fixture.run_id if fixture is not None else "strategy-track-comparison",
        created_at=fixture.created_at if fixture is not None else datetime.now(timezone.utc),
        comparison_count=len(comparisons),
        comparisons=comparisons,
    )
