# Provider Pack #3: Dilution / Filings Public Data Adapter Design

## Goal

Extend the existing Provider Pack orchestration with a dilution-only pack that
acquires public HTTP or local filings exports, normalizes provider fields,
imports conservative DILUTION signals, and feeds existing signal enrichment.

## Configuration Contract

`provider_pack_config.dilution.providers` is the single source of connector and
normalizer configuration. Required column mappings are:

- `ticker`
- `observed_at`
- `event_type`
- `dilution_risk`
- `source_name`

Optional mappings are `filing_date`, `filing_type`, `title`, `summary`, `url`,
`shares_before`, `shares_after`, `offering_amount_usd`, and
`accession_number`. There is no separate normalizer config file.

## Normalized Dilution Contract

The Provider Pack-specific dilution normalizer emits the existing internal
signal fields plus provider evidence:

- `ticker`, `observed_at`, `event_type`, `source_name`
- generated or provider `title`, optional `summary` and `url`
- normalized `severity`, `sentiment`, and `score_delta`
- complete provider row in `raw_payload_json`

Filing-specific fields remain in `raw_payload_json`. A missing title is
generated from `event_type`.

## Risk Mapping

Dilution signals never provide a positive boost. The Provider Pack applies:

- NONE: LOW severity, neutral direction, score 0
- LOW: LOW severity, negative direction, score -1
- MEDIUM: MEDIUM severity, negative direction, score -3
- HIGH: HIGH severity, negative direction, score -7
- CRITICAL: CRITICAL severity, negative direction, score -10
- UNKNOWN or unrecognized: HIGH severity, negative direction, score -7

This scoring applies only to richer Dilution Provider Pack output. Shared
signal scoring and legacy dilution file behavior remain unchanged.

## Enrichment And Hard-Risk Boundary

Imported Provider Pack records are DILUTION signals. Existing enrichment rules
therefore downgrade HIGH and UNKNOWN negative dilution from INCLUDE to WATCH,
and exclude CRITICAL negative dilution. Positive signals never promote an
existing EXCLUDE candidate.

This stage does not convert Provider Pack signals into
`CompanyRisk.dilution_risk`. Existing Risk Engine rules
`block_dilution_high` and `block_unknown_dilution` remain unchanged, but a
direct Provider Pack signal-to-CompanyRisk hard-risk bridge is future work.
This avoids automatic hard blocks without a defined as-of and source
precedence contract.

## Provider Pack Integration

Add `ProviderPackType.DILUTION`, `ProviderPackConfig.dilution`, and
`run_dilution_provider_pack`. The generic Provider Pack pipeline selects
dilution providers and treats a successful DILUTION_SIGNAL import as success.

Public HTTP remains default-off and allowlisted. Redirect targets are
revalidated by the existing safe downloader. Local files run without network.
Existing connector, NormalizeRun, ImportRun, and ProviderPackRun records remain
the audit trail.

## CLI And Documentation

Add `run-dilution-provider-pack` with existing Provider Pack arguments.
Existing list/show commands inspect DILUTION runs. README and WORK_SUMMARY
document the config, mappings, enrichment effects, and intentionally absent
CompanyRisk hard-risk bridge.

## Verification

Tests cover config validation, all dilution risk mappings, raw payload
preservation, local and fake HTTP flows, missing normalizer behavior, imported
DILUTION signals, HIGH/CRITICAL enrichment, unchanged common scoring and Risk
Engine rules, absence of automatic CompanyRisk conversion, CLI inspection, and
unchanged Price/FX/News packs. Final verification runs the full pytest suite,
compileall, git diff check, and network-free system smoke.
