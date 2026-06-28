from __future__ import annotations

from stock_risk_mcp.offline_strategy_models import (
    OfflineStrategyDataRequirement,
    OfflineStrategyDirection,
    OfflineStrategyFamily,
    OfflineStrategyParameter,
    OfflineStrategyParameterSpace,
    OfflineStrategyTemplate,
    OfflineStrategyTemplateId,
)


def build_offline_strategy_template_catalog() -> list[OfflineStrategyTemplate]:
    return [
        OfflineStrategyTemplate(
            template_id=OfflineStrategyTemplateId.VOLUME_PULLBACK_LONG_V1,
            family=OfflineStrategyFamily.VOLUME_PULLBACK_LONG,
            direction=OfflineStrategyDirection.LONG_ONLY,
            promotion_eligible=True,
            supported_intervals=["1D", "1M"],
            data_requirements=[
                OfflineStrategyDataRequirement.DAILY_OHLCV,
                OfflineStrategyDataRequirement.HIGH_LOW_REQUIRED,
                OfflineStrategyDataRequirement.VOLUME_REQUIRED,
            ],
            parameter_space=OfflineStrategyParameterSpace(
                space_id="VOLUME_PULLBACK_LONG_V1_SPACE",
                template_id=OfflineStrategyTemplateId.VOLUME_PULLBACK_LONG_V1,
                max_parameter_combinations=32,
                parameters=[
                    OfflineStrategyParameter(parameter_name="VOLUME_LOOKBACK", dtype="INT", candidate_values=[5, 10]),
                    OfflineStrategyParameter(parameter_name="VOLUME_MULTIPLIER", dtype="FLOAT", candidate_values=[1.5, 2.0]),
                    OfflineStrategyParameter(parameter_name="PULLBACK_MAX_BARS", dtype="INT", candidate_values=[2, 3]),
                    OfflineStrategyParameter(parameter_name="TARGET_R_MULTIPLE", dtype="FLOAT", candidate_values=[1.5, 2.0]),
                ],
            ),
        ),
        OfflineStrategyTemplate(
            template_id=OfflineStrategyTemplateId.UPPER_WICK_REVERSAL_V1,
            family=OfflineStrategyFamily.UPPER_WICK_REVERSAL,
            direction=OfflineStrategyDirection.AVOID_LONG_ONLY,
            promotion_eligible=False,
            supported_intervals=["1D", "1M"],
            data_requirements=[
                OfflineStrategyDataRequirement.DAILY_OHLCV,
                OfflineStrategyDataRequirement.HIGH_LOW_REQUIRED,
                OfflineStrategyDataRequirement.VOLUME_REQUIRED,
            ],
            parameter_space=OfflineStrategyParameterSpace(
                space_id="UPPER_WICK_REVERSAL_V1_SPACE",
                template_id=OfflineStrategyTemplateId.UPPER_WICK_REVERSAL_V1,
                max_parameter_combinations=16,
                parameters=[
                    OfflineStrategyParameter(parameter_name="UPPER_WICK_RATIO", dtype="FLOAT", candidate_values=[0.4, 0.6]),
                    OfflineStrategyParameter(parameter_name="VOLUME_MULTIPLIER", dtype="FLOAT", candidate_values=[1.5, 2.0]),
                ],
            ),
        ),
        OfflineStrategyTemplate(
            template_id=OfflineStrategyTemplateId.RSI_OVERSOLD_REBOUND_V1,
            family=OfflineStrategyFamily.RSI_OVERSOLD_REBOUND,
            direction=OfflineStrategyDirection.LONG_ONLY,
            promotion_eligible=True,
            supported_intervals=["1D", "1M"],
            data_requirements=[OfflineStrategyDataRequirement.DAILY_OHLCV],
            parameter_space=OfflineStrategyParameterSpace(
                space_id="RSI_OVERSOLD_REBOUND_V1_SPACE",
                template_id=OfflineStrategyTemplateId.RSI_OVERSOLD_REBOUND_V1,
                max_parameter_combinations=24,
                parameters=[
                    OfflineStrategyParameter(parameter_name="RSI_PERIOD", dtype="INT", candidate_values=[7, 14]),
                    OfflineStrategyParameter(parameter_name="OVERSOLD_THRESHOLD", dtype="FLOAT", candidate_values=[25.0, 30.0]),
                    OfflineStrategyParameter(parameter_name="REBOUND_THRESHOLD", dtype="FLOAT", candidate_values=[35.0, 40.0]),
                    OfflineStrategyParameter(parameter_name="HOLD_BARS", dtype="INT", candidate_values=[1, 2]),
                ],
            ),
        ),
        OfflineStrategyTemplate(
            template_id=OfflineStrategyTemplateId.MACD_RSI_MOMENTUM_V1,
            family=OfflineStrategyFamily.MACD_RSI_MOMENTUM,
            direction=OfflineStrategyDirection.LONG_ONLY,
            promotion_eligible=True,
            supported_intervals=["1D", "1M"],
            data_requirements=[
                OfflineStrategyDataRequirement.DAILY_OHLCV,
                OfflineStrategyDataRequirement.VOLUME_REQUIRED,
                OfflineStrategyDataRequirement.DIVERGENCE_CONTEXT_REQUIRED,
            ],
            parameter_space=OfflineStrategyParameterSpace(
                space_id="MACD_RSI_MOMENTUM_V1_SPACE",
                template_id=OfflineStrategyTemplateId.MACD_RSI_MOMENTUM_V1,
                max_parameter_combinations=48,
                parameters=[
                    OfflineStrategyParameter(parameter_name="MACD_FAST", dtype="INT", candidate_values=[8, 12]),
                    OfflineStrategyParameter(parameter_name="MACD_SLOW", dtype="INT", candidate_values=[21, 26]),
                    OfflineStrategyParameter(parameter_name="MACD_SIGNAL", dtype="INT", candidate_values=[5, 9]),
                    OfflineStrategyParameter(parameter_name="RSI_MIDLINE", dtype="FLOAT", candidate_values=[50.0]),
                    OfflineStrategyParameter(parameter_name="ALLOW_OVERBOUGHT_SECOND_LEG", dtype="BOOL", candidate_values=[False, True]),
                ],
            ),
        ),
    ]
