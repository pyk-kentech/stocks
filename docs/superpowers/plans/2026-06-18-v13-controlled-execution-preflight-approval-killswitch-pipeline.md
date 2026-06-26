## v13.0 Controlled Execution Preflight / Approval / Kill-Switch Pipeline Plan

### Scope

- Add new independent `controlled_execution_*` public surface
- Keep execution default blocked and non-executable
- Support report-only, preflight-only, mock execution, and dry-run-no-broker modes
- Expose live execution only as blocked capability/preview boundary

### Work Items

1. Implement canonical models and fixture loader
2. Implement guard, preflight, approval, kill-switch, duplicate guard, adapter, rehearsal, and audit engines
3. Wire CLI report commands
4. Extend `system_smoke.py` with v13 smoke coverage
5. Add focused tests
6. Run focused pytest, system smoke, full pytest
7. Commit and tag `v13.0.0-controlled-execution-preflight-approval-killswitch-pipeline`

### Constraints

- No real broker/provider/network calls in tests
- No env or credential reads in tests
- No account mutation path
- No executable live order output by default
