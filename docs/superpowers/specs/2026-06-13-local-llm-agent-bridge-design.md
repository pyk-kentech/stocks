# Local LLM Agent Bridge Design

## Scope

Add a read-only bridge that converts stored analysis reports and pipeline evidence into deterministic agent contexts, prompts, and briefs. It defaults to DRY_RUN and never calls cloud LLM APIs, executes orders, changes policies, or modifies hard-risk rules.

## Safety

Every context is READ_ONLY and includes fixed forbidden actions for order execution, policy activation/approval, hard-risk changes, stop-loss disabling, broker changes, private-account scraping, and terms-of-service bypass. Agent tool manifests contain only read-only repository lookups.

## Local LLM Backends

- `DRY_RUN`: creates a request and returns a DRY_RUN response without transport use.
- `OLLAMA_LOCAL`: explicit local invocation only.
- `OPENAI_COMPAT_LOCAL`: endpoint required and local loopback hosts only.
- `DISABLED`: no invocation.

Only `localhost`, `127.0.0.1`, and `::1` are permitted. Any other endpoint is blocked before transport invocation and produces a FAILED response containing `non-local endpoint blocked`.

## Persistence

Agent contexts, prompts, briefs, local LLM requests, and responses are stored only through explicit save options. A blocked endpoint request/response pair can be persisted for audit without sending data.
