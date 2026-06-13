# End-to-End Demo / Release Hardening Design

## Scope

Add a deterministic local orchestration layer that validates the existing mock
connector, import, operational paper pipeline, report, read-only agent, local
LLM dry-run, notification, and static dashboard layers. It performs no external
API calls, scraping, web requests, or real orders. Results describe system
smoke and release validation, not investment advice.

## Architecture

- `demo_pipeline.py` defines demo models and orchestrates public Python APIs.
- `demo_report.py` renders and writes the final JSON summary.
- `system_smoke.py` runs a fixed lightweight local demo and extracts core
  release-smoke checks.
- `release_check.py` reports repository release checklist guidance without
  running commands or changing git tags.

The demo uses the existing SQLite repository and deterministic mock connectors.
It records step results in memory and writes `demo_summary.json`; no new demo
database tables are required.

## Data And Time Contract

Mock connectors generate 120 days of local price history ending at the requested
`as_of_date`. The paper pipeline evaluates at `as_of_date - horizon_days` so the
imported history also contains deterministic forward bars for paper outcome
validation. Both dates are recorded in step metrics and summary output.

Default tickers are `AAPL`, `TSLA`, and `NVDA`. Default account values are
research-only sizing inputs and never create orders.

## Steps And Dependencies

The ordered steps are CONNECTORS, IMPORT, PAPER_PIPELINE, ANALYSIS_REPORT,
AGENT_CONTEXT, AGENT_PROMPT, LOCAL_LLM_DRY_RUN, NOTIFICATION, DASHBOARD, and
SUMMARY.

CONNECTORS, IMPORT, and PAPER_PIPELINE are core steps. A core failure makes the
overall result FAILED. Import failure skips pipeline and all dependent steps.
Report failure skips agent context, prompt, and dry-run, while notification and
dashboard may continue when a pipeline run exists. Non-core failures make the
overall result PARTIAL.

Every exception is captured in its DemoStepResult. CLI output remains
structured JSON and does not expose a traceback for expected step failures.

## Persistence And Outputs

Connector, import, and operational pipeline records follow their existing
persistence contracts. With `save_intermediate=true`, report, context, prompt,
local LLM request/response, notification, and dashboard audit records are also
saved. Output files are:

- `demo_summary.json`
- `notification.md`
- `dashboard.html`
- optional `report.md`

Output write failure is recorded on the relevant step while independent later
steps continue when possible.

## System Smoke And Release Check

`system-smoke` reuses `run_local_demo` with deterministic defaults and reports
DB migration, mock connector, import, pipeline, dashboard, and no-network
checks. `release-check` only prints recommended verification commands, required
documentation presence, major CLI names, recent dashboard smoke information,
and a suggested version tag string. It never runs tests or creates a tag.
