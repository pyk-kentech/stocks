# Analysis Report Layer Design

## Scope

Create deterministic English/Korean JSON and Markdown reports from existing stored pipeline, scan, basket, paper, policy-suite, and alert records. The layer makes no external API or LLM calls, does not request realtime data, and does not provide investment advice.

## Architecture

- `report_context.py` reads stored source records and builds evidence-oriented dictionaries.
- `analysis_report.py` turns each context into a typed `AnalysisReport`.
- `report_templates.py` contains English/Korean labels, disclaimer, and suggested next questions.
- `report_markdown.py` and `report_json.py` render the same report model.
- CLI commands share one persistence path for optional output files and DB storage.

## Source Rules

Pipeline reports include the PipelineRun, severity-sorted alerts, and linked scan, official basket, and policy suite when available. Scan reports summarize decision counts, top INCLUDE candidates, warnings, and signal enrichment metadata. Basket reports prefer official `basket_plans`; if absent they use a replay basket snapshot matched by `basket_id` and explicitly warn that it may be replay-only. Policy reports compare baseline and candidate metrics and warn that recommendation does not itself approve or activate a policy.

Memory-only paper results are never reconstructed or estimated.

## Output Persistence

Output-file writes occur after report generation. Write failure adds `failed to write output file: <error>` to report warnings and does not fail report generation. Optional DB save happens afterward and persists the warning independently. CLI output always includes requested/saved/error output-file metadata.
