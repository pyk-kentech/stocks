# Public HTTP Data Connector / Network Safety Design

## Scope

Add an opt-in public HTTP connector that downloads explicitly configured public
CSV or JSON resources into local normalized files for the existing import
pipeline. The default remains network disabled. This layer does not implement
authentication, cookies, sessions, private API keys, login scraping, brokerage
access, Toss or securities-app scraping, or order execution.

## Safety Boundary

`network_safety.py` validates every initial and redirected URL before transport.
Only `http` and `https` schemes are accepted. URL username/password values,
credential headers, and hosts outside the effective allowlist are blocked.
Hosts are normalized to lowercase without a trailing dot and compared by exact
match; subdomains are not implicitly allowed.

Provider-config allowed hosts and CLI `--allowed-host` values form an
intersection when both are present. URLs written to logs remove query strings
and fragments. Headers and response bodies are never stored in connector
metadata.

## Download Client

`http_download.py` provides a transport-injection boundary and a stdlib client.
The stdlib implementation disables automatic redirects, follows at most five
redirects manually, and revalidates every target. Response data is read in
chunks and aborted when `max_bytes` is exceeded. Tests use fake clients only and
perform no real network calls.

## Provider Config And Connector

`provider_config.py` loads JSON or YAML provider files into HTTPProviderConfig
models. Credential-like headers are rejected. The default connector registry
does not include any public HTTP connector; dynamic registration happens only
when a provider config file is explicitly supplied.

`PublicHTTPConnector` follows the existing BaseConnector contract.
Network-disabled or provider-disabled connectors record `DISABLED`. Safety
blocks and download failures record ConnectorRun `FAILED` with the more precise
HTTP download status in metadata. Successful files use the configured CSV/JSON
extension and reuse existing row-count logic.

## CLI And Import Integration

`validate-provider-config` reports provider-level validation without transport.
`run-http-connector` executes one configured provider. Existing
`run-connectors-and-import` accepts provider config, network enablement, and
runtime allowed-host options. Public provider failures remain isolated while
successful mock, local, or HTTP outputs continue into unified import.
