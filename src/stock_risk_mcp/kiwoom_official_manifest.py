from __future__ import annotations

import json
from datetime import date
from enum import StrEnum
from pathlib import Path

from pydantic import Field

from stock_risk_mcp.models import StrictModel


class KiwoomOfficialEndpointClass(StrEnum):
    READ_ONLY = "READ_ONLY"
    ORDER = "ORDER"
    ACCOUNT_READ = "ACCOUNT_READ"
    AUTH = "AUTH"
    UNKNOWN_REVIEW_REQUIRED = "UNKNOWN_REVIEW_REQUIRED"


class KiwoomOfficialEndpoint(StrictModel):
    api_id: str
    path: str
    name: str
    category: str
    method: str
    read_write_class: KiwoomOfficialEndpointClass
    runtime_allowed_in_current_version: bool
    requires_credentials: bool
    requires_account: bool
    risk_notes: str
    source: str
    verified_at: date


class KiwoomOfficialEndpointManifest(StrictModel):
    manifest_version: str
    scope: str
    source_policy: str
    endpoints: list[KiwoomOfficialEndpoint] = Field(default_factory=list)


def default_kiwoom_official_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "configs" / "kiwoom_official_endpoint_manifest.json"


def load_kiwoom_official_manifest(path: Path | None = None) -> KiwoomOfficialEndpointManifest:
    source = path or default_kiwoom_official_manifest_path()
    return KiwoomOfficialEndpointManifest.model_validate(json.loads(source.read_text(encoding="utf-8")))
