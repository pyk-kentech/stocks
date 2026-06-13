from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit, urlunsplit


CREDENTIAL_HEADER_PARTS = (
    "authorization", "cookie", "api-key", "apikey", "access-token", "auth-token",
    "secret", "private-key", "proxy-authorization",
)


def is_localhost(host: str) -> bool:
    normalized = _host(host)
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def is_allowed_host(url: str, allowed_hosts: list[str]) -> bool:
    try:
        host = _host(urlsplit(url).hostname or "")
    except ValueError:
        return False
    return bool(host) and host in {_host(item) for item in allowed_hosts}


def validate_public_http_url(url: str, allowed_hosts: list[str]) -> list[str]:
    errors: list[str] = []
    try:
        parsed = urlsplit(url)
    except ValueError as error:
        return [f"invalid URL: {error}"]
    if parsed.scheme.lower() not in {"http", "https"}:
        errors.append("only http/https URLs are allowed")
    if parsed.username or parsed.password:
        errors.append("URL username/password credentials are not allowed")
    if not parsed.hostname:
        errors.append("URL host is required")
    elif not is_allowed_host(url, allowed_hosts):
        errors.append("URL host is not in allowed_hosts")
    return errors


def validate_no_credentials(headers: dict[str, str]) -> list[str]:
    errors = []
    for key in headers:
        normalized = key.strip().lower().replace("_", "-")
        if any(part in normalized for part in CREDENTIAL_HEADER_PARTS):
            errors.append(f"credential header is not allowed: {key}")
    return errors


def sanitize_url_for_logging(url: str) -> str:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return "<invalid-url>"
    host = parsed.hostname or ""
    if ":" in host:
        host = f"[{host}]"
    try:
        port = parsed.port
    except ValueError:
        port = None
    if port:
        host = f"{host}:{port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def effective_allowed_hosts(config_hosts: list[str], runtime_hosts: list[str] | None = None) -> list[str]:
    configured = {_host(item) for item in config_hosts}
    if runtime_hosts is None:
        return sorted(configured)
    return sorted(configured & {_host(item) for item in runtime_hosts})


def _host(value: str) -> str:
    return value.strip().lower().rstrip(".")
