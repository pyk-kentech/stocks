# v3.8 Local LLM Advisory Adapter Hardening Design

## Scope

v3.8 adds a hardened local LLM advisory adapter. It consumes one explicit local
JSON fixture containing an advisory request, local backend metadata, allowed
task type, local input texts, and strict safety flags. It validates the input,
optionally represents a local backend in metadata, produces advisory-only
responses or safe refusals, and emits auditable JSON results.

The LLM is not a trader. v3.8 does not create `StrategyDecision`,
`OrderIntent`, order drafts, execution approvals, or broker requests. It does
not bypass `RiskGate` or `ExecutionGate`, access broker/account/order paths,
use credentials or tokens, or access network or cloud LLM services.

## Release Baseline

The design assumes the current release state is:

- `v3.0.0-strategy-core-local-llm-safety-boundary`
- `v3.1.0-strategy-fixture-backtest-harness`
- `v3.2.0-technical-setup-evidence-pack`
- `v3.3.0-market-universe-volume-spike-discovery`
- `v3.4.0-llm-feature-store-signal-evaluation`
- `v3.5.0-trade-plan-basket-risk-engine`
- `v3.6.0-paper-trading-strategy-evaluation`
- `v3.7.0-walk-forward-replay-policy-optimizer` -> `b86f5bc`

v3.8 is design-only in this step. The v3.7 tag remains unchanged.

## Goals

v3.8 introduces a fail-closed local advisory adapter for local LLM workflows.
The adapter must:

- consume explicit local JSON fixture inputs only
- default to backend `DISABLED`
- allow `LOCAL_MODEL` representation only through explicit local fixture
  metadata
- enforce strict advisory-only safety flags
- validate prompt intent and response content
- reject or safely refuse unsafe outputs
- remain fully offline, reproducible, and auditable

The output is an advisory response or safe refusal. It is not a trading
instruction.

## Non-Goals

v3.8 does not:

- enable cloud LLM backends
- access external network
- read credentials or tokens
- access broker, Kiwoom, account-read, order, realtime, or provider paths
- create `StrategyDecision`
- create `OrderIntent`
- create order drafts
- approve execution
- bypass `RiskGate` or `ExecutionGate`
- activate LIVE or PROD behavior
- expand into general-purpose agent autonomy

The first version prioritizes fail-closed safety validation over runtime
capability expansion.

## Architecture And Dependency Boundaries

The implementation should use pure core plus thin service boundaries:

- `local_llm_advisory_models.py`
  - strict Pydantic models for request fixture, backend metadata, allowed task
    enum, response schema, refusal schema, and safety metadata
- `local_llm_advisory_fixture.py`
  - exact-file JSON loading and strict validation
- `local_llm_advisory_guard.py`
  - forbidden-intent detection, unsafe output detection, and fail-closed
    refusal conversion
- `local_llm_advisory_engine.py`
  - pure advisory orchestration: default disabled path, optional local-model
    metadata path, and normalized result production
- `local_llm_advisory_service.py`
  - orchestration only: load exact fixture, compute checksums, run pure core,
    and write JSON output

Core modules must not import database, repository, provider, realtime, broker,
Kiwoom, account, order, strategy execution, credential, token, network, cloud,
RiskGate, or ExecutionGate modules. Default execution is JSON output only. If
SQLite audit is ever added later, it must remain optional, append-only, and
service-layer only.

## Backend Mode

The backend mode for v3.8 is `disabled-by-default, opt-in local backend`.

Rules:

- default backend must be `DISABLED`
- `LOCAL_MODEL` may be represented only through explicit local fixture/config
  metadata
- no cloud backend is allowed
- no external network is allowed
- fail-closed safety validation takes priority over runtime expansion

The presence of `LOCAL_MODEL` metadata does not grant permission to use any
network, broker, or order path. It only indicates that a local-only backend may
exist within the advisory boundary.

## Fixture Strategy

v3.8 should use one strict local JSON fixture rather than multiple file
references. The fixture should contain:

- advisory task type
- backend metadata
- input text fragments or structured evidence summaries
- strict safety flags
- optional local prompt metadata

The adapter must never fetch missing context from external files, databases,
providers, brokers, accounts, or network paths.

## Fixture Contract

The v3.8 fixture should be one exact local JSON file:

```json
{
  "schema_version": "3.8-local-llm-advisory-fixture",
  "run_id": "local-llm-advisory-run-1",
  "created_at": "2026-01-22T16:00:00+00:00",
  "task_type": "SUMMARIZE_TECHNICAL_EVIDENCE",
  "backend": {
    "backend_type": "DISABLED",
    "model_name": "disabled",
    "model_version": "0"
  },
  "prompt_metadata": {
    "prompt_id": "tech-summary-v1",
    "prompt_version": "1.0.0",
    "prompt_checksum": "sha256:..."
  },
  "inputs": {
    "ticker": "ABC",
    "title": "Technical evidence summary",
    "text_blocks": [
      "RSI recovered above 50",
      "Price is above 20 EMA"
    ]
  },
  "safety": {
    "advisory_only": true,
    "may_create_order": false,
    "may_bypass_gates": false
  }
}
```

Validation requires:

- schema version exactly `3.8-local-llm-advisory-fixture`
- non-empty `run_id`
- timezone-aware `created_at`
- one allowed `task_type`
- exactly one `backend`
- exactly one `inputs`
- exactly one `safety`
- no unknown fields
- uppercase normalized non-empty tickers when present
- non-empty text blocks after trimming
- `backend.backend_type` exactly `DISABLED` or `LOCAL_MODEL`
- `backend.backend_type=DISABLED` by default in system smoke and baseline usage
- if `LOCAL_MODEL` is used, it must be explicit in fixture metadata
- no cloud backend identifiers
- no endpoint, URL, token, credential, authorization, cookie, account, broker,
  or network metadata keys
- `advisory_only=true`
- `may_create_order=false`
- `may_bypass_gates=false`

The fixture must be self-contained. The adapter must not infer missing prompt,
model, or evidence fields from outside the fixture.

## Advisory Request Schema

Recommended top-level request models:

- `LocalLLMAdvisoryFixture`
  - top-level fixture with metadata, task, inputs, backend, and safety
- `LocalLLMBackendConfig`
  - `backend_type`, `model_name`, `model_version`, and safe local runtime
    metadata
- `LocalLLMAdvisoryPromptMetadata`
  - prompt identifiers and checksums only
- `LocalLLMAdvisoryInputs`
  - normalized advisory input texts and summaries
- `LocalLLMAdvisorySafetyFlags`
  - strict inbound safety assertions

Runtime metadata must be JSON-safe and recursively checked so that no nested
key contains token, secret, API-key, authorization, cookie, endpoint, URL,
broker, account, or credential terms.

## Allowed Tasks

Allowed tasks for v3.8 are:

- summarize technical evidence
- summarize market discovery evidence
- summarize LLM signal evaluation
- explain trade plan risk
- challenge weak assumptions
- list missing data
- classify advisory risk language from local fixture text

Recommended first-version task enum values:

- `SUMMARIZE_TECHNICAL_EVIDENCE`
- `SUMMARIZE_MARKET_DISCOVERY`
- `SUMMARIZE_LLM_SIGNAL_EVALUATION`
- `EXPLAIN_TRADE_PLAN_RISK`
- `CHALLENGE_WEAK_ASSUMPTIONS`
- `LIST_MISSING_DATA`
- `CLASSIFY_ADVISORY_RISK_LANGUAGE`

Every task remains descriptive, explanatory, or classificatory only.

## Forbidden Tasks

Forbidden tasks include:

- direct buy/sell decision
- direct hold/exit decision
- position sizing authority
- broker access
- account access
- order access
- credential access
- network access
- live or PROD activation
- gate bypass instructions
- strategy execution approval

The adapter must reject unsafe task intent before any local backend execution
path is considered.

## Advisory Response Schema

The response should use one strict envelope with either:

- safe advisory content
- safe refusal content

Recommended models:

- `LocalLLMAdvisoryResponse`
  - safe advisory result
- `LocalLLMAdvisoryRefusal`
  - safe refusal result
- `LocalLLMAdvisoryResult`
  - discriminated union or explicit status-based top-level result

Suggested response fields:

- `status`
- `task_type`
- `backend_type`
- `summary_text`
- `bullet_points`
- `risk_language_classification`
- `missing_data_items`
- `challenge_points`
- `refusal_reason`
- `safety_flags`

The response must always include strict safety metadata:

- `advisory_only=true`
- `may_create_order=false`
- `may_bypass_gates=false`
- `orders_created=false`
- `order_intents_created=false`
- `execution_approved=false`
- `external_network_calls=false`

## Prompt And Result Validation

The adapter should validate:

- task type is allowed
- fixture-provided input blocks are non-empty and safe
- backend metadata is safe and local-only
- output content does not contain forbidden execution intent
- output content does not promise broker/account access
- output content does not activate LIVE/PROD behavior

Prompt metadata should store identifiers and checksums only. Full prompt text
may be allowed only if explicitly scoped as local fixture content and still
subject to safety scanning. The first version should prefer checksum-based
prompt provenance over raw prompt persistence.

## Fail-Closed Safety Behavior

Unsafe outputs must never be normalized into apparently safe advisory text.

If an output contains forbidden content such as:

- buy/sell instructions
- order creation language
- gate bypass language
- broker/account access instructions
- live/prod activation language
- credential or token requests

the adapter must:

1. reject the unsafe output
2. replace it with a safe refusal result
3. mark the result as refused or rejected in a machine-readable status

Recommended statuses:

- `ADVISORY_RESPONSE`
- `SAFE_REFUSAL`
- `UNSAFE_OUTPUT_REJECTED`
- `INVALID_REQUEST`
- `BACKEND_DISABLED`

The adapter should fail closed whenever there is uncertainty about safety.

## Default Disabled Behavior

The default baseline behavior is backend `DISABLED`.

When backend is `DISABLED`:

- the adapter does not attempt any runtime local model call
- the result may be a safe disabled notice or a deterministic safe refusal
- the adapter still validates the fixture and emits safety metadata

This default path is the safest baseline for system smoke and offline testing.

## Optional Local Model Representation

`LOCAL_MODEL` may be represented only when the fixture explicitly opts in.

This representation may include:

- `backend_type=LOCAL_MODEL`
- `model_name`
- `model_version`
- safe local runtime metadata

It must not include:

- endpoint URLs
- remote hosts
- cloud provider names
- API tokens
- broker or account references

The first implementation may still simulate or stub the local backend rather
than performing a real local model invocation. Hardening and validation take
priority over backend capability breadth.

## Report Schema

The JSON result should contain:

- schema version `3.8-local-llm-advisory-result`
- fixture checksum
- `run_id`
- `created_at`
- normalized request metadata
- advisory response or refusal payload
- safety metadata

Required safety metadata:

- `advisory_only=true`
- `may_create_order=false`
- `may_bypass_gates=false`
- `orders_created=false`
- `order_intents_created=false`
- `execution_approved=false`
- `external_network_calls=false`

The result must make it explicit that no strategy, order, or execution artifact
was created.

## Optional Audit Persistence

JSON output is the preferred and default persistence format in v3.8.

If SQLite audit is later justified, it must satisfy all of:

- service-layer only
- optional and default-off
- append-only
- never used as core advisory input
- not imported by core advisory modules

SQLite is not required for the first v3.8 implementation.

## CLI

Suggested commands:

```bash
python3.11 -m stock_risk_mcp.cli local-llm-advisory-run --fixture-file data/local_llm_advisory_fixture.json --output-file outputs/local_llm_advisory_result.json
python3.11 -m stock_risk_mcp.cli local-llm-advisory-show --output-file outputs/local_llm_advisory_result.json
```

`local-llm-advisory-run`:

- requires one exact local fixture file
- validates task, backend, and safety boundaries
- writes JSON output only by default
- must not access broker, Kiwoom, account, network, cloud, or credential paths

`local-llm-advisory-show`:

- reads one exact output JSON file
- prints or returns a deterministic summary
- performs no recalculation and no external access

## Safety Boundary

v3.8 must keep the existing v3 advisory safety boundary intact:

- no LIVE
- no PROD
- no broker integration
- no Kiwoom integration
- no account-read
- no credential or token access
- no external network
- no cloud LLM call
- no `StrategyDecision` creation
- no `OrderIntent` creation
- no order draft creation
- no execution approval
- no RiskGate or ExecutionGate bypass

Even when the advisory text is informative or critical, it may not issue
trading authority.

## Testing Requirements

The implementation plan should include tests for:

- strict fixture validation
- default backend `DISABLED`
- explicit `LOCAL_MODEL` metadata acceptance
- cloud backend rejection
- unsafe metadata-key rejection
- allowed task acceptance
- forbidden task rejection
- fail-closed unsafe output rejection
- refusal result generation
- prompt/result validation
- no automatic `StrategyDecision`
- no automatic `OrderIntent`
- no order draft creation
- no execution approval
- no broker, Kiwoom, account, order, or network imports in core modules
- offline deterministic system-smoke
- preservation of existing v2 through v3.7 tests

Representative deterministic cases should include:

- disabled backend with safe advisory refusal
- disabled backend with safe validation-only response
- explicit `LOCAL_MODEL` metadata with allowed summarize task
- explicit unsafe request asking for buy/sell instruction
- output containing gate-bypass language converted into refusal
- output containing broker/account language converted into refusal
- invalid backend metadata containing endpoint URL rejected at fixture load

## System Smoke

The v3.8 system-smoke should use a temporary local JSON fixture only. It should
verify:

- `local_llm_advisory_fixture_run=true`
- backend default is `DISABLED`
- deterministic JSON output written
- `advisory_only=true`
- `orders_created=false`
- `order_intents_created=false`
- `execution_approved=false`
- `external_network_calls=false`

The smoke path must not depend on broker, Kiwoom, account, network, cloud,
credential, token, or execution infrastructure.

## Implementation Notes

The first implementation should stay intentionally boring:

- one strict fixture
- disabled-by-default backend
- explicit allowlist of tasks
- explicit denylist of unsafe intents
- explicit fail-closed refusal conversion
- no cloud support
- no hidden runtime escalation

Later releases may add richer local backend execution details, more granular
task schemas, or compatibility with more local model runtimes, but only through
separately scoped designs with the same safety review discipline.
