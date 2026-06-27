## v15.0.4 Kiwoom OAuth KA10081 Real Capture And Train Design

### Milestone

- Version: `v15.0.4`
- Final tag: `v15.0.4-kiwoom-oauth-ka10081-real-capture-and-train`
- Commit message target: `Implement Kiwoom OAuth KA10081 capture and training run path`

### Starting Point

Current repository state before this milestone:

- repo: `/home/yoonkeun/stocks`
- functional baseline tag: `v15.0.3-kiwoom-real-chart-network-capture-runner`
- v15.0.3 commit: `93f181c786e8c67c104717ecdb3ed8e6e6c45104`
- full pytest after v15.0.3: `2879 passed, 1 warning`

Known current state:

- fail-closed hybrid corrective is complete
- fake or mock KA10081 rows can flow through raw_lake -> normalized OHLCV -> coverage -> `HistoricalOhlcvDatasetManifest`
- real Kiwoom network path is still blocked or dependency-gapped

### Goal

Finish the full usable read-only real-data path in one corrective milestone:

1. appkey and secretkey load from local credential refs
2. OAuth access token issuance
3. `Authorization: Bearer <token>` creation
4. KA10081 real endpoint call
5. real daily chart row reception
6. raw_lake storage
7. OHLCV normalization
8. `HistoricalOhlcvDatasetManifest` generation and persistence
9. persisted manifest reload
10. offline strategy training execution

This milestone must implement actual working code, not only boundaries, specs, or reports.

### Hard Safety Boundary

Allowed:

- real local credential file read outside pytest with explicit opt-in
- real HTTP POST to Kiwoom OAuth token endpoint outside pytest with explicit opt-in
- real HTTP POST to Kiwoom chart endpoint outside pytest with explicit opt-in
- real raw_lake, OHLCV, manifest generation from provider rows
- real offline strategy training over generated manifest

Forbidden:

- no account API
- no order API
- no account read
- no account mutation
- no broker mutation
- no executable buy, sell, or order output
- no autonomous trading
- no live order
- no paper order
- no raw credential logging
- no token or header logging
- no secrets in raw_lake, logs, reports, manifest, or training artifacts
- no network calls in pytest
- no credential reads in pytest unless tests create fake tmp fixtures
- no fake success path
- no `row_count=0` pseudo-success
- no “implemented” claim if runtime cannot emit token, request, and response diagnostics

### Official Kiwoom REST Facts To Encode

OAuth token issuance:

- method: `POST`
- real domain: `https://api.kiwoom.com`
- mock domain: `https://mockapi.kiwoom.com`
- path: `/oauth2/token`
- content type: `application/json;charset=UTF-8`
- body:
  - `grant_type: client_credentials`
  - `appkey`
  - `secretkey`
- response fields include:
  - `expires_dt`
  - `token_type`
  - `token`
  - `return_code`
  - `return_msg`

Chart APIs listed in official guide:

- `ka10080` minute chart request
- `ka10081` daily chart request

Implement `KA10081` first.

Implement `KA10080` only if request and schema evidence is clear enough from repo-local docs or runtime guide.

### Architecture

Use an explicit three-boundary pipeline plus one wrapper.

#### 1. `kiwoom_oauth_*`

Responsibilities:

- credential ref parsing
- preflight validation
- token issuance
- token cache and token store
- token ref reporting only

#### 2. `kiwoom_chart_*`

Responsibilities:

- environment-specific endpoint config
- KA10081 request building
- auth header injection from token ref
- real response parsing
- tolerant chart row extraction without silent guessing

#### 3. `historical_market_data_*`

Responsibilities:

- raw_lake persistence
- OHLCV normalization
- coverage report generation
- `HistoricalOhlcvDatasetManifest` generation
- persisted manifest write and reload validation

#### 4. Wrapper orchestration

Responsibilities:

- capture
- persisted manifest handoff
- offline strategy training
- final summary output

### Default Handoff Rule

Support both handoff modes, but make persisted manifest the default.

Default:

1. capture KA10081 rows
2. write raw_lake artifacts
3. normalize OHLCV
4. generate and persist `HistoricalOhlcvDatasetManifest` JSON
5. re-read that manifest JSON from disk
6. pass the reloaded manifest into offline strategy training
7. write final capture-and-train summary with:
   - `manifest_path`
   - `manifest_id`
   - raw_lake paths
   - normalized OHLCV paths
   - training output root
   - promotion gate output path

Optional:

- `--training-handoff-mode in_process`

Even in `in_process` mode:

- still persist manifest JSON unless explicitly running a test fixture path

Failure behavior:

- manifest write failure blocks training
- manifest reload or validation failure blocks training
- training failure keeps capture artifacts and manifest for rerun
- success requires both persisted manifest and training outputs

### Part A. Kiwoom OAuth Token Module

Create or modify:

- `src/stock_risk_mcp/kiwoom_oauth_models.py`
- `src/stock_risk_mcp/kiwoom_oauth_credential_ref.py`
- `src/stock_risk_mcp/kiwoom_oauth_client.py`
- `src/stock_risk_mcp/kiwoom_oauth_token_store.py`
- `src/stock_risk_mcp/kiwoom_oauth_guard.py`
- `src/stock_risk_mcp/kiwoom_oauth_cli.py` or integrate into `cli.py`

#### OAuth models

- `KiwoomEnvironment`
  - `MOCK`
  - `REAL`
- `KiwoomOAuthEndpointConfig`
  - environment
  - base_url
  - token_path
  - content_type
  - timeout_seconds
- `KiwoomCredentialRef`
  - credential_ref
  - appkey_ref_path
  - secretkey_ref_path
  - credential_id
  - source_kind
- `KiwoomOAuthTokenIssueRequest`
  - environment
  - credential_ref
  - grant_type
  - endpoint
  - opt-in flags
- `KiwoomOAuthTokenIssueResponse`
  - status
  - token_type
  - token_ref
  - expires_dt
  - return_code
  - return_msg_redacted
  - issued_at
  - expires_at if parseable
  - redaction_status
- `KiwoomOAuthTokenRef`
  - token_ref_path
  - token_type
  - expires_dt
  - issued_at
  - environment
  - credential_fingerprint_redacted
- `KiwoomOAuthStatus`
  - `TOKEN_PREFLIGHT_READY`
  - `TOKEN_ISSUED`
  - `TOKEN_CACHE_HIT`
  - `TOKEN_EXPIRED`
  - `TOKEN_REFRESH_REQUIRED`
  - `BLOCKED_CREDENTIAL_MISSING`
  - `BLOCKED_CREDENTIAL_FORMAT`
  - `BLOCKED_TOKEN_ENDPOINT_CONFIG`
  - `BLOCKED_NETWORK_IN_TEST`
  - `BLOCKED_REAL_OAUTH_OPT_IN_REQUIRED`
  - `PROVIDER_AUTH_ERROR`
  - `PROVIDER_TOKEN_ERROR`
  - `TRANSPORT_ERROR`
  - `REJECTED`

#### Credential contract

Support all of:

Directory form:

- `<credential_ref_dir>/66787923_appkey.txt`
- `<credential_ref_dir>/66787923_secretkey.txt`

Generic directory fallback:

- `<credential_ref_dir>/appkey.txt`
- `<credential_ref_dir>/secretkey.txt`

Explicit path object form:

- `appkey_ref_path`
- `secretkey_ref_path`

Each txt file must contain only the raw one-line value.

If labeled text such as `api:` or `app secret:` is present:

- return `BLOCKED_CREDENTIAL_FORMAT`

Never print raw values.

#### Token store

Default token store:

- `/home/yoonkeun/.secrets/kiwoom_tokens/`

Also support:

- `--token-store-root`

Requirements:

- token files are outside repo by default
- token file mode is `600`
- token values never appear in logs
- reports include token ref only
- valid token cache is reused unless `--force-refresh-token`
- expired or missing token triggers refresh

#### OAuth HTTP

Implement actual HTTP POST outside pytest:

- `POST {base_url}/oauth2/token`
- `Content-Type: application/json;charset=UTF-8`
- body:
  - `grant_type`
  - `appkey`
  - `secretkey`

Use standard library transport unless existing repo-local style clearly prefers another lightweight path.

Bound timeout.

Capture:

- HTTP status code
- `return_code`
- `return_msg`

Redact response before logs.

If token is returned:

- write token store
- return token ref

### Part B. Kiwoom KA10081 Chart Module

Create or modify:

- `src/stock_risk_mcp/kiwoom_chart_models.py`
- `src/stock_risk_mcp/kiwoom_chart_schema.py`
- `src/stock_risk_mcp/kiwoom_chart_client.py`
- `src/stock_risk_mcp/kiwoom_chart_guard.py`
- `src/stock_risk_mcp/historical_market_data_transport.py`
- `src/stock_risk_mcp/historical_market_data_capture_runner.py`
- `src/stock_risk_mcp/historical_market_data_real_capture.py`
- `src/stock_risk_mcp/historical_market_data_models.py`
- `src/stock_risk_mcp/historical_market_data_normalizer.py`

#### KA10081 request path

Implement actual request path if repo-local official docs or runtime guide give sufficient evidence for:

- endpoint path
- required headers
- body fields
- continuation semantics

Do not silently guess.

Do not stop at dependency gap if local evidence is sufficient to implement.

#### KA10081 runtime behavior

Required:

- token ref load
- `Authorization: Bearer <token>` construction in-memory only
- actual local opt-in HTTP request outside pytest
- daily chart row extraction
- raw_lake persistence only for valid row payloads
- OHLCV normalization
- manifest generation

If response is auth failure:

- return provider auth or token error

If response shape is insufficient:

- return explicit schema gap

If rows are valid:

- continue full success path

### Part C. Capture, Manifest, And Train Wrapper

Create or modify:

- `src/stock_risk_mcp/historical_market_data_manifest_engine.py`
- `src/stock_risk_mcp/offline_strategy_integration_engine.py`
- `src/stock_risk_mcp/offline_strategy_fixture.py`
- `src/stock_risk_mcp/offline_strategy_models.py`
- `src/stock_risk_mcp/cli.py`
- `scripts/run_kiwoom_ka10081_capture_and_train.sh`

#### Wrapper command

Required:

- `kiwoom-ka10081-capture-and-train-run`

Default flow:

1. token preflight
2. token issue or cache hit
3. real KA10081 capture
4. raw_lake write
5. OHLCV normalization
6. manifest write
7. manifest reload
8. offline strategy training
9. promotion gate summary

#### Final summary output

Must include:

- `status`
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

### CLI Surface

Required commands:

- `kiwoom-oauth-token-preflight-report`
- `kiwoom-oauth-token-issue-run`
- `historical-market-data-real-capture-run`
- `historical-market-data-real-capture-and-manifest-run`
- `kiwoom-ka10081-capture-and-train-run`

Optional support commands:

- `kiwoom-oauth-token-cache-report`
- `kiwoom-ka10081-request-preview-report`
- `kiwoom-ka10081-response-parse-report`

### Safety Rules

OAuth and token:

- no network in pytest
- no credential reads in pytest except fake tmp fixtures used by tests
- no raw token or header logging
- token ref only in reports

Chart capture:

- read-only chart data only
- no account API
- no order API
- no account read
- no broker mutation
- valid rows required for success path

Manifest handoff:

- manifest write failure stops training
- manifest reload failure stops training
- training failure keeps capture artifacts

Wrapper:

- no executable trading output
- summary is redacted and filesystem-oriented only

### Verification Plan

Focused tests:

- OAuth credential directory form
- OAuth explicit credential path form
- invalid labeled credential format
- token cache hit
- token refresh
- pytest network block
- KA10081 request build
- KA10081 tolerant row parse
- auth or token error status
- provider empty response status
- schema gap status
- valid rows -> raw_lake -> OHLCV
- manifest write success
- manifest write failure blocks training
- manifest reload failure blocks training
- persisted manifest default path
- `in_process` optional path still writes manifest
- one-shot wrapper success path with fake or controlled transport
- training failure preserves manifest
- summary paths emitted

System smoke must prove:

- no real network in pytest
- no credential leak
- current smoke remains green

Required commands:

- `python3.11 -m pytest tests/test_system_smoke.py -q`
- `python3.11 -m pytest -q`

### Acceptance

v15.0.4 is complete when:

- real OAuth token issuance is actually implemented for local opt-in runtime
- real or controlled mock KA10081 rows can reach manifest and training path
- persisted manifest handoff is the default
- one-shot wrapper exists
- no fake success path remains
- no account, order, or trading path is introduced
- focused tests, `tests/test_system_smoke.py`, and full `pytest` pass
