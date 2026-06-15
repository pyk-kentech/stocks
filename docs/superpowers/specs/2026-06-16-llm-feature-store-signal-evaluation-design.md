# v3.4 LLM Feature Store And LLM Signal Evaluation Design

## Scope

v3.4 adds an offline deterministic feature store and evaluation layer for
already-created LLM signals. It reads explicit local JSON signal and outcome
fixtures, validates semantic, theme, catalyst, and risk-language features,
evaluates those advisory features against fixture-contained 1D, 3D, and 5D
future outcomes, and produces auditable evaluation reports.

The LLM is not a trader. v3.4 does not call an LLM, generate prompts, change
strategy weights, create `StrategyDecision`, create `OrderIntent`, create
order drafts, approve RiskGate or ExecutionGate, submit orders, or execute
trades. It does not access live data, PROD, broker, Kiwoom, account-read,
credentials, tokens, external network, or cloud LLM services.

## Architecture And Dependency Boundaries

The implementation is divided into pure core and optional audit boundaries:

- `llm_feature_models.py` defines strict prompt, model, signal, outcome,
  feature-store result, evaluation, and report models.
- `llm_feature_fixture.py` reads and validates one exact local signal JSON
  fixture and one exact local outcome JSON fixture. It performs no discovery
  or external reads.
- `llm_signal_evaluation.py` is the pure deterministic evaluator. It consumes
  validated models only and has no repository or service dependency.
- `llm_feature_service.py` coordinates exact-file loading, checksums, pure
  evaluation, optional exact local JSON output, and optional append-only audit
  persistence.

Core models, fixture loading, and evaluation modules must not import database,
repository, provider, realtime, broker, Kiwoom, account, order, strategy,
credential, token, network, cloud LLM, RiskGate, or ExecutionGate modules.
Only the service and repository layers may persist audit records, and only
when the user explicitly supplies `--db`.

Default execution is DB-free JSON output only. SQLite is never an input to the
v3.4 evaluator.

## Signal Fixture Contract

The strict signal fixture is:

```json
{
  "schema_version": "3.4-signals",
  "run_id": "llm-feature-run-1",
  "created_at": "2026-01-01T16:00:00+00:00",
  "prompt_version": {
    "prompt_version_id": "prompt-theme-v1",
    "name": "theme-catalyst-extraction",
    "version": "1.0.0",
    "prompt_checksum": "sha256:...",
    "created_at": "2026-01-01T00:00:00+00:00"
  },
  "model_version": {
    "model_version_id": "model-local-v1",
    "backend": "LOCAL_FIXTURE",
    "model_name": "fixture-model",
    "model_version": "1.0.0",
    "runtime_metadata": {
      "quantization": "fixture"
    }
  },
  "signals": [
    {
      "ticker": "ABC",
      "as_of_time": "2026-01-01T15:30:00+00:00",
      "source_ids": ["news-1"],
      "event_type": "PRODUCT_LAUNCH",
      "theme_tags": ["AI", "SEMICONDUCTOR"],
      "direction": "POSITIVE",
      "catalyst_strength_score": 0.8,
      "risk_language_score": 0.2,
      "uncertainty_score": 0.25,
      "related_tickers": ["XYZ"],
      "summary": "Advisory fixture summary",
      "evidence_refs": ["evidence-1"],
      "may_create_order": false,
      "may_bypass_gates": false
    }
  ]
}
```

Validation requires:

- schema version exactly `3.4-signals`
- non-empty `run_id`
- timezone-aware fixture, prompt, and signal timestamps
- `prompt_version.created_at <= signal.as_of_time <= fixture.created_at`
- at least one signal
- normalized uppercase non-empty tickers
- non-empty `event_type`, `summary`, version IDs, names, and version strings
- a non-empty checksum identifier without storing the original prompt
- direction exactly `POSITIVE`, `NEGATIVE`, `NEUTRAL`, or `UNCERTAIN`
- catalyst, risk-language, and uncertainty scores from `0.0` through `1.0`
- `may_create_order` present and exactly `false`
- `may_bypass_gates` present and exactly `false`
- no unknown fields

`source_ids`, `theme_tags`, `related_tickers`, and `evidence_refs` are
normalized into sorted de-duplicated string lists. The lists may be empty, but
every included string must be non-empty after trimming. Related tickers are
uppercased and may not contain the signal ticker itself. The other lists
preserve case after trimming.

The duplicate signal key is:

```text
ticker + as_of_time + event_type + prompt_version_id + model_version_id
```

More than one signal with the same normalized key is a fixture validation
error. Array order never determines precedence.

## Prompt And Model Metadata

`LLMPromptVersion` contains:

- `prompt_version_id`
- `name`
- `version`
- `prompt_checksum`
- `created_at`

`LLMModelVersion` contains:

- `model_version_id`
- `backend`
- `model_name`
- `model_version`
- `runtime_metadata`

Allowed backends are:

- `LOCAL_FIXTURE`
- `LOCAL_MODEL`
- `DISABLED`

Cloud backends and arbitrary endpoint metadata are forbidden. Runtime metadata
must be JSON-safe and is recursively checked so no nested key may contain
credential, token, secret, API-key, authorization, cookie, endpoint, URL, or
account terms. The full original prompt is not accepted by the fixture schema
and is not persisted.

Prompt and model metadata identify the already-created signals. They do not
cause v3.4 to invoke any model.

## Outcome Fixture Contract

The strict outcome fixture is:

```json
{
  "schema_version": "3.4-outcomes",
  "created_at": "2026-01-07T16:00:00+00:00",
  "snapshots": [
    {
      "ticker": "ABC",
      "as_of_time": "2026-01-01T15:30:00+00:00",
      "reference_price": 100,
      "horizons": [
        {
          "horizon": "1D",
          "outcome_time": "2026-01-02T16:00:00+00:00",
          "future_price": 105,
          "return_pct": 5,
          "max_drawdown_pct": 2
        }
      ]
    }
  ]
}
```

Validation requires:

- schema version exactly `3.4-outcomes`
- timezone-aware fixture, snapshot, and outcome timestamps
- at least one unique normalized `ticker + as_of_time` snapshot
- positive finite reference and future prices
- horizon exactly `1D`, `3D`, or `5D`
- no duplicate horizons within a snapshot
- `snapshot.as_of_time <= fixture.created_at`
- `outcome_time > snapshot.as_of_time`
- `outcome_time <= fixture.created_at`
- finite `return_pct`
- finite `max_drawdown_pct` from `0` through `100`
- no unknown fields

`max_drawdown_pct` is a positive loss magnitude: `0` means no drawdown and
larger values mean worse drawdown. The fixture-supplied `return_pct` must match
`(future_price - reference_price) / reference_price * 100` within an absolute
tolerance of `1e-9`. v3.4 does not derive missing horizons or synthesize
prices.

Signals connect only to an outcome snapshot whose normalized ticker and
`as_of_time` exactly match. A matching snapshot may omit one or more horizons;
each omitted horizon produces an auditable `NEEDS_MORE_DATA` evaluation.
Missing snapshots also produce `NEEDS_MORE_DATA` for all three horizons.

## Lookahead Prevention

Signal features are fixed at `signal.as_of_time`. Future outcome values are
used only after the signal has already been loaded and validated.

The evaluator enforces:

- exact signal-to-outcome matching by ticker and `as_of_time`
- every outcome timestamp strictly after its matched signal timestamp
- no outcome data in feature-store signal output
- no result from one as-of snapshot reused for another as-of snapshot
- no inferred or nearest-timestamp matching

Related-ticker spillover uses only a related ticker outcome snapshot with the
same `as_of_time` as the source signal and the requested horizon. A missing
related-ticker snapshot or horizon is missing data, not a zero return.

## Feature Store Result

`LLMFeatureStoreResult` records:

- schema version `3.4-feature-store-result`
- signal fixture checksum
- run, prompt-version, and model-version metadata
- normalized advisory signals
- signal count
- safe metadata

Feature-store ingestion validates and normalizes signals but does not evaluate
future outcomes or change any strategy behavior.

## Pure Signal Evaluation

For every signal and each ordered horizon `1D`, `3D`, and `5D`, the evaluator
produces one `LLMSignalEvaluation`.

Evaluation status is:

- `EVALUATED`
- `NEEDS_MORE_DATA`

Confidence is fixed:

```text
confidence = 1 - uncertainty_score
```

Confidence buckets are:

- `HIGH` when confidence is at least `0.75`
- `MEDIUM` when confidence is at least `0.50` and below `0.75`
- `LOW` when confidence is below `0.50`

Risk-warning buckets are:

- `HIGH_RISK_WARNING` when `risk_language_score >= 0.70`
- `LOW_RISK_WARNING` otherwise

Directional outcomes are:

- `HIT` for a positive signal when `return_pct > 0`
- `HIT` for a negative signal when `return_pct < 0`
- `MISS` for the opposite sign or a zero return
- `NOT_APPLICABLE` for neutral and uncertain signals
- `NEEDS_MORE_DATA` when the horizon outcome is unavailable

Neutral and uncertain signals are separately counted and excluded from
directional hit-rate denominators.

Each evaluated related ticker produces a spillover record containing the
source signal key, related ticker, horizon, return, drawdown, and availability
status. Related-ticker direction uses the source signal direction. Neutral and
uncertain source signals remain `NOT_APPLICABLE` for spillover hit rate.

## Evaluation Questions And Metrics

`LLMSignalEvaluationReport` contains per-horizon metrics and version-group
metrics. All aggregation order is deterministic.

### Positive Signal Outperformance

For each horizon, compare positive-signal mean and median return against the
full fixture baseline.

The full fixture baseline uses each unique available
`ticker + as_of_time + horizon` outcome once. It is not weighted by the number
of signals referencing an outcome. Positive-signal metrics use evaluated
positive signals and retain signal-level weighting because the question is
about signal performance.

Output includes sample counts, mean and median returns, and positive-minus-
baseline deltas.

### Confidence Comparison

For each horizon and confidence bucket, report:

- evaluated directional sample count
- mean and median return
- directional hit rate
- missing-data count and rate

The report explicitly compares `HIGH` and `LOW` bucket metrics. It does not
claim confidence calibration when either bucket has insufficient samples.

### Risk Warning Accuracy

For each horizon, compare mean and median `max_drawdown_pct` for
`HIGH_RISK_WARNING` and `LOW_RISK_WARNING` signals.

This evaluates whether risk language identified later drawdown. It does not
claim that warnings caused or reduced drawdown. Larger drawdown magnitude in
the high-risk group is evidence of warning accuracy.

### Related-Ticker Spillover

For each horizon, report related-ticker available count, missing count, mean
and median return, directional hit rate where applicable, and mean drawdown.
Only exact same-as-of related-ticker outcomes are evaluated.

### Prompt And Model Version Comparison

Group evaluations by:

```text
prompt_version_id + model_version_id + horizon
```

For each group, report:

- prompt and model version identifiers
- evaluated sample count
- missing-data count and rate
- mean and median return
- directional hit rate
- mean and median max drawdown

Because one approved signal fixture contains exactly one prompt version and
one model version, a single v3.4 evaluation report contains one version group.
The version-tagged metrics make separately generated reports comparable, but
v3.4 does not combine multiple reports or declare a winning version. A future
explicit multi-report comparison command may answer which version performed
best after defining common-outcome and sample-adequacy rules.

v3.4 does not select a winning version automatically, promote a prompt/model,
or change strategy weights.

## Minimum Sample Policy

The minimum sample count is fixed at `5` available observations per horizon
for every aggregate metric group.

Aggregate status is:

- `SUFFICIENT_SAMPLE` when available sample count is at least `5`
- `INSUFFICIENT_SAMPLE` otherwise

Metrics may still be calculated and displayed below the threshold for
auditability, but no below-threshold group may be described as outperforming,
better, calibrated, or validated. Missing-data rate always uses available plus
missing observations as its denominator.

## Result Safety Metadata

`LLMFeatureStoreResult`, `LLMSignalEvaluation`, and
`LLMSignalEvaluationReport` contain safety metadata including:

```json
{
  "advisory_only": true,
  "llm_called": false,
  "strategy_weight_changed": false,
  "strategy_decisions_created": false,
  "orders_created": false,
  "gates_bypassed": false,
  "external_network_calls": false
}
```

No output model contains execution authority or an executable recommendation.

## Optional SQLite Audit

When and only when `--db` is explicitly supplied, the service layer may store
append-only audit records in:

- `llm_prompt_versions`
- `llm_model_versions`
- `llm_feature_store_runs`
- `llm_feature_signals`
- `llm_signal_evaluations`

The feature-store run records checksums, counts, status, and safe metadata.
Signal and evaluation rows store normalized strict-model JSON plus indexed
lookup columns. Prompt and model rows store identifiers, versions, checksums,
backend, and safe metadata only.

Persistence rules:

- core modules never import repository or database modules
- default execution performs no SQLite read or write
- SQLite is output audit storage only and never supplies evaluation inputs
- records are append-only
- prompt versions are unique by `prompt_version_id` and by `name + version`
- model versions are unique by `model_version_id` and by
  `backend + model_name + model_version`
- normalized duplicate signal keys have unique constraints
- an already-stored identical prompt or model version may be referenced by a
  later run without inserting or mutating the version row
- full prompts, credentials, tokens, secrets, endpoints, URLs, authorization
  values, cookies, account data, and unsafe runtime metadata are not stored
- an audit conflict returns a JSON-safe error and does not alter existing rows

`llm_signal_evaluations` stores individual evaluation records, including
missing-data outcomes. The complete aggregate report remains in the explicit
output JSON rather than adding a separate report table in v3.4.

## CLI

Add JSON-safe commands:

```bash
python -m stock_risk_mcp.cli llm-feature-store-run \
  --signal-fixture-file data/llm_signals.json \
  [--db data/stock_risk_mcp.sqlite3] \
  [--output-file outputs/llm_feature_store.json]

python -m stock_risk_mcp.cli llm-signal-evaluate \
  --signal-fixture-file data/llm_signals.json \
  --outcome-fixture-file data/llm_outcomes.json \
  [--db data/stock_risk_mcp.sqlite3] \
  [--output-file outputs/llm_signal_evaluation.json]

python -m stock_risk_mcp.cli llm-signal-evaluation-show \
  --output-file outputs/llm_signal_evaluation.json
```

Without `--db`, feature-store and evaluation commands read only their explicit
local JSON fixtures and perform no persistence. Without `--output-file`, they
print strict JSON results. With an output file, they write exactly that local
JSON file and print a safe summary.

`llm-signal-evaluation-show` reads and validates exactly the selected local
result JSON. It does not discover files or read SQLite.

SQLite list/show commands are omitted from the required v3.4 scope. They may
be added only if implementation review identifies a concrete audit inspection
need, and they must read only the new audit tables.

Invalid fixtures, result files, or audit conflicts return JSON-safe validation
errors without traceback or partial successful result.

## Safety And Testing

Required tests cover:

- strict signal, prompt, model, and outcome fixture validation
- normalized sorted de-duplicated list fields
- duplicate signal and outcome key rejection
- required false order and gate flags
- forbidden cloud backend and unsafe runtime metadata rejection
- deterministic feature-store and evaluation output
- exact ticker/as-of matching and lookahead prevention
- missing snapshot and missing horizon `NEEDS_MORE_DATA`
- positive versus unique-outcome baseline metrics
- confidence bucket and directional hit-rate metrics
- risk-warning drawdown accuracy metrics without causal claims
- related-ticker same-as-of spillover evaluation
- prompt/model version grouping and minimum-sample status
- version-tagged metrics without cross-report winner selection
- default DB-free operation and optional append-only audit persistence
- JSON-safe CLI errors and exact result-file loading
- no cloud LLM calls, credentials, tokens, external network, or extra-file
  discovery
- no broker, Kiwoom, account, order, StrategyDecision, OrderIntent, RiskGate,
  or ExecutionGate dependency in core modules
- offline deterministic system smoke
- preservation of all existing v2 and v3 tests

System smoke creates temporary local signal and outcome JSON fixtures, runs
feature-store validation and signal evaluation without `--db`, and verifies:

- `llm_feature_store_fixture_run=true`
- `llm_signal_evaluation_fixture_run=true`
- `llm_called=false`
- `external_network_calls=false`

System smoke does not call a local or cloud model, read credentials or tokens,
query provider/realtime data, or create strategy/order artifacts.

## Explicit Non-Goals

v3.4 intentionally excludes:

- prompt generation, prompt execution, and any local or cloud LLM invocation
- live data, provider, realtime, scraping, and external network
- credential, token, account, broker, or Kiwoom access
- automatic prompt/model promotion or strategy-weight changes
- multi-report prompt/model winner selection
- StrategyDecision, OrderIntent, order draft, gate approval, order, execution,
  PROD, and LIVE paths
- causal claims that risk warnings reduced drawdown
- synthetic, inferred, nearest-time, or DB-sourced future outcomes
- strategy, backtest, technical evidence, or discovery-layer integration

Future versions may separately define controlled signal generation, strategy
feature consumption, or promotion gates only after sufficient offline
evaluation evidence and without weakening the advisory-only boundary.

## Success Criteria

The design is implemented successfully when:

- explicit local signal and outcome JSON fixtures produce deterministic
  feature-store and evaluation results
- all signal and outcome timestamps, keys, scores, versions, and safety flags
  are strictly validated
- future outcomes are used only after exact ticker/as-of matching
- missing outcomes remain auditable and are never inferred
- evaluation reports answer all in-scope questions with sample and
  missing-data status and emit version-tagged metrics for later comparison
- default execution is DB-free and optional SQLite storage is append-only
  service-layer audit output
- no LLM is called and no strategy weight, decision, order artifact, gate, or
  execution state changes
- no live, PROD, broker, Kiwoom, account, credential, token, provider,
  realtime, cloud, or external-network path is used
