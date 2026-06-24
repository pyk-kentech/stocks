from __future__ import annotations

from collections.abc import Callable

from stock_risk_mcp.kiwoom_rest_readonly_rank_models import KiwoomRestRankRequest


TransportCallable = Callable[[dict[str, object]], dict[str, object]]


def execute_kiwoom_rest_readonly_rank_transport(
    request: KiwoomRestRankRequest,
    *,
    transport: TransportCallable | None,
) -> dict[str, object]:
    if transport is None:
        raise ValueError("real network transport is blocked; mocked transport is required")
    request_payload = {
        "method": request.method,
        "path": request.path,
        "api_id": request.api_id.value.lower(),
        "headers": request.request_headers,
        "body": request.request_body,
    }
    return transport(request_payload)
