# v9.0 External Macro / Regime Data Pipeline

## Scope
- Build a new independent `macro_regime_*` pipeline for external macro and cross-asset regime context.
- Keep the existing `market_regime_*` public contract stable in v9.0.
- Expose canonical macro outputs first, then emit explicit downstream compatibility reports for v7.9, v7.10, v7.11, v7.12, and v8.
- Keep all non-FRED providers boundary-only, manual-import, or mocked in v9.0.
- Keep the entire milestone read-only, report-only, non-trading, and non-account-mutating.

## Public v9 Surface
- `CanonicalMacroSeriesPoint`
- `CanonicalMacroEvent`
- `CanonicalMacroEventWindow`
- `CanonicalMacroRegimeSnapshot`
- `CanonicalRegimeClassification`
- `MacroRegimeProviderCapabilityReport`
- `MacroRegimeFreshnessReport`
- `MacroRegimeConflictReport`
- `MacroRegimeEventWindowReport`
- `MacroRegimeV7IntegrationReport`
- `MacroRegimeV8IntegrationReport`

## Core Inputs
- NQ futures regime input
- ES futures regime input
- VIX input
- Dollar-strength input
- U.S. 10Y yield input
- USD/KRW input
- Economic event calendar input

## Architecture
- `macro_regime_provider_models.py`
  - Define provider enums, capability enums, provider status, credential policy, canonical series identifiers, futures identifiers, snapshot models, reports, and safety flags.
- `macro_regime_provider_guard.py`
  - Enforce provider safety policy, pytest/network blocking, opt-in rules, request preview rules, and redaction policy.
- `macro_regime_provider_fixture.py`
  - Load local/manual fixture inputs for mocked providers, manual calendars, and canonical series/event bundles.
- `macro_regime_provider_client.py`
  - Build provider-specific request previews and mocked/manual parsers.
  - Implement real opt-in HTTP only for FRED.
- `macro_regime_event_calendar.py`
  - Parse manual/mock event JSON and compute canonical event windows compatible with v7.11 event-risk timing semantics.
- `macro_regime_snapshot_engine.py`
  - Merge provider outputs into a canonical macro snapshot plus capability, freshness, completeness, and conflict reports.
- `macro_regime_classifier_engine.py`
  - Classify macro regime from canonical inputs and output a new independent macro regime classification/report surface.
- `macro_regime_integration_engine.py`
  - Build explicit adapter reports into v7.9, v7.10, v7.11, v7.12, and v8 without exposing raw provider semantics downstream.
- `cli.py`
  - Add report-only commands for provider preview, fixture/manual import, snapshot build, classification, and integration reports.
- `system_smoke.py`
  - Add deterministic offline v9 smoke coverage using local/manual fixtures only.

## Provider Matrix

### Default
- Default provider is `LOCAL_FIXTURE`.
- v9.0 must remain useful with no credentials, no env reads, and no network.

### FRED
- Implement request builder.
- Implement mocked parser.
- Implement canonical conversion.
- Implement real opt-in HTTP boundary.
- Real FRED calls are disabled by default.
- Real FRED calls must never run in pytest.
- Real FRED calls require explicit opt-in flags and key-ref/token policy.
- Supported series:
  - `VIXCLS` for VIX
  - `DGS10` for U.S. 10Y yield
  - `DEXKOUS` for USD/KRW
  - `DTWEXBGS` for dollar-strength fallback and must not be labeled exact DXY

### Futures Providers
- `DATABENTO`, `CME`, and `LS_OPEN_API_FUTURE` remain boundary-only in v9.0.
- No real HTTP, websocket, or paid-provider execution in v9.0.
- Implement capability matrix plus manual/local fixture parsing only.
- Provider readiness/status should remain `PROVIDER_SETUP_REQUIRED`, `OPT_IN_REQUIRED`, or equivalent gap state until configured.
- NQ and ES remain explicit provider gaps unless manual futures fixtures are supplied.
- FRED must never be treated as futures coverage.

### BLS and BEA
- No real HTTP in v9.0.
- Implement provider boundary, capability matrix, local/manual fixture parser, and mocked parser where straightforward.
- Represent CPI, NFP, PCE, and GDP as canonical event/data capabilities only.
- If request preview exists, use key-ref placeholder policy only.

### Federal Reserve / BOK / ECOS / Economic Calendar
- No real web or API fetch in v9.0.
- Implement manual JSON event-calendar import only.
- Represent FOMC, CPI, PCE, NFP, GDP, and BOK events through canonical manual or mocked events.
- Compute event windows for downstream v7.11 compatibility.

## Canonical Modeling Rules
- Every canonical series point must include:
  - stable series id
  - provider id
  - observed timestamp
  - available timestamp when known
  - value
  - unit or value semantics
  - source reference
  - freshness metadata
- Every canonical event must include:
  - stable event id
  - event type
  - provider
  - country or region scope
  - title
  - scheduled time
  - timezone
  - importance
  - affected assets
  - pre-event block window
  - reduce-size window
  - post-event cooldown
  - source reference
  - available timestamp when known
- The macro snapshot must expose both data availability and provider gaps explicitly.
- Missing critical inputs must produce gap/readiness findings rather than silent defaults.

## Classification Rules
- Classification must operate on the canonical macro snapshot, not on raw provider payloads.
- Classification must remain report-only and non-executable.
- Classification should at minimum reason over:
  - futures direction and trend evidence for NQ and ES when available
  - VIX stress level
  - dollar-strength condition
  - U.S. 10Y rates condition
  - USD/KRW stress or stability condition
  - active or near-term event windows
- If critical inputs are missing, classification must degrade to explicit gap or partial-readiness states instead of manufacturing confidence.

## Downstream Integration
- `MacroRegimeV7IntegrationReport`
  - Map macro snapshot/classification into compatibility outputs for:
    - v7.9 market regime context
    - v7.10 sizing/risk context
    - v7.11 event-risk context
    - v7.12 leadership/outlier routing context
- `MacroRegimeV8IntegrationReport`
  - Map macro snapshot/classification into v8 domestic snapshot macro-context fields and readiness/gap overlays.
- Existing downstream modules must not depend directly on external provider payloads, credential policy, or transport semantics.

## Safety
- No real provider or network calls in pytest.
- No env read in pytest.
- No raw API key or token output.
- No account path.
- No order path.
- No trading decision output.
- No feature store or parquet in v9.0.
- No non-FRED real HTTP implementation in v9.0.
- Keep report-only, read-only, local-file-safe defaults across all new models and reports.

## CLI
- Add report-oriented commands for:
  - provider capability inspection
  - request preview for FRED
  - fixture/manual import validation
  - macro snapshot build
  - macro classification build
  - v7 integration report
  - v8 integration report
- Any real FRED execution path must require explicit opt-in arguments and must clearly indicate preview versus execute mode.

## Test Plan
- `tests/test_macro_regime_provider_models.py`
  - Validate enums, safety flags, local path policy, provider status policy, and canonical model normalization.
- `tests/test_macro_regime_provider_engine.py`
  - Validate FRED request preview, mocked parser, manual futures fixture parsing, provider gap reporting, and pytest network blocking behavior.
- `tests/test_macro_regime_event_calendar.py`
  - Validate manual event import and event-window computation.
- `tests/test_macro_regime_classifier_engine.py`
  - Validate snapshot-to-classification behavior, partial/gap behavior, and cross-asset stress classification.
- `tests/test_macro_regime_integration_cli.py`
  - Validate CLI output for capability reports, snapshot/classification generation, and downstream integration reports.
- `tests/test_system_smoke.py`
  - Validate deterministic offline v9 smoke coverage using only local/manual fixtures.

## Verification
- `python3.11 -m pytest tests/test_macro_regime_provider_models.py tests/test_macro_regime_provider_engine.py tests/test_macro_regime_event_calendar.py tests/test_macro_regime_classifier_engine.py tests/test_macro_regime_integration_cli.py tests/test_system_smoke.py -q`
- `python3.11 -m pytest -q`

## Milestone Discipline
- Do not create v9.1 or v9.2.
- Finish the entire scope under v9.0.
- Tag exactly once at the end:
  - `v9.0.0-external-macro-regime-data-pipeline`
