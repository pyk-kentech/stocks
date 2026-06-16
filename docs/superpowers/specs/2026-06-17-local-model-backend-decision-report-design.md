# v3.11 Local Model Backend Decision Report / Benchmark Pack Expansion Design

## Scope

v3.11 designs the next offline benchmark expansion layer after v3.10.

It has two connected goals:

- turn multiple v3.10 benchmark reports into one offline backend decision
  report
- expand the benchmark pack so that recommendations are based on broader
  language, schema, safety, and advisory-boundary coverage

v3.11 is design-only in this step. It does not implement any runtime adapter,
does not call any real model, and does not perform inference.

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
- `v3.8.0-local-llm-advisory-adapter-hardening`
- `v3.9.0-local-model-runtime-adapter-contract`
- `v3.10.0-local-model-backend-selection-benchmark` -> `d40c38e`

v3.11 is design-only in this step. The v3.10 tag remains unchanged.

## Goals

v3.11 should define a deterministic offline pack-level decision layer that uses
multiple benchmark reports as evidence and never relies on a single benchmark
report to recommend a backend.

The design goals are:

- make benchmark pack aggregation the primary decision unit
- keep single-report summaries only for traceability and debugging
- preserve hard fail persistence across the pack
- generate a backend decision report without production activation
- expand benchmark coverage across language, domain, JSON behavior, and safety
  traps
- remain fully offline, fixture-only, and deterministic

## Core Principle

v3.11 uses pack-first decision reporting.

Decision status is derived from multiple benchmark reports grouped into a
benchmark pack. A candidate must remain eligible across the pack, not just in a
single report.

Single benchmark reports are supporting evidence only. They help explain why a
candidate passed or failed, but they are not sufficient on their own to produce
a backend recommendation.

## Non-Goals

v3.11 does not:

- call a real model
- call Ollama
- call llama.cpp
- call transformers or direct Python inference
- download a model
- access cloud backends
- access external network
- read credentials or tokens
- access broker, Kiwoom, account-read, order, realtime, provider, or execution
  paths
- create `StrategyDecision`
- create `OrderIntent`
- create order drafts
- approve execution
- bypass `RiskGate` or `ExecutionGate`
- activate any backend automatically
- change production policy or model selection automatically

## Architecture And Dependency Boundaries

The future implementation should remain pure-core with thin service
orchestration.

Recommended logical units:

- `local_model_decision_report_models.py`
  - benchmark pack fixture, report references, aggregation models, decision
    report schema, and recommendation status enum
- `local_model_decision_report_fixture.py`
  - exact-file JSON loaders for benchmark pack and report reference fixtures
- `local_model_decision_report_guard.py`
  - aggregation safety rules, hard-fail persistence, coverage checks, and
    no-activation validation
- `local_model_decision_report_engine.py`
  - pure pack-level aggregation, recommendation status assignment, and
    deterministic trace summaries
- `local_model_decision_report_service.py`
  - file loading, checksum handling, report generation, and optional JSON
    output persistence

Core modules must not import DB, repository, provider, realtime, broker,
Kiwoom, account, order, credential, token, network, cloud, `StrategyDecision`,
`OrderIntent`, RiskGate, or ExecutionGate modules.

## Primary Unit: Benchmark Pack Aggregation

The primary decision unit must be the benchmark pack.

Recommended inputs:

- one benchmark pack fixture
- multiple v3.10 benchmark reports referenced by local file or embedded summary
  fixture data

Pack-level aggregation should answer:

- which candidates stayed eligible across the pack
- which candidates failed and why
- whether benchmark coverage is sufficient to make a shortlist recommendation
- whether the result is still mock-only or needs more coverage

## Secondary Unit: Single Report Traceability

Single benchmark report summaries should remain visible as supporting evidence.

Recommended uses:

- explain a hard fail source
- show where a candidate lost eligibility
- show language or domain-specific weak spots
- help debug pack coverage gaps

Single report summaries must not be enough to recommend a backend.

## Benchmark Pack Expansion

v3.11 should expand the benchmark pack across these categories:

- Korean-only tasks
- English-only tasks
- mixed Korean/English tasks
- JSON-only response tasks
- missing-data awareness tasks
- unsafe instruction rejection tasks
- advisory-boundary tasks
- risk explanation tasks
- assumption challenge tasks
- hallucinated execution authority trap tasks

The pack should be designed so that a candidate cannot look good by excelling
in only one narrow task family.

## Benchmark Pack Fixture Contract

Recommended pack fixture schema:

```json
{
  "schema_version": "3.11-local-model-benchmark-pack-fixture",
  "pack_id": "local-model-pack-1",
  "created_at": "2026-06-17T12:00:00+00:00",
  "pack_type": "DECISION_PACK",
  "required_language_tags": ["KOREAN", "ENGLISH", "MIXED"],
  "required_domain_tags": [
    "TECHNICAL_EVIDENCE",
    "RISK_EXPLANATION",
    "MISSING_DATA",
    "ASSUMPTION_CHALLENGE"
  ],
  "benchmark_report_files": [
    "reports/report_ko.json",
    "reports/report_en.json",
    "reports/report_mixed.json"
  ]
}
```

Validation should require:

- schema version exactly `3.11-local-model-benchmark-pack-fixture`
- non-empty `pack_id`
- timezone-aware `created_at`
- explicit `pack_type`
- at least one benchmark report reference
- explicit required language tags
- explicit required domain tags
- no unknown fields

## Benchmark Report Reference Strategy

v3.11 should support local report references only.

Recommended reference strategies:

- local file paths to v3.10 benchmark reports
- optional future inline embedded summaries for test fixtures only

Rules:

- no network fetching
- no cloud object storage
- no remote URI loading
- all report references must resolve locally

## Backend Decision Report Schema

Recommended decision report schema:

- `LocalModelBackendDecisionReport`
  - pack metadata
  - benchmark report references
  - candidate summaries
  - eligibility summaries
  - rankings among eligible candidates
  - fail reasons for rejected candidates
  - recommendation status
  - trace summaries from individual reports
  - safety metadata

Recommended top-level fields:

- `pack_id`
- `report_count`
- `candidate_count`
- `eligible_candidate_count`
- `recommendation_status`
- `shortlisted_candidates`
- `rejected_candidates`
- `trace_reports`
- `coverage_summary`
- `aggregation_summary`
- `metadata_json`

## Recommendation Status

Recommendation status must be pack-level only.

Allowed values:

- `NO_ELIGIBLE_BACKEND`
- `NEEDS_MORE_BENCHMARKS`
- `CANDIDATE_SHORTLIST_READY`
- `MOCK_ONLY_READY`

Interpretation:

- `NO_ELIGIBLE_BACKEND`
  - no candidate stayed eligible across the pack
- `NEEDS_MORE_BENCHMARKS`
  - some candidates may be safe, but pack coverage is incomplete or unstable
- `CANDIDATE_SHORTLIST_READY`
  - one or more candidates stayed eligible across the pack with sufficient
    coverage and acceptable stability
- `MOCK_ONLY_READY`
  - safe enough for mock-only discussion or future backend planning, but not
    enough to shortlist a real runtime path

These statuses are advisory only. They must not activate any backend.

## Decision Rules

Decision rules must be strict and pack-level.

Rules:

- candidates with any hard fail remain ineligible across the pack
- no candidate may be recommended if safety or advisory gates fail anywhere in
  the pack
- ranking is only among pack-eligible candidates
- the report may recommend a shortlist, not runtime activation
- the report must not select a production model automatically
- single report success cannot override pack-level hard fail persistence

## Hard Fail Persistence

Hard fail persistence is a core rule.

If a candidate has any hard fail in any included benchmark report, that
candidate remains ineligible in the pack-level decision result.

This includes:

- schema failures
- safety failures
- advisory boundary failures
- execution authority hallucination failures
- real model called failures
- external network failures
- cloud backend failures
- model download failures
- unsupported backend failures

The only future exception path would be an explicitly designed
`QUARANTINED_NON_DECISION_REPORT` class, which is out of scope for v3.11.

## Candidate Summary Aggregation

Each candidate should receive a pack-level summary built from all included
benchmark reports.

Recommended fields:

- `candidate_model_id`
- `report_count_seen`
- `eligible_report_count`
- `hard_fail_count`
- `final_pack_eligibility`
- `average_overall_score`
- `average_schema_validity_score`
- `average_safety_score`
- `average_advisory_boundary_score`
- `average_missing_data_awareness_score`
- `average_language_handling_score`
- `average_json_reliability_score`
- `average_hallucination_risk_score`
- `average_local_advisory_suitability_score`
- `fail_reason_counts`
- `language_coverage`
- `domain_coverage`

## Aggregation Metrics

v3.11 should compute pack-level aggregation metrics for each candidate and for
the report as a whole.

Required aggregation metrics:

- per-candidate average score
- per-domain score
- per-language score
- schema reliability
- safety failure rate
- advisory boundary failure rate
- missing-data awareness rate
- JSON parse success rate
- hard fail count

Recommended additional summary fields:

- eligible candidate ranking count
- total rejected candidate count
- coverage completeness flag
- benchmark pack stability summary

## Coverage Rules

Recommendation status should depend on coverage, not just average score.

Recommended coverage rules:

- pack should include Korean, English, and mixed-language evidence before
  shortlist recommendation
- pack should include both safe tasks and trap tasks
- pack should include missing-data awareness and advisory-boundary tasks
- lack of required coverage pushes status toward `NEEDS_MORE_BENCHMARKS`

This ensures that a candidate cannot be shortlisted from a narrow, incomplete
benchmark pack.

## Benchmark Pack Validator

v3.11 should include a deterministic benchmark pack validator in the design.

Validator responsibilities:

- verify required language coverage
- verify required domain coverage
- verify at least one trap-style benchmark exists
- verify report references are local and parseable
- verify report schemas match expected v3.10 benchmark report schema
- verify no duplicated report references if duplicates would skew aggregation

The validator is offline and fixture-only.

## Traceability Section

The decision report should include single-report trace summaries as subordinate
evidence.

Recommended trace summary fields:

- `report_id` or local report path
- language tag coverage contributed
- domain tag coverage contributed
- candidate-level eligibility snapshot
- candidate fail reasons in that report
- top and bottom scoring candidates in that report

These summaries support debugging without changing the pack-first rule.

## Recommendation Thresholds

v3.11 should define conservative recommendation thresholds.

Recommended rules:

- `NO_ELIGIBLE_BACKEND`
  - zero pack-eligible candidates
- `NEEDS_MORE_BENCHMARKS`
  - at least one safe candidate exists but coverage or stability is incomplete
- `CANDIDATE_SHORTLIST_READY`
  - at least one candidate is pack-eligible, coverage is complete, and failure
    rates remain acceptable
- `MOCK_ONLY_READY`
  - results are stable enough for mock-only planning, but still not enough for
    shortlist promotion

Threshold specifics should remain deterministic and explicit in fixture-driven
configuration when implemented.

## Safety Metadata

The decision report must include explicit safety metadata:

- `benchmark_offline_only=true`
- `real_model_called=false`
- `external_network_calls=false`
- `cloud_backend_used=false`
- `model_downloaded=false`
- `orders_created=false`
- `order_intents_created=false`
- `order_drafts_created=false`
- `execution_approved=false`
- `gates_bypassed=false`
- `production_policy_changed=false`

These fields describe the decision-report system state, not any candidate claim.

## Benchmark Pack Expansion Areas

The initial expanded pack should intentionally include:

- Korean-only summarization benchmark
- English-only summarization benchmark
- mixed-language summarization benchmark
- JSON-only schema response benchmark
- missing-data awareness benchmark
- unsafe instruction rejection benchmark
- advisory-boundary preservation benchmark
- risk explanation benchmark
- assumption challenge benchmark
- hallucinated execution authority trap benchmark

This expansion is meant to increase confidence in pack-level consistency.

## CLI Design Proposal

Recommended CLI names:

- `local-model-decision-report --benchmark-pack-file ... [--output-file ...]`
- `local-model-benchmark-pack-validate --fixture-file ...`

Recommended behavior:

`local-model-decision-report`

- loads a local benchmark pack fixture
- loads referenced v3.10 benchmark reports
- aggregates candidates across the pack
- assigns recommendation status
- outputs a deterministic decision report

`local-model-benchmark-pack-validate`

- validates benchmark pack structure and coverage rules
- performs no ranking beyond validation summaries

If naming needs minor adjustment for CLI consistency, behavior should remain
the same.

## System Smoke Design

System smoke should remain fully offline and deterministic.

Recommended smoke design:

- use temporary local JSON benchmark report fixture only
- use temporary local JSON benchmark pack fixture only
- include at least one eligible candidate and one rejected candidate

Expected smoke indicators:

- `local_model_decision_report_fixture_run=true`
- `real_model_called=false`
- `external_network_calls=false`
- `cloud_backend_used=false`
- `model_downloaded=false`

No smoke path may require:

- real model runtime
- model download
- local server connectivity
- local process execution
- direct Python inference
- broker or provider access
- credentials or tokens

## Testing Plan

v3.11 should require no real model for any test.

Required tests:

- strict benchmark pack fixture validation
- strict benchmark report reference validation
- pack-level aggregation tests
- candidate summary aggregation tests
- hard fail persistence across pack tests
- eligible-only ranking tests
- recommendation status assignment tests
- required language coverage tests
- required domain coverage tests
- missing-data awareness aggregation tests
- advisory-boundary failure rate aggregation tests
- JSON parse success rate aggregation tests
- trace summary generation tests
- no `StrategyDecision` or `OrderIntent` creation tests
- no broker/Kiwoom/account/order/network import tests
- offline deterministic system-smoke preservation

All tests must be fixture-only and deterministic.

## Implementation Boundary For Later

The first future implementation scope should be limited to:

- benchmark pack fixture loader
- benchmark report loader
- pack validator
- decision report generator
- deterministic aggregation logic
- CLI commands
- tests and offline system smoke

Explicitly forbidden:

- actual backend integration
- real inference
- model download
- network access
- cloud backend support
- broker, account, or order integration
- `StrategyDecision`
- `OrderIntent`
- order draft creation
- execution approval
- RiskGate or ExecutionGate bypass

## Safety Invariants

v3.11 must preserve these invariants:

- no LIVE
- no PROD
- no real model call
- no Ollama call
- no llama.cpp call
- no transformers or direct Python inference
- no model download
- no cloud backend
- no external network
- no credential or token access
- no broker, Kiwoom, account-read, or order path
- no `StrategyDecision`
- no `OrderIntent`
- no order draft
- no execution approval
- no production policy change
- pack-level recommendation only, never activation

## Verification Baseline For Future Implementation

Any future v3.11 implementation should be validated with:

```bash
python3.11 -m pytest -q
python3.11 -m compileall -q src
git diff --check
python3.11 -m stock_risk_mcp.cli system-smoke --db data/smoke.sqlite3 --output-dir smoke_outputs
git status --short
```

Expected safety indicators:

- `local_model_decision_report_fixture_run=true`
- `real_model_called=false`
- `external_network_calls=false`
- `cloud_backend_used=false`
- `model_downloaded=false`

## Summary

v3.11 should expand v3.10 by adding:

- pack-level benchmark aggregation
- backend decision reporting
- broader benchmark pack coverage
- deterministic trace summaries from individual reports
- shortlist-style advisory outcomes without activation

The first future implementation should stop at pack validator, aggregation, and
decision report generation. Real backend execution remains outside v3.11.
