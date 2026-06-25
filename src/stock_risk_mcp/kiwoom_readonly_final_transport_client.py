from __future__ import annotations

import json
import os
from importlib import import_module
from typing import Callable

from stock_risk_mcp.kiwoom_readonly_final_transport_models import (
    KiwoomReadonlyFinalDomain,
    KiwoomReadonlyFinalRequestPreview,
    KiwoomReadonlyFinalTokenProviderKind,
    KiwoomReadonlyFinalTokenProviderSpec,
)


TransportCallable = Callable[[dict[str, object]], dict[str, object]]
TokenProviderCallable = Callable[[KiwoomReadonlyFinalTokenProviderSpec], str | None]


def resolve_kiwoom_readonly_final_token(
    spec: KiwoomReadonlyFinalTokenProviderSpec,
    *,
    token_provider: TokenProviderCallable | None = None,
) -> str | None:
    if spec.provider_kind == KiwoomReadonlyFinalTokenProviderKind.DISABLED:
        return None
    if token_provider is not None:
        return token_provider(spec)
    if spec.provider_kind == KiwoomReadonlyFinalTokenProviderKind.FAKE_PROVIDER:
        return "FAKE_TOKEN_ONLY"
    if spec.provider_kind == KiwoomReadonlyFinalTokenProviderKind.ENV_EXPLICIT:
        if not spec.env_var_name:
            return None
        return getattr(os, "environ").get(spec.env_var_name)
    return None


def build_kiwoom_readonly_final_http_request(preview: KiwoomReadonlyFinalRequestPreview, *, token: str | None) -> dict[str, object]:
    headers = dict(preview.headers)
    headers["authorization"] = "Bearer <REDACTED_TOKEN_REF>" if token else "<REDACTED_TOKEN_REF>"
    return {
        "url": preview.url,
        "method": preview.method,
        "headers": headers,
        "body_json": preview.body_json,
    }


def execute_kiwoom_readonly_final_http_transport(
    preview: KiwoomReadonlyFinalRequestPreview,
    *,
    token: str | None,
    transport: TransportCallable | None = None,
) -> dict[str, object]:
    envelope = build_kiwoom_readonly_final_http_request(preview, token=token)
    if transport is not None:
        return transport(envelope)
    request_module = import_module("urllib.request")
    body = json.dumps(preview.body_json).encode("utf-8")
    request = request_module.Request(
        preview.url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json;charset=UTF-8",
            "api-id": str(preview.headers.get("api-id") or ""),
            "authorization": f"Bearer {token or ''}",
            "cont-yn": str(preview.headers.get("cont-yn") or "N"),
            "next-key": str(preview.headers.get("next-key") or ""),
        },
    )
    with request_module.urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
        headers = dict(response.headers.items())
        return {
            "status_code": response.status,
            "headers": headers,
            "body_json": payload,
        }


def domain_base_url(domain: KiwoomReadonlyFinalDomain) -> str | None:
    if domain == KiwoomReadonlyFinalDomain.KIWOOM_MOCK_KRX:
        return "https://mockapi.kiwoom.com"
    if domain == KiwoomReadonlyFinalDomain.KIWOOM_PROD_READONLY:
        return "https://api.kiwoom.com"
    return None
