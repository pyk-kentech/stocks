from __future__ import annotations

from itertools import product

from stock_risk_mcp.offline_strategy_models import OfflineStrategyCandidate, OfflineStrategyTemplate


def _parameter_summary(parameter_values: dict[str, object]) -> str:
    parts = [f"{key}={parameter_values[key]}" for key in sorted(parameter_values)]
    return ",".join(parts)


def expand_offline_strategy_candidates(
    dataset_id: str,
    template: OfflineStrategyTemplate,
    asset_liquidity_profile,
    *,
    max_candidates: int | None = None,
) -> list[OfflineStrategyCandidate]:
    parameters = template.parameter_space.parameters
    value_grid = [parameter.candidate_values or [parameter.default_value] for parameter in parameters]
    combinations = []
    effective_cap = template.parameter_space.max_parameter_combinations
    if max_candidates is not None:
        effective_cap = min(effective_cap, max(1, int(max_candidates)))
    for values in product(*value_grid):
        parameter_values = {parameter.parameter_name: value for parameter, value in zip(parameters, values)}
        combinations.append(parameter_values)
        if len(combinations) >= effective_cap:
            break
    return [
        OfflineStrategyCandidate(
            candidate_id=f"{dataset_id}-{template.template_id.value}-{index}",
            dataset_id=dataset_id,
            template_id=template.template_id,
            family=template.family,
            direction=template.direction,
            promotion_eligible=template.promotion_eligible,
            parameter_set_id=f"{template.template_id.value}-P{index:03d}",
            parameter_summary=_parameter_summary(parameter_values),
            parameter_values=parameter_values,
            asset_liquidity_profile=asset_liquidity_profile,
        )
        for index, parameter_values in enumerate(combinations, start=1)
    ]
