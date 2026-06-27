from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from stock_risk_mcp.historical_market_data_guard import validate_safe_local_root
from stock_risk_mcp.kiwoom_oauth_models import KiwoomCredentialRef, KiwoomEnvironment, KiwoomOAuthStoredToken


def _token_path(token_store_root: str, environment: KiwoomEnvironment, credential_ref: KiwoomCredentialRef) -> Path:
    root = validate_safe_local_root(token_store_root)
    env_dir = root / environment.value.lower()
    env_dir.mkdir(parents=True, exist_ok=True)
    return env_dir / f"{credential_ref.credential_id.lower()}_oauth_token.json"


def load_stored_token(
    token_store_root: str,
    environment: KiwoomEnvironment,
    credential_ref: KiwoomCredentialRef,
) -> tuple[KiwoomOAuthStoredToken | None, Path]:
    path = _token_path(token_store_root, environment, credential_ref)
    if not path.exists():
        return None, path
    token = KiwoomOAuthStoredToken.model_validate_json(path.read_text(encoding="utf-8"))
    return token, path


def persist_stored_token(
    token_store_root: str,
    environment: KiwoomEnvironment,
    credential_ref: KiwoomCredentialRef,
    token: KiwoomOAuthStoredToken,
) -> Path:
    path = _token_path(token_store_root, environment, credential_ref)
    path.write_text(token.model_dump_json(indent=2), encoding="utf-8")
    return path


def stored_token_is_usable(token: KiwoomOAuthStoredToken, *, now: datetime | None = None) -> bool:
    if token.expires_dt is None:
        return True
    current = now or datetime.now().astimezone()
    expires_dt = datetime.fromisoformat(token.expires_dt)
    return expires_dt > current + timedelta(seconds=30)
