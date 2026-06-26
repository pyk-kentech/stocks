from stock_risk_mcp.offline_strategy_parameter_space import expand_offline_strategy_candidates
from stock_risk_mcp.offline_strategy_template_catalog import build_offline_strategy_template_catalog


def test_offline_strategy_parameter_space_expands_bounded_candidates() -> None:
    template = build_offline_strategy_template_catalog()[0]
    candidates = expand_offline_strategy_candidates("offline-strategy-test", template, "LARGE_CAP")
    assert 1 <= len(candidates) <= template.parameter_space.max_parameter_combinations
