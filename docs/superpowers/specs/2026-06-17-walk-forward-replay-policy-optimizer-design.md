# v3.7 Walk-Forward Replay Policy Optimizer Design

## Scope

v3.7 adds an offline deterministic walk-forward / replay policy optimizer. It
consumes one explicit local JSON replay fixture containing baseline and
candidate policy definitions, replay inputs, and timestamp-based window
configuration. It reruns baseline and candidate policies on the same replay
fixture by deterministic window, compares outcomes, applies explicit promotion
gates, and emits advisory-only policy evaluation and comparison reports.

This release does not perform live trading, does not enable PROD, does not
integrate with brokers, does not use real accounts, and does not submit orders
or create real broker requests. v3.7 may recommend policy promotion or
demotion only. It must not directly change production strategy behavior.

## Release Baseline

The design assumes the current release state is:

- `v3.0.0-strategy-core-local-llm-safety-boundary`
- `v3.1.0-strategy-fixture-backtest-harness`
- `v3.2.0-technical-setup-evidence-pack`
- `v3.3.0-market-universe-volume-spike-discovery`
- `v3.4.0-llm-feature-store-signal-evaluation`
- `v3.5.0-trade-plan-basket-risk-engine`
- `v3.6.0-paper-trading-strategy-evaluation` -> `214d976`

v3.7 is design-only in this step. The v3.6 tag remains unchanged.

## Goals

v3.7 introduces deterministic walk-forward replay evaluation for policy
selection. The optimizer must:

- rerun baseline and candidate policies on the same replay fixture
- split replay windows deterministically by timestamp
- compare per-window and aggregate policy metrics
- gate policy promotion or demotion through explicit safety and evidence rules
- emit advisory promotion recommendations only
- remain fully offline, reproducible, and auditable

The output is a policy recommendation report. It is not a trading instruction.

## Non-Goals

v3.7 does not:

- use precomputed paper evaluation reports as the primary comparison unit
- perform live trading
- enable PROD
- create `StrategyDecision`
- create `OrderIntent`
- create order drafts
- submit orders
- approve execution
- bypass `RiskGate` or `ExecutionGate`
- read broker, Kiwoom, account-read, provider, realtime, repository, network,
  credential, or token dependencies in core optimizer modules
- automatically activate or mutate the production strategy policy

Compatibility modes that consume previously generated advisory reports may be
added later as separate input modes, but not in v3.7.

## Architecture And Dependency Boundaries

The implementation should use pure core plus thin service boundaries:

- `policy_replay_models.py`
  - strict Pydantic models for the fixture, policy schema, replay rows, replay
    windows, per-window results, comparisons, promotion decisions, and final
    report
- `policy_replay_fixture.py`
  - exact-file JSON loading and strict validation
- `policy_window_split.py`
  - deterministic timestamp-based replay window construction
- `policy_replay_engine.py`
  - pure rerun logic that applies baseline and candidate policies to the same
    replay windows
- `policy_promotion_gate.py`
  - pure recommendation logic for sample count, drawdown, improvement,
    stability, and safety gates
- `policy_replay_service.py`
  - orchestration only: load exact fixture, compute checksums, invoke pure
    engines, and write JSON output

Core modules must not import database, repository, provider, realtime, broker,
Kiwoom, account, order, strategy execution, credential, token, network, cloud,
RiskGate, or ExecutionGate modules. Default execution is JSON output only. If
SQLite audit is ever added later, it must remain optional, append-only, and
service-layer only.

## Walk-Forward Unit

The walk-forward unit for v3.7 is `policy-rerun on replay fixture`.

This means:

- baseline and candidate policies are both rerun on the same explicit replay
  fixture
- comparison is based on rerun outcomes, not only on precomputed reports
- each window uses the same timestamp rules and replay rows for both policies
- every recommendation is backed by deterministic replay evidence from the
  same source fixture

Precomputed paper evaluation reports are not the primary comparison unit in
v3.7.

## Fixture Strategy

v3.7 should use one strict local JSON fixture rather than separate file
references. The fixture should contain:

- walk-forward window configuration
- one baseline policy
- one or more named candidate policies
- replay rows
- local replay price paths or equivalent deterministic replay evidence
- optional advisory evidence summaries such as market discovery, technical
  evidence, LLM signal evaluation, trade plans, or paper-eval summaries, only
  when embedded directly into the same fixture

The optimizer must never fetch missing inputs from external files, databases,
providers, or network paths.

## Fixture Contract

The v3.7 fixture should be one exact local JSON file:

```json
{
  "schema_version": "3.7-policy-replay-fixture",
  "run_id": "policy-replay-run-1",
  "created_at": "2026-01-20T16:00:00+00:00",
  "window_config": {
    "train_window_count": 2,
    "eval_window_count": 1,
    "window_stride": 1,
    "minimum_eval_trades": 20
  },
  "promotion_gates": {
    "minimum_sample_count": 20,
    "max_drawdown_pct_cap": 12.0,
    "minimum_return_improvement_pct": 2.0,
    "minimum_stability_score": 0.6
  },
  "baseline_policy": {
    "policy_id": "baseline-v1",
    "score_weights": {
      "technical": 0.5,
      "discovery": 0.3,
      "llm": 0.2
    },
    "minimum_score_threshold": 70.0,
    "minimum_risk_reward": 2.0,
    "allowed_setup_grades": ["A", "B"],
    "max_risk_pct_per_trade": 0.01,
    "max_basket_risk_pct": 0.03,
    "llm_weight_cap": 0.25,
    "allow_short": false,
    "allow_margin": false,
    "allow_leverage": false,
    "allow_market_orders": false
  },
  "candidate_policies": [
    {
      "policy_id": "candidate-v2",
      "score_weights": {
        "technical": 0.55,
        "discovery": 0.25,
        "llm": 0.20
      },
      "minimum_score_threshold": 72.0,
      "minimum_risk_reward": 2.5,
      "allowed_setup_grades": ["A"],
      "max_risk_pct_per_trade": 0.01,
      "max_basket_risk_pct": 0.025,
      "llm_weight_cap": 0.20,
      "allow_short": false,
      "allow_margin": false,
      "allow_leverage": false,
      "allow_market_orders": false
    }
  ],
  "replay_rows": [
    {
      "ticker": "ABC",
      "timestamp": "2026-01-10T09:30:00+00:00",
      "setup_grade": "A",
      "technical_score": 80.0,
      "discovery_score": 70.0,
      "llm_score": 60.0,
      "entry_reference": 100.0,
      "stop_reference": 96.0,
      "target_reference": 108.0,
      "price_path_id": "ABC-1"
    }
  ],
  "price_paths": [
    {
      "price_path_id": "ABC-1",
      "ticker": "ABC",
      "bars": [
        {
          "timestamp": "2026-01-10T09:31:00+00:00",
          "open": 99.5,
          "high": 101.0,
          "low": 99.0,
          "close": 100.5
        }
      ]
    }
  ]
}
```

Validation requires:

- schema version exactly `3.7-policy-replay-fixture`
- non-empty `run_id`
- timezone-aware `created_at`
- exactly one `window_config`
- exactly one `promotion_gates`
- exactly one `baseline_policy`
- at least one candidate policy
- at least one replay row
- at least one price path
- no unknown fields
- uppercase normalized non-empty tickers
- ordered non-duplicate replay timestamps per price path
- finite positive OHLC values
- finite positive entry, stop, and target references
- every replay row linked to one exact `price_path_id`
- timestamp-aware replay row and price bar timestamps
- finite numeric policy weights and thresholds
- candidate policies with duplicate `policy_id` are rejected

The fixture must be self-contained. The optimizer must not infer missing policy
or replay fields from outside the fixture.

## Replay Inputs

The replay fixture may embed advisory evidence derived from:

- market discovery evidence
- technical setup evidence
- LLM signal evaluation
- trade plans
- paper evaluation summaries

However, the primary replay comparison unit is not the embedded summary object
itself. v3.7 should rerun policy logic on normalized replay rows. Embedded
evidence fields are just inputs to deterministic scoring and filtering.

Each replay row should normalize into one policy-evaluable event with:

- `ticker`
- `timestamp`
- deterministic score inputs
- setup grade
- entry/stop/target references
- linked price path

If a replay row lacks required deterministic fields, it should contribute to
missing-data or blocked-rate metrics rather than guessed outputs.

## Policy Parameter Schema

The baseline and candidate policy schema should include:

- score weights
- thresholds
- minimum risk/reward
- setup grade requirements
- maximum risk caps
- LLM weight cap

Recommended fields:

- `policy_id`
- `score_weights.technical`
- `score_weights.discovery`
- `score_weights.llm`
- `minimum_score_threshold`
- `minimum_risk_reward`
- `allowed_setup_grades`
- `max_risk_pct_per_trade`
- `max_basket_risk_pct`
- `llm_weight_cap`
- `allow_short`
- `allow_margin`
- `allow_leverage`
- `allow_market_orders`

Safety constraints are not negotiable. Candidate policies that enable short,
margin, leverage, market-order-first behavior, LIVE-like behavior, or safety
boundary relaxation should be rejected as unsafe before replay comparison.

## Window Construction

Walk-forward windows should be timestamp-based and deterministic.

Recommended first-version behavior:

- sort replay rows by timestamp
- partition them into ordered windows
- for each evaluation step:
  - use the configured number of earlier windows as training context
  - use the next window as the evaluation window
- advance by fixed stride

The train phase in v3.7 is not an unconstrained search engine. It exists to
evaluate candidate policies against baseline policies under walk-forward
discipline. The first version should focus on evaluating pre-specified
candidate policies, not auto-generating new policies.

The optimizer must prevent lookahead:

- evaluation windows may not use future replay rows
- train context for one window may not include any later window
- baseline and candidate policies must see the same window boundaries

## Deterministic Policy Rerun

For each policy and each evaluation window:

1. normalize replay rows
2. score each row using the policy weights
3. apply threshold and setup-grade filters
4. enforce risk/reward and risk-cap gates
5. generate advisory paper-trade inputs
6. rerun deterministic replay evaluation on the linked price paths
7. collect per-window metrics

The rerun path is advisory only. It must not create `StrategyDecision`,
`OrderIntent`, order drafts, or execution approvals.

## Metrics

The optimizer should calculate, per window and in aggregate:

- `total_return_pct`
- `max_drawdown_pct`
- `win_rate`
- `profit_factor`
- `expectancy_amount`
- `exposure_time_pct`
- `trade_count`
- `missing_data_rate`
- `blocked_rate`
- `stability_score`

Definitions:

- `missing_data_rate = missing_data_count / replay_row_count`
- `blocked_rate = blocked_count / replay_row_count`
- `stability_score` measures consistency of candidate-minus-baseline outcomes
  across evaluation windows

The first implementation should avoid opaque statistics. Stability should be a
simple deterministic function over per-window deltas, such as directional
consistency plus capped variance penalties.

## Baseline Vs Candidate Comparison

The optimizer compares baseline and candidate policies on the same evaluation
windows.

Per candidate, the report should include:

- per-window baseline metrics
- per-window candidate metrics
- per-window delta metrics
- aggregate baseline metrics
- aggregate candidate metrics
- aggregate deltas
- stability score
- gate results

The optimizer should not compare policies that were evaluated on different row
sets or different window boundaries.

## Promotion Gates

Promotion decisions must use explicit deterministic gates:

- minimum sample count
- drawdown cap
- performance improvement threshold
- stability threshold
- no safety violation

Recommended semantics:

- `INSUFFICIENT_EVIDENCE`
  - candidate did not meet minimum sample count or produced too little usable
    data across windows
- `REJECT_UNSAFE_POLICY`
  - candidate violated any permanent safety constraint
- `KEEP_BASELINE_POLICY`
  - candidate was safe but did not clear promotion thresholds
- `DEMOTE_CANDIDATE_POLICY`
  - candidate materially underperformed baseline or exceeded drawdown bounds
- `PROMOTE_CANDIDATE_POLICY`
  - candidate cleared all safety and evidence gates and achieved required
    improvement with acceptable stability

Suggested first-version gate ordering:

1. safety rejection
2. sample sufficiency
3. drawdown cap
4. performance improvement threshold
5. stability threshold

## Report Schema

The JSON report should contain:

- schema version `3.7-policy-replay-report`
- fixture checksum
- `run_id`
- `created_at`
- baseline policy summary
- candidate policy summaries
- replay window summaries
- per-candidate comparison results
- final promotion decisions
- advisory-only safety metadata

Required advisory metadata:

- `advisory_only=true`
- `policy_changed=false`
- `orders_created=false`
- `order_intents_created=false`
- `order_drafts_created=false`
- `execution_approved=false`
- `gates_bypassed=false`
- `external_network_calls=false`

The report must make it explicit that recommendation output does not activate
or mutate production strategy behavior.

## Optional Audit Persistence

JSON output is the preferred and default persistence format in v3.7.

If SQLite audit is later justified, it must satisfy all of:

- service-layer only
- optional and default-off
- append-only
- never used as optimizer core input
- not imported by core optimizer modules

SQLite is not required for the first v3.7 implementation.

## CLI

Suggested commands:

```bash
python3.11 -m stock_risk_mcp.cli policy-replay-run --fixture-file data/policy_replay_fixture.json --output-file outputs/policy_replay_report.json
python3.11 -m stock_risk_mcp.cli policy-replay-show --output-file outputs/policy_replay_report.json
```

`policy-replay-run`:

- requires one exact local fixture file
- reruns baseline and candidate policies deterministically by replay window
- writes JSON output only by default
- must not access broker, Kiwoom, account, network, cloud, or credential paths

`policy-replay-show`:

- reads one exact output JSON file
- prints or returns a deterministic report summary
- performs no recalculation and no external access

## Safety Boundary

v3.7 must keep the existing v3 advisory safety boundary intact:

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
- no real account or holdings dependency

Even when candidate policies outperform baseline, the optimizer may only
recommend promotion. It must not activate the candidate policy automatically.

## Testing Requirements

The implementation plan should include tests for:

- strict fixture validation
- deterministic timestamp window splitting
- baseline and candidate policies seeing identical replay rows
- deterministic policy rerun outputs
- unsafe policy rejection
- insufficient evidence gating
- drawdown cap gating
- performance improvement threshold gating
- stability threshold gating
- missing-data rate and blocked-rate calculation
- no broker, Kiwoom, account, order, or network imports in core modules
- no `StrategyDecision`, `OrderIntent`, order draft, or execution approval
- offline deterministic system-smoke
- preservation of existing v2 through v3.6 tests

Representative deterministic cases should include:

- one candidate clearly outperforming baseline and being promoted
- one candidate matching baseline and being kept behind baseline
- one candidate underperforming and being demoted
- one candidate rejected for unsafe parameters
- one candidate with too few usable trades yielding `INSUFFICIENT_EVIDENCE`
- one replay fixture with missing price-path linkage
- one multi-window fixture where the candidate is unstable across windows

## System Smoke

The v3.7 system-smoke should use a temporary local JSON fixture only. It should
verify:

- `policy_replay_fixture_run=true`
- deterministic JSON output written
- `policy_changed=false`
- `order_intents_created=false`
- `external_network_calls=false`

The smoke path must not depend on broker, Kiwoom, account, network, cloud,
credential, token, or execution infrastructure.

## Implementation Notes

The first implementation should stay intentionally boring:

- one self-contained fixture
- explicit timestamp windows
- explicit baseline-vs-candidate rerun
- explicit gate ordering
- explicit recommendation statuses
- no auto-search
- no stochastic optimization
- no hidden parameter mutation

Later releases may add broader candidate sweeps, compatibility modes for
precomputed advisory reports, richer hyperparameter search, or automatic draft
promotion workflows, but only through separately scoped designs with the same
safety review discipline.
