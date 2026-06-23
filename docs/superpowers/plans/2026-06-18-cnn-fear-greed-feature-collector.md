## v7.6.1 CNN Fear & Greed Feature Collector

### Goal
- Collect CNN Fear & Greed snapshots as a local report-only feature source.
- Keep the collector safe by default: mocked transport, dry-run, explicit network opt-in.
- Emit feature fields compatible with offline regime/allocation workflows without embedding trading rules.

### Scope
- Local JSON fixture/config loader
- Injectable HTTP transport client
- Conservative JSON-first payload parsing with schema-health fallback
- Snapshot/history/feature/source-health/gap/audit reports
- CLI commands for report generation
- system_smoke coverage for safe default behavior

### Non-goals
- No browser automation
- No Selenium
- No login
- No credential, token, account, broker, order, or trading path
- No autonomous actioning from fear/greed levels
- No parquet support

### Safety
- Default mode is mocked and non-executable
- Real collection requires `--execute` and `--acknowledge-cnn-fear-greed-collection`
- Pytest uses mocked HTTP only
- Schema drift produces degraded source-health and gap output rather than unsafe assumptions

### Data shape
- Snapshot: score, category, as_of, available_at, source_url, collection_mode, component scores, observed schema version, raw payload redacted
- Feature integration: `cnn_fear_greed_score`, `cnn_fear_greed_category`, `cnn_fear_greed_available_at`, `cnn_fear_greed_source_ref`, `sentiment_fear_bucket`
- Reports: snapshot, history, feature integration, source health, gap, audit

### Execution order
1. Add models, guard, and fixture loader
2. Add client and engine with mocked transport-first behavior
3. Wire CLI commands and explicit network opt-in gate
4. Add focused tests
5. Add system_smoke coverage
6. Run focused tests, system_smoke, full pytest
