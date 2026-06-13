# Provider Pack #2: News Public Data Adapter Design

## Goal

Extend the existing Provider Pack orchestration with a news-only pack that
acquires public HTTP or local files, normalizes provider-specific news fields,
imports NEWS signals, and preserves existing signal enrichment behavior.

## Configuration Contract

`provider_pack_config.news.providers` is the single source of connector and
normalizer configuration. Each provider uses the same structure as Price and
FX providers. Required news column mappings are:

- `ticker`
- `observed_at`
- `headline`
- `source_name`

Optional mappings are `url`, `sentiment`, `severity`, and `summary`. There is
no separate normalizer config file. The config does not require `title`;
`headline` names the external provider concept.

## Normalized News Contract

The existing internal signal contract remains title-based. The news
normalizer maps provider `headline` to internal `title`. It also emits
`source_name`, `summary`, `url`, normalized `sentiment`, normalized `severity`,
News Pack-specific `score_delta`, and `raw_payload_json`.

`INFO` severity is normalized to internal `LOW`; the original provider row,
including the original severity, remains in `raw_payload_json`. Missing
optional values use conservative defaults: no URL or summary, neutral
sentiment, and LOW severity.

## News Pack Scoring

Only normalized News Provider Pack outputs use this conservative score policy:

- positive INFO/LOW: +1
- positive MEDIUM: +2
- positive HIGH or CRITICAL: +3
- negative INFO/LOW: -1
- negative MEDIUM: -3
- negative HIGH: -5
- negative CRITICAL: -10
- neutral or unknown: 0

The shared `calculate_signal_score` function and legacy signal file behavior
remain unchanged.

## Import Compatibility

Unified import accepts the richer normalized news fields when present:
`source_name`, `severity`, `score_delta`, `url`, and `raw_payload_json`.
Provider headlines are already mapped to `title` before import. Legacy news
files without these richer fields retain their current event/materiality-based
mapping and common signal score.

The existing enrichment contract remains unchanged: critical negative signals
exclude candidates, high negative signals downgrade INCLUDE to WATCH, and
positive signals never promote an existing EXCLUDE candidate.

## Provider Pack Integration

Add `ProviderPackType.NEWS`, `ProviderPackConfig.news`, and a small
`run_news_provider_pack` wrapper. The existing generic Provider Pack pipeline
selects news providers and considers a successful NEWS_SIGNAL import a
successful News pack.

Public HTTP continues to require explicit network enablement and exact
allowlists. Local files run without network access. Existing connector,
normalization, import, and ProviderPackRun records remain the audit trail.

## CLI And Documentation

Add `run-news-provider-pack` with the existing Provider Pack arguments.
`provider-pack-runs` and `provider-pack-show` continue to inspect all pack
types. README documents the news config, headline/title mapping, INFO/LOW
mapping, News Pack-only scoring, and network safety boundaries.

## Verification

Tests cover news config validation, headline-to-title mapping, optional
defaults, raw severity preservation, News Pack scores, HTTP-disabled and
local-file behavior, fake HTTP acquisition, import into NEWS signals,
enrichment behavior, CLI execution, and unchanged Price/FX and common scoring
behavior. Final verification runs the complete pytest suite, compileall, git
diff check, and network-free system smoke.
