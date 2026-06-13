from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import Field, model_validator

from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.network_safety import validate_no_credentials, validate_public_http_url


class NetworkMode(StrEnum):
    DISABLED = "DISABLED"
    ENABLED = "ENABLED"


class ProviderDataKind(StrEnum):
    PRICE_HISTORY = "PRICE_HISTORY"
    NEWS_SIGNAL = "NEWS_SIGNAL"
    DILUTION_SIGNAL = "DILUTION_SIGNAL"
    TOSS_SIGNAL = "TOSS_SIGNAL"
    FLOW_SIGNAL = "FLOW_SIGNAL"
    COMPLIANCE = "COMPLIANCE"
    FX_RATE = "FX_RATE"
    UNKNOWN = "UNKNOWN"


class ProviderOutputFormat(StrEnum):
    CSV = "CSV"
    JSON = "JSON"


class HTTPProviderConfig(StrictModel):
    provider_name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    url: str
    data_kind: ProviderDataKind
    output_format: ProviderOutputFormat
    allowed_hosts: list[str]
    timeout_seconds: int = Field(20, gt=0)
    max_bytes: int = Field(10_000_000, gt=0)
    headers: dict[str, str] = Field(default_factory=dict)
    enabled: bool = False
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def block_credentials(self):
        errors = validate_no_credentials(self.headers)
        if errors:
            raise ValueError("; ".join(errors))
        return self


def load_provider_configs(path: str | Path) -> list[HTTPProviderConfig]:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    payload = yaml.safe_load(text) if file_path.suffix.lower() in {".yaml", ".yml"} else json.loads(text)
    records = payload.get("providers", []) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise ValueError("Provider config must contain a providers list")
    return [HTTPProviderConfig.model_validate(item) for item in records]


def validate_provider_config(config: HTTPProviderConfig, runtime_allowed_hosts: list[str] | None = None) -> list[str]:
    from stock_risk_mcp.network_safety import effective_allowed_hosts
    allowed = effective_allowed_hosts(config.allowed_hosts, runtime_allowed_hosts)
    return [*validate_no_credentials(config.headers), *validate_public_http_url(config.url, allowed)]


def validate_provider_config_file(path: str | Path, runtime_allowed_hosts: list[str] | None = None) -> list[dict]:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    payload = yaml.safe_load(text) if file_path.suffix.lower() in {".yaml", ".yml"} else json.loads(text)
    records = payload.get("providers", []) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise ValueError("Provider config must contain a providers list")
    results = []
    for record in records:
        provider_name = record.get("provider_name", "unknown") if isinstance(record, dict) else "unknown"
        warnings = []
        try:
            config = HTTPProviderConfig.model_validate(record)
            errors = validate_provider_config(config, runtime_allowed_hosts)
            warnings = config.notes
        except Exception as error:
            errors = [str(error)]
        results.append({
            "provider_name": provider_name,
            "status": "VALID" if not errors else "BLOCKED",
            "warnings": warnings,
            "errors": errors,
        })
    return results
