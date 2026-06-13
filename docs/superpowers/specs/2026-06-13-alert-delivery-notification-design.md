# Alert Delivery / Notification Layer Design

## Scope

Add a local-only notification outbox that converts PipelineAlert,
AnalysisReport, AgentBrief, and LocalLLMResponse records into deliverable
NotificationMessage records. Implement only console, local-file, mock, and
disabled channels. No external APIs, webhooks, email, chat services, orders, or
investment advice are in scope.

## Architecture

- `notifications.py` defines channel, severity, and message models.
- `notification_run.py` defines delivery run status and counters.
- `notification_templates.py` converts stored source records into sorted,
  deduplicated, disclaimer-bearing notification messages.
- `notification_channels.py` provides isolated local delivery adapters.
- `notification_outbox.py` handles DB dedupe, channel delivery, status
  aggregation, and opt-in persistence.
- `notification_digest.py` builds a dated markdown digest from stored evidence.

## Delivery Contract

Messages are sorted CRITICAL, HIGH, WARNING, INFO. A saved dedupe key suppresses
later saved delivery attempts; duplicate keys inside one delivery batch are
also suppressed. `save=false` never persists runs or messages.

No messages produces `NO_ALERTS`; disabled produces `DISABLED`; all successful
deliveries produce `COMPLETED`; mixed results produce `PARTIAL`; and all failed
deliveries produce `FAILED`. Channel failures are captured in the run and
message records and never crash an operational pipeline.

Local-file output uses JSONL for `.jsonl` paths and Markdown otherwise. Failed
file writes remain auditable when `save=true`.

## Source Conversion

Pipeline dedupe keys use pipeline run ID, alert type, ticker, and title. Reports
include summary, metrics, and warnings. Briefs include key points, risks, and
next actions. Local LLM response dedupe keys use response ID, status, backend,
and model. LLM content preview is capped at 500 characters; full content stays
in the original stored response.

FAILED local LLM responses are WARNING, except `non-local endpoint blocked`,
which is HIGH. COMPLETED and DRY_RUN responses are INFO.

## Digest And Pipeline Integration

Daily digest collects source records created on the selected date and applies
the minimum severity filter. Local LLM responses are excluded unless explicitly
requested, and only failed responses are included in that digest source.

`run-paper-pipeline` and `watch-loop` deliver only with `--notify`. Notification
status and run ID are appended to PipelineRun notes after pipeline completion.
Notification failure never changes the pipeline's existing status.
