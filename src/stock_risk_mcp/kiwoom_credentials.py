from __future__ import annotations

import json
from pathlib import Path

from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentials, KiwoomCredentialSource


def load_kiwoom_credentials(
    source: KiwoomCredentialSource,
    credential_file: Path | None = None,
    env: dict[str, str] | None = None,
) -> KiwoomCredentials:
    if source == KiwoomCredentialSource.NONE:
        return KiwoomCredentials(source=source)
    if source == KiwoomCredentialSource.ENV:
        values = env or {}
        return KiwoomCredentials(
            appkey=values.get("KIWOOM_APPKEY"), secretkey=values.get("KIWOOM_SECRETKEY"),
            account_number=values.get("KIWOOM_ACCOUNT_NUMBER"), source=source,
            errors=[] if values.get("KIWOOM_APPKEY") and values.get("KIWOOM_SECRETKEY") else ["explicit Kiwoom environment credentials missing"],
        )
    if credential_file is None:
        return KiwoomCredentials(source=source, errors=["explicit credential file required"])
    try:
        values = json.loads(Path(credential_file).read_text(encoding="utf-8"))
        return KiwoomCredentials(
            appkey=values.get("appkey"), secretkey=values.get("secretkey"),
            account_number=values.get("account_number"), source=source,
            errors=[] if values.get("appkey") and values.get("secretkey") else ["credential file missing appkey or secretkey"],
        )
    except FileNotFoundError:
        return KiwoomCredentials(source=source, errors=["explicit credential file not found"])
    except (OSError, ValueError, TypeError) as error:
        return KiwoomCredentials(source=source, errors=[f"failed to load explicit credential file: {error}"])
