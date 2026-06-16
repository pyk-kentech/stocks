# v3.9 Local Model Runtime Adapter / Model Selection Design

## Scope

v3.9 designs the next layer after v3.8 local LLM advisory hardening. It covers
two things together:

- local model candidate selection criteria
- a contract-first mock runtime adapter interface for future local-only model
  integration

v3.9 is design only in this step. It does not implement any runtime adapter,
does not integrate any real model backend, and does not perform inference.

The local model remains advisory-only. It must not become a trader, execution
agent, broker adapter, or order decision maker.

## Release Baseline

The design assumes the current completed release line is:

- `v3.0.0-strategy-core-local-llm-safety-boundary`
- `v3.1.0-strategy-fixture-backtest-harness`
- `v3.2.0-technical-setup-evidence-pack`
- `v3.3.0-market-universe-volume-spike-discovery`
- `v3.4.0-llm-feature-store-signal-evaluation`
- `v3.5.0-trade-plan-basket-risk-engine`
- `v3.6.0-paper-trading-strategy-evaluation`
- `v3.7.0-walk-forward-replay-policy-optimizer`
- `v3.8.0-local-llm-advisory-adapter-hardening` -> `cb2b11e`

v3.9 does not change the v3.8 tag.

## Goals

v3.9 should define a safe path for future local model integration without
integrating any actual model runtime yet.

The design goals are:

- keep backend default `DISABLED`
- preserve all v3.8 advisory-only guarantees
- define a strict runtime adapter boundary
- define deterministic mock backend behavior
- define backend capability metadata and health-check metadata
- define timeout, resource, audit, and fail-closed validation rules
- compare candidate backend families and candidate model families
- keep all testing offline, deterministic, and fixture-first

The recommended implementation direction for a later v3.9 build is:

- add mock/runtime interface only
- do not add real Ollama, llama.cpp, transformers, or model downloads
- do not perform real inference

## Non-Goals

v3.9 does not:

- enable cloud LLM backends
- enable external network
- download any model
- read credentials or tokens
- access broker, Kiwoom, account-read, order, realtime, provider, or execution
  paths
- create `StrategyDecision`
- create `OrderIntent`
- create order drafts
- approve execution
- bypass `RiskGate` or `ExecutionGate`
- activate LIVE or PROD behavior
- change production strategy or policy automatically

## Core Principle

The local model is not a trading authority.

Even after a future local runtime is added, the local model remains within an
advisory boundary. It may summarize, explain, challenge, classify, or restate
local fixture-provided information. It may not make the final trade decision,
approve execution, or produce broker-facing actions.

## Recommended Direction

v3.9 should use a contract-first mock adapter approach.

That means:

- define the future runtime interface before integrating any runtime
- keep the current v3.8 advisory fixture-driven path intact
- add a deterministic mock backend design as the only permitted execution mode
  beyond `DISABLED`
- represent future backend families as metadata and interface contracts only

This approach is preferred because it preserves the safety boundary, keeps
tests deterministic, and avoids backend-specific coupling before the contract
is stable.

## Architecture And Dependency Boundaries

The future implementation should continue to separate pure core from thin
service orchestration.

Recommended logical units:

- `local_model_runtime_models.py`
  - strict request, response, backend capability, health-check, and audit
    metadata models
- `local_model_runtime_fixture.py`
  - exact-file JSON loader and strict validation
- `local_model_runtime_guard.py`
  - validation for prompt templates, response schema, unsafe output detection,
    timeout/resource policy checks, and fail-closed conversion
- `local_model_runtime_adapter.py`
  - abstract runtime adapter contract and mock adapter contract
- `local_model_runtime_engine.py`
  - pure orchestration across `DISABLED` and `MOCK_LOCAL_RUNTIME`
- `local_model_runtime_service.py`
  - file loading, checksums, output writing, optional service-layer audit

Core modules must not import DB, repository, provider, realtime, broker,
Kiwoom, account, order, credential, token, network, cloud, `StrategyDecision`,
`OrderIntent`, RiskGate, or ExecutionGate modules.

If optional SQLite audit is ever introduced later, it must remain service-layer
only, append-only, and disabled by default.

## Backend Mode Strategy

The default backend remains `DISABLED`.

v3.9 should distinguish between:

- `DISABLED`
  - the baseline safe state
- `MOCK_LOCAL_RUNTIME`
  - deterministic fixture-derived response path for tests and interface
    verification
- future represented-only backends
  - `OLLAMA_LOCAL`
  - `LLAMACPP_LOCAL`
  - `PYTHON_LOCAL_WRAPPER`

Rules:

- only `DISABLED` and `MOCK_LOCAL_RUNTIME` should be implementable in the first
  future v3.9 implementation
- future backend types may appear in schema design and validation rules
- represented future backends must still be rejected at runtime until
  explicitly implemented and approved
- no backend type may imply permission to use network, brokers, accounts, or
  orders

## Runtime Adapter Contract

The future runtime adapter should be represented as a narrow interface with no
trading authority.

Recommended conceptual interface:

- `adapter_name`
- `backend_type`
- `capabilities() -> LocalModelBackendCapabilities`
- `health_check(request) -> LocalModelRuntimeHealth`
- `run_advisory(request) -> LocalModelRuntimeRawResponse`

Contract rules:

- input must be explicit local JSON fixture-derived data only
- adapter must accept strict timeout and resource budget parameters
- adapter must return structured metadata even on refusal or failure
- adapter must never reach broker/account/order/network paths
- adapter must never return execution approval or order authority
- unsafe output must be converted to a refusal or rejection result

The contract must stay small so that future backend integrations cannot expand
silently into a general-purpose agent.

## Mock Backend Behavior

The mock backend is the only non-disabled execution design in v3.9.

Its purpose is to validate:

- request schema
- prompt template binding
- backend capability representation
- timeout/resource policy wiring
- response schema enforcement
- unsafe output fail-closed behavior

Recommended behavior:

- consume fixture-provided request and optional mock response template
- emit deterministic advisory text or deterministic refusal text
- emit capability metadata exactly as configured in fixture
- emit resource metadata such as simulated token counts or latency only from
  fixture values
- never call a real local process, server, or Python model

The mock backend should support both:

- safe success responses
- intentionally unsafe responses for rejection-path tests

## Candidate Backend Families

v3.9 should document backend families without integrating them.

### 1. Fixture-only / Disabled or Mock Backend

Characteristics:

- highest testability
- deterministic
- zero external runtime dependency
- safest baseline

Tradeoff:

- no real inference capability

### 2. llama.cpp-Style Local Process

Representation only in v3.9:

- local executable path metadata
- model file identifier metadata
- local process timeout/resource configuration
- no actual process execution

Strengths:

- fully local operation is possible later
- fine-grained resource control

Risks:

- process supervision complexity
- prompt/output streaming and parser edge cases

### 3. Ollama-Style Local Server

Representation only in v3.9:

- local server adapter type
- local model identifier metadata
- local health-check contract
- no actual server call

Strengths:

- simple operator experience later
- easier local model switching later

Risks:

- server-style boundary can drift toward network semantics
- health checks and connectivity rules must remain local-only and explicitly
  constrained

### 4. Direct Python Local Model Wrapper

Representation only in v3.9:

- wrapper module identifier metadata
- local model family metadata
- resource budget metadata
- no actual import or inference path

Strengths:

- potentially simpler structured output handling later
- strong in-process schema control later

Risks:

- dependency bloat
- tighter coupling to local Python environment

## Candidate Model Families

v3.9 should document model families for future evaluation only. It should not
download, import, benchmark, or call any model.

Candidate families to document:

- Qwen 7B/14B class
- Llama 8B class
- Mistral 7B class
- Korean-capable smaller local models when relevant

Selection criteria:

- local-only execution path
- no cloud dependency
- offline deterministic test harness compatibility
- stable JSON or constrained-structure output potential
- Korean and English mixed-language support
- strong summarization and explanation quality
- lower hallucination tendency relative to peers
- acceptable latency on likely local hardware
- acceptable RAM / VRAM footprint
- ability to remain within advisory-only tasks

v3.9 should recommend documenting a comparison matrix with:

- family
- approximate parameter class
- language support notes
- expected hardware tier
- structured output suitability
- known safety or hallucination concerns
- operator complexity

## Capability Metadata Design

v3.9 should introduce explicit backend capability metadata so that runtime
selection is declarative and auditable.

Recommended capability fields:

- `supports_mock_execution`
- `supports_structured_json_output`
- `supports_korean`
- `supports_english`
- `supports_mixed_language`
- `supports_refusal_mode`
- `supports_timeout_budget`
- `supports_resource_budget`
- `supports_health_check`
- `supports_streaming=false` by default in initial design
- `requires_network=false`
- `requires_credentials=false`
- `may_create_order=false`
- `may_bypass_gates=false`

Capability metadata must describe what the backend claims to support. It must
not grant execution authority.

## Fixture Strategy

v3.9 should keep explicit local JSON fixture input only.

Recommended fixtures:

- runtime candidate listing fixture
- runtime check fixture
- advisory dry-run fixture

Each fixture must be self-contained and must not require fetching context from
network, cloud, broker, account, or external service paths.

## Fixture Contract

Recommended runtime-check fixture shape:

```json
{
  "schema_version": "3.9-local-model-runtime-fixture",
  "run_id": "local-model-runtime-check-1",
  "created_at": "2026-06-17T12:00:00+00:00",
  "backend": {
    "backend_type": "MOCK_LOCAL_RUNTIME",
    "adapter_name": "mock-local-runtime-v1",
    "model_name": "mock-qwen-class",
    "model_version": "0",
    "capabilities": {
      "supports_mock_execution": true,
      "supports_structured_json_output": true,
      "supports_korean": true,
      "supports_english": true,
      "supports_mixed_language": true,
      "supports_refusal_mode": true,
      "supports_timeout_budget": true,
      "supports_resource_budget": true,
      "supports_health_check": true,
      "requires_network": false,
      "requires_credentials": false,
      "may_create_order": false,
      "may_bypass_gates": false
    }
  },
  "request": {
    "task_type": "SUMMARIZE_TECHNICAL_EVIDENCE",
    "ticker": "ABC",
    "text_blocks": [
      "RSI recovered above 50",
      "Volume expanded above 20-day average"
    ]
  },
  "runtime_limits": {
    "timeout_ms": 500,
    "max_output_tokens": 300,
    "max_memory_mb": 1024
  },
  "mock_response": {
    "response_text": "Technical evidence is constructive but incomplete.",
    "risk_labels": [
      "MISSING_STOP_CONTEXT"
    ]
  },
  "safety": {
    "advisory_only": true,
    "may_create_order": false,
    "may_bypass_gates": false
  }
}
```

Validation should require:

- schema version exactly `3.9-local-model-runtime-fixture`
- timezone-aware `created_at`
- non-empty `run_id`
- backend type exactly one supported enum value
- strict capability metadata with no unknown fields
- no endpoint, URL, token, cookie, credential, authorization, broker, account,
  order, or network keys
- positive timeout and resource limits within allowed local bounds
- advisory-only safety flags locked true/false as required
- non-empty request data for allowed task types only

## Response Contract

Recommended output schema:

- `LocalModelRuntimeResult`
  - status
  - backend_type
  - adapter_name
  - model_name
  - capability_metadata
  - health_metadata
  - advisory_payload
  - refusal_reason
  - validation_errors
  - timeout_applied_ms
  - resource_limits_applied
  - audit_metadata
  - safety_metadata

Suggested statuses:

- `BACKEND_DISABLED`
- `MOCK_RUNTIME_READY`
- `ADVISORY_RESPONSE`
- `SAFE_REFUSAL`
- `UNSAFE_OUTPUT_REJECTED`
- `INVALID_RUNTIME_CONFIGURATION`
- `UNIMPLEMENTED_BACKEND_REJECTED`
- `HEALTH_CHECK_FAILED`

Required safety metadata:

- `advisory_only=true`
- `may_create_order=false`
- `may_bypass_gates=false`
- `orders_created=false`
- `order_intents_created=false`
- `order_drafts_created=false`
- `execution_approved=false`
- `gates_bypassed=false`
- `external_network_calls=false`
- `real_model_called=false`

## Prompt Template Validation

v3.9 should define strict prompt-template validation even for mock execution.

Validation rules:

- prompt template identifiers must be explicit and versioned
- prompt checksum should be recorded when present
- allowed task type must match the template purpose
- prompt text must not request buy, sell, submit, execute, approve, override,
  bypass, or broker/account access
- prompt variables must be explicit and locally provided
- no hidden prompt fetching from files, DB, URLs, or providers

## Unsafe Output Fail-Closed Behavior

Unsafe output must be rejected or converted into a safe refusal.

Forbidden output categories include:

- direct buy or sell instruction
- order creation or submission intent
- execution approval language
- RiskGate or ExecutionGate bypass claims
- position sizing authority beyond explanatory restatement
- broker, account, credential, token, or network request
- LIVE or PROD activation language

The guard should treat partial unsafe output as unsafe output. Mixed safe and
unsafe content must still fail closed.

## Timeout And Resource Limit Design

v3.9 should define resource boundaries before any real backend integration.

Recommended fields:

- `timeout_ms`
- `max_output_tokens`
- `max_memory_mb`
- optional `max_cpu_seconds` for future local process adapters

Rules:

- limits must be explicit in runtime fixtures
- limits must be validated before runtime invocation
- timeout expiry must produce a structured refusal or runtime error result
- resource over-budget must produce a structured refusal or configuration error
- v3.9 tests should simulate these paths through mock metadata only

## Health Check Design

Health check must be local, explicit, and advisory-bound.

Recommended health metadata:

- `health_status`
- `adapter_name`
- `backend_type`
- `configured_model_name`
- `mock_mode`
- `timeout_supported`
- `resource_limits_supported`
- `structured_output_supported`
- `local_only_asserted`
- `network_required=false`

Rules:

- `DISABLED` health check returns a valid disabled-state report
- `MOCK_LOCAL_RUNTIME` health check returns deterministic ready-state metadata
- represented-only backends return `UNIMPLEMENTED_BACKEND_REJECTED` until
  approved and implemented

## Audit Metadata Design

Audit metadata should remain JSON-safe and service-layer friendly.

Recommended fields:

- fixture checksum
- prompt checksum
- backend type
- adapter name
- model name and version
- capability checksum
- timeout/resource limits
- result status
- refusal reason code
- unsafe output flag
- local-only assertion flag

This metadata supports later append-only audit without changing core behavior.

## CLI Design Proposal

The existing CLI naming style uses hyphenated verbs with `-run` and `-show`
patterns. For v3.9 the recommended commands are:

- `local-model-candidates-list --fixture-file ... [--output-file ...]`
- `local-model-runtime-check --fixture-file ... [--output-file ...]`
- `local-model-advisory-dry-run --fixture-file ... [--output-file ...]`

Recommended behavior:

`local-model-candidates-list`

- reads a local candidate-selection fixture
- returns documented candidate backends and model families
- performs no runtime execution

`local-model-runtime-check`

- validates backend metadata, capabilities, timeout/resource limits, and health
  check contract
- on `DISABLED`, returns disabled-state metadata
- on `MOCK_LOCAL_RUNTIME`, returns deterministic ready-state metadata
- on future backend types, returns unimplemented-backend rejection

`local-model-advisory-dry-run`

- validates advisory request, prompt metadata, runtime limits, and mock
  response path
- returns deterministic advisory output or safe refusal
- never calls a real model

`local-model-runtime-show` may be added later if output inspection patterns need
to match the existing CLI more closely, but it is not required for the first
design.

## Testing Plan

v3.9 should require no real model for any test.

Required tests:

- strict fixture validation
- backend enum validation
- default disabled backend tests
- mock backend deterministic response tests
- unimplemented backend rejection tests
- prompt template validation tests
- unsafe response rejection tests
- timeout limit validation tests
- resource limit validation tests
- capability metadata validation tests
- safety metadata enforcement tests
- no `StrategyDecision` or `OrderIntent` creation tests
- no broker/Kiwoom/account/order/network import tests
- offline deterministic system-smoke preservation

All tests must be fixture-only and deterministic.

## System Smoke

System smoke should remain fully offline.

Recommended v3.9 smoke expectations:

- temporary local JSON fixture only
- `local_model_runtime_fixture_run=true`
- `real_model_called=false`
- `llm_called=false`
- `external_network_calls=false`

No smoke path may require:

- model download
- local server connectivity
- local process execution
- broker or provider access
- credentials or tokens

## Decision On v3.9 Implementation Scope

v3.9 should not remain design-only forever, but the first implementation scope
should be limited to interface and mock runtime only.

Recommended first implementation scope:

- fixture loader
- runtime models
- mock adapter contract
- disabled and mock backend engine
- validation and fail-closed guard
- CLI commands
- tests and offline system smoke

Explicitly excluded from first implementation scope:

- real Ollama integration
- real llama.cpp process integration
- real Python transformers wrapper
- model download management
- real inference
- hardware probing

## Safety Invariants

v3.9 must preserve these invariants:

- no LIVE
- no PROD
- no cloud backend
- no external network
- no credential or token access
- no broker, Kiwoom, account-read, or order path
- no `StrategyDecision`
- no `OrderIntent`
- no order draft
- no execution approval
- no production policy change
- local model remains advisory-only
- backend default remains `DISABLED`
- unsafe output fails closed

## Verification Baseline For Future Implementation

Any future v3.9 implementation should be validated with:

```bash
python3.11 -m pytest -q
python3.11 -m compileall -q src
git diff --check
python3.11 -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs
git status --short
```

Expected safety indicators:

- offline deterministic completion
- `real_model_called=false`
- `llm_called=false`
- `external_network_calls=false`
- no broker/account/order path usage

## Summary

v3.9 should prepare a safe future path for local model integration by defining:

- how candidate models and backend families are evaluated
- how a local runtime adapter is represented
- how mock execution works
- how timeout/resource/health metadata is validated
- how unsafe output is rejected

The first future implementation should stop at mock/runtime interface support.
Actual local model integration belongs to a later approved release.
