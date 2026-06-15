from __future__ import annotations

from stock_risk_mcp.market_discovery_models import (
    MarketDiscoveryCandidate,
    MarketDiscoveryClassification,
    MarketDiscoveryEvaluation,
    MarketDiscoveryEvidence,
    MarketDiscoveryFixture,
    MarketDiscoveryResult,
)


def _component(value: float, threshold: float, passing: int, strong: int) -> int:
    if value >= 2 * threshold:
        return strong
    if value >= threshold:
        return passing
    return 0


def evaluate_market_row(row, config) -> MarketDiscoveryEvaluation:
    price_change = (row.price - row.previous_close) / row.previous_close * 100
    volume_spike = row.volume / row.average_volume_20d
    dollar_volume = row.price * row.volume
    dollar_volume_spike = dollar_volume / row.average_dollar_volume_20d
    price_in_range = row.price >= config.min_price and (
        config.max_price is None or row.price <= config.max_price
    )
    conditions = {
        "price_change_pass": price_change >= config.min_price_change_pct,
        "volume_spike_pass": volume_spike >= config.min_volume_spike_ratio,
        "dollar_volume_spike_pass": dollar_volume_spike >= config.min_dollar_volume_spike_ratio,
    }
    liquidity_pass = row.average_dollar_volume_20d >= config.min_average_dollar_volume_20d
    components = {
        "price_movement": _component(price_change, config.min_price_change_pct, 10, 20),
        "volume_spike": _component(volume_spike, config.min_volume_spike_ratio, 20, 30),
        "dollar_volume_spike": _component(dollar_volume_spike, config.min_dollar_volume_spike_ratio, 20, 30),
        "liquidity": _component(row.average_dollar_volume_20d, config.min_average_dollar_volume_20d, 10, 20),
    }
    confirmation_count = sum(conditions.values())
    if not price_in_range or not liquidity_pass:
        classification = MarketDiscoveryClassification.EXCLUDE
    elif confirmation_count == 3:
        classification = MarketDiscoveryClassification.DISCOVER
    elif confirmation_count == 2:
        classification = MarketDiscoveryClassification.WATCH
    else:
        classification = MarketDiscoveryClassification.EXCLUDE
    reasons = [
        "PRICE_IN_RANGE" if price_in_range else (
            "PRICE_BELOW_MINIMUM" if row.price < config.min_price else "PRICE_ABOVE_MAXIMUM"
        ),
        "PRICE_CHANGE_CONFIRMED" if conditions["price_change_pass"] else "PRICE_CHANGE_BELOW_MINIMUM",
        "VOLUME_SPIKE_CONFIRMED" if conditions["volume_spike_pass"] else "VOLUME_SPIKE_BELOW_MINIMUM",
        "DOLLAR_VOLUME_SPIKE_CONFIRMED" if conditions["dollar_volume_spike_pass"] else "DOLLAR_VOLUME_SPIKE_BELOW_MINIMUM",
        "LIQUIDITY_CONFIRMED" if liquidity_pass else "LIQUIDITY_BELOW_MINIMUM",
    ]
    return MarketDiscoveryEvaluation(
        ticker=row.ticker,
        observed_at=row.observed_at,
        classification=classification,
        score=max(0, min(100, sum(components.values()))),
        component_scores=components,
        evidence=MarketDiscoveryEvidence(
            price_change_pct=price_change,
            volume_spike_ratio=volume_spike,
            dollar_volume=dollar_volume,
            dollar_volume_spike_ratio=dollar_volume_spike,
            price_in_range=price_in_range,
            liquidity_pass=liquidity_pass,
            **conditions,
        ),
        reasons=reasons,
    )


def scan_market_discovery(fixture: MarketDiscoveryFixture, checksum: str, fixture_format: str) -> MarketDiscoveryResult:
    priority = {
        MarketDiscoveryClassification.DISCOVER: 0,
        MarketDiscoveryClassification.WATCH: 1,
        MarketDiscoveryClassification.EXCLUDE: 2,
    }
    evaluations = [evaluate_market_row(row, fixture.scanner_config) for row in fixture.rows]
    evaluations.sort(key=lambda item: (priority[item.classification], -item.score, item.ticker))
    eligible = [item for item in evaluations if item.classification != MarketDiscoveryClassification.EXCLUDE]
    eligible.sort(key=lambda item: (-item.score, item.ticker))
    candidates = [
        MarketDiscoveryCandidate.model_validate(item.model_dump())
        for item in eligible[:fixture.scanner_config.max_candidates]
    ]
    return MarketDiscoveryResult(
        fixture_checksum=checksum,
        fixture_format=fixture_format,
        as_of_timestamp=fixture.as_of_timestamp,
        scanner_config=fixture.scanner_config,
        evaluations=evaluations,
        candidates=candidates,
        summary_counts={
            item.value: sum(result.classification == item for result in evaluations)
            for item in MarketDiscoveryClassification
        },
    )
