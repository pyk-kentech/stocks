# Local Static Dashboard Design

## Scope

Build self-contained UTF-8 HTML dashboards from records already stored in the
local SQLite database. The layer is for paper-trading and research monitoring
only. It starts no web server, makes no network request, loads no CDN asset, and
does not expose credentials, endpoint secrets, or order execution controls.

## Architecture

- `dashboard_models.py` defines dashboard types, build status, sections, and
  persisted build results.
- `dashboard_assets.py` contains the inline CSS string.
- `dashboard_html.py` provides escaped cards, badges, tables, JSON details, and
  full-page rendering.
- `dashboard_sections.py` queries repository records and creates overview,
  pipeline, daily, and policy section lists.
- `dashboard.py` renders, writes, records warnings/errors, and optionally saves
  DashboardBuildResult records.

## Rendering Contract

HTML is self-contained and uses inline CSS only. It contains no script tags,
external images, stylesheet links, or external anchors. All source values are
HTML escaped. Long structured values use `<details><pre>` blocks. HIGH and
CRITICAL sections sort before lower severities. Every dashboard includes a
paper-trading/research monitoring disclaimer and no performance guarantee.

## Build Status

- `COMPLETED`: HTML was written with all requested sections.
- `PARTIAL`: HTML was written, but one or more optional source sections failed.
- `FAILED`: output persistence failed and no usable HTML file was written.
- `NO_DATA`: HTML was written, but no stored source records matched.

Build failures are returned as DashboardBuildResult records instead of raising
through CLI or operational pipeline integration. Persistence remains opt-in
through `--save`, except pipeline integration records its dashboard build for
traceability.

## Dashboard Types

Overview shows recent operational, notification, reporting, import, connector,
LLM, and active-policy evidence. Pipeline shows one run and its linked records.
Daily filters evidence by the selected date and reports whether critical alerts
exist. Policy shows active/draft/approved policies, evaluation suites, and
promotion proposals without providing activation controls.

## Optional Browser Smoke

`scripts/preview_dashboard.py` validates a local HTML file and optionally opens
it in the system browser. It is not part of pytest or CI, starts no server,
loads no external resource, and exits with a warning when browser opening is
unavailable.
