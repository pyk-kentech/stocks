from __future__ import annotations

from itertools import product

from stock_risk_mcp.offline_strategy_models import OfflineStrategyCandidate, OfflineStrategyTemplate


def expand_offline_strategy_candidates(dataset_id: str, template: OfflineStrategyTemplate, asset_liquidity_profile) -> list[OfflineStrategyCandidate]:
    parameters = template.parameter_space.parameters
    value_grid = [parameter.candidate_values or [parameter.default_value] for parameter in parameters]
    combinations = []
    for values in product(*value_grid):
        parameter_values = {parameter.parameter_name: value for parameter, value in zip(parameters, values)}
        combinations.append(parameter_values)
        if len(combinations) >= template.parameter_space.max_parameter_combinations:
            break
    return [
        OfflineStrategyCandidate(
            candidate_id=f"{dataset_id}-{template.template_id.value}-{index}",
            dataset_id=dataset_id,
            template_id=template.template_id,
            family=template.family,
            direction=template.direction,
            promotion_eligible=template.promotion_eligible,
            parameter_values=parameter_values,
            asset_liquidity_profile=asset_liquidity_profile,
        )
        for index, parameter_values in enumerate(combinations, start=1)
    ]
