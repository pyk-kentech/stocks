from stock_risk_mcp.normalizer_registry import default_normalizer_registry


def test_default_normalizer_registry_registers_generic_normalizers() -> None:
    registry = default_normalizer_registry()

    assert [item.name for item in registry.list_normalizers()] == [
        "generic-price-csv", "generic-news-csv", "generic-dilution-csv",
        "generic-flow-csv", "generic-fx-csv",
    ]
    assert registry.get_normalizer("generic-price-csv").name == "generic-price-csv"
