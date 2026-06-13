from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from pydantic import Field

from stock_risk_mcp.connector_outputs import count_output_rows
from stock_risk_mcp.models import StrictModel
from stock_risk_mcp.network_safety import (
    effective_allowed_hosts,
    sanitize_url_for_logging,
    validate_no_credentials,
    validate_public_http_url,
)


class HTTPDownloadStatus(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    DISABLED = "DISABLED"


class HTTPDownloadResult(StrictModel):
    provider_name: str
    url: str
    status: HTTPDownloadStatus
    output_path: str | None = None
    row_count: int = 0
    content_type: str | None = None
    bytes_downloaded: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


def download_public_http(config, output_dir, enable_network: bool, client=None, runtime_allowed_hosts=None):
    safe_url = sanitize_url_for_logging(config.url)
    if not enable_network or not config.enabled:
        return HTTPDownloadResult(provider_name=config.provider_name, url=safe_url, status=HTTPDownloadStatus.DISABLED)
    allowed = effective_allowed_hosts(config.allowed_hosts, runtime_allowed_hosts)
    errors = [*validate_no_credentials(config.headers), *validate_public_http_url(config.url, allowed)]
    if errors:
        return HTTPDownloadResult(provider_name=config.provider_name, url=safe_url, status=HTTPDownloadStatus.BLOCKED, errors=errors)
    transport = client or StdlibHTTPClient()
    current = config.url
    try:
        for _ in range(6):
            response = transport.get(current, config.headers, config.timeout_seconds, config.max_bytes)
            status_code = int(response["status_code"])
            headers = {str(key): str(value) for key, value in response.get("headers", {}).items()}
            body = bytes(response.get("body", b""))
            if 300 <= status_code < 400:
                target = headers.get("Location") or headers.get("location")
                if not target:
                    raise ValueError("redirect response missing Location")
                target = urljoin(current, target)
                redirect_errors = validate_public_http_url(target, allowed)
                if redirect_errors:
                    return HTTPDownloadResult(provider_name=config.provider_name, url=safe_url, status=HTTPDownloadStatus.BLOCKED, errors=redirect_errors)
                current = target
                continue
            if status_code < 200 or status_code >= 300:
                raise ValueError(f"HTTP status {status_code}")
            if len(body) > config.max_bytes:
                raise ValueError("response exceeded max_bytes")
            output = Path(output_dir) / f"{config.provider_name}.{config.output_format.value.lower()}"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(body)
            return HTTPDownloadResult(
                provider_name=config.provider_name, url=safe_url, status=HTTPDownloadStatus.COMPLETED,
                output_path=str(output), row_count=count_output_rows(output),
                content_type=headers.get("Content-Type") or headers.get("content-type"), bytes_downloaded=len(body),
            )
        raise ValueError("too many redirects")
    except Exception as error:
        return HTTPDownloadResult(provider_name=config.provider_name, url=safe_url, status=HTTPDownloadStatus.FAILED, errors=[str(error)])


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class StdlibHTTPClient:
    def get(self, url, headers, timeout_seconds, max_bytes):
        request = Request(url, headers=headers)
        opener = build_opener(ProxyHandler({}), _NoRedirect())
        try:
            response = opener.open(request, timeout=timeout_seconds)
        except HTTPError as error:
            response = error
        with response:
            body = response.read(max_bytes + 1)
            return {"status_code": response.status, "headers": dict(response.headers.items()), "body": body}
