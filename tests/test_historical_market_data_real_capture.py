from stock_risk_mcp.historical_market_data_real_capture import build_blocked_capture_run_result


def test_historical_market_data_real_capture_builds_blocked_result() -> None:
    result = build_blocked_capture_run_result(
        "historical-market-data-test",
        blocked_reasons=["CREDENTIAL_REF_MISSING"],
        transport_kind="MOCK",
        credential_ref_present=False,
    )
    assert result.readiness_status.value == "BLOCKED"
