from stock_risk_mcp.strategy_advisor import DisabledLocalLLMAdvisor


def test_local_llm_advisor_is_disabled_and_advisory_only() -> None:
    advisor = DisabledLocalLLMAdvisor()
    health = advisor.health()
    assert health == {
        "status": "DISABLED", "network_called": False, "credentials_read": False,
        "account_data_read": False, "can_create_orders": False, "can_approve_execution": False,
    }
