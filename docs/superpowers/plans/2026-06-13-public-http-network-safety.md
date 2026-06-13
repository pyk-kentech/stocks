# Public HTTP Data Connector / Network Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicitly enabled, allowlisted, credential-free public CSV/JSON download connector.

**Architecture:** Pure safety validators and typed provider configs gate a transport-injected downloader. Public HTTP connectors dynamically join the existing connector/import pipeline only when explicitly configured.

**Tech Stack:** Python 3.11, Pydantic v2, urllib, JSON/YAML, argparse, pytest

---

### Task 1: Network Safety And Provider Config

- [x] Write failing URL, credential-header, sanitization, and config-load tests.
- [x] Implement safety validators and typed JSON/YAML config loading.
- [x] Run focused tests.

### Task 2: Download Client And Public HTTP Connector

- [x] Write failing disabled, blocked, redirect, max-bytes, file, and row-count tests.
- [x] Implement injected download abstraction and connector adapter.
- [x] Run focused tests.

### Task 3: Registry, Pipeline, And CLI

- [x] Write failing dynamic registry, validate-config, single connector, and import-integration tests.
- [x] Implement provider registration and CLI/pipeline options.
- [x] Run focused tests.

### Task 4: Documentation And Verification

- [x] Update README and WORK_SUMMARY.
- [x] Run full pytest, compileall, diff check, and required system-smoke.
- [x] Commit verified changes.
