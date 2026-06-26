from __future__ import annotations

from pathlib import Path

from stock_risk_mcp.historical_market_data_guard import is_pytest_runtime, validate_no_sensitive_markers
from stock_risk_mcp.historical_market_data_models import HistoricalMarketDataCredentialRef


def load_historical_market_data_credential_ref(ref: HistoricalMarketDataCredentialRef) -> tuple[str, str]:
    if is_pytest_runtime():
        raise ValueError("credential refs must not be read in pytest")
    validate_no_sensitive_markers(ref.credential_ref_id, context="credential_ref_id")
    appkey_path = Path(ref.appkey_ref_path).expanduser().resolve()
    secretkey_path = Path(ref.secretkey_ref_path).expanduser().resolve()
    appkey = appkey_path.read_text(encoding="utf-8").strip()
    secretkey = secretkey_path.read_text(encoding="utf-8").strip()
    if not appkey or not secretkey:
        raise ValueError("credential ref files must not be blank")
    return appkey, secretkey


def redact_credential_ref_summary(ref: HistoricalMarketDataCredentialRef | None) -> dict[str, object]:
    if ref is None:
        return {
            "credential_ref_present": False,
            "credential_policy": "BLOCKED",
            "redaction_status": "PASSED",
            "auth_header_present": False,
        }
    return {
        "credential_ref_present": True,
        "credential_policy": "KEY_REF_ONLY",
        "redaction_status": ref.redaction_status.value,
        "auth_header_present": True,
    }
