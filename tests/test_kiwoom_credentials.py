import json

from stock_risk_mcp.kiwoom_credentials import load_kiwoom_credentials
from stock_risk_mcp.kiwoom_real_readonly_models import KiwoomCredentialSource


def test_kiwoom_credentials_load_only_explicit_env_and_mask_values() -> None:
    credentials = load_kiwoom_credentials(
        KiwoomCredentialSource.ENV,
        env={"KIWOOM_APPKEY": "app-secret-value", "KIWOOM_SECRETKEY": "secret-value"},
    )
    assert credentials.loaded
    assert "app-secret-value" not in repr(credentials)
    assert "secret-value" not in repr(credentials)
    assert credentials.safe_summary() == {"credential_source": "ENV", "credentials_loaded": True}


def test_kiwoom_credentials_load_exact_explicit_file_and_missing_is_safe(tmp_path) -> None:
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({"appkey": "fake-app", "secretkey": "fake-secret"}), encoding="utf-8")
    loaded = load_kiwoom_credentials(KiwoomCredentialSource.FILE_EXPLICIT, credential_file=path)
    missing = load_kiwoom_credentials(KiwoomCredentialSource.FILE_EXPLICIT, credential_file=tmp_path / "missing.json")

    assert loaded.loaded
    assert missing.loaded is False
    assert "not found" in missing.errors[0]
