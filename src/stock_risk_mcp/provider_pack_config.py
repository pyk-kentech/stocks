from __future__ import annotations

import json
from pathlib import Path

import yaml
from pydantic import Field, model_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.provider_config import (
    HTTPProviderConfig,
    ProviderDataKind,
    ProviderOutputFormat,
    validate_provider_config,
)


REQUIRED_COLUMNS = {
    ProviderDataKind.PRICE_HISTORY: {"ticker", "date", "close", "volume"},
    ProviderDataKind.FX_RATE: {"base_currency", "quote_currency", "date", "rate"},
    ProviderDataKind.NEWS_SIGNAL: {"ticker", "observed_at", "headline", "source_name"},
    ProviderDataKind.NEWS: {"ticker", "observed_at", "headline", "source_name"},
    ProviderDataKind.DILUTION: {"ticker", "observed_at", "event_type", "dilution_risk", "source_name"},
    ProviderDataKind.DILUTION_SIGNAL: {"ticker", "observed_at", "event_type", "dilution_risk", "source_name"},
    ProviderDataKind.FOREIGN_INSTITUTION_FLOW: {"ticker", "observed_at", "source_name"},
}

FLOW_VALUE_COLUMNS = {
    "foreign_net_buy_amount",
    "institution_net_buy_amount",
    "foreign_net_buy_shares",
    "institution_net_buy_shares",
}


class ProviderPackProviderConfig(StrictModel):
    provider_name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    url: str | None = None
    local_file: str | None = None
    data_kind: ProviderDataKind
    output_format: ProviderOutputFormat
    allowed_hosts: list[str]
    enabled: bool = False
    normalizer: str | None = None
    columns: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_source_and_columns(self):
        if bool(self.url) == bool(self.local_file):
            raise ValueError("exactly one of url or local_file is required")
        missing = sorted(REQUIRED_COLUMNS.get(self.data_kind, set()) - set(self.columns))
        if missing:
            raise ValueError(f"missing required columns for {self.data_kind.value}: {', '.join(missing)}")
        if self.data_kind == ProviderDataKind.FOREIGN_INSTITUTION_FLOW and not FLOW_VALUE_COLUMNS.intersection(self.columns):
            raise ValueError("at least one foreign or institution flow value column is required")
        return self

    def as_http_config(self) -> HTTPProviderConfig:
        if not self.url:
            raise ValueError("url is required for an HTTP provider")
        return HTTPProviderConfig(
            provider_name=self.provider_name,
            url=self.url,
            data_kind=self.data_kind,
            output_format=self.output_format,
            allowed_hosts=self.allowed_hosts,
            enabled=self.enabled,
        )


class ProviderPackGroup(StrictModel):
    providers: list[ProviderPackProviderConfig] = Field(default_factory=list)


class ProviderPackConfig(StrictModel):
    price: ProviderPackGroup = Field(default_factory=ProviderPackGroup)
    fx: ProviderPackGroup = Field(default_factory=ProviderPackGroup)
    news: ProviderPackGroup = Field(default_factory=ProviderPackGroup)
    dilution: ProviderPackGroup = Field(default_factory=ProviderPackGroup)
    flow: ProviderPackGroup = Field(default_factory=ProviderPackGroup)


def load_provider_pack_config(path: str | Path) -> ProviderPackConfig:
    file_path = Path(path)
    payload = _read_payload(file_path)
    config = ProviderPackConfig.model_validate(payload)
    for group in (config.price, config.fx, config.news, config.dilution, config.flow):
        for provider in group.providers:
            if provider.local_file and not Path(provider.local_file).is_absolute():
                provider.local_file = str((file_path.parent / provider.local_file).resolve())
    return config


def validate_provider_pack_config_file(
    path: str | Path, runtime_allowed_hosts: list[str] | None = None
) -> dict[str, object]:
    try:
        config = load_provider_pack_config(path)
    except Exception as error:
        return {"status": "BLOCKED", "providers": [], "errors": [str(error)]}
    results = []
    errors = []
    for provider in [*config.price.providers, *config.fx.providers, *config.news.providers, *config.dilution.providers, *config.flow.providers]:
        provider_errors = []
        provider_warnings = []
        if provider.url:
            provider_errors.extend(validate_provider_config(provider.as_http_config(), runtime_allowed_hosts))
        if not provider.normalizer:
            provider_warnings.append("normalizer is missing; this source will fail during normalization")
        results.append({
            "provider_name": provider.provider_name,
            "status": "VALID" if not provider_errors else "BLOCKED",
            "warnings": provider_warnings,
            "errors": provider_errors,
        })
        errors.extend(f"{provider.provider_name}: {item}" for item in provider_errors)
    return {"status": "VALID" if not errors else "BLOCKED", "providers": results, "errors": errors}


def _read_payload(path: Path):
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text) if path.suffix.lower() in {".yaml", ".yml"} else json.loads(text)
