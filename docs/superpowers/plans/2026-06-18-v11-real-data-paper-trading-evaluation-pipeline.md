# v11.0 Real-Data Paper Trading Evaluation Pipeline

## Architecture

Introduce a new independent `paper_evaluation_*` layer on top of v10 `feature_store_*` manifests and rows. Keep orchestration in `paper_evaluation_integration_engine.py` and push actual stage logic into dedicated signal, fill, ledger, portfolio, and metrics engines.

## Work Items

- Add canonical `paper_evaluation_models.py`
- Add guard and fixture loader for local-only v11 inputs
- Implement signal replay, fill simulation, ledger simulation, portfolio accounting, and metrics calculation
- Wire CLI report commands
- Extend system smoke with an offline v11 path
- Add focused tests and run full verification

## Verification

- Focused pytest for `paper_evaluation_*` and `test_system_smoke.py`
- Standalone `test_system_smoke.py`
- Full repository `pytest -q`
- Commit and tag `v11.0.0-real-data-paper-trading-evaluation-pipeline`
