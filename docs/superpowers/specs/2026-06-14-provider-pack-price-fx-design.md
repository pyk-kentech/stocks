# Provider Pack #1: Price and FX Design

## Goal

Add a safe orchestration layer that acquires public or local price and FX raw
files, normalizes them, imports them, and stores an auditable ProviderPackRun.
The layer reuses the existing connector, normalization, unified import, and
network-safety implementations.

## Configuration Contract

One provider pack JSON or YAML file is the single source of connector and
normalizer configuration. It contains `price.providers` and `fx.providers`.
Each provider contains:

- `provider_name`
- exactly one of `url` or `local_file`
- `data_kind`
- `output_format`
- `allowed_hosts`
- `enabled`
- `normalizer`
- `columns`

HTTP providers use the existing PublicHTTPConnector. Local providers copy or
reference the configured local file without network access. A missing
normalizer is recorded as a source failure. Missing required column mappings
are reported during config validation.

No separate normalizer config file or CLI option is introduced.

## Architecture

`provider_pack_config.py` loads and validates the combined configuration.
`provider_packs.py` defines ProviderPackRun models. `provider_pack_pipeline.py`
coordinates acquisition, normalization, import, status aggregation, and run
persistence. `price_provider_pack.py` and `fx_provider_pack.py` are small
entry-point wrappers that select the relevant provider group.

Raw provider files always flow through the configured normalizer before unified
import. Existing connector, NormalizeRun, and ImportRun records remain the
detailed audit trail; ProviderPackRun stores their IDs and aggregate outcome.

## Status Rules

- Network remains disabled unless `enable_network=true`.
- Disabled HTTP providers create DISABLED ConnectorRuns.
- Provider acquisition or normalization failures are isolated where possible.
- A price-only pack completes when at least one price source imports
  successfully; partial source failures produce PARTIAL.
- An FX-only pack follows the same rule for FX sources.
- A combined pack treats price as core. If price has no successfully imported
  output, the combined result is FAILED. If price succeeds and FX fails, the
  combined result is PARTIAL.
- When no raw output exists, normalization and import are skipped and their IDs
  remain null.

## Persistence

Add a backward-compatible `provider_pack_runs` table. Repository helpers save,
get, and list ProviderPackRun records. Pack execution saves its run by default,
while all detailed connector, normalize, and import records continue using
their existing repositories.

## CLI

Add:

- `run-price-provider-pack`
- `run-fx-provider-pack`
- `run-price-fx-provider-pack`
- `provider-pack-runs`
- `provider-pack-show`

Run commands accept one `--provider-pack-config`, output directory, as-of date,
optional ticker filters, explicit `--enable-network`, and runtime allowed-host
restrictions. No normalizer-config option exists.

## Safety

The pack adds no downloader, authentication, cookies, sessions, scraping,
broker API, or order execution. Public HTTP access remains opt-in and
allowlisted through the existing Safe HTTP Connector. Tests inject fake clients
and perform no external network calls. System smoke remains network-free.

## Verification

Tests cover config validation, persistence, disabled network behavior,
fake-client price and FX end-to-end flows, missing normalization configuration,
combined status aggregation, and all new CLI commands. Final verification runs
the complete pytest suite, compileall, git diff check, and system smoke.
