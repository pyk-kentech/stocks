import json

import pytest

from stock_risk_mcp.provider_config import (
    HTTPProviderConfig,
    ProviderDataKind,
    load_provider_configs,
    validate_provider_config,
)


def test_provider_config_loads_json_and_rejects_credential_headers(tmp_path) -> None:
    path = tmp_path / "providers.json"
    path.write_text(json.dumps({"providers": [{
        "provider_name": "prices", "url": "https://example.com/prices.csv",
        "data_kind": "PRICE_HISTORY", "output_format": "CSV",
        "allowed_hosts": ["example.com"], "enabled": True,
    }]}), encoding="utf-8")

    configs = load_provider_configs(path)

    assert configs[0].data_kind == ProviderDataKind.PRICE_HISTORY
    assert validate_provider_config(configs[0]) == []
    with pytest.raises(ValueError):
        HTTPProviderConfig(
            provider_name="bad", url="https://example.com/a.csv", data_kind=ProviderDataKind.UNKNOWN,
            output_format="CSV", allowed_hosts=["example.com"], headers={"Authorization": "secret"},
        )
    with pytest.raises(ValueError):
        HTTPProviderConfig(
            provider_name="../outside", url="https://example.com/a.csv", data_kind=ProviderDataKind.UNKNOWN,
            output_format="CSV", allowed_hosts=["example.com"],
        )
