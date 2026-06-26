from stock_risk_mcp.historical_market_data_credential_ref import redact_credential_ref_summary
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
