from __future__ import annotations

import hashlib
from pathlib import Path

from stock_risk_mcp.kiwoom_oauth_guard import is_pytest_runtime
from stock_risk_mcp.kiwoom_oauth_models import KiwoomCredentialRef


def load_kiwoom_oauth_credentials(ref: KiwoomCredentialRef, *, allow_pytest_fixture_read: bool = False) -> tuple[str, str]:
    if is_pytest_runtime() and not allow_pytest_fixture_read:
        raise ValueError("credential refs must not be read in pytest")
    if ref.credential_ref_dir:
        base = Path(ref.credential_ref_dir).expanduser().resolve()
        appkey_path = base / "66787923_appkey.txt"
        secretkey_path = base / "66787923_secretkey.txt"
    else:
        appkey_path = Path(ref.appkey_ref_path).expanduser().resolve()
        secretkey_path = Path(ref.secretkey_ref_path).expanduser().resolve()
    appkey = appkey_path.read_text(encoding="utf-8").strip()
    secretkey = secretkey_path.read_text(encoding="utf-8").strip()
    if not appkey or not secretkey:
        raise ValueError("credential ref files must not be blank")
    return appkey, secretkey


def build_credential_fingerprint_redacted(appkey: str, secretkey: str) -> str:
    digest = hashlib.sha256(f"{appkey}::{secretkey}".encode("utf-8")).hexdigest()
    return f"sha256:{digest[:12]}"
