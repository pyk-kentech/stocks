from __future__ import annotations

import json
from urllib.request import Request, urlopen

from stock_risk_mcp.cnn_fear_greed_models import CNNFearGreedCollectorConfig, CNNFearGreedCollectionMode


def fetch_cnn_fear_greed_payload(
    config: CNNFearGreedCollectorConfig,
    *,
    transport=None,
) -> tuple[dict | list | str, CNNFearGreedCollectionMode]:
    if transport is not None:
        return transport(config.source_url, config.timeout_seconds), CNNFearGreedCollectionMode.MOCKED_HTTP

    if config.execute_collection and config.acknowledge_collection and config.allow_real_network:
        request = Request(config.source_url, headers={"User-Agent": "stock-risk-mcp/1.0"})
        with urlopen(request, timeout=config.timeout_seconds) as response:  # noqa: S310
            body = response.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = body
        return parsed, CNNFearGreedCollectionMode.REAL_HTTP

    if config.mock_payload is None:
        raise ValueError("mock payload is required when real network collection is not explicitly enabled")
    return config.mock_payload, CNNFearGreedCollectionMode.MOCKED_HTTP
