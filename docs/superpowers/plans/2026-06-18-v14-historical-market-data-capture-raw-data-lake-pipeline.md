# v14.0 Historical Market Data Capture / Raw Data Lake / OHLCV Normalization Implementation Plan

## Scope

- Build a new independent `historical_market_data_*` surface.
- Support schema-ready Kiwoom chart evidence only for `KA10080` and `KA10081`.
- Keep `KA10079`, `KA10082`, `KA10083`, and `KA10094` in the API catalog as capability-only or schema-gap.
- Allow manual local import and mocked capture only in tests.
- Keep real capture as an explicit blocked boundary with request preview only.

## Implementation Order

1. Add canonical v14 models, fixture loader, and safety guard.
2. Add API catalog and bounded capture-plan engine.
3. Add manual/mock import engine and raw lake writer under safe local roots only.
4. Add OHLCV normalizer for `KA10080` and `KA10081`.
5. Add coverage, completeness, freshness, storage, and manifest engines.
6. Add v8/v10/v11 integration reports and strategy-research-readiness report.
7. Wire CLI commands and `system_smoke`.
8. Add focused pytest coverage and run verification.

## Safety

- No provider or network call in pytest.
- No env or credential read in pytest.
- No account or order API path.
- No executable order or trading output.
- No writes outside safe local roots.

## Source Of Truth

- Source of truth is the coverage report plus normalized OHLCV dataset manifest.
- Raw lake records are preservation artifacts only.
