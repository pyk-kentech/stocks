from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.account_read_models import AccountReadPipelineInput, AccountReadSnapshot


def load_account_read_fixture(path: Path) -> AccountReadPipelineInput:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return load_account_read_fixture_from_payload(payload)


def load_account_read_fixture_from_payload(payload: dict) -> AccountReadPipelineInput:
    return AccountReadPipelineInput.model_validate(payload)


def load_account_read_snapshot_fixture(path: Path) -> AccountReadSnapshot:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AccountReadSnapshot.model_validate(payload)
