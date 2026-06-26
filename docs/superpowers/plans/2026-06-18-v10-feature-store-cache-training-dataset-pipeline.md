# v10.0 Feature Store / Cache / Training Dataset Pipeline

## Scope
- Build a new manifest-first `feature_store_*` pipeline for local/offline canonical feature rows, label rows, training rows, walk-forward plans, leakage reports, and dataset manifests.
- Keep physical materialization secondary to the manifest and optional behind safe local backend capability checks.
- Support deterministic label derivation from local price history plus manual label fixtures.
- Remain strictly read-only from provider/account/order/training/paper-trading perspectives.

## Implementation
- Add core feature-store models, guard, backend capability/materialization layer, fixture loader, cache engine, dataset engine, walk-forward engine, and integration engine.
- Add explicit v7/v8/v9 integration reports.
- Add CLI commands for capability, cache, dataset, leakage, split, integration, safety, gap, and materialization reports.
- Extend `system_smoke` with deterministic offline v10 coverage.

## Verification
- `python3.11 -m pytest tests/test_feature_store_models.py tests/test_feature_store_backend.py tests/test_feature_store_cache_engine.py tests/test_feature_store_dataset_engine.py tests/test_feature_store_walk_forward_engine.py tests/test_feature_store_integration_cli.py tests/test_system_smoke.py -q`
- `python3.11 -m pytest -q`

## Milestone Discipline
- Do not create v10.1 or v10.2.
- Tag exactly once at completion:
  - `v10.0.0-feature-store-cache-training-dataset-pipeline`
