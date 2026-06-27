# v15.0.4 Kiwoom OAuth KA10081 Real Capture And Train Implementation Plan

## Scope

This corrective milestone finishes the actual usable read-only Kiwoom REST path:

1. local credential ref load
2. OAuth token issuance and token cache
3. authenticated KA10081 chart capture
4. raw_lake persistence
5. OHLCV normalization
6. `HistoricalOhlcvDatasetManifest` persistence
7. persisted manifest reload
8. offline strategy training run
9. one-shot capture-and-train wrapper

Final tag only:

- `v15.0.4-kiwoom-oauth-ka10081-real-capture-and-train`

## Safety Invariants

- no account API
- no order API
- no account read
- no account mutation
- no broker mutation
- no executable buy, sell, or order output
- no autonomous trading
- no paper order path
- no raw appkey, secretkey, token, or auth header logging
- no token or secret persistence inside repo
- no network calls in pytest
- no non-test credential reads in pytest
- no fake success path for empty or invalid chart responses

## Step 1. OAuth models, guard, and credential contract

Create:

- `src/stock_risk_mcp/kiwoom_oauth_models.py`
- `src/stock_risk_mcp/kiwoom_oauth_credential_ref.py`
- `src/stock_risk_mcp/kiwoom_oauth_guard.py`

Implement:

- `KiwoomEnvironment`
- `KiwoomOAuthEndpointConfig`
- `KiwoomCredentialRef`
- `KiwoomOAuthTokenIssueRequest`
- `KiwoomOAuthTokenIssueResponse`
- `KiwoomOAuthTokenRef`
- `KiwoomOAuthStatus`

Credential contract:

- directory form:
  - `66787923_appkey.txt`
  - `66787923_secretkey.txt`
- generic fallback:
  - `appkey.txt`
  - `secretkey.txt`
- explicit path form:
  - `appkey_ref_path`
  - `secretkey_ref_path`

Guard rules:

- pytest network block
- pytest non-test credential read block
- credential file must contain one-line raw value only
- labeled content produces `BLOCKED_CREDENTIAL_FORMAT`

Verify:

- credential directory tests
- explicit path tests
- labeled credential rejection tests

## Step 2. OAuth client and token store

Create:

- `src/stock_risk_mcp/kiwoom_oauth_client.py`
- `src/stock_risk_mcp/kiwoom_oauth_token_store.py`

Implement:

- bounded `urllib.request` POST to `/oauth2/token`
- `REAL` and `MOCK` environment endpoint config
- token cache reuse
- force refresh path
- token file persistence under `/home/yoonkeun/.secrets/kiwoom_tokens/` by default
- token file mode `600`
- redacted response handling

Verify:

- fake HTTP client token success
- cache hit
- expired token refresh
- pytest real network blocked

## Step 3. CLI for OAuth

Modify:

- `src/stock_risk_mcp/cli.py`

Add commands:

- `kiwoom-oauth-token-preflight-report`
- `kiwoom-oauth-token-issue-run`
- optional `kiwoom-oauth-token-cache-report`

Outputs:

- token preflight readiness
- token issue status
- token ref path only
- redacted fingerprint only

Verify:

- parser registration
- help exposure
- fixture-only tests

## Step 4. KA10081 chart request and parser

Create:

- `src/stock_risk_mcp/kiwoom_chart_models.py`
- `src/stock_risk_mcp/kiwoom_chart_schema.py`
- `src/stock_risk_mcp/kiwoom_chart_client.py`
- `src/stock_risk_mcp/kiwoom_chart_guard.py`

Modify:

- `src/stock_risk_mcp/historical_market_data_transport.py`
- `src/stock_risk_mcp/historical_market_data_capture_runner.py`
- `src/stock_risk_mcp/historical_market_data_real_capture.py`
- `src/stock_risk_mcp/historical_market_data_models.py`
- `src/stock_risk_mcp/historical_market_data_normalizer.py`

Implement:

- actual authenticated KA10081 request path when repo-local evidence is sufficient
- auth header creation from token ref
- real response parsing
- tolerant row extraction
- explicit statuses for:
  - auth or token error
  - provider empty response
  - schema gap
  - transport error

Do not:

- silently guess unsupported schema
- persist empty or invalid row payloads as successful raw_lake capture

Verify:

- valid row parse
- auth/token error
- empty response
- schema gap
- fake/mock row success path still works

## Step 5. Capture + manifest runner

Modify:

- `src/stock_risk_mcp/historical_market_data_manifest_engine.py`
- `src/stock_risk_mcp/historical_market_data_capture_runner.py`
- `src/stock_risk_mcp/cli.py`

Add command:

- `historical-market-data-real-capture-and-manifest-run`

Implement:

- capture
- raw_lake write
- OHLCV normalize
- coverage
- manifest JSON persistence
- manifest reload validation

Failure rules:

- manifest write failure blocks training
- manifest reload failure blocks training

Verify:

- manifest file exists
- manifest reload works
- write failure and reload failure tests

## Step 6. Offline strategy handoff and one-shot wrapper

Modify:

- `src/stock_risk_mcp/offline_strategy_integration_engine.py`
- `src/stock_risk_mcp/offline_strategy_fixture.py`
- `src/stock_risk_mcp/offline_strategy_models.py`
- `src/stock_risk_mcp/cli.py`

Create:

- `scripts/run_kiwoom_ka10081_capture_and_train.sh`

Add command:

- `kiwoom-ka10081-capture-and-train-run`

Default behavior:

- `--training-handoff-mode persisted_manifest`
- write manifest
- reload manifest from disk
- pass reloaded manifest into offline strategy training

Optional:

- `--training-handoff-mode in_process`
- still write manifest unless explicit test-only path

Summary fields:

- `training_handoff_mode`
- `manifest_written`
- `manifest_path`
- `manifest_id`
- `manifest_reloaded`
- `training_started`
- `training_completed`
- `offline_strategy_output_root`
- `promotion_gate_output_path`
- `raw_lake_paths`
- `normalized_ohlcv_paths`

Verify:

- default persisted handoff path
- in-process non-default path
- training failure leaves manifest for rerun

## Step 7. Smoke and regression coverage

Add or update tests:

- `tests/test_kiwoom_oauth_models.py`
- `tests/test_kiwoom_oauth_guard.py`
- `tests/test_kiwoom_oauth_credential_ref.py`
- `tests/test_kiwoom_oauth_client.py`
- `tests/test_kiwoom_oauth_token_store.py`
- `tests/test_kiwoom_chart_client.py`
- `tests/test_kiwoom_chart_schema.py`
- `tests/test_historical_market_data_capture_runner.py`
- `tests/test_historical_market_data_credential_ref.py`
- `tests/test_kiwoom_capture_and_train_cli.py`
- update `tests/test_system_smoke.py`

Smoke assertions:

- no real network in pytest
- no credential leak
- no token leak
- fake row path still reaches manifest and training
- existing system smoke remains green

## Step 8. Verification sequence

Run in order:

1. focused pytest for OAuth and chart modules
2. `python3.11 -m pytest tests/test_system_smoke.py -q`
3. `python3.11 -m pytest -q`

## Acceptance

Close v15.0.4 only when:

- real OAuth token issuance is implemented for local opt-in runtime
- KA10081 chart capture is actually wired to token-bearing HTTP requests
- valid rows can reach persisted manifest and training path
- persisted manifest is the default handoff
- one-shot wrapper exists
- no account, order, or trading path is introduced
- tests pass
