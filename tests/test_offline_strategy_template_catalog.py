from stock_risk_mcp.offline_strategy_template_catalog import build_offline_strategy_template_catalog


def test_offline_strategy_template_catalog_has_four_families() -> None:
    catalog = build_offline_strategy_template_catalog()
    assert len(catalog) == 4
    assert any(item.family.value == "VOLUME_PULLBACK_LONG" for item in catalog)
    assert any(item.promotion_eligible is False for item in catalog)
