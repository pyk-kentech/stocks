## v15.0.2 Local LLM Advisory Runtime Boundary Design

### Milestone

- Version: `v15.0.2`
- Final tag: `v15.0.2-local-llm-advisory-runtime-boundary`
- Version discipline:
  - do not create `v16`
  - do not modify `v15.0.0` or `v15.0.1` tags

### Starting Point

Current stable baseline before this corrective milestone:

- v15.0.1 tag: `v15.0.1-real-chart-capture-offline-strategy-postcheck-fix`
- commit: `3bab3d63e026bb75ba8599508f530c653062152a`
- full pytest: `2872 passed, 1 warning`
- working tree: clean

Important correction:

- existing `local_llm_*` code is fixture-only and advisory-only
- no real local LLM runtime is currently connected
- this milestone adds a real local LLM runtime adapter boundary
- that runtime remains advisory-only and optional
- it must not sit on the critical path for offline strategy training

### Goal

After v15.0.2 the user should be able to:

1. run real Kiwoom `KA10081` and `KA10080` historical chart capture
2. generate `HistoricalOhlcvDatasetManifest`
3. run offline strategy training launch plan
4. run bounded grid search
5. run anchored walk-forward validation
6. run conservative backtest
7. run stability-first promotion gate
8. optionally attach a local LLM advisory summary after the numeric result already exists

Local LLM runtime is not required for steps 1 through 7.

### Hard Safety Boundary

The whole milestone remains fail-closed around these rules:

- no live trading
- no paper trading execution
- no real order
- no account read
- no account mutation
- no account/order API
- no executable order output
- no buy/sell recommendation output
- no LLM control over promotion gate
- no LLM control over strategy parameter selection
- no LLM control over Kiwoom capture
- no LLM access to credentials, tokens, API keys, account numbers, or broker routes
- no cloud LLM calls by default
- no local LLM runtime in pytest
- no network calls in pytest
- no external provider calls in pytest
- no raw prompt containing credentials or account/order payloads
- all LLM output is treated as untrusted text and passed through safety guard

### Hardware Target

Target hardware is a dual RTX 4090-class machine.

Interpretation:

- treat hardware as 2 separate 24GB GPUs
- do not assume a guaranteed unified 48GB memory pool
- support multi-GPU inference through backend metadata, not hardcoded allocator assumptions
- default advisory profile should be conservative and stable
- tests must not require a specific real model file

Recommended advisory model policy:

- dual 4090 stable/default recommendation: `LARGE_30B_34B` quantized
- dual 4090 experimental recommendation: `XL_70B_QUANTIZED`
- example alias such as `Qwen/Qwen3-32B-AWQ` may be documented
- no model alias is required for numeric offline strategy execution

### Architecture

Proceed with a new independent `local_llm_runtime_*` boundary layer.

#### Numeric pipeline stays closed

`offline_strategy_*` remains numerically closed and deterministic:

- no embedded runtime LLM transport
- no promotion mutation
- no parameter override
- no strategy selection override
- no dependency on model download, vLLM server, or local runtime

#### Advisory is optional post-processing

`local_llm_advisory_engine` becomes the orchestration layer:

- build redacted advisory context
- select fixture-only or runtime-backed execution
- call runtime boundary only after explicit opt-in
- apply output guard
- return advisory-only metadata

`offline_strategy_integration_engine` may attach advisory metadata only after the numeric result already exists.

Advisory failure must not invalidate or change the numeric result.

### Required Layers

#### 1. `local_llm_runtime_models.py`

Defines:

- backend, mode, hardware, quantization, model profile enums
- runtime config
- runtime request and response
- advisory task, advisory context, advisory result
- capability, safety, and gap reports

#### 2. `local_llm_runtime_config.py`

Responsibilities:

- bounded runtime config parsing
- default disabled behavior
- local OpenAI-compatible endpoint config
- vLLM dual-GPU metadata such as `tensor_parallel_size=2`
- Ollama and llama.cpp preview-only config in v15.0.2

#### 3. `local_llm_runtime_guard.py`

Responsibilities:

- pytest runtime block
- loopback-only URL validation
- credential, account, and order marker block
- forbidden advisory task block
- VRAM and context policy
- output guard

#### 4. `local_llm_runtime_client.py`

Responsibilities:

- common client interface
- bounded timeout handling
- no real calls in tests
- redacted error handling

#### 5. `local_llm_runtime_adapters.py`

Responsibilities:

- real local HTTP call only for OpenAI-compatible loopback endpoint
- allow `VLLM_OPENAI_COMPAT`
- allow `CUSTOM_HTTP_OPENAI_COMPAT`
- keep `OLLAMA_HTTP` and `LLAMACPP_SERVER` as config, report, and request-preview only unless exposed through an OpenAI-compatible loopback endpoint

#### 6. `local_llm_advisory_engine.py`

Responsibilities:

- task-to-prompt shaping
- redacted summary construction
- fixture/runtime selection
- output guard application
- advisory-only result creation

#### 7. `offline_strategy_integration_engine.py`

Responsibilities:

- optional post-result advisory attachment only
- keep numeric result valid when advisory is skipped, disabled, blocked, downgraded, or failed

### Core Models

#### Runtime enums

- `LocalLLMRuntimeBackend`
  - `LOCAL_LLM_DISABLED`
  - `FIXTURE_ONLY`
  - `OLLAMA_HTTP`
  - `VLLM_OPENAI_COMPAT`
  - `LLAMACPP_SERVER`
  - `CUSTOM_HTTP_OPENAI_COMPAT`
  - `REJECTED`
- `LocalLLMRuntimeMode`
  - `DISABLED`
  - `FIXTURE_ONLY`
  - `RUNTIME_OPT_IN`
  - `RUNTIME_ACTIVE`
  - `BLOCKED_IN_TEST`
- `LocalLLMHardwareProfile`
  - `CPU_ONLY`
  - `SINGLE_24GB_GPU`
  - `DUAL_24GB_GPU`
  - `DUAL_4090_48GB_SPLIT`
  - `UNSUPPORTED`
- `LocalLLMQuantizationProfile`
  - `FP16`
  - `BF16`
  - `Q8`
  - `Q6`
  - `Q5`
  - `Q4`
  - `UNKNOWN`
- `LocalLLMModelProfile`
  - `SMALL_7B_8B`
  - `MEDIUM_14B`
  - `LARGE_30B_34B`
  - `XL_70B_QUANTIZED`
  - `UNSUPPORTED_TOO_LARGE`
  - `MODEL_PROFILE_UNKNOWN`

#### Runtime data models

- `LocalLLMRuntimeConfig`
- `LocalLLMRuntimeRequest`
- `LocalLLMRuntimeResponse`
- `LocalLLMRuntimeCapabilityReport`
- `LocalLLMRuntimeSafetyReport`
- `LocalLLMRuntimeGapReport`

#### Advisory data models

- `LocalLLMAdvisoryTask`
- `LocalLLMAdvisoryContext`
- `LocalLLMAdvisoryResult`

### Advisory Tasks

Allowed advisory tasks:

- `STRATEGY_RESULT_SUMMARY`
- `PROMOTION_DECISION_EXPLANATION`
- `REJECTION_REASON_EXPLANATION`
- `MARKET_REGIME_NARRATIVE`
- `DATA_GAP_SUMMARY`
- `RISK_WARNING_SUMMARY`
- `TRAINING_RUN_REPORT_SUMMARY`
- `HUMAN_REVIEW_CHECKLIST`

Forbidden tasks:

- `BUY_SELL_DECISION`
- `ORDER_GENERATION`
- `POSITION_SIZING_DECISION`
- `ACCOUNT_ACTION`
- `BROKER_API_CALL`
- `KIWOOM_API_CALL`
- `PROMOTION_GATE_OVERRIDE`
- `PARAMETER_SEARCH_OVERRIDE`
- `REALTIME_TRADING_CONTROL`

### Runtime Statuses

Use separate runtime and advisory statuses.

#### Runtime statuses

- `LOCAL_LLM_RUNTIME_DISABLED`
- `LOCAL_LLM_FIXTURE_ONLY`
- `LOCAL_LLM_RUNTIME_OPT_IN_REQUIRED`
- `LOCAL_LLM_RUNTIME_READY`
- `LOCAL_LLM_RUNTIME_BLOCKED_IN_TEST`
- `BLOCKED_NETWORK_IN_TEST`
- `BLOCKED_VRAM_POLICY`
- `DOWNGRADED_CONTEXT_POLICY`
- `DEPENDENCY_GAP`
- `REJECTED`

#### Advisory statuses

- `ADVISORY_SKIPPED`
- `LOCAL_LLM_ADVISORY_READY`
- `LOCAL_LLM_OUTPUT_BLOCKED`
- `LOCAL_LLM_OUTPUT_DOWNGRADED`
- `BLOCKED_CREDENTIAL_EXPOSURE`
- `BLOCKED_EXECUTABLE_ADVICE`
- `BLOCKED_ACCOUNT_OR_ORDER`
- `REJECTED`

### Default Behavior

- runtime disabled by default
- fixture-only in tests
- real runtime only outside pytest
- explicit local opt-in required for real runtime
- OpenAI-compatible local loopback endpoint is the only real runtime execution path in v15.0.2
- offline strategy results remain valid even if advisory is skipped, disabled, blocked, downgraded, or fails

### Backend Policy

Execution-capable backends in v15.0.2:

- `LOCAL_LLM_DISABLED`
- `FIXTURE_ONLY`
- `VLLM_OPENAI_COMPAT`
- `CUSTOM_HTTP_OPENAI_COMPAT`

Config and preview only in v15.0.2:

- `OLLAMA_HTTP`
- `LLAMACPP_SERVER`

Loopback-only runtime policy:

- only `localhost`
- only `127.0.0.1`
- unix socket if implemented locally
- reject non-local URLs
- reject cloud or public hostnames

### Prompt Input Policy

Allowed prompt inputs:

- redacted summaries
- metric summaries
- strategy template IDs
- promotion decisions
- coverage and gap reports
- non-sensitive metadata

Forbidden prompt inputs:

- API keys
- tokens
- authorization headers
- account numbers
- order IDs
- credential paths
- raw broker payloads
- executable order objects
- raw unbounded dataframes

Prompt shaping rules:

- truncate or summarize large inputs
- always include `non_executable`, `advisory_only`, and `human_review_required`

### Output Guard Policy

Detect and block or downgrade outputs containing:

- buy now
- sell now
- execute
- order
- market order
- limit order instruction
- account action
- position size instruction
- broker or API instruction
- raw credential echo
- token or header echo
- guaranteed profit claims
- unsupported certainty claims
- promotion override language

Output guard outcomes:

- safe output: `LOCAL_LLM_ADVISORY_READY`
- disabled: `LOCAL_LLM_RUNTIME_DISABLED`
- no opt-in: `LOCAL_LLM_RUNTIME_OPT_IN_REQUIRED`
- skipped: `ADVISORY_SKIPPED`
- unsafe output: `LOCAL_LLM_OUTPUT_BLOCKED`
- partially unsafe or over-assertive output: `LOCAL_LLM_OUTPUT_DOWNGRADED`

### CLI Surface

Add:

- `local-llm-runtime-capability-report`
- `local-llm-runtime-config-report`
- `local-llm-advisory-fixture-report`
- `local-llm-advisory-runtime-report`
- `local-llm-safety-report`
- `local-llm-gap-report`

CLI behavior:

- report-only by default
- runtime disabled by default
- fixture-only in tests
- real runtime requires explicit local opt-in:
  - `--allow-local-llm-runtime`
  - `--acknowledge-advisory-only`
  - `--acknowledge-no-trading-control`
  - `--acknowledge-no-credentials-in-prompt`
- output remains redacted JSON only

Input support:

- support both offline strategy input and standalone advisory fixture input
- default input priority is offline strategy input

Preferred runtime invocation path:

1. offline strategy fixture or report input
2. numeric offline strategy result created first
3. optional advisory runtime report runs afterward

### Integration With Offline Strategy

`offline_strategy_*` remains:

- numeric
- deterministic
- backtest and walk-forward driven
- promotion-gate driven

LLM may:

- summarize results after promotion or rejection
- explain risk warnings
- explain gap summaries
- produce human review checklist text

LLM must not:

- change promotion decision
- choose parameters
- select final strategy
- invalidate numeric result on failure

Advisory result storage:

- stored only as optional report metadata
- absent advisory is normal and non-blocking

### Verification Plan

Focused tests:

- `tests/test_local_llm_runtime_models.py`
- `tests/test_local_llm_runtime_guard.py`
- `tests/test_local_llm_runtime_config.py`
- `tests/test_local_llm_runtime_client.py`
- `tests/test_local_llm_runtime_adapters.py`
- `tests/test_local_llm_advisory_runtime_cli.py`
- update `tests/test_system_smoke.py`

Focused assertions:

- runtime disabled by default
- pytest blocks real runtime
- loopback-only URL validation
- forbidden tasks blocked
- prompt redaction blocks credentials, account, and order markers
- output guard blocks executable advice
- offline strategy numeric result remains valid when advisory is skipped or blocked
- no real runtime call in pytest
- no cloud LLM call
- no account or broker path

System smoke must prove:

- local LLM fixture advisory still passes
- real runtime blocked in pytest
- unsafe output blocked
- safe advisory summary accepted
- offline strategy works without local LLM
- no cloud LLM called
- no local runtime called in tests

Required milestone verification commands:

- `python3.11 -m pytest tests/test_system_smoke.py -q`
- `python3.11 -m pytest -q`

### Acceptance

v15.0.2 is complete when:

- a new independent `local_llm_runtime_*` boundary exists
- real runtime remains advisory-only and optional
- offline strategy training works with local LLM disabled
- no model download is required
- no vLLM server is required for offline strategy training
- no advisory output can change numeric strategy results
- no runtime call occurs in pytest
- no credential, token, account, or order material enters prompt or output
- CLI reports exist for capability, config, fixture, runtime, safety, and gap
- focused tests, `tests/test_system_smoke.py`, and full `pytest` pass
