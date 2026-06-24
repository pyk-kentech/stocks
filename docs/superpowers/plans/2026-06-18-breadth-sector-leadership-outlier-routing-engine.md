## v7.12 Breadth / Sector Leadership / Outlier Momentum Routing Engine

Goal: add a local/offline/report-only routing layer that distinguishes broad participation, narrow sector leadership, crowded or distorted leadership, and separate outlier momentum eligibility without creating executable trading paths.

Core design:
- single independent `breadth_leadership_routing_*` layer following the v7.9 / v7.10 / v7.11 pattern
- one input object carrying breadth snapshot, sector leadership snapshots, index distortion snapshot, outlier candidates, provider readiness refs, and v7.9/v7.10/v7.11 report-only dependency refs
- one engine producing:
  - primary routing decision
  - downstream routing constraints / warnings
  - report-only detail reports for breadth, participation, sector leadership, distortion, outlier sleeve policy, provider readiness, leakage, and gaps
- training-feature-compatible report for downstream offline dataset or model workflows

Policy:
- weak breadth is not an automatic market-wide ban
- healthy sector leadership may still route to `LEADERSHIP_ONLY` or `SECTOR_ONLY`
- large-cap leadership may route to `LARGE_CAP_ONLY`
- non-leaders under weak breadth fall to `WATCH_NON_LEADERS`
- outlier momentum is a separate high-risk sleeve only; it never implies normal broad-market permission
- v7.10 position sizing and v7.11 event risk hard gates are never overridden

Hard boundaries:
- local fixture only
- offline only
- report only
- non-executable
- no broker / Kiwoom / provider / network / account / order / WebSocket path
- no credential / token / secret handling
- no live / prod / autonomous path
- parquet unsupported

Implementation scope:
- models, guard, fixture loader, engine
- CLI wiring
- system smoke coverage
- focused tests plus full regression before commit/tag
