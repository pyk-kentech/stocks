from stock_risk_mcp.policy_evaluation_suite import PolicyEvaluationSuiteResult


def policy_evaluation_report(suite: PolicyEvaluationSuiteResult) -> dict[str, object]:
    return suite.model_dump(mode="json")
