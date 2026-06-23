from __future__ import annotations

import json
from typing import Callable
from urllib import request


TransportCallable = Callable[[dict[str, object]], dict[str, object]]


def execute_kiwoom_mock_market_data_http_transport(
    request_payload: dict[str, object],
    *,
    transport: TransportCallable | None = None,
) -> dict[str, object]:
    if transport is not None:
        return transport(request_payload)

    req = request.Request(
        url=str(request_payload["url"]),
        data=json.dumps(request_payload["body"]).encode("utf-8"),
        headers=dict(request_payload["headers"]),
        method="POST",
    )
    timeout = float(request_payload["timeout_seconds"])
    with request.urlopen(req, timeout=timeout) as response:  # pragma: no cover
        return json.loads(response.read().decode("utf-8"))  # pragma: no cover
