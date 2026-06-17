from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from stock_risk_mcp.models import StrictModel


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


STRATEGY_TRACK_METADATA = {
    "strategy_track_fixture_run": True,
    "broker_api_called": False,
    "credentials_accessed": False,
    "external_network_calls": False,
    "orders_created": False,
    "live_or_prod_used": False,
}


class StrategyTrack(StrEnum):
    DOMESTIC_KR = "DOMESTIC_KR"
    OVERSEAS_US = "OVERSEAS_US"


class ProviderCapabilityStatus(StrEnum):
    AVAILABLE_DOMESTIC_ONLY = "AVAILABLE_DOMESTIC_ONLY"
    SIMULATION_ONLY = "SIMULATION_ONLY"
    FUTURE_PROVIDER_CANDIDATE = "FUTURE_PROVIDER_CANDIDATE"
    REJECTED_UNSUPPORTED_MARKET = "REJECTED_UNSUPPORTED_MARKET"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"


class MarketProfile(StrictModel):
    market_id: str = Field(..., min_length=1)
    country: str = Field(..., min_length=2)
    base_currency: str = Field(..., min_length=3)
    exchange_session_profile: str = Field(..., min_length=1)
    trading_hours: str = Field(..., min_length=1)
    settlement_cash_availability: str = Field(..., min_length=1)
    fee_tax_profile_reference: str = Field(..., min_length=1)
    realtime_data_profile_reference: str = Field(..., min_length=1)
    provider_capability_reference: str = Field(..., min_length=1)
    fx_reference: str | None = None

    @field_validator("market_id", "country", "base_currency")
    @classmethod
    def normalize_codes(cls, value: str) -> str:
        return value.strip().upper()


class ProviderCapabilityByTrack(StrictModel):
    provider_id: str = Field(..., min_length=1)
    track: StrategyTrack
    supported_markets: list[str] = Field(..., min_length=1)
    supported_asset_types: list[str] = Field(..., min_length=1)
    domestic_support: bool
    overseas_support: bool
    realtime_support: bool
    order_support: bool
    account_support: bool
    status: ProviderCapabilityStatus

    @field_validator("provider_id")
    @classmethod
    def normalize_provider_id(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("supported_markets", "supported_asset_types")
    @classmethod
    def normalize_values(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip().upper() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("provider capability values must not be blank")
        return cleaned

    @model_validator(mode="after")
    def enforce_safe_status(self):
        if self.status == ProviderCapabilityStatus.AVAILABLE_DOMESTIC_ONLY:
            if self.track != StrategyTrack.DOMESTIC_KR or not self.domestic_support or self.overseas_support:
                raise ValueError("provider capability status AVAILABLE_DOMESTIC_ONLY is inconsistent")
        if self.status == ProviderCapabilityStatus.SIMULATION_ONLY and (self.order_support or self.account_support):
            raise ValueError("provider capability status SIMULATION_ONLY must not allow order or account support")
        return self


class StrategyTrackRequest(StrictModel):
    request_id: str = Field(..., min_length=1)
    strategy_track: StrategyTrack
    strategy_track_candidates: list[StrategyTrack] = Field(..., min_length=1)
    market_profile: MarketProfile
    provider_capability: ProviderCapabilityByTrack

    @field_validator("request_id")
    @classmethod
    def normalize_request_id(cls, value: str) -> str:
        return value.strip()

    @field_validator("strategy_track_candidates")
    @classmethod
    def reject_ambiguous_candidates(cls, values: list[StrategyTrack]) -> list[StrategyTrack]:
        if len(set(values)) != 1:
            raise ValueError("ambiguous strategy_track candidates are not allowed")
        return values

    @model_validator(mode="after")
    def validate_track_first_consistency(self):
        if self.strategy_track_candidates[0] != self.strategy_track:
            raise ValueError("strategy_track candidates must resolve to the explicit strategy_track")
        if self.provider_capability.track != self.strategy_track:
            raise ValueError("provider capability track conflicts with strategy_track")

        profile = self.market_profile
        provider = self.provider_capability
        if self.strategy_track == StrategyTrack.DOMESTIC_KR:
            if profile.market_id != "KRX" or profile.country != "KR" or profile.base_currency != "KRW":
                raise ValueError("DOMESTIC_KR market profile is inconsistent")
            if profile.fx_reference is not None:
                raise ValueError("cross-track domestic profile must not define FX reference")
            if "domestic_kr" not in profile.fee_tax_profile_reference.lower():
                raise ValueError("cross-track fee/tax reference leaked into DOMESTIC_KR")
            if "domestic_kr" not in profile.realtime_data_profile_reference.lower():
                raise ValueError("cross-track realtime reference leaked into DOMESTIC_KR")
            if "domestic_kr" not in profile.provider_capability_reference.lower():
                raise ValueError("cross-track provider reference leaked into DOMESTIC_KR")
            if provider.status != ProviderCapabilityStatus.AVAILABLE_DOMESTIC_ONLY:
                raise ValueError("provider capability status is invalid for DOMESTIC_KR")
        if self.strategy_track == StrategyTrack.OVERSEAS_US:
            if profile.country != "US" or profile.base_currency != "USD":
                raise ValueError("OVERSEAS_US market profile is inconsistent")
            if not profile.fx_reference:
                raise ValueError("OVERSEAS_US requires explicit FX reference")
            if "overseas_us" not in profile.fee_tax_profile_reference.lower():
                raise ValueError("cross-track fee/tax reference leaked into OVERSEAS_US")
            if "overseas_us" not in profile.realtime_data_profile_reference.lower():
                raise ValueError("cross-track realtime reference leaked into OVERSEAS_US")
            if "overseas_us" not in profile.provider_capability_reference.lower():
                raise ValueError("cross-track provider reference leaked into OVERSEAS_US")
            if provider.status not in {
                ProviderCapabilityStatus.SIMULATION_ONLY,
                ProviderCapabilityStatus.FUTURE_PROVIDER_CANDIDATE,
                ProviderCapabilityStatus.NEEDS_MORE_EVIDENCE,
            }:
                raise ValueError("provider capability status is invalid for OVERSEAS_US")
        return self


class StrategyTrackFixture(StrictModel):
    schema_version: str
    run_id: str = Field(..., min_length=1)
    created_at: datetime
    strategy_requests: list[StrategyTrackRequest] = Field(..., min_length=1)
    _created = field_validator("created_at")(aware)

    @field_validator("schema_version")
    @classmethod
    def exact_schema(cls, value: str) -> str:
        if value != "4.0-strategy-track-fixture":
            raise ValueError("schema_version must be exactly 4.0-strategy-track-fixture")
        return value


class StrategyTrackValidationReport(StrictModel):
    schema_version: str = "4.0-strategy-track-validation-report"
    run_id: str
    created_at: datetime
    requests: list[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    metadata_json: dict = Field(default_factory=lambda: dict(STRATEGY_TRACK_METADATA))
    _created = field_validator("created_at")(aware)


class StrategyTrackComparisonReport(StrictModel):
    schema_version: str = "4.0-strategy-track-comparison-report"
    run_id: str
    created_at: datetime
    comparison_count: int = Field(..., ge=0)
    comparisons: list[dict] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=lambda: dict(STRATEGY_TRACK_METADATA))
    _created = field_validator("created_at")(aware)
