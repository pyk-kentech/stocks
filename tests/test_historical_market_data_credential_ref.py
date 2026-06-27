import pytest

from stock_risk_mcp import historical_market_data_credential_ref as credential_ref_module
from stock_risk_mcp.historical_market_data_credential_ref import load_historical_market_data_credential_ref, redact_credential_ref_summary
from stock_risk_mcp.historical_market_data_models import HistoricalMarketDataCredentialRef


def test_historical_market_data_credential_ref_redacts_summary() -> None:
    summary = redact_credential_ref_summary(
        HistoricalMarketDataCredentialRef(
            credential_ref_id="TEST_REF",
            appkey_ref_path="/tmp/appkey.txt",
            secretkey_ref_path="/tmp/secret.txt",
        )
    )
    assert summary["credential_ref_present"] is True
    assert summary["auth_header_present"] is True


def test_historical_market_data_credential_ref_supports_directory_form(tmp_path, monkeypatch) -> None:
    secret_dir = tmp_path / "kiwoom_ref"
    secret_dir.mkdir()
    (secret_dir / "66787923_appkey.txt").write_text("APPKEY", encoding="utf-8")
    (secret_dir / "66787923_secretkey.txt").write_text("SECRETKEY", encoding="utf-8")
    monkeypatch.setattr(credential_ref_module, "is_pytest_runtime", lambda: False)
    appkey, secretkey = load_historical_market_data_credential_ref(
        HistoricalMarketDataCredentialRef(
            credential_ref_id="TEST_REF",
            credential_ref_dir=str(secret_dir),
        )
    )
    assert appkey == "APPKEY"
    assert secretkey == "SECRETKEY"


def test_historical_market_data_credential_ref_supports_explicit_paths(tmp_path, monkeypatch) -> None:
    appkey_path = tmp_path / "appkey.txt"
    secretkey_path = tmp_path / "secretkey.txt"
    appkey_path.write_text("APPKEY", encoding="utf-8")
    secretkey_path.write_text("SECRETKEY", encoding="utf-8")
    monkeypatch.setattr(credential_ref_module, "is_pytest_runtime", lambda: False)
    appkey, secretkey = load_historical_market_data_credential_ref(
        HistoricalMarketDataCredentialRef(
            credential_ref_id="TEST_REF",
            appkey_ref_path=str(appkey_path),
            secretkey_ref_path=str(secretkey_path),
        )
    )
    assert appkey == "APPKEY"
    assert secretkey == "SECRETKEY"


def test_historical_market_data_credential_ref_requires_dir_or_explicit_paths() -> None:
    with pytest.raises(ValueError):
        HistoricalMarketDataCredentialRef(credential_ref_id="TEST_REF")
