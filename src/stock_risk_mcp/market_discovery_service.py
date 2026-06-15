from __future__ import annotations

import hashlib
from pathlib import Path

from stock_risk_mcp.market_discovery_fixture import load_market_discovery_fixture
from stock_risk_mcp.market_discovery_models import MarketDiscoveryResult
from stock_risk_mcp.market_discovery_scoring import scan_market_discovery


def run_market_discovery(fixture_file, output_file=None) -> MarketDiscoveryResult:
    path = Path(fixture_file)
    fixture, fixture_format = load_market_discovery_fixture(path)
    result = scan_market_discovery(
        fixture,
        hashlib.sha256(path.read_bytes()).hexdigest(),
        fixture_format,
    )
    if output_file:
        Path(output_file).write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result


def load_market_discovery_result(path) -> MarketDiscoveryResult:
    try:
        return MarketDiscoveryResult.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid market discovery result: {exc}") from exc
