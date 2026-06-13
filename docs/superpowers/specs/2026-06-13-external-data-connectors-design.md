# External Data Connector Interface Design

## Scope

Add a network-free connector skeleton that produces normalized local CSV/JSON files, records every connector run, and optionally feeds successful outputs into the existing Unified Data Import Pipeline. No API calls, scraping, authentication bypass, realtime requests, or order execution are implemented.

## Components

- `connector_run.py`: connector enums and immutable run/result/output models.
- `connectors.py`: `BaseConnector` protocol.
- `connector_outputs.py`: normalized CSV writing and row counting helpers.
- `mock_connectors.py`: deterministic market, news, dilution, Toss, and flow CSV generators.
- `local_connector.py`: validates an existing CSV/JSON and optionally copies it without changing content.
- `connector_registry.py`: explicit connector registration and default mock registry.
- `connector_pipeline.py`: sequential fault-isolated execution, persistence, output-to-import mapping, and aggregate status.

## Persistence

Each connector execution writes one `connector_runs` row. Successful connectors use `COMPLETED`; disabled connectors use `DISABLED`; expected connector failures are converted to `FAILED` with errors and do not stop later connectors.

## Import Integration

`run-connectors-and-import` maps successful output files by connector type into the existing Unified Import Pipeline. When no output exists, it still creates a failed ImportRun and adds `no connector output files available for import` to notes. Aggregate status is `COMPLETED` only when all connectors and import complete, `PARTIAL` when some output succeeds but any stage is incomplete, and `FAILED` when no output is available and import fails.

## CLI

- `connectors`
- `run-connectors`
- `connector-runs`
- `connector-show`
- `run-connectors-and-import`

All commands return traceable JSON. Expected connector failures do not produce tracebacks.
