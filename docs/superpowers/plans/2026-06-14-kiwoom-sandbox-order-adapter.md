# Kiwoom Sandbox Order Adapter Implementation Plan

**Goal:** Add an explicit MOCK-only sandbox BUY LIMIT order path behind existing gates.

**Architecture:** Extend ExecutionGate with explicit SANDBOX approval, then add separate sandbox models, strict manifest ORDER transport, adapter, service, redacted audit, and CLI. Tests inject fake transport only.

## Tasks

1. TDD `ExecutionMode.SANDBOX` and explicit sandbox gate approval while preserving PAPER and blocking LIVE.
2. TDD sandbox config/models and strict `kt10000`/`kt10003` ORDER transport policy.
3. TDD service validation, dry-run, approved-intent-only submit, duplicate rejection, cancel, and local status.
4. TDD append-only redacted SQLite run/request/receipt/status audit.
5. TDD separate sandbox CLI and safety source checks.
6. Update README/WORK_SUMMARY.
7. Run pytest, compileall, diff check, system-smoke, then commit without a tag.
