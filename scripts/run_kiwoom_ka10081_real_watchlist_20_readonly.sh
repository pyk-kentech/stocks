#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

RUN_ID="real_ka10081_20symbol_watchlist_$(date +%Y%m%d_%H%M%S)"
ROOT="local_data/manual_verification/${RUN_ID}"
STORE_ROOT="${ROOT}/store"
RAW_LAKE_ROOT="${ROOT}/raw_lake"
CREDENTIAL_REF="/home/yoonkeun/stocks/local_secrets/kiwoom_real_production_readonly_credential.ref"
TOKEN_STORE_ROOT="/home/yoonkeun/stocks/local_data/kiwoom_token_store"

if [ ! -d "$CREDENTIAL_REF" ]; then
  echo "Missing credential ref directory: $CREDENTIAL_REF" >&2
  exit 2
fi

mkdir -p "$STORE_ROOT" "$RAW_LAKE_ROOT"

for IDX in 1 2 3 4; do
  echo "===== REAL KA10081 WATCHLIST BATCH ${IDX}/4 ====="

  python3.11 -m stock_risk_mcp.cli \
    kiwoom-ka10081-capture-and-train-run \
    --kiwoom-environment REAL \
    --api-id KA10081 \
    --capture-profile DAILY_RESEARCH_PROFILE \
    --symbols-file examples/kiwoom_watchlist_20_sample.csv \
    --start-date 20250101 \
    --end-date 20260628 \
    --store-root "$STORE_ROOT" \
    --raw-lake-root "$RAW_LAKE_ROOT" \
    --credential-ref "$CREDENTIAL_REF" \
    --token-store-root "$TOKEN_STORE_ROOT" \
    --batch-size 5 \
    --batch-index "$IDX" \
    --max-symbols-per-run 5 \
    --max-request-count 10 \
    --max-continuation-pages 1 \
    --request-sleep-seconds 8 \
    --symbol-sleep-seconds 15 \
    --rate-limit-profile CONSERVATIVE \
    --stop-on-provider-limit \
    --allow-real-chart-capture \
    --acknowledge-readonly-only \
    --acknowledge-no-orders \
    --acknowledge-user-initiated \
    --acknowledge-rate-limit-and-capacity \
    --acknowledge-credential-redaction \
    --output-file "${ROOT}/batch_${IDX}_result.json"

  RC=$?
  echo "===== BATCH ${IDX} EXIT CODE: ${RC} ====="

  if [ "$RC" -ne 0 ]; then
    echo "Batch ${IDX} failed/stopped. Not continuing."
    exit "$RC"
  fi

  sleep 20
done

echo "ROOT=$ROOT"
echo -n "raw_lake count: "
find "$RAW_LAKE_ROOT" -type f -name 'ka10081-*-response.json' | wc -l

python3.11 - <<PY
import json
from pathlib import Path

p = Path("${ROOT}/batch_4_result.json")
d = json.loads(p.read_text())

for k in [
    "status",
    "watchlist_status",
    "completed_batches",
    "pending_batches",
    "watchlist_completion_ratio",
    "full_coverage_ratio",
    "provider_limit_hit",
    "provider_limit_despite_limiter",
    "leakage_audit_status",
    "batch_status",
]:
    print(f"{k}: {d.get(k)}")
PY
