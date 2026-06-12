# Policy Evaluation Suite And Promotion Gate Design

## Goal

Evaluate baseline and candidate StrategyPolicies across multiple ReplayRuns,
aggregate only comparable completed replay pairs, and create auditable promotion
proposals without automatically changing policy status.

## Pair-Based Aggregation

Each requested ReplayRun forms one baseline/candidate pair.

- `replay_run_count` is the number of unique requested ReplayRuns.
- `completed_pair_count` counts pairs where both results are `COMPLETED`.
- Only completed pairs contribute returns, objectives, win rates, loss rates,
  and their deltas.
- A pair with either side `NO_DATA` is counted in `no_data_replay_count`.
- A pair with either side missing, `FAILED`, or `CREATED` is counted in
  `incomplete_pair_count`.
- Excluded pairs never contribute to performance metrics.
- Notes record excluded pair counts and reasons.

`no_data_rate` is `(no_data_replay_count + incomplete_pair_count) /
replay_run_count`, conservatively treating every unusable pair as unavailable
data.

## Models And Persistence

Add:

- `PolicyEvaluationDecision`: `ACCEPT`, `REJECT`, `NEED_MORE_DATA`
- `PolicyEvaluationSuiteResult`
- `PolicyPromotionProposal`

The suite model uses `completed_pair_count` and `incomplete_pair_count` as
explicit fields. Add new SQLite tables `policy_evaluation_suites` and
`policy_promotion_proposals` with repository save/get/list methods.

## Replay Batch

`run_policy_replay_batch` accepts explicit ReplayRun IDs and both policies.
For each run and policy, it reuses the latest matching `COMPLETED` or `NO_DATA`
PolicyReplayResult when available; otherwise it runs Full Policy Replay.
Failures are captured as incomplete pairs so one bad ReplayRun does not abort
the entire suite.

When CLI ReplayRun IDs are omitted, the latest ReplayRuns are used. Batch replay
keeps intermediate TradePlans and official BasketPlans memory-only/snapshot-only
by default.

## Suite Evaluation

Data sufficiency rules have priority:

1. `replay_run_count < min_replay_runs` -> `NEED_MORE_DATA`
2. `completed_pair_count < min_completed_replays` -> `NEED_MORE_DATA`
3. `no_data_rate > 0.4` -> `NEED_MORE_DATA`
4. Any completed baseline or candidate replay with `candidate_count < 3` ->
   `NEED_MORE_DATA`

After data sufficiency:

- `ACCEPT` requires objective delta `>= +5`, positive return delta, and
  candidate win rate not below baseline win rate.
- `REJECT` applies when objective delta `<= -5` or return delta `< -2`.
- Otherwise return `NEED_MORE_DATA`.

## Promotion Gate

Creating a promotion proposal never changes StrategyPolicy status.

- Accepted suite -> proposed `APPROVED`
- Rejected suite -> proposed `REJECTED`
- Need-more-data suite -> proposed `DRAFT`

`policy-approve` explicitly changes a non-rejected existing policy to
`APPROVED`.

`policy-activate` explicitly changes only an `APPROVED` policy to `ACTIVE` and
retires every currently active policy first. No force option is provided.

## CLI

Add:

- `policy-evaluate-suite`
- `policy-evaluation-suites`
- `policy-propose-promotion`
- `policy-promotion-proposals`
- `policy-approve`
- `policy-activate`

Suite output includes policy identities, replay count, completed/incomplete/no
data pair counts, no-data rate, performance deltas, recommendation, and notes.

## Safety And Documentation

The suite uses local paper replay results only. It does not call external APIs,
place orders, modify hard-risk rules, guarantee investment performance, or
automatically activate a policy.

README and WORK_SUMMARY explain pair-only aggregation, proposal versus status
change, `APPROVED` versus `ACTIVE`, and the operational impact of activation.

## Testing

Tests cover pair inclusion/exclusion, all data sufficiency rules, ACCEPT and
REJECT thresholds, persistence, promotion proposal mapping, explicit approval,
approved-only activation, retirement of the prior active policy, all CLI
commands, and the full existing test suite.
